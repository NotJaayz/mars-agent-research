#!/usr/bin/env python
"""Compara el conteo clásico (watershed) con un modelo general de segmentación (FastSAM).

FastSAM segmenta de forma agnóstica a la clase; para obtener un conteo comparable se
conservan solo las instancias que caen mayoritariamente dentro de la región etiquetada
como roca grande. Guarda la tabla de comparación (con identificadores) y las métricas.

Uso:  python scripts/compare_sam.py --n 50
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import torch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from src import config, mask_utils as mu, sam_compare as sc  # noqa: E402

BANDAS = ["0", "1-3", "4-9", "10+"]
banda = lambda v: "0" if v == 0 else "1-3" if v <= 3 else "4-9" if v <= 9 else "10+"


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--n", type=int, default=50)
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--weights", default="FastSAM-s.pt")
    args = ap.parse_args()

    device = "mps" if torch.backends.mps.is_available() else "cpu"
    results = pd.read_csv("outputs/results.csv")
    ok = results[results.quality_flag == "ok"]
    sample = ok.sample(n=min(args.n, len(ok)), random_state=args.seed)

    model = sc.load_fastsam(args.weights)
    rows = []
    for k, (iid, ws) in enumerate(zip(sample.image_id, sample.n_rocks), 1):
        mp = config.MSL_NCAM_LABELS_TRAIN / f"{iid}.png"
        ip = mu.mask_to_image_path(mp)
        if ip is None:
            continue
        roi = sc.region_from_classes(mu.read_mask(mp), (config.NAV_BIG_ROCK,))
        masks = sc.sam_instance_masks(ip, model, device=device)
        n_sam, _ = sc.count_in_region(masks, roi, 0.0005, 0.5)
        rows.append({"image_id": iid, "watershed": int(ws), "sam": n_sam})
        if k % 10 == 0:
            print(f"  ...{k} imágenes", flush=True)

    comp = pd.DataFrame(rows)
    comp.to_csv("outputs/comparacion_watershed_sam.csv", index=False)

    comp["wb"] = comp.watershed.map(banda)
    comp["sb"] = comp.sam.map(banda)
    acuerdo = (comp.wb == comp.sb).mean() * 100
    pear = float(comp.watershed.corr(comp.sam))
    spear = float(comp.watershed.corr(comp.sam, method="spearman"))
    mae = float((comp.sam - comp.watershed).abs().mean())

    met = {"n": len(comp), "acuerdo_bandas_pct": round(acuerdo, 1),
           "pearson": round(pear, 3), "spearman": round(spear, 3), "mae": round(mae, 2)}
    Path("outputs/comparacion_sam_metricas.json").write_text(
        json.dumps(met, indent=2, ensure_ascii=False))

    print(f"\nn={len(comp)}  acuerdo de banda={acuerdo:.0f}%  "
          f"Pearson={pear:.2f}  Spearman={spear:.2f}  MAE={mae:.1f}")
    M = pd.crosstab(comp.wb, comp.sb).reindex(index=BANDAS, columns=BANDAS, fill_value=0)
    print("\nMatriz (filas=watershed, columnas=SAM):")
    print(M.to_string())


if __name__ == "__main__":
    main()
