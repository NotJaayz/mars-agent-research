#!/usr/bin/env python
"""Entrena DeepLabV3 para segmentar roca y compara la cobertura predicha vs. humana.

Línea futura (E5): un modelo que, a partir únicamente de la imagen, predice qué píxeles
son roca; después se contrasta el indicador de cobertura derivado de la máscara predicha
con el derivado de la máscara humana de AI4Mars.

Guarda en outputs/: modelo (.pt), métricas (.json) y figura de dispersión.

Uso:
  python scripts/train_segmentation.py                       # configuración completa
  python scripts/train_segmentation.py --n-train 200 --epochs 2   # prueba rápida
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
import torch
from torch.utils.data import DataLoader

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from src import config, mask_utils as mu, segmentation as seg  # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--n-train", type=int, default=2000)
    ap.add_argument("--n-val", type=int, default=400)
    ap.add_argument("--n-test", type=int, default=400)
    ap.add_argument("--epochs", type=int, default=6)
    ap.add_argument("--img-size", type=int, default=512)
    ap.add_argument("--batch", type=int, default=4)
    ap.add_argument("--lr", type=float, default=1e-4)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--n-coverage", type=int, default=200,
                    help="nº de imágenes de test para comparar cobertura")
    args = ap.parse_args()

    device = "mps" if torch.backends.mps.is_available() else "cpu"
    num_classes = 2  # binario: roca / no-roca
    torch.manual_seed(args.seed)
    print(f"device={device}  img={args.img_size}  épocas={args.epochs}", flush=True)

    # --- Splits balanceados (mitad con roca, mitad sin) ---
    results = pd.read_csv("outputs/results.csv")
    pool = results[(results.frac_valid >= 0.2)
                   & (results.quality_flag.isin(["ok", "no_bigrock", "no_rock"]))]
    rng = np.random.default_rng(args.seed)
    rock = pool[pool.rock_coverage_pct.fillna(0) > 1].image_id.tolist()
    other = pool[pool.rock_coverage_pct.fillna(0) <= 1].image_id.tolist()
    rng.shuffle(rock); rng.shuffle(other)
    n_total = args.n_train + args.n_val + args.n_test
    n_rock = min(len(rock), n_total // 2)
    ids = rock[:n_rock] + other[:n_total - n_rock]
    rng.shuffle(ids); ids = ids[:n_total]
    tr = ids[:args.n_train]
    va = ids[args.n_train:args.n_train + args.n_val]
    te = ids[args.n_train + args.n_val:]
    print(f"train={len(tr)} val={len(va)} test={len(te)}", flush=True)

    mk = lambda s: seg.RockSegDataset(s, args.img_size, binary=True)
    train_dl = DataLoader(mk(tr), batch_size=args.batch, shuffle=True)
    val_dl = DataLoader(mk(va), batch_size=args.batch)
    test_dl = DataLoader(mk(te), batch_size=args.batch)

    model = seg.build_model(num_classes, pretrained=True).to(device)
    opt = torch.optim.Adam(model.parameters(), lr=args.lr)
    crit = torch.nn.CrossEntropyLoss(ignore_index=seg.IGNORE_INDEX)

    @torch.no_grad()
    def eval_iou(dl):
        model.eval()
        inter = np.zeros(num_classes); union = np.zeros(num_classes)
        for xb, yb in dl:
            pred = model(xb.to(device))["out"].argmax(1).cpu()
            v = yb != seg.IGNORE_INDEX
            for c in range(num_classes):
                p = (pred == c) & v; t = (yb == c) & v
                inter[c] += (p & t).sum().item(); union[c] += (p | t).sum().item()
        return [inter[c] / union[c] if union[c] else float("nan") for c in range(num_classes)]

    out = {"config": vars(args) | {"device": device}, "epochs": []}
    outdir = Path("outputs"); outdir.mkdir(exist_ok=True)
    meta_path = outdir / "segmentacion_metricas.json"

    for ep in range(args.epochs):
        model.train(); t0 = time.time(); running = 0.0
        for xb, yb in train_dl:
            xb, yb = xb.to(device), yb.to(device)
            opt.zero_grad()
            o = model(xb)
            loss = crit(o["out"], yb) + 0.4 * crit(o["aux"], yb)
            loss.backward(); opt.step(); running += loss.item()
        ious = eval_iou(val_dl)
        rec = {"epoch": ep + 1, "loss": round(running / len(train_dl), 4),
               "iou_no_roca": round(ious[0], 4), "iou_roca": round(ious[1], 4),
               "miou": round(float(np.nanmean(ious)), 4), "seconds": round(time.time() - t0)}
        out["epochs"].append(rec)
        print(f"época {rec['epoch']}/{args.epochs} loss={rec['loss']:.3f} "
              f"IoU=(no-roca {rec['iou_no_roca']:.3f}, roca {rec['iou_roca']:.3f}) "
              f"mIoU={rec['miou']:.3f} ({rec['seconds']}s)", flush=True)
        meta_path.write_text(json.dumps(out, indent=2, ensure_ascii=False))  # guardado incremental

    # --- IoU final en test ---
    ious_test = eval_iou(test_dl)
    out["test"] = {"iou_no_roca": round(ious_test[0], 4), "iou_roca": round(ious_test[1], 4),
                   "miou": round(float(np.nanmean(ious_test)), 4)}
    print(f"\nTEST  IoU no-roca={ious_test[0]:.3f}  IoU roca={ious_test[1]:.3f}  "
          f"mIoU={np.nanmean(ious_test):.3f}", flush=True)

    # --- Cobertura predicha vs. humana ---
    rows = []
    for iid in te[:args.n_coverage]:
        mp = config.MSL_NCAM_LABELS_TRAIN / f"{iid}.png"
        ip = mu.mask_to_image_path(mp)
        if ip is None:
            continue
        human = mu.read_mask(mp); valid = human != config.NAV_NULL
        if valid.sum() == 0:
            continue
        hc = 100 * np.isin(human, config.COVERAGE_CLASSES)[valid].mean()
        pred = seg.predict_mask(model, ip, args.img_size, device=device)
        pc = 100 * (pred == 1)[valid].mean()
        rows.append({"image_id": iid, "human_cov": hc, "pred_cov": pc})
    cov = pd.DataFrame(rows)
    cov.to_csv(outdir / "cobertura_modelo_vs_humano.csv", index=False)
    r = float(cov.human_cov.corr(cov.pred_cov))
    mae = float((cov.pred_cov - cov.human_cov).abs().mean())
    out["coverage"] = {"n": len(cov), "pearson_r": round(r, 4), "mae_pp": round(mae, 2)}
    print(f"COBERTURA  n={len(cov)}  r={r:.3f}  MAE={mae:.1f} pp", flush=True)

    # --- Figura ---
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(figsize=(6, 6))
    ax.plot([0, 100], [0, 100], "--", color="gray", label="igualdad")
    ax.scatter(cov.human_cov, cov.pred_cov, c="#2c6fbb", s=25, alpha=0.6)
    ax.set(xlabel="cobertura desde máscara humana (%)",
           ylabel="cobertura desde máscara predicha (%)",
           title=f"Cobertura: DeepLabV3 vs. anotación humana (n={len(cov)}, r={r:.2f})",
           xlim=(0, 100), ylim=(0, 100))
    ax.legend(); ax.grid(alpha=0.3)
    figdir = outdir / "figures" / "analisis"; figdir.mkdir(parents=True, exist_ok=True)
    fig.savefig(figdir / "12_cobertura_modelo_vs_humano.png", dpi=120, bbox_inches="tight")

    torch.save(model.state_dict(), outdir / "modelo_deeplab_binario.pt")
    meta_path.write_text(json.dumps(out, indent=2, ensure_ascii=False))
    print(f"\nOK -> {meta_path}", flush=True)


if __name__ == "__main__":
    main()
