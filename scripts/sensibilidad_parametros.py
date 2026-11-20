#!/usr/bin/env python
"""Sensibilidad del conteo E2 a sus parámetros principales, frente al conteo humano.

No es una calibración: los parámetros por defecto se congelaron antes de recoger la
validación humana, y ninguna escena de calibración forma parte de la muestra de validación.
Este guion solo describe cuánto cambia el acuerdo con el observador si se mueven los tres
parámetros que más influyen en el conteo —prominencia de la semilla h, suavizado de la
distancia sigma y área mínima—, para mostrar si la conclusión depende de un ajuste fino.
Se calcula frente a las dos rondas del conteo manual sobre las mismas escenas: la primera
(``validacion_manual_v2``, resultado principal) y la repetición (``validacion_manual_v3``).

Uso:  python scripts/sensibilidad_parametros.py
"""
from __future__ import annotations

import itertools
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import cohen_kappa_score

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from src import config, mask_utils as mu, rock_count as rc  # noqa: E402

BANDAS = ["0", "1-3", "4-9", "10-24", "25-49", "50+"]
H = [0.5, 1.0, 2.0, 3.0]
SIGMA = [1.0, 3.0, 5.0]
AREA = [0.00025, 0.0005, 0.001]


def banda(n):
    return ("0" if n == 0 else "1-3" if n <= 3 else "4-9" if n <= 9
            else "10-24" if n <= 24 else "25-49" if n <= 49 else "50+")


RONDAS = {1: "outputs/validacion_manual_v2", 2: "outputs/validacion_manual_v3"}


def main():
    filas = []
    for ronda, carpeta in RONDAS.items():
        filas += evaluar(ronda, carpeta)
    t = pd.DataFrame(filas)
    t.to_csv("outputs/sensibilidad_parametros.csv", index=False)
    for ronda, tr in t.groupby("ronda"):
        print(f"ronda {ronda}: {len(tr)} configuraciones · kappa ponderado: mín {tr.kappa_pond.min():.2f}, "
              f"máx {tr.kappa_pond.max():.2f}, mediana {tr.kappa_pond.median():.2f}")
        print(f"  por defecto: {tr[tr.defecto].kappa_pond.iloc[0]:.2f}")
        print(f"  configuraciones que quedan más veces por debajo que por encima: "
              f"{(tr.abajo > tr.arriba).sum()} de {len(tr)}")
        print(f"  banda máxima alcanzada en cualquier configuración: "
              f"{max(tr.max_banda, key=BANDAS.index)}")


def evaluar(ronda, carpeta):
    d = (pd.read_csv(f"{carpeta}/plantilla.csv", dtype={"banda": str})
           .merge(pd.read_csv(f"{carpeta}/clave.csv"), on="id"))
    regiones = {r.id: mu.big_rock_mask(mu.read_mask(config.MSL_NCAM_LABELS_TRAIN / f"{r.image_id}.png"))
                for r in d.itertuples()}
    y = d.banda.tolist()
    filas = []
    for h, s, a in itertools.product(H, SIGMA, AREA):
        p = {**rc.DEFAULT_PARAMS, "peak_h": h, "distance_sigma": s, "min_area_frac": a}
        x = [banda(len(rc.compute_stages(regiones[i], p)["kept_ids"])) for i in d.id]
        idx = {b: k for k, b in enumerate(BANDAS)}
        dif = np.array([idx[u] for u in x]) - np.array([idx[v] for v in y])
        filas.append({"ronda": ronda, "peak_h": h, "distance_sigma": s, "min_area_frac": a,
                      "defecto": (h, s, a) == (1.0, 3.0, 0.0005),
                      "acuerdo": float(np.mean([u == v for u, v in zip(x, y)])),
                      "kappa": float(cohen_kappa_score(y, x, labels=BANDAS)),
                      "kappa_pond": float(cohen_kappa_score(y, x, labels=BANDAS, weights="linear")),
                      "abajo": int((dif < 0).sum()), "arriba": int((dif > 0).sum()),
                      "max_banda": BANDAS[max(idx[u] for u in x)]})
    return filas


if __name__ == "__main__":
    main()
