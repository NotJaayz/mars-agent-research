#!/usr/bin/env python
"""Riesgo de fuga de información en la evaluación del segmentador.

Las imágenes del rover se adquieren en secuencias, y dos tomas separadas por segundos pueden
ser casi idénticas: si una cae en entrenamiento y otra en prueba, el desempeño medido se infla.

Para cada imagen de prueba se calcula la distancia, en reloj de nave, a la imagen de
entrenamiento más próxima, y se mide el desempeño del modelo por tramos de esa distancia.
Si el desempeño en las imágenes lejanas es similar al de las cercanas, la fuga no infla la
cifra reportada. Se calcula también esa distancia para las máscaras de experto. Con el reparto por bloques
temporales de scripts/train_segmentation.py ninguna imagen de prueba queda a menos de un sol
de una de entrenamiento; este guion lo verifica.

Requiere outputs/split_deeplab.json, que escribe scripts/train_segmentation.py.
Uso:  python scripts/eval_fuga_temporal.py
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import numpy as np
import torch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from src import config, mask_utils as mu  # noqa: E402
from src.segmentation import IGNORE_INDEX, build_model, predict_mask, to_binary_target  # noqa: E402

SOL = 88775.244  # segundos por sol marciano
TRAMOS = [(0, 60, "menos de 1 minuto"), (60, 3600, "1 minuto a 1 hora"),
          (3600, SOL, "1 hora a 1 sol"), (SOL, 10 * SOL, "1 a 10 soles"),
          (10 * SOL, 50 * SOL, "10 a 50 soles"), (50 * SOL, 1e15, "más de 50 soles")]


def sclk(stem: str) -> int:
    return int(re.match(r"^N[LR][AB]_(\d+)", stem).group(1))


def distancia(s: int, T: np.ndarray) -> float:
    k = np.searchsorted(T, s)
    return float(min(abs(s - T[j]) for j in (k - 1, k) if 0 <= j < len(T)))


def main():
    split = json.load(open("outputs/split_deeplab.json"))
    T = np.sort([sclk(i) for i in split["train"]])
    model = build_model(2, pretrained=False).to("mps")
    model.load_state_dict(torch.load("outputs/modelo_deeplab_binario.pt", map_location="mps"))
    model.eval()

    filas = []
    for iid in split["test"]:
        mp = config.MSL_NCAM_LABELS_TRAIN / f"{iid}.png"
        obj = to_binary_target(mu.read_mask(mp))
        pred = predict_mask(model, mu.mask_to_image_path(mp))
        val = obj != IGNORE_INDEX
        filas.append({"image_id": iid, "gap": distancia(sclk(iid), T),
                      "inter": [int(((pred == c) & (obj == c) & val).sum()) for c in (0, 1)],
                      "union": [int((((pred == c) | (obj == c)) & val).sum()) for c in (0, 1)],
                      "cob_h": 100 * ((obj == 1) & val).sum() / max(val.sum(), 1),
                      "cob_m": 100 * ((pred == 1) & val).sum() / max(val.sum(), 1)})

    def resumen(sub):
        miou = np.mean([sum(f["inter"][c] for f in sub) / max(sum(f["union"][c] for f in sub), 1)
                        for c in (0, 1)])
        h = np.array([f["cob_h"] for f in sub]); m = np.array([f["cob_m"] for f in sub])
        return {"n": len(sub), "miou": float(miou), "r_cobertura": float(np.corrcoef(h, m)[0, 1]),
                "mae": float(np.abs(m - h).mean()), "error_medio": float((m - h).mean())}

    g = np.array([f["gap"] for f in filas])
    out = {"prueba_total": resumen(filas),
           "proximidad_prueba": {f"menos_de_{u}s": int((g < u).sum()) for u in (60, 600, 3600, int(SOL))},
           "minimo_soles": float(g.min() / SOL),
           "mediana_gap_s": float(np.median(g)),
           "por_tramo": {lab: resumen([f for f in filas if lo <= f["gap"] < hi])
                         for lo, hi, lab in TRAMOS if sum(lo <= f["gap"] < hi for f in filas) > 3}}
    gold = sorted((config.MSL_NCAM_LABELS_TRAIN.parent / "test" / "masked-gold-min1-100agree").glob("*.png"))
    gg = np.array([distancia(sclk(p.stem), T) for p in gold])
    out["experto"] = {"n": int(len(gg)), "menos_de_1h": int((gg < 3600).sum()),
                      "menos_de_1sol": int((gg < SOL).sum()), "mediana_soles": float(np.median(gg) / SOL)}
    Path("outputs/fuga_temporal.json").write_text(json.dumps(out, indent=2, ensure_ascii=False))
    print(json.dumps(out, indent=1, ensure_ascii=False))


if __name__ == "__main__":
    main()
