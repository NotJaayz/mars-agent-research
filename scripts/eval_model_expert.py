#!/usr/bin/env python
"""¿El segmentador aprendió «roca» o «lo que los anotadores llaman roca»?

El modelo binario se entrenó con las máscaras colaborativas, que sobreestiman la roca de
forma sistemática (subsección de sesgo de la anotación). Su desempeño reportado —IoU medio
de 0,94— se midió también contra máscaras colaborativas, de modo que responde a «cuánto se
parece a la anotación de la que aprendió», no a «cuánta roca hay».

Este guion lo evalúa contra las máscaras de experto del propio conjunto, que el modelo
nunca vio, y compara ambas cifras. Si el desempeño se mantiene, el modelo capta la roca; si
cae, reprodujo el sesgo.

Uso:  python scripts/eval_model_expert.py [--nivel 1] [--limite 0]
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import torch
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src import config, mask_utils as mu  # noqa: E402
from src.segmentation import IGNORE_INDEX, build_model, predict_mask, to_binary_target  # noqa: E402

PESOS = Path("outputs/modelo_deeplab_binario.pt")


def iou_binario(pred: np.ndarray, obj: np.ndarray) -> tuple[float, float]:
    """IoU de no-roca y de roca, sobre los píxeles que el experto etiquetó."""
    val = obj != IGNORE_INDEX
    out = []
    for c in (0, 1):
        p, t = (pred == c) & val, (obj == c) & val
        u = (p | t).sum()
        out.append(float((p & t).sum() / u) if u else float("nan"))
    return out[0], out[1]


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--nivel", type=int, default=1, choices=(1, 2, 3),
                    help="nivel de acuerdo exigido a los expertos")
    ap.add_argument("--limite", type=int, default=0, help="0 = todas")
    ap.add_argument("--device", default="mps")
    args = ap.parse_args()

    if not PESOS.exists():
        sys.exit(f"Faltan los pesos en {PESOS}; entrena con scripts/train_segmentation.py")

    gold_dir = (config.MSL_NCAM_LABELS_TRAIN.parent / "test"
                / f"masked-gold-min{args.nivel}-100agree")
    masks = sorted(gold_dir.glob("*.png"))
    if args.limite:
        masks = masks[:args.limite]
    if not masks:
        sys.exit(f"No hay máscaras en {gold_dir}")

    model = build_model(num_classes=2, pretrained=False).to(args.device)
    model.load_state_dict(torch.load(PESOS, map_location=args.device))
    model.eval()
    print(f"Modelo cargado. Evaluando {len(masks)} máscaras de experto (nivel {args.nivel})...")

    inter = np.zeros(2, dtype=np.int64)
    union = np.zeros(2, dtype=np.int64)
    cob_pred, cob_exp, saltadas = [], [], 0

    for i, mp in enumerate(masks, 1):
        ip = mu.mask_to_image_path(mp)
        if ip is None:
            saltadas += 1
            continue
        obj = to_binary_target(mu.read_mask(mp))
        pred = predict_mask(model, ip, device=args.device)
        if pred.shape != obj.shape:
            saltadas += 1
            continue

        val = obj != IGNORE_INDEX
        if not val.any():
            saltadas += 1
            continue
        for c in (0, 1):
            p, t = (pred == c) & val, (obj == c) & val
            inter[c] += int((p & t).sum())
            union[c] += int((p | t).sum())

        # Cobertura sobre los píxeles que el experto etiquetó, para comparar como en E1.
        cob_pred.append(100 * float(((pred == 1) & val).sum()) / int(val.sum()))
        cob_exp.append(100 * float(((obj == 1) & val).sum()) / int(val.sum()))
        if i % 50 == 0:
            print(f"  {i}/{len(masks)}")

    iou = [inter[c] / union[c] if union[c] else float("nan") for c in (0, 1)]
    cp, ce = np.array(cob_pred), np.array(cob_exp)
    r = float(np.corrcoef(cp, ce)[0, 1]) if len(cp) > 2 else float("nan")

    print(f"\n=== Contra EXPERTO (nivel {args.nivel}, n={len(cp)}, {saltadas} saltadas) ===")
    print(f"  IoU no-roca : {iou[0]:.3f}")
    print(f"  IoU roca    : {iou[1]:.3f}")
    print(f"  IoU medio   : {np.nanmean(iou):.3f}")
    err = cp - ce
    print(f"\n  cobertura mediana — modelo {np.median(cp):5.1f} %   experto {np.median(ce):5.1f} %")
    print(f"  correlación modelo/experto: {r:.3f}")
    print(f"\n  error (modelo - experto), en puntos porcentuales:")
    print(f"    media {err.mean():+6.1f}   mediana {np.median(err):+6.1f}   "
          f"error absoluto medio {np.abs(err).mean():5.1f}")
    for q in (5, 25, 75, 95):
        print(f"    percentil {q:2d}: {np.percentile(err, q):+6.1f}")
    print(f"  escenas donde el modelo sobreestima: "
          f"{100*(err > 0).mean():.0f} %   subestima: {100*(err < 0).mean():.0f} %")

    # Se guardan los valores por escena para poder auditar el contraste.
    out_csv = Path(f"outputs/modelo_vs_experto_min{args.nivel}.csv")
    import pandas as pd
    pd.DataFrame({"cobertura_modelo": cp, "cobertura_experto": ce}).to_csv(
        out_csv, index=False)
    print(f"\n  valores por escena -> {out_csv}")
    print("\n=== Referencia: contra COLABORATIVAS (lo ya reportado) ===")
    print("  IoU medio 0,940 · correlación de la cobertura 0,950 · error 4,3 p.p.")


if __name__ == "__main__":
    main()
