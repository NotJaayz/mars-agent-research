"""Lectura de máscaras AI4Mars (codificación NAV) y construcción de máscaras binarias.

Todas las funciones son puras: reciben/retornan arrays de NumPy (o rutas para la
lectura) y no tienen efectos secundarios. Los umbrales y tamaños se pasan como
argumentos con defaults documentados, nunca hardcodeados dentro de la lógica.

Codificación NAV (ver ``src/config.py``):
    0 = soil, 1 = bedrock, 2 = sand, 3 = big rock, 255 = NULL (sin etiqueta).
"""
from __future__ import annotations

from pathlib import Path
from typing import Iterator

import numpy as np
from PIL import Image
from skimage.morphology import closing, opening

from . import config


# --- Lectura -------------------------------------------------------------------------
def read_mask(path: str | Path) -> np.ndarray:
    """Lee una máscara PNG de AI4Mars como array 2D ``uint8`` con códigos NAV.

    Las máscaras vienen en modo escala de grises (``L``); se fuerza ese modo por
    robustez. Cada valor es un código de clase (0,1,2,3) o 255 (sin etiqueta).
    """
    with Image.open(path) as im:
        return np.asarray(im.convert("L"), dtype=np.uint8)


# --- Máscaras binarias ---------------------------------------------------------------
def valid_mask(mask: np.ndarray) -> np.ndarray:
    """Bool 2D: ``True`` donde el píxel tiene etiqueta válida (distinto de 255).

    Son los píxeles que cuentan como "denominador" al calcular la cobertura: los
    enmascarados (rover, distancias > 30 m, sin acuerdo de anotadores) se excluyen.
    """
    return mask != config.NAV_NULL


def coverage_mask(mask: np.ndarray) -> np.ndarray:
    """Bool 2D: ``True`` en roca visible para cobertura (bedrock o big rock; {1,3})."""
    return np.isin(mask, config.COVERAGE_CLASSES)


def big_rock_mask(mask: np.ndarray) -> np.ndarray:
    """Bool 2D: ``True`` solo en big rock (clase 3). Entrada del conteo de rocas."""
    return mask == config.BIG_ROCK_CLASS


# --- Limpieza morfológica ------------------------------------------------------------
def clean_mask(
    binary: np.ndarray,
    open_size: int = 3,
    close_size: int = 3,
) -> np.ndarray:
    """Limpia una máscara binaria con apertura seguida de cierre (elementos cuadrados).

    - **Apertura** (erosión→dilatación) elimina manchas pequeñas y ruido aislado.
    - **Cierre** (dilatación→erosión) rellena huecos pequeños dentro de las manchas.

    Parameters
    ----------
    binary : np.ndarray
        Máscara binaria (bool o {0,1}).
    open_size : int, default 3
        Lado del cuadrado de la apertura, en píxeles. ``<= 1`` desactiva la apertura.
    close_size : int, default 3
        Lado del cuadrado del cierre, en píxeles. ``<= 1`` desactiva el cierre.

    Returns
    -------
    np.ndarray
        Máscara binaria booleana limpia, del mismo tamaño que la entrada.
    """
    out = np.asarray(binary, dtype=bool)
    if open_size and open_size > 1:
        out = opening(out, footprint=np.ones((open_size, open_size), dtype=bool))
    if close_size and close_size > 1:
        out = closing(out, footprint=np.ones((close_size, close_size), dtype=bool))
    return out


# --- Emparejamiento imagen ↔ máscara (subconjunto MSL NavCam) ------------------------
def mask_to_image_path(
    mask_path: str | Path,
    images_dir: str | Path = config.MSL_NCAM_IMAGES,
) -> Path | None:
    """Devuelve la ruta de la imagen ``.JPG`` que corresponde a una máscara, o ``None``.

    El emparejamiento es por nombre base. Algunas máscaras traen el sufijo ``_merged``
    que la imagen original no tiene, por lo que se prueba también sin él.
    """
    images_dir = Path(images_dir)
    stem = Path(mask_path).stem
    candidates = [stem]
    if stem.endswith("_merged"):
        candidates.append(stem[: -len("_merged")])
    for cand in candidates:
        for ext in (".JPG", ".jpg", ".png", ".PNG"):
            p = images_dir / f"{cand}{ext}"
            if p.exists():
                return p
    return None


def iter_pairs(
    labels_dir: str | Path = config.MSL_NCAM_LABELS_TRAIN,
    images_dir: str | Path = config.MSL_NCAM_IMAGES,
) -> Iterator[tuple[str, Path, Path]]:
    """Itera tripletas ``(image_id, image_path, mask_path)`` con imagen+máscara presentes.

    ``image_id`` es el nombre base de la máscara (sin extensión). Se omiten las
    máscaras sin imagen correspondiente.
    """
    labels_dir = Path(labels_dir)
    for mask_path in sorted(labels_dir.glob("*.png")):
        image_path = mask_to_image_path(mask_path, images_dir)
        if image_path is not None:
            yield mask_path.stem, image_path, mask_path
