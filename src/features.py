"""Características adicionales por imagen derivadas de la máscara AI4Mars.

Dos grupos de descriptores, todos calculados sobre la máscara (funciones puras):

1. Composición del terreno — fracción de cada clase (soil, bedrock, sand, big rock)
   sobre los píxeles válidos, más la clase dominante y una tipología de escena.
2. Geometría de las rocas — tamaño de la roca mayor, tamaño medio, conteo por
   clases de tamaño (pequeña/mediana/grande) y solidez media (forma).

Estos descriptores enriquecen el análisis descriptivo (E3) y la discusión (E5),
en particular la lectura tipo distribución tamaño–frecuencia de rocas.
"""
from __future__ import annotations

from typing import Any, Sequence

import numpy as np

from . import config

# Umbrales de clases de tamaño de roca, como fracción del área de la imagen.
# small:  [min_area, 0.5%)   medium: [0.5%, 2%)   large: >= 2%
SIZE_SMALL_MAX = 0.005
SIZE_MEDIUM_MAX = 0.02


def class_composition(mask: np.ndarray) -> dict[str, Any]:
    """Fracción de cada clase NAV sobre píxeles válidos + clase dominante + tipo de escena."""
    valid = mask != config.NAV_NULL
    n_valid = int(valid.sum())
    counts = {
        "soil": int((mask == config.NAV_SOIL).sum()),
        "bedrock": int((mask == config.NAV_BEDROCK).sum()),
        "sand": int((mask == config.NAV_SAND).sum()),
        "bigrock": int((mask == config.NAV_BIG_ROCK).sum()),
    }
    if n_valid == 0:
        pct = {k: float("nan") for k in counts}
        return {"pct_soil": pct["soil"], "pct_bedrock": pct["bedrock"],
                "pct_sand": pct["sand"], "pct_bigrock": pct["bigrock"],
                "dominant_class": None, "scene_type": "sin_etiqueta"}

    pct = {k: 100.0 * v / n_valid for k, v in counts.items()}
    dominant = max(counts, key=counts.get)
    rock_share = pct["bedrock"] + pct["bigrock"]

    # Tipología de escena a partir de la composición.
    if rock_share >= 66:
        scene = "rocoso"
    elif pct["sand"] >= 50:
        scene = "arenoso"
    elif pct["soil"] >= 50:
        scene = "suelo"
    else:
        scene = "mixto"

    return {
        "pct_soil": round(pct["soil"], 2),
        "pct_bedrock": round(pct["bedrock"], 2),
        "pct_sand": round(pct["sand"], 2),
        "pct_bigrock": round(pct["bigrock"], 2),
        "dominant_class": dominant,
        "scene_type": scene,
    }


def rock_geometry(
    areas: Sequence[int],
    solidities: Sequence[float],
    image_area: int,
    n_valid: int,
) -> dict[str, Any]:
    """Descriptores de tamaño y forma de las rocas aceptadas por el conteo.

    Parameters
    ----------
    areas : lista de áreas (px) de las rocas que pasaron los filtros.
    solidities : solidez (área / área convexa) de esas mismas rocas.
    image_area : nº total de píxeles de la imagen (para clases de tamaño).
    n_valid : nº de píxeles válidos (para expresar tamaños como % de escena).
    """
    if not areas:
        return {"largest_rock_pct": 0.0, "mean_rock_area_px": 0.0,
                "n_small": 0, "n_medium": 0, "n_large": 0, "mean_solidity": None}

    a = np.asarray(areas, dtype=float)
    fracs = a / image_area  # tamaño como fracción de la imagen
    largest_pct = 100.0 * a.max() / n_valid if n_valid else float("nan")

    n_small = int((fracs < SIZE_SMALL_MAX).sum())
    n_medium = int(((fracs >= SIZE_SMALL_MAX) & (fracs < SIZE_MEDIUM_MAX)).sum())
    n_large = int((fracs >= SIZE_MEDIUM_MAX).sum())

    return {
        "largest_rock_pct": round(largest_pct, 4),
        "mean_rock_area_px": round(float(a.mean()), 1),
        "n_small": n_small,
        "n_medium": n_medium,
        "n_large": n_large,
        "mean_solidity": round(float(np.mean(solidities)), 3) if len(solidities) else None,
    }
