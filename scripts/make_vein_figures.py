#!/usr/bin/env python
"""Figuras de las escenas con vetas minerales anotadas (M2020_GEO, Perseverance).

Las vetas son depósitos minerales precipitados por circulación de agua, de modo que su
presencia en una escena señala interés científico. Este guion localiza las escenas con
mayor extensión de veta y superpone la anotación sobre la imagen original, para verificar
visualmente que la señal corresponde a rasgos reales del terreno.

Uso:  python scripts/make_vein_figures.py --n 6
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from src import config  # noqa: E402

VETA = 40
NULL = 255
SALIDA = Path("outputs/figures/vetas")


def buscar_imagen(image_id: str) -> Path | None:
    """La máscara lleva sufijo ``_mergedN`` que la imagen no tiene; se prueba sin él."""
    base = image_id.split("_merged")[0]
    for sub in ("ncam", "mcam"):
        for ext in (".jpg", ".jpeg", ".JPG", ".png"):
            p = config.AI4MARS_ROOT / "m2020" / "images" / sub / f"{base}{ext}"
            if p.exists():
                return p
    return None


def buscar_mascara(image_id: str) -> Path | None:
    raiz = config.AI4MARS_ROOT / "m2020" / "labels" / "M2020_GEO"
    for p in raiz.rglob(f"{image_id}.png"):
        return p
    return None


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--n", type=int, default=6)
    ap.add_argument("--min-frac-valid", type=float, default=0.20,
                    help="excluye escenas con poca anotación, donde el porcentaje engaña")
    args = ap.parse_args()

    g = pd.read_csv("outputs/geologia_m2020.csv")
    # Solo las anotaciones plausibles: las que cubren gran parte de la escena son
    # errores de anotación (véase scripts/scan_geology.py).
    cv = g[(g.alerta_veta == "veta_probable") & (g.frac_valid >= args.min_frac_valid)]
    # Muestra variada: desde vetas que dominan la escena hasta presencias discretas
    cv = cv.sort_values("pct_veta", ascending=False)
    idx = np.linspace(0, len(cv) - 1, args.n).astype(int)
    sel = cv.iloc[idx]

    SALIDA.mkdir(parents=True, exist_ok=True)
    hechas = 0
    for i, (_, r) in enumerate(sel.iterrows(), 1):
        mp = buscar_mascara(r.image_id)
        ip = buscar_imagen(r.image_id)
        if mp is None or ip is None:
            print(f"  [{i}] {r.image_id[:38]}: falta imagen o máscara, se omite")
            continue
        img = np.asarray(Image.open(ip).convert("L"))
        m = np.asarray(Image.open(mp), dtype=np.uint8)
        veta = m == VETA
        if veta.shape != img.shape:      # la máscara puede diferir en unos píxeles
            h = min(veta.shape[0], img.shape[0]); w = min(veta.shape[1], img.shape[1])
            img, veta = img[:h, :w], veta[:h, :w]

        fig, ax = plt.subplots(1, 2, figsize=(11, 4.4), dpi=110)
        fig.patch.set_facecolor("white")
        ax[0].imshow(img, cmap="gray"); ax[0].set_title("Imagen original", fontsize=10)
        ax[1].imshow(img, cmap="gray")
        ov = np.zeros((*veta.shape, 4))
        ov[veta] = [0.10, 0.85, 0.95, 0.55]      # cian: máximo contraste sobre el terreno
        ax[1].imshow(ov)
        ax[1].contour(veta, levels=[0.5], colors="#00e5ff", linewidths=0.7)
        ax[1].set_title(f"Vetas anotadas — {r.pct_veta:.0f} % del área etiquetada",
                        fontsize=10)
        for a in ax:
            a.axis("off")
        fig.suptitle(f"{r.image_id[:52]}", fontsize=9, color="#555")
        fig.tight_layout()
        out = SALIDA / f"veta_{i:02d}.png"
        fig.savefig(out, bbox_inches="tight"); plt.close(fig)
        print(f"  [{i}] {out.name}  veta {r.pct_veta:5.1f} %  "
              f"anotado {100*r.frac_valid:.0f} %")
        hechas += 1
    print(f"\n{hechas} figuras en {SALIDA}/")


if __name__ == "__main__":
    main()
