"""Conteo híbrido: la máscara indica *dónde* hay roca, la imagen *cuántos* bloques.

Motivación (validación humana, §4.2.2): el conteo basado solo en la máscara subestima el
número de rocas en escenas densas. La causa no es algorítmica sino de granularidad de la
anotación: un único polígono trazado holgadamente puede cubrir un campo entero de rocas, y
la transformada de distancia no presenta entonces estrechamientos por donde cortar.

La información que falta está en la imagen. Dentro de la región anotada, los límites entre
bloques aparecen como crestas de gradiente —sombras y fracturas—, mientras que los
interiores de cada bloque son relativamente planos. Este módulo:

1. Calcula la magnitud del gradiente de la imagen suavizada, que actúa como relieve.
2. Sitúa semillas en los interiores planos mediante máximos de prominencia sobre el
   gradiente invertido, **restringidas a la región de la máscara**.
3. Inunda el gradiente desde esas semillas (división de aguas) dentro de la región.
4. Filtra las subregiones por área y forma, con los mismos criterios que el conteo
   basado únicamente en la máscara.

Sigue siendo procesamiento clásico: no entrena ningún modelo.

RESULTADO MEDIDO — no usar como sustituto del conteo basado en máscara
---------------------------------------------------------------------
Evaluado contra las 24 escenas con conteo humano (``outputs/validacion_manual``) y
calibrado por rejilla con validación cruzada dejando una fuera:

======================================  =======  ==========
método                                   kappa   ponderado
======================================  =======  ==========
conteo basado en máscara (``rock_count``)  0,28       0,40
híbrido, parámetros por defecto            0,26       0,38
híbrido, calibrado (h=0,008, área=0,002)   0,28       0,44
======================================  =======  ==========

La diferencia del híbrido calibrado frente al conteo basado en máscara es de
**+0,04 en kappa ponderado, con intervalo de confianza del 95 % de [-0,14, +0,23]**
(bootstrap, 4000 remuestreos). El intervalo contiene el cero: con n = 24 la mejora
**no es demostrable**. El híbrido gana en el 67 % de los remuestreos.

El comportamiento de las dos configuraciones conviene distinguirlo, porque explica por qué
la mejora es marginal:

- Con los **parámetros por defecto** el híbrido invierte el sesgo en lugar de eliminarlo.
  Corrige los subconteos de escenas densas —en una escena pasa de 6 a 81 bloques donde el
  observador vio más de diez— pero sobreestima en afloramientos continuos, donde el
  observador identificó de una a tres rocas y el híbrido cuenta decenas. Sobre las escenas
  de anotación apreciable pasa de 5 subconteos y 5 sobreconteos a 0 y 9 respectivamente.
- La **calibración** corrige ese exceso subiendo el área mínima cuatro veces, lo que
  suprime los bloques añadidos. El resultado vuelve a subcontar (9 por debajo frente a 4
  por encima), con un comportamiento próximo al del conteo basado en máscara. De ahí que
  el kappa apenas se mueva: la calibración deshace buena parte de lo que el híbrido aporta.

La causa es que el gradiente no distingue **el borde entre dos rocas** de **la textura
interna de una sola**: una losa estratificada produce crestas de gradiente en cada estrato.
Es la misma limitación observada en el modelo fundacional de segmentación, que subdivide
una roca según su textura.

Este módulo se conserva como exploración documentada y como base para la línea futura de
trabajo, no como mejora del indicador. Para levantar el techo haría falta antes una muestra
de conteo humano sustancialmente mayor, que permita distinguir mejoras de este tamaño.

El conteo se realiza dentro de la región de *roca grande*, que es la misma zona sobre la
que se recogió el conteo humano, de modo que ambos responden a la misma pregunta.
"""
from __future__ import annotations

from typing import Any

import numpy as np
from skimage.filters import gaussian, sobel
from skimage.measure import label, regionprops
from skimage.morphology import h_maxima
from skimage.segmentation import watershed

from . import mask_utils as mu
from .rock_count import _aspect_ratio

