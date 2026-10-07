#!/usr/bin/env python
"""Consenso entre especialistas por clase, a partir de los tres niveles de las máscaras de experto.

AI4Mars publica las máscaras de especialista en tres versiones (``masked-gold-min{1,2,3}-100agree``):
un píxel entra en la versión K si al menos K especialistas lo etiquetaron y todos coinciden. Un
píxel de una clase en el nivel 1 solo puede conservar esa clase o quedar sin etiqueta en los
niveles 2 y 3; no puede pasar a otra. La proporción de píxeles que se conserva mide, por tanto,
cuántos especialistas coinciden en marcar esa clase en los mismos píxeles, pero no con qué otra
clase se confunde.

Salida: ``outputs/consenso_experto.json``.

Uso:  python scripts/consenso_experto.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))
from src import config, mask_utils as mu  # noqa: E402

CLASES = {config.NAV_SOIL: "suelo", config.NAV_BEDROCK: "lecho_rocoso",
          config.NAV_SAND: "arena", config.NAV_BIG_ROCK: "roca_grande"}


def main() -> None:
    base = config.MSL_NCAM_LABELS_TRAIN.parent / "test"
    niveles = [base / f"masked-gold-min{k}-100agree" for k in (1, 2, 3)]
    cuenta = {c: np.zeros(4, dtype=np.int64) for c in CLASES}   # nivel 1, conserva 2, conserva 3, cambia
    n_img = 0
    for p1 in sorted(niveles[0].glob("*.png")):
        p2, p3 = niveles[1] / p1.name, niveles[2] / p1.name
        if not (p2.exists() and p3.exists()):
            continue
        m1, m2, m3 = mu.read_mask(p1), mu.read_mask(p2), mu.read_mask(p3)
        n_img += 1
        for c in CLASES:
            sel = m1 == c
            otra = (m3[sel] != c) & (m3[sel] != config.NAV_NULL)
            cuenta[c] += [sel.sum(), (m2[sel] == c).sum(), (m3[sel] == c).sum(), otra.sum()]
    out = {"n_imagenes": n_img, "clases": {}}
    for c, nombre in CLASES.items():
        n1, s2, s3, ch = (int(v) for v in cuenta[c])
        out["clases"][nombre] = {"pixeles_nivel1": n1, "pct_conserva_nivel2": 100 * s2 / n1,
                                 "pct_conserva_nivel3": 100 * s3 / n1, "pct_cambia_de_clase": 100 * ch / n1}
    destino = RAIZ / "outputs/consenso_experto.json"
    destino.write_text(json.dumps(out, indent=1, ensure_ascii=False))
    print(json.dumps(out, indent=1, ensure_ascii=False))


if __name__ == "__main__":
    main()
