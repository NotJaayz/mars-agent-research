"""Cálculo de la cobertura de roca visible por imagen (objetivo E1).

Cobertura (%) = píxeles de roca visible / píxeles válidos × 100,
donde "roca visible" = bedrock + big rock ({1,3}) y "válidos" = etiqueta ≠ 255.

Nota de diseño: por defecto la cobertura se calcula sobre las etiquetas crudas
(``clean=False``), para que el indicador refleje fielmente la anotación humana. La
limpieza morfológica está pensada sobre todo para la máscara de conteo (watershed);
su efecto sobre la cobertura es marginal. Se deja como parámetro para poder comparar.
"""
from __future__ import annotations

from typing import Any

import numpy as np

from . import mask_utils as mu


def rock_coverage(
    mask: np.ndarray,
    clean: bool = False,
    open_size: int = 3,
    close_size: int = 3,
) -> tuple[float, dict[str, Any]]:
    """Calcula la cobertura de roca visible de una máscara AI4Mars (codificación NAV).

    Parameters
    ----------
    mask : np.ndarray
        Máscara 2D con códigos NAV (0 soil, 1 bedrock, 2 sand, 3 big rock, 255 null).
    clean : bool, default False
        Si ``True``, aplica limpieza morfológica a la máscara de roca antes de contar
        (restringida a la región válida). Por defecto se cuenta sobre etiquetas crudas.
    open_size, close_size : int, default 3
        Tamaños de apertura/cierre si ``clean=True`` (ver ``mask_utils.clean_mask``).

    Returns
    -------
    coverage_pct : float
        Porcentaje de cobertura de roca visible. ``nan`` si no hay píxeles válidos.
    details : dict
        Conteos auxiliares: ``n_valid``, ``n_rock``, ``n_bedrock``, ``n_bigrock``,
        ``n_total``, ``frac_null`` (proporción de píxeles sin etiqueta en la imagen).
    """
    valid = mu.valid_mask(mask)
    n_total = int(mask.size)
    n_valid = int(valid.sum())

    n_bedrock = int((mask == mu.config.NAV_BEDROCK).sum())
    n_bigrock = int((mask == mu.config.NAV_BIG_ROCK).sum())

    cov = mu.coverage_mask(mask)
    if clean:
        cov = mu.clean_mask(cov, open_size, close_size) & valid
    n_rock = int(cov.sum())

    coverage_pct = float("nan") if n_valid == 0 else 100.0 * n_rock / n_valid
    coverage_total_pct = float("nan") if n_total == 0 else 100.0 * n_rock / n_total

    details = {
        "n_total": n_total,
        "n_valid": n_valid,
        "n_rock": n_rock,
        "n_bedrock": n_bedrock,
        "n_bigrock": n_bigrock,
        "frac_valid": n_valid / n_total if n_total else float("nan"),
        "frac_null": 1.0 - n_valid / n_total if n_total else float("nan"),
        "coverage_total_pct": coverage_total_pct,
    }
    return coverage_pct, details
