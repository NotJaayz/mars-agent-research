#!/usr/bin/env python
"""Compara el conteo híbrido con el basado en máscara, contra el conteo humano.

Responde a la pregunta de si usar la imagen dentro de la región anotada mejora la
precisión del conteo. El juez son las escenas con conteo humano de
``outputs/validacion_manual``, que es la única referencia disponible.

Procedimiento:

1. Precalcula el gradiente de cada escena (no depende de los parámetros que se exploran).
2. Recorre una rejilla de prominencia de semilla y área mínima.
3. Selecciona la mejor combinación con **validación cruzada dejando una fuera**, para no
   informar una mejora elegida sobre las mismas escenas con que se mide.
4. Contrasta con el conteo basado en máscara mediante bootstrap de la diferencia de kappa
   ponderado, que es la medida apropiada porque las bandas son ordinales.

Uso:  python scripts/eval_hybrid.py [--rapido]
"""
from __future__ import annotations

import argparse
import sys
from collections import Counter
from pathlib import Path

import numpy as np
import pandas as pd
from PIL import Image
from skimage.filters import gaussian, sobel
from skimage.measure import label, regionprops
from skimage.morphology import h_maxima
from skimage.segmentation import watershed
from sklearn.metrics import cohen_kappa_score

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src import config, mask_utils as mu  # noqa: E402
from src.rock_count import _aspect_ratio  # noqa: E402

BANDAS = ["0", "1-3", "4-9", "10+"]
GRID_H = [0.004, 0.008, 0.015, 0.025, 0.04, 0.06, 0.09, 0.13]
GRID_A = [0.0005, 0.002, 0.005, 0.01]
DIR_VAL = Path("outputs/validacion_manual")


def banda(n: int) -> str:
    return "0" if n == 0 else "1-3" if n <= 3 else "4-9" if n <= 9 else "10+"


def kappa_pond(y, x, weights: str | None = "linear") -> float:
    """Kappa de Cohen ponderado; NaN si la referencia no tiene al menos dos categorías."""
    if len(set(y)) < 2:
        return float("nan")
    return cohen_kappa_score(y, x, labels=BANDAS, weights=weights)


def precalcular(d: pd.DataFrame) -> dict[str, dict]:
    """Gradiente e interior por escena; independientes de la rejilla de parámetros."""
    cache: dict[str, dict] = {}
    for r in d.itertuples():
        mask = mu.read_mask(config.MSL_NCAM_LABELS_TRAIN / f"{r.image_id}.png")
        with Image.open(config.MSL_NCAM_IMAGES / f"{r.image_id}.JPG") as im:
            img = np.asarray(im.convert("L"), dtype=float)
        rango = float(img.max() - img.min())
        img = (img - img.min()) / rango if rango > 0 else np.zeros_like(img)
        grad = sobel(gaussian(img, sigma=2.0))
        cache[r.id] = {
            "region": mu.big_rock_mask(mask),
            "grad": grad,
            "interior": gaussian(-grad, sigma=1.0),
            "size": img.size,
            "humano": r.banda,
            "auto": r.auto,
        }
    return cache


