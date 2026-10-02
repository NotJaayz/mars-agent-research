"""Pipeline principal: procesa un par (imagen, máscara) y produce una fila de resultados.

Orquesta los módulos ``coverage`` (E1) y ``rock_count`` (E2) y deriva metadatos e
indicadores de calidad. La función central es :func:`process_image`. Para procesar
todo el subconjunto MSL NavCam de una vez, :func:`process_subset` devuelve un
``pandas.DataFrame`` listo para guardar como ``outputs/results.csv``.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Iterable

import re

from . import config
from . import coverage as cov
from . import features as ft
from . import mask_utils as mu
from . import rock_count as rc

# Parámetros por defecto del pipeline (reutiliza los del conteo de rocas).
DEFAULT_PARAMS: dict[str, Any] = dict(rc.DEFAULT_PARAMS)

_EYE_RE = re.compile(r"^N([LR])([AB])")  # NLA/NLB/NRA/NRB -> ojo L/R, cámara A/B
# Reloj de nave (SCLK): segundos desde la época del reloj de a bordo, codificados en el
# identificador del producto PDS (p. ej. NLB_559866561EDR_...). Crece monótonamente con el
# tiempo de adquisición, por lo que ordena las imágenes en el tiempo. NO equivale a distancia
# recorrida: el rover toma varias imágenes desde una misma posición.
_SCLK_RE = re.compile(r"^N[LR][AB]_(\d+)")

# Una escena con más de esta fracción de píxeles sin etiqueta se considera casi vacía.
UMBRAL_MOSTLY_NULL = 0.95

# Columnas del CSV de resultados (§8.8 de la tesis).
# Grupos: identificación · cobertura (E1) · composición del terreno ·
#         conteo y geometría de rocas (E2) · calidad · elegibilidad.
RESULT_COLUMNS = [
    "image_id", "rover", "camera", "eye", "sclk",
    "rock_coverage_pct", "coverage_total_pct", "frac_valid",
    "pct_soil", "pct_bedrock", "pct_sand", "pct_bigrock",
    "dominant_class", "scene_type",
    "n_bigrock", "n_rocks", "n_raw_components",
    "largest_rock_pct", "mean_rock_area_px", "n_small", "n_medium", "n_large",
    "mean_solidity", "quality_flag",
    "has_bigrock", "is_mostly_null", "is_e1_eligible", "is_e2_eligible",
]


def eligibility(n_valid: int, frac_null: float, n_bigrock: int) -> dict[str, bool]:
    """Condiciones de elegibilidad, independientes entre sí, de una escena.

    ``n_rocks`` se calcula para todas las escenas, pero solo las elegibles para E2 entran
    en los resúmenes oficiales del conteo (ver :mod:`src.poblaciones`).

    - ``has_bigrock``    : la máscara tiene algún píxel de roca grande.
    - ``is_mostly_null`` : más del 95 % de la imagen sin etiqueta (incluye las vacías).
    - ``is_e1_eligible`` : hay al menos un píxel etiquetado, de modo que la cobertura existe.
    - ``is_e2_eligible`` : elegible para E1, con roca grande y no casi vacía.
    """
    has_big = n_bigrock > 0
    mostly_null = frac_null > UMBRAL_MOSTLY_NULL
    e1 = n_valid > 0
    return {"has_bigrock": has_big, "is_mostly_null": mostly_null,
            "is_e1_eligible": e1, "is_e2_eligible": e1 and has_big and not mostly_null}


def _quality_flag(details: dict[str, Any], n_bigrock: int) -> str:
    """Bandera de calidad por imagen, con prioridad de la condición más severa.

    - ``empty``        : sin píxeles etiquetados (todo NULL).
    - ``mostly_null``  : > 95% de la imagen sin etiqueta.
    - ``no_rock``      : con etiquetas, pero 0 píxeles de roca visible.
    - ``no_bigrock``   : hay roca visible (bedrock) pero ninguna big rock que contar.
    - ``ok``           : apta para cobertura y conteo.
    """
    if details["n_valid"] == 0:
        return "empty"
    if details["frac_null"] > UMBRAL_MOSTLY_NULL:
        return "mostly_null"
    if details["n_rock"] == 0:
        return "no_rock"
    if n_bigrock == 0:
        return "no_bigrock"
    return "ok"


def process_image(
    image_path: str | Path,
    mask_path: str | Path,
    params: dict[str, Any] | None = None,
    rover: str = config.ROVER,
    camera: str = config.CAMERA,
) -> dict[str, Any]:
    """Procesa un par (imagen, máscara) y devuelve una fila de resultados como dict.

    ``image_path`` no se lee (el análisis usa solo la máscara), pero se recibe para
    fijar el ``image_id`` y mantener una firma estable.

    Returns
    -------
    dict con las claves de :data:`RESULT_COLUMNS`.
    """
    p = {**DEFAULT_PARAMS, **(params or {})}
    image_id = Path(mask_path).stem

    mask = mu.read_mask(mask_path)
    coverage_pct, details = cov.rock_coverage(mask)
    comp = ft.class_composition(mask)

    big_rock = mu.big_rock_mask(mask)
    stages = rc.compute_stages(big_rock, p)
    n_rocks = len(stages["kept_ids"])
    geom = ft.rock_geometry(stages["areas"], stages["solidities"],
                            mask.size, details["n_valid"])

    m = _EYE_RE.match(image_id)
    eye = m.group(1) if m else None  # L / R (par estéreo NavCam)
    ms = _SCLK_RE.match(image_id)
    sclk = int(ms.group(1)) if ms else None

    def _r(x, nd=4):
        return round(x, nd) if x == x else None  # None si es NaN

    return {
        "image_id": image_id,
        "rover": rover,
        "camera": camera,
        "eye": eye,
        "sclk": sclk,
        "rock_coverage_pct": _r(coverage_pct),
        "coverage_total_pct": _r(details["coverage_total_pct"]),
        "frac_valid": _r(details["frac_valid"]),
        "pct_soil": comp["pct_soil"],
        "pct_bedrock": comp["pct_bedrock"],
        "pct_sand": comp["pct_sand"],
        "pct_bigrock": comp["pct_bigrock"],
        "dominant_class": comp["dominant_class"],
        "scene_type": comp["scene_type"],
        "n_bigrock": details["n_bigrock"],
        "n_rocks": n_rocks,
        "n_raw_components": stages["n_raw_components"],
        "largest_rock_pct": geom["largest_rock_pct"],
        "mean_rock_area_px": geom["mean_rock_area_px"],
        "n_small": geom["n_small"],
        "n_medium": geom["n_medium"],
        "n_large": geom["n_large"],
        "mean_solidity": geom["mean_solidity"],
        "quality_flag": _quality_flag(details, details["n_bigrock"]),
        **eligibility(details["n_valid"], details["frac_null"], details["n_bigrock"]),
    }


def process_subset(
    labels_dir: str | Path = config.MSL_NCAM_LABELS_TRAIN,
    images_dir: str | Path = config.MSL_NCAM_IMAGES,
    params: dict[str, Any] | None = None,
    limit: int | None = None,
    progress: bool = True,
    workers: int = 1,
):
    """Procesa todo el subconjunto y devuelve un ``pandas.DataFrame`` de resultados.

    Parameters
    ----------
    limit : int, optional
        Si se indica, procesa solo las primeras ``limit`` parejas (útil en pruebas).
    progress : bool, default True
        Muestra barra de progreso con tqdm si está disponible.
    workers : int, default 1
        Procesos en paralelo. El resultado es idéntico al secuencial y en el mismo orden,
        porque cada imagen se procesa de forma independiente.
    """
    import pandas as pd

    pairs: Iterable = mu.iter_pairs(labels_dir, images_dir)
    pairs = list(pairs)
    if limit is not None:
        pairs = pairs[:limit]

    if workers > 1:
        from concurrent.futures import ProcessPoolExecutor
        from functools import partial
        with ProcessPoolExecutor(max_workers=workers) as ex:
            rows = list(ex.map(partial(_process_pair, params=params), pairs, chunksize=64))
        return pd.DataFrame(rows, columns=RESULT_COLUMNS)

    if progress:
        try:
            from tqdm import tqdm
            pairs = tqdm(pairs, desc="Procesando MSL NavCam")
        except ImportError:
            pass

    rows = [
        process_image(image_path, mask_path, params)
        for _image_id, image_path, mask_path in pairs
    ]
    return pd.DataFrame(rows, columns=RESULT_COLUMNS)


def _process_pair(pair, params=None):
    """Adaptador para la ejecución en paralelo."""
    _image_id, image_path, mask_path = pair
    return process_image(image_path, mask_path, params)
