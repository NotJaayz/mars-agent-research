"""Pipeline principal: procesa un par (imagen, máscara) y produce una fila de resultados.

Orquesta los módulos ``coverage`` (E1) y ``rock_count`` (E2) y deriva metadatos e
indicadores de calidad. La función central es :func:`process_image`. Para procesar
todo el subconjunto MSL NavCam de una vez, :func:`process_subset` devuelve un
``pandas.DataFrame`` listo para guardar como ``outputs/results.csv``.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Iterable

from . import config
from . import coverage as cov
from . import mask_utils as mu
from . import rock_count as rc

# Parámetros por defecto del pipeline (reutiliza los del conteo de rocas).
DEFAULT_PARAMS: dict[str, Any] = dict(rc.DEFAULT_PARAMS)

# Columnas del CSV de resultados (ver CLAUDE.md / §8.8 de la tesis).
RESULT_COLUMNS = [
    "image_id", "rover", "camera", "sol",
    "rock_coverage_pct", "n_rocks", "n_raw_components", "quality_flag",
]


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
    if details["frac_null"] > 0.95:
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
    sol: int | None = None,
) -> dict[str, Any]:
    """Procesa un par (imagen, máscara) y devuelve una fila de resultados como dict.

    ``image_path`` no se lee (el análisis usa solo la máscara), pero se recibe para
    fijar el ``image_id`` y mantener la firma documentada en CLAUDE.md.

    Returns
    -------
    dict con las claves de :data:`RESULT_COLUMNS`.
    """
    p = {**DEFAULT_PARAMS, **(params or {})}
    image_id = Path(mask_path).stem

    mask = mu.read_mask(mask_path)
    coverage_pct, details = cov.rock_coverage(mask)

    big_rock = mu.big_rock_mask(mask)
    n_rocks, n_raw_components, _, _ = rc.count_rocks(big_rock, p)

    return {
        "image_id": image_id,
        "rover": rover,
        "camera": camera,
        "sol": sol,
        "rock_coverage_pct": round(coverage_pct, 4) if coverage_pct == coverage_pct else None,
        "n_rocks": n_rocks,
        "n_raw_components": n_raw_components,
        "quality_flag": _quality_flag(details, details["n_bigrock"]),
    }


def process_subset(
    labels_dir: str | Path = config.MSL_NCAM_LABELS_TRAIN,
    images_dir: str | Path = config.MSL_NCAM_IMAGES,
    params: dict[str, Any] | None = None,
    limit: int | None = None,
    progress: bool = True,
):
    """Procesa todo el subconjunto y devuelve un ``pandas.DataFrame`` de resultados.

    Parameters
    ----------
    limit : int, optional
        Si se indica, procesa solo las primeras ``limit`` parejas (útil en pruebas).
    progress : bool, default True
        Muestra barra de progreso con tqdm si está disponible.
    """
    import pandas as pd

    pairs: Iterable = mu.iter_pairs(labels_dir, images_dir)
    pairs = list(pairs)
    if limit is not None:
        pairs = pairs[:limit]

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