# Parámetros por defecto. Los dos primeros son los propios del enfoque híbrido; los dos
# últimos se heredan del conteo basado en máscara para que ambos filtren igual.
DEFAULT_PARAMS: dict[str, Any] = {
    "img_sigma": 2.0,        # suavizado de la imagen antes del gradiente (px)
    "seed_h": 0.004,         # prominencia mínima de una semilla sobre el gradiente invertido
    "seed_sigma": 1.0,       # suavizado del gradiente invertido antes de buscar semillas
    "min_area_frac": 0.0005, # área mínima de una roca (fracción del área de la imagen)
    "max_aspect_ratio": 5.0, # relación de aspecto máxima de la caja envolvente
}


def compute_stages(
    image_gray: np.ndarray,
    region: np.ndarray,
    params: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Etapas intermedias del conteo híbrido, para figuras y depuración.

    Parameters
    ----------
    image_gray : np.ndarray
        Imagen en escala de grises. Se normaliza internamente a ``[0, 1]``.
    region : np.ndarray
        Máscara booleana que delimita dónde contar (típicamente la región de roca grande).
    params : dict, optional
        Sobrescribe :data:`DEFAULT_PARAMS`.

    Returns
    -------
    dict con ``params``, ``gradient``, ``seeds``, ``labels_ws``, ``kept_ids``, ``areas``
    y ``solidities``.
    """
    p = {**DEFAULT_PARAMS, **(params or {})}
    region = region.astype(bool)

    vacio: dict[str, Any] = {
        "params": p,
        "gradient": np.zeros(region.shape, dtype=float),
        "seeds": np.zeros(region.shape, dtype=bool),
        "labels_ws": np.zeros(region.shape, dtype=np.int32),
        "kept_ids": [], "areas": [], "solidities": [],
    }
    if not region.any():
        return vacio

    img = image_gray.astype(float)
    rango = float(img.max() - img.min())
    img = (img - img.min()) / rango if rango > 0 else np.zeros_like(img)

    # El gradiente actúa como relieve: alto en los bordes entre bloques, bajo en su interior.
    grad = sobel(gaussian(img, sigma=p["img_sigma"]))

    # Semillas en los interiores planos: máximos de prominencia del gradiente invertido.
    interior = gaussian(-grad, sigma=p["seed_sigma"])
    seeds = h_maxima(interior, p["seed_h"]).astype(bool) & region
    if not seeds.any():
        # Sin semillas la región no se subdivide; se trata como un único bloque.
        markers = label(region)
    else:
        markers = label(seeds)

    labels_ws = watershed(grad, markers, mask=region)

    min_area = p["min_area_frac"] * image_gray.size
    kept_ids, areas, solidities = [], [], []
    for reg in regionprops(labels_ws):
        if reg.area < min_area:
            continue
        if _aspect_ratio(reg) > p["max_aspect_ratio"]:
            continue
        kept_ids.append(reg.label)
        areas.append(int(reg.area))
        solidities.append(float(reg.solidity))

    vacio.update(gradient=grad, seeds=seeds, labels_ws=labels_ws,
                 kept_ids=kept_ids, areas=areas, solidities=solidities)
    return vacio


def count_rocks(
    image_gray: np.ndarray,
    region: np.ndarray,
    params: dict[str, Any] | None = None,
) -> tuple[int, dict[str, Any]]:
    """Cuenta rocas dentro de ``region`` usando la estructura de ``image_gray``.

    Returns
    -------
    n_rocks : int
    details : dict con ``n_seeds``, ``areas``, ``solidities`` y ``params``.
    """
    s = compute_stages(image_gray, region, params)
    return len(s["kept_ids"]), {
        "n_seeds": int(label(s["seeds"]).max()) if s["seeds"].any() else 0,
        "areas": s["areas"], "solidities": s["solidities"], "params": s["params"],
    }


def count_from_paths(
    image_path, mask_path, params: dict[str, Any] | None = None,
) -> tuple[int, dict[str, Any]]:
    """Variante de conveniencia que lee la imagen y la máscara de disco."""
    from PIL import Image

    mask = mu.read_mask(mask_path)
    with Image.open(image_path) as im:
        img = np.asarray(im.convert("L"))
    return count_rocks(img, mu.big_rock_mask(mask), params)
