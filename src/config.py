"""Rutas y constantes del dataset AI4Mars (subconjunto del proyecto: MSL NavCam).

El dataset (~16 GB, v0.6) NO se versiona y vive fuera del repositorio. La raíz se
configura con la variable de entorno ``AI4MARS_ROOT``; si no está definida se usa la
ubicación por defecto en el escritorio del autor.

Codificación de clases: esquema **NAV** de AI4Mars (ver ``label_keys.json`` / ``info.md``
del dataset). NO confundir con la codificación que asumía la propuesta original.
"""
from __future__ import annotations

import os
from pathlib import Path

# --- Raíz del dataset (configurable) -------------------------------------------------
# Orden de preferencia: 1) variable de entorno AI4MARS_ROOT; 2) copia dentro del repo
# (el dataset NO se versiona, ver .gitignore); 3) copia en el escritorio.
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
_IN_PROJECT = _PROJECT_ROOT / "ai4mars-dataset-merged-0.6"
_ON_DESKTOP = Path.home() / "Desktop" / "ai4mars-dataset-merged-0.6"
_DEFAULT_ROOT = _IN_PROJECT if _IN_PROJECT.exists() else _ON_DESKTOP

AI4MARS_ROOT = Path(os.environ.get("AI4MARS_ROOT", _DEFAULT_ROOT))

# --- Subconjunto del proyecto: MSL NavCam (Curiosity) --------------------------------
MSL_NCAM_IMAGES = AI4MARS_ROOT / "msl" / "ncam" / "images" / "edr"
MSL_NCAM_LABELS_TRAIN = AI4MARS_ROOT / "msl" / "ncam" / "labels" / "train"
MSL_NCAM_LABELS_TEST = AI4MARS_ROOT / "msl" / "ncam" / "labels" / "test"

ROVER = "MSL"        # Mars Science Laboratory (rover Curiosity)
CAMERA = "navcam"

# --- Codificación NAV (un entero por píxel) ------------------------------------------
NAV_SOIL = 0
NAV_BEDROCK = 1
NAV_SAND = 2
NAV_BIG_ROCK = 3
NAV_NULL = 255       # sin etiqueta / enmascarado (rover, distancias > 30 m)

NAV_NAMES = {
    NAV_SOIL: "soil",
    NAV_BEDROCK: "bedrock",
    NAV_SAND: "sand",
    NAV_BIG_ROCK: "big rock",
    NAV_NULL: "null",
}

# Clases que cuentan como "roca visible" para la cobertura (E1): bedrock + big rock.
COVERAGE_CLASSES = (NAV_BEDROCK, NAV_BIG_ROCK)
# Clase usada para el conteo de rocas individuales (E2): solo big rock.
BIG_ROCK_CLASS = NAV_BIG_ROCK
