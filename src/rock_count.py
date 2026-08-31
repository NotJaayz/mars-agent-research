"""Conteo aproximado de rocas individuales (objetivo E2).

Flujo (sobre la máscara binaria de *big rock*, clase 3):

1. Limpieza morfológica (apertura + cierre).
2. Componentes conectadas (8-vecinos) → ``n_raw_components``.
3. Transformada de distancia euclidiana (opcionalmente suavizada con gaussiano).
4. Máximos locales de la distancia → marcadores (semillas).
5. *Watershed* sobre ``-distancia`` guiado por los marcadores → separa rocas pegadas.
6. Filtrado de subcomponentes por **área mínima** y **relación de aspecto**.
7. Conteo de las subcomponentes que pasan los filtros → ``n_rocks``.

Todos los umbrales se pasan por ``params`` (dict) con defaults documentados en
``DEFAULT_PARAMS``; nada queda hardcodeado dentro de la lógica. Para reducir la
sobresegmentación, subir ``peak_min_distance`` o ``distance_sigma``.
"""
from __future__ import annotations

from typing import Any

import numpy as np
from scipy import ndimage as ndi
from skimage.feature import peak_local_max
from skimage.filters import gaussian
from skimage.measure import label, regionprops
from skimage.segmentation import watershed

from . import mask_utils as mu


# Parámetros por defecto del conteo. Documentados; modificables por imagen/escena.
# Calibrados visualmente sobre 6 escenas MSL NavCam variadas (ver outputs/figures/calibracion):
# peak_min_distance=15 + distance_sigma=3.0 es el compromiso que preserva las separaciones
# reales de cúmulos de rocas y a la vez recorta los máximos espurios que sobresegmentaban los
# bloques continuos grandes (con los valores previos 5/1.0 una sola losa generaba hasta 142
# máximos). Para reducir aún más la sobresegmentación, subir ambos; para separar rocas más
# pequeñas y pegadas, bajarlos.
DEFAULT_PARAMS: dict[str, Any] = {
    "open_size": 3,            # apertura morfológica (px); <=1 desactiva
    "close_size": 3,           # cierre morfológico (px); <=1 desactiva
    "min_area_frac": 0.0005,   # área mínima de una roca = 0.05% del área de la imagen
    "max_aspect_ratio": 5.0,   # relación de aspecto máxima de la caja envolvente
    "distance_sigma": 3.0,     # suavizado gaussiano de la transformada de distancia; 0 desactiva
    "peak_min_distance": 15,   # separación mínima entre máximos locales (px)
    "connectivity": 2,         # 2 = 8-vecinos para componentes conectadas
}


def _aspect_ratio(region) -> float:
    """Relación de aspecto (lado mayor / lado menor) de la caja envolvente de una región."""
    minr, minc, maxr, maxc = region.bbox
    h, w = maxr - minr, maxc - minc
    if h == 0 or w == 0:
        return float("inf")
    return max(h, w) / min(h, w)


def compute_stages(
    big_rock_binary: np.ndarray,
    params: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Calcula todas las etapas intermedias del conteo (para figuras y depuración).

    Fuente única de la lógica de segmentación; :func:`count_rocks` la reutiliza.

    Returns
    -------
    dict con: ``params``, ``clean`` (binaria limpia), ``n_raw_components``,
    ``distance`` (transformada de distancia, posiblemente suavizada),
    ``coords`` (Nx2 de los máximos locales), ``labels_ws`` (etiquetas del watershed),
    ``kept_ids`` (labels que pasan los filtros) y ``areas`` (sus áreas).
    """
    p = {**DEFAULT_PARAMS, **(params or {})}
    image_area = int(big_rock_binary.size)
    min_area = p["min_area_frac"] * image_area

    clean = mu.clean_mask(big_rock_binary, p["open_size"], p["close_size"])
    n_raw_components = int(label(clean, connectivity=p["connectivity"]).max())

    stages: dict[str, Any] = {
        "params": p, "clean": clean, "n_raw_components": n_raw_components,
        "distance": np.zeros_like(clean, dtype=float),
        "coords": np.empty((0, 2), dtype=int),
        "labels_ws": np.zeros_like(clean, dtype=np.int32),
        "kept_ids": [], "areas": [], "solidities": [],
    }
    if not clean.any():
        return stages

    distance = ndi.distance_transform_edt(clean)
    if p["distance_sigma"] and p["distance_sigma"] > 0:
        distance = gaussian(distance, sigma=p["distance_sigma"])

    coords = peak_local_max(
        distance, min_distance=p["peak_min_distance"], labels=clean, exclude_border=False,
    )
    if len(coords) == 0:
        markers = label(clean, connectivity=p["connectivity"])
    else:
        mask_peaks = np.zeros(distance.shape, dtype=bool)
        mask_peaks[tuple(coords.T)] = True
        markers = label(mask_peaks)

    labels_ws = watershed(-distance, markers, mask=clean)

    kept_ids, areas, solidities = [], [], []
    for region in regionprops(labels_ws):
        if region.area < min_area:
            continue
        if _aspect_ratio(region) > p["max_aspect_ratio"]:
            continue
        kept_ids.append(region.label)
        areas.append(int(region.area))
        solidities.append(float(region.solidity))

    stages.update(distance=distance, coords=coords, labels_ws=labels_ws,
                  kept_ids=kept_ids, areas=areas, solidities=solidities)
    return stages


def count_rocks(
    big_rock_binary: np.ndarray,
    params: dict[str, Any] | None = None,
) -> tuple[int, int, np.ndarray, dict[str, Any]]:
    """Cuenta rocas individuales en una máscara binaria de *big rock*.

    Parameters
    ----------
    big_rock_binary : np.ndarray
        Máscara binaria (bool o {0,1}) de la clase big rock.
    params : dict, optional
        Sobrescribe ``DEFAULT_PARAMS`` (solo las claves dadas).

    Returns
    -------
    n_rocks : int
        Número de rocas tras watershed y filtrado de tamaño/forma.
    n_raw_components : int
        Número de componentes conectadas tras limpieza, antes del watershed.
    labels_ws : np.ndarray
        Imagen etiquetada (int) del resultado del watershed (0 = fondo). Útil para figuras.
    details : dict
        ``n_seeds`` (marcadores), ``areas`` (de las rocas aceptadas), ``params`` usados.
    """
    s = compute_stages(big_rock_binary, params)
    n_rocks = len(s["kept_ids"])
    details = {"n_seeds": len(s["coords"]), "areas": s["areas"], "params": s["params"]}
    return n_rocks, s["n_raw_components"], s["labels_ws"], details
