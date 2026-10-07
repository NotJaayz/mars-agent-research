#!/usr/bin/env python
"""Figura del mecanismo que limita el conteo: la división de aguas necesita una cintura.

Contrapone dos escenas de la validación humana, una donde el procedimiento acierta y otra
donde subcuenta de forma grave, mostrando las cuatro etapas relevantes. El propósito es que
la causa se vea en lugar de tener que explicarse: cuando la anotación traza cada bloque por
separado hay manchas distintas con estrangulamientos claros y el corte funciona; cuando es
un único polígono trazado holgadamente sobre un campo de rocas, la transformada de
distancia forma una sola meseta y no hay por dónde cortar.

Uso:  python scripts/make_mechanism_figure.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src import config, mask_utils as mu, rock_count as rc  # noqa: E402

OUT = Path("outputs/figures/tesis")
CLAVE = Path("outputs/validacion_manual_v2/clave.csv")

# Dos escenas de la validación: la primera con acuerdo, la segunda con subconteo grave.
CASOS = [
    ("W26", "Coincide con\nel observador", "observador: 4–9 · procedimiento: 9", "#1E6B45"),
    ("W48", "Subcuenta", "observador: 25–49 · procedimiento: 3", "#C0392B"),
]


def recorte(region: np.ndarray, margen: int = 25):
    f, c = np.where(region)
    return (slice(max(0, f.min() - margen), f.max() + margen),
            slice(max(0, c.min() - margen), c.max() + margen))


def main() -> None:
    if not CLAVE.exists():
        sys.exit(f"Falta {CLAVE}; genera el kit con make_validation_kit2.py")
    key = pd.read_csv(CLAVE).set_index("id")

    fig, axes = plt.subplots(2, 4, figsize=(15, 7.6))
    for fila, (vid, veredicto, detalle, color) in enumerate(CASOS):
        if vid not in key.index:
            print(f"  {vid} no está en la clave; se omite")
            continue
        iid = key.loc[vid, "image_id"]
        with Image.open(config.MSL_NCAM_IMAGES / f"{iid}.JPG") as im:
            img = np.asarray(im.convert("L"))
        region = mu.big_rock_mask(mu.read_mask(config.MSL_NCAM_LABELS_TRAIN / f"{iid}.png"))
        st = rc.compute_stages(region, rc.DEFAULT_PARAMS)
        rs, cs = recorte(region)

        ax = axes[fila]
        ax[0].imshow(img[rs, cs], cmap="gray")
        ax[0].contour(region[rs, cs], levels=[0.5], colors="yellow", linewidths=1.6)
        ax[0].set_ylabel(veredicto, fontsize=12, fontweight="bold", color=color)
        ax[0].set_title("1. Imagen y región anotada", fontsize=10)

        ax[1].imshow(region[rs, cs], cmap="gray_r")
        ax[1].set_title("2. La región que recibe el procedimiento", fontsize=10)

        ax[2].imshow(np.where(region[rs, cs], st["distance"][rs, cs], np.nan), cmap="viridis")
        ax[2].set_title("3. Transformada de distancia\n(claro = centro de la región)",
                        fontsize=10)

        kept = np.isin(st["labels_ws"], st["kept_ids"])
        ax[3].imshow(img[rs, cs], cmap="gray")
        if kept.any():
            sub = st["labels_ws"][rs, cs]
            rgba = np.zeros((*sub.shape, 4))
            rng = np.random.default_rng(3)
            for lid in st["kept_ids"]:
                rgba[sub == lid] = (*rng.uniform(0.3, 1.0, 3), 0.70)
            ax[3].imshow(rgba)
        k = len(st["kept_ids"])
        ax[3].set_title(f"4. Resultado: {k} {'roca' if k == 1 else 'rocas'}\n{detalle}", fontsize=10)

        for a in ax:
            a.set_xticks([]); a.set_yticks([])

    fig.suptitle("La división de aguas solo puede cortar donde la región presenta un "
                 "estrangulamiento", fontsize=14, y=0.985)
    fig.tight_layout(rect=(0, 0, 1, 0.95))
    OUT.mkdir(parents=True, exist_ok=True)
    out = OUT / "Figura_28_mecanismo_subconteo.png"
    fig.savefig(out, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  Figura 28  {out.name}")


if __name__ == "__main__":
    main()
