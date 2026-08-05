"""Comparación de conteo de rocas: watershed (clásico) vs. Segment Anything (FastSAM).

FastSAM segmenta la imagen de forma *class-agnostic* (todo objeto/región visible).
Para obtener un conteo de "rocas" comparable con el watershed —que opera sobre la
máscara de big rock— nos quedamos con las máscaras de instancia de FastSAM que caen
mayoritariamente dentro de la región etiquetada como big rock (clase 3) y superan un
área mínima.

Requiere ``ultralytics`` (``pip install ultralytics``) y sus pesos ``FastSAM-s.pt``
(se descargan automáticamente la primera vez). Corre en Apple Silicon con ``device="mps"``.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Sequence

import numpy as np

from . import config


def region_from_classes(
    mask: np.ndarray,
    classes: Sequence[int] = (config.NAV_BIG_ROCK,),
) -> np.ndarray:
    """Construye una región de interés (ROI) booleana a partir de clases NAV.

    Ejemplos:
        region_from_classes(m)                      # solo big rock (clase 3)
        region_from_classes(m, (1, 3))              # bedrock + big rock (roca expuesta)
    """
    return np.isin(mask, tuple(classes))


def sam_instance_masks(
    image_path: str | Path,
    model: Any,
    device: str = "mps",
    imgsz: int = 1024,
    conf: float = 0.4,
    iou: float = 0.9,
) -> list[np.ndarray]:
    """Corre FastSAM sobre una imagen y devuelve una lista de máscaras booleanas (H, W).

    ``retina_masks=True`` devuelve las máscaras a la resolución original de la imagen.
    """
    r = model(str(image_path), device=device, retina_masks=True,
              imgsz=imgsz, conf=conf, iou=iou, verbose=False)[0]
    if r.masks is None:
        return []
    return list(r.masks.data.cpu().numpy().astype(bool))


def count_in_region(
    masks: list[np.ndarray],
    region: np.ndarray,
    min_area_frac: float = 0.0005,
    overlap_thresh: float = 0.5,
) -> tuple[int, list[int]]:
    """Cuenta las máscaras de instancia que caen mayoritariamente dentro de ``region``.

    Parameters
    ----------
    masks : lista de máscaras booleanas (H, W) de FastSAM.
    region : máscara booleana (H, W) de la zona válida (p. ej. big rock).
    min_area_frac : área mínima de una instancia como fracción de la imagen.
    overlap_thresh : fracción mínima de la máscara SAM que debe caer dentro de ``region``.

    Returns
    -------
    (n, areas) : número de instancias aceptadas y sus áreas en píxeles.
    """
    min_area = min_area_frac * region.size
    areas: list[int] = []
    for m in masks:
        if m.shape != region.shape:
            continue  # se asume misma resolución (retina_masks=True)
        a = int(m.sum())
        if a < min_area:
            continue
        inter = int(np.logical_and(m, region).sum())
        if inter and inter / a >= overlap_thresh:
            areas.append(a)
    return len(areas), areas


def load_fastsam(weights: str = "FastSAM-s.pt") -> Any:
    """Carga el modelo FastSAM (descarga pesos si es necesario)."""
    from ultralytics import FastSAM
    return FastSAM(weights)
