#!/usr/bin/env python
"""Evalúa el segmentador entrenado contra las máscaras de experto del propio conjunto.

El modelo se entrenó solo con máscaras colaborativas; las de experto no intervienen en el
entrenamiento ni en la elección del punto de control, y ninguna está a menos de una hora,
en reloj de nave, de una imagen de entrenamiento. La comparación se restringe a los píxeles
que el experto etiquetó.

Salidas auditables:
  outputs/modelo_vs_experto_min{N}.csv   una fila por escena: image_id, n_valid,
                                         cobertura del experto, del modelo y error
  outputs/modelo_vs_experto_min{N}.json  métricas agregadas y SHA-256 del modelo evaluado

Uso:  python scripts/eval_model_expert.py [--nivel 1] [--limite 0]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import torch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from src import config, mask_utils as mu  # noqa: E402
from src.segmentation import IGNORE_INDEX, build_model, predict_mask, to_binary_target  # noqa: E402

PESOS = Path("outputs/modelo_deeplab_binario.pt")


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--nivel", type=int, default=1, choices=(1, 2, 3),
                    help="nivel de acuerdo exigido a los expertos")
    ap.add_argument("--limite", type=int, default=0, help="0 = todas")
    ap.add_argument("--device", default="mps")
    args = ap.parse_args()
    if not PESOS.exists():
        sys.exit(f"Faltan los pesos en {PESOS}; entrena con scripts/train_segmentation.py")

    gold_dir = config.MSL_NCAM_LABELS_TRAIN.parent / "test" / f"masked-gold-min{args.nivel}-100agree"
    masks = sorted(gold_dir.glob("*.png"))[: args.limite or None]
    model = build_model(num_classes=2, pretrained=False).to(args.device)
    model.load_state_dict(torch.load(PESOS, map_location=args.device)); model.eval()
    print(f"Evaluando {len(masks)} máscaras de experto (nivel {args.nivel})...", flush=True)

    inter = np.zeros(2, dtype=np.int64); union = np.zeros(2, dtype=np.int64)
    filas, saltadas = [], []
    for mp in masks:
        ip = mu.mask_to_image_path(mp)
        obj = to_binary_target(mu.read_mask(mp))
        val = obj != IGNORE_INDEX
        if ip is None or not val.any():
            saltadas.append(mp.stem); continue
        pred = predict_mask(model, ip, device=args.device)
        for c in (0, 1):
            p, t = (pred == c) & val, (obj == c) & val
            inter[c] += int((p & t).sum()); union[c] += int((p | t).sum())
        nv = int(val.sum())
        filas.append({"image_id": mp.stem, "n_valid": nv,
                      "cobertura_experto": 100 * float(((obj == 1) & val).sum()) / nv,
                      "cobertura_modelo": 100 * float(((pred == 1) & val).sum()) / nv})
    df = pd.DataFrame(filas); df["error"] = df.cobertura_modelo - df.cobertura_experto
    iou = [float(inter[c] / union[c]) if union[c] else float("nan") for c in (0, 1)]
    seg = json.load(open("outputs/segmentacion_metricas.json"))
    resumen = {"n": int(len(df)), "saltadas": saltadas, "iou_no_roca": iou[0], "iou_roca": iou[1],
               "miou": float(np.nanmean(iou)),
               "r_cobertura": float(df.cobertura_modelo.corr(df.cobertura_experto)),
               "error_medio": float(df.error.mean()), "error_mediano": float(df.error.median()),
               "mae": float(df.error.abs().mean()),
               "pct_sobreestima": float(100 * (df.error > 0).mean()),
               "pct_subestima": float(100 * (df.error < 0).mean()),
               "sha256_modelo": sha256(PESOS), "epoca_modelo": seg.get("epoca_elegida")}
    df.to_csv(f"outputs/modelo_vs_experto_min{args.nivel}.csv", index=False)
    Path(f"outputs/modelo_vs_experto_min{args.nivel}.json").write_text(json.dumps(resumen, indent=2, ensure_ascii=False))
    print(json.dumps({k: v for k, v in resumen.items() if k != "saltadas"}, indent=1, ensure_ascii=False))


if __name__ == "__main__":
    main()
