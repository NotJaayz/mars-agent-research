#!/usr/bin/env python
"""Figura de la prueba de concepto del conteo híbrido (máscara + gradiente de la imagen).

Usa la escena que ``scripts/diagnose_errors.py`` elige para ilustrar la roca visible
etiquetada como lecho rocoso (bandera no_bigrock, lecho rocoso > 90 %, mayor fracción
etiquetada) y cuenta bloques con :mod:`src.rock_count_hybrid` y sus parámetros por defecto,
dentro de la región que la máscara marca como roca.

Salidas: outputs/figures/tesis/diag_prueba_hibrido.png y outputs/prueba_hibrido.json.
Uso:  python scripts/make_hybrid_figure.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from PIL import Image
from skimage.color import label2rgb

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from src import config, mask_utils as mu, rock_count_hybrid as hy  # noqa: E402


def main():
    df = pd.read_csv("outputs/results.csv")
    c = df[(df.quality_flag == "no_bigrock") & (df.pct_bedrock > 90) & (df.frac_valid > 0.5)]
    iid = c.nlargest(1, "frac_valid").iloc[0].image_id
    mp = config.MSL_NCAM_LABELS_TRAIN / f"{iid}.png"
    mask = mu.read_mask(mp)
    with Image.open(mu.mask_to_image_path(mp)) as im:
        img = np.asarray(im.convert("L"))
    region = mu.coverage_mask(mask)
    st = hy.compute_stages(img, region)
    n = len(st["kept_ids"])
    ws = np.where(np.isin(st["labels_ws"], st["kept_ids"]), st["labels_ws"], 0)

    fig, ax = plt.subplots(1, 3, figsize=(12, 4.2))
    ax[0].imshow(img, cmap="gray"); ax[0].set_title("1. Imagen original")
    ax[1].imshow(img, cmap="gray"); ax[1].imshow(np.ma.masked_where(~region, region), cmap="autumn", alpha=0.35)
    ax[1].set_title("2. Región de roca de la máscara (" + f"{100 * region.mean():.1f}".replace(".", ",") + " %)")
    ax[2].imshow(label2rgb(ws, image=img / 255.0, bg_label=0, alpha=0.45))
    ax[2].set_title(f"3. Bloques delimitados por el gradiente: {n}")
    for a in ax:
        a.set_xticks([]); a.set_yticks([])
    fig.tight_layout()
    out = Path("outputs/figures/tesis/diag_prueba_hibrido.png"); out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out, dpi=150, bbox_inches="tight"); plt.close(fig)
    Path("outputs/prueba_hibrido.json").write_text(json.dumps(
        {"image_id": iid, "n_bloques": n, "fraccion_region": float(region.mean()),
         "params": st["params"]}, indent=2, ensure_ascii=False))
    print(f"{iid}: {n} bloques -> {out}")


if __name__ == "__main__":
    main()