def contar(c: dict, seed_h: float, min_area_frac: float) -> int:
    if not c["region"].any():
        return 0
    seeds = h_maxima(c["interior"], seed_h).astype(bool) & c["region"]
    markers = label(seeds) if seeds.any() else label(c["region"])
    ws = watershed(c["grad"], markers, mask=c["region"])
    min_area = min_area_frac * c["size"]
    return sum(1 for g in regionprops(ws)
               if g.area >= min_area and _aspect_ratio(g) <= 5.0)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--rapido", action="store_true",
                    help="rejilla reducida (para comprobar que el guion corre)")
    args = ap.parse_args()

    plantilla = pd.read_csv(DIR_VAL / "plantilla.csv", dtype={"banda": str})
    clave = pd.read_csv(DIR_VAL / "clave.csv")
    d = plantilla.merge(clave, on="id")
    d["banda"] = d.banda.astype(str).str.strip()
    d = d[d.banda.isin(BANDAS)]
    if d.empty:
        sys.exit("plantilla.csv no tiene respuestas válidas; complétala primero.")

    gh = GRID_H[:2] if args.rapido else GRID_H
    ga = GRID_A[:2] if args.rapido else GRID_A

    print(f"Precalculando {len(d)} escenas...")
    cache = precalcular(d)
    ids = list(cache)
    hum = {i: cache[i]["humano"] for i in ids}

    print(f"Explorando {len(gh) * len(ga)} combinaciones...")
    pred = {(h, a): {i: banda(contar(cache[i], h, a)) for i in ids}
            for h in gh for a in ga}
    combos = list(pred)

    y = [hum[i] for i in ids]
    mejor = max(combos, key=lambda c: kappa_pond(y, [pred[c][i] for i in ids]))

    # Leave-one-out: la combinación se elige sin ver la escena que se predice.
    elegidas, y_loo, x_loo = [], [], []
    for hold in ids:
        resto = [i for i in ids if i != hold]
        yr = [hum[i] for i in resto]
        c = max(combos, key=lambda c: kappa_pond(yr, [pred[c][i] for i in resto]))
        elegidas.append(c)
        y_loo.append(hum[hold])
        x_loo.append(pred[c][hold])

    x_e2 = [banda(cache[i]["auto"]) for i in ids]
    x_hib = [pred[mejor][i] for i in ids]

    def linea(nombre, x):
        ac = 100 * np.mean([a == b for a, b in zip(y, x)])
        print(f"  {nombre:38s} acuerdo {ac:3.0f}%  kappa {kappa_pond(y, x, None):5.2f}"
              f"  ponderado {kappa_pond(y, x):5.2f}")

    print(f"\nn = {len(ids)} escenas con conteo humano\n")
    linea("conteo basado en máscara (E2)", x_e2)
    linea(f"híbrido calibrado h={mejor[0]}, área={mejor[1]}", x_hib)
    print(f"\n  leave-one-out: kappa {kappa_pond(y_loo, x_loo, None):.2f}  "
          f"ponderado {kappa_pond(y_loo, x_loo):.2f}")
    print(f"  combinación elegida en los pliegues: {Counter(elegidas).most_common(2)}")

    # Bootstrap de la diferencia: sin esto, una mejora de 0,04 sobre n=24 no significa nada.
    rng = np.random.default_rng(0)
    ya, xh, xe = np.array(y), np.array(x_hib), np.array(x_e2)
    dif = []
    for _ in range(4000):
        b = rng.integers(0, len(ya), len(ya))
        a, c = kappa_pond(ya[b], xh[b]), kappa_pond(ya[b], xe[b])
        if not (np.isnan(a) or np.isnan(c)):
            dif.append(a - c)
    dif = np.array(dif)
    lo, hi = np.percentile(dif, [2.5, 97.5])
    print(f"\nDiferencia (híbrido - E2) en kappa ponderado: {dif.mean():+.3f}"
          f"   IC95% [{lo:+.2f}, {hi:+.2f}]")
    print(f"  el híbrido gana en el {100 * (dif > 0).mean():.0f}% de los remuestreos")
    if lo < 0 < hi:
        print("  El intervalo contiene el cero: la mejora NO es demostrable con esta muestra.")
    else:
        print("  El intervalo excluye el cero: la diferencia es distinguible.")

    idx = {b: i for i, b in enumerate(BANDAS)}
    for nombre, x in (("E2", x_e2), ("híbrido", x_hib)):
        dd = np.array([idx[a] for a in x]) - np.array([idx[a] for a in y])
        print(f"  {nombre:8s} por encima {int((dd > 0).sum()):2d}  "
              f"por debajo {int((dd < 0).sum()):2d}")


if __name__ == "__main__":
    main()
