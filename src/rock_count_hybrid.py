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

RESULTADO MEDIDO (60 escenas con conteo humano)
----------------------------------------------
Evaluado contra ``outputs/validacion_manual_v2``, con seis bandas y muestreo estratificado
por área de la región. Configuración fija ``seed_h=0,008``, ``min_area_frac=0,0005``:

====================================  =========  =======  ==========
método                                 acuerdo    kappa   ponderado
====================================  =========  =======  ==========
conteo basado en máscara (E2)             50 %     0,13       0,11
híbrido                                   45 %     0,21       0,21
====================================  =========  =======  ==========

**Lo que sí queda demostrado.** El híbrido corrige dos defectos estructurales de E2, y
ambos se leen directamente en las distribuciones, sin depender de ningún estadístico:

- *Elimina el techo.* E2 no supera las nueve rocas en ninguna de las 60 escenas, de modo
  que las bandas ``10-24``, ``25-49`` y ``50+`` quedan vacías aunque el observador situó
  doce escenas en ellas. El híbrido las alcanza (máximo 127 rocas).
- *Elimina el sesgo sistemático.* E2 queda por debajo del observador en 28 escenas y por
  encima en 2. El híbrido reparte 16 por debajo y 17 por encima.
- *Reproduce la forma de la distribución.* E2 acumula 51 de 60 escenas en la banda
  ``1-3``, donde el observador situó 27; el híbrido sitúa 26.

**Lo que NO queda demostrado.** Que el acuerdo con el juicio humano sea mejor. La
diferencia en kappa ponderado es de **+0,10 con intervalo de confianza del 95 % de
[-0,12, +0,31]** (bootstrap, 4000 remuestreos); el intervalo contiene el cero. El híbrido
gana en el 81 % de los remuestreos, frente al 67 % que daba la muestra piloto de 24
escenas, pero la muestra sigue siendo insuficiente para concluir. Nótese además que el
acuerdo *exacto* del híbrido es menor (45 % frente a 50 %): E2 acierta más veces por
concentrarse en la banda más poblada, que es justamente lo que el kappa penaliza.

La selección de parámetros es estable en lo que importa: las dos combinaciones que se
reparten los pliegues de la validación cruzada dan ambas un kappa ponderado de 0,21
aplicadas fijas a las 60 escenas. El valor de *leave-one-out* que reporta
``scripts/eval_hybrid.py`` (0,06) mide el desempeño de un procedimiento que **reelige**
parámetros en cada pliegue, que es inestable; no el de una configuración fija, que es como
se usaría.

**Límite de fondo.** Ninguna de las dos variantes puede contar lo que la anotación no
delimita. En 36 de las 60 escenas la clase roca grande cubre menos del 20 % de la roca
etiquetada (mediana 9,1 %), de modo que ambos métodos cuentan dentro de una fracción
pequeña y arbitraria de la roca visible.

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
