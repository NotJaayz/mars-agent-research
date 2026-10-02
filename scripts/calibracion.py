#!/usr/bin/env python
"""Reconstruye la calibración del conteo (E2) a partir de un manifiesto de escenas.

Esquema: muestra de calibración -> parámetros congelados (31-ago-2026, commit 2d93d43)
-> muestra independiente de evaluación (validación humana). Este guion:

1. Lee el manifiesto ``manifiestos/calibracion_escenas.csv`` (seis escenas, versionado).
2. Evalúa sobre ellas las configuraciones consideradas, en el orden en que se probaron:
     A  separación mínima 5 px,  sigma 1   (versión inicial)
     B  separación mínima 15 px, sigma 3
     C  separación mínima 20 px, sigma 3
     D  prominencia h = 1,       sigma 3   (configuración final)
   y registra semillas, componentes conectadas y rocas -> outputs/calibracion_tabla.csv.
3. Verifica el cambio B -> D sobre la población de E2: en las escenas con indicios de
   sobresegmentación según B (solidez media < 0,7 o más de 15 rocas) y en las demás
   -> outputs/calibracion_verificacion.json.
4. Comprueba que ninguna escena de calibración pertenece a la muestra de validación.

Uso:  python scripts/calibracion.py
"""
from __future__ import annotations

import json
import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from src import config, mask_utils as mu, poblaciones, rock_count as rc  # noqa: E402

warnings.filterwarnings("ignore", category=DeprecationWarning)
CONFIGS = {
    "A": {"peak_h": 0.0, "peak_min_distance": 5, "distance_sigma": 1.0},
    "B": {"peak_h": 0.0, "peak_min_distance": 15, "distance_sigma": 3.0},
    "C": {"peak_h": 0.0, "peak_min_distance": 20, "distance_sigma": 3.0},
    "D": {"peak_h": 1.0, "distance_sigma": 3.0},
}


def etapas(iid, cfg):
    b = mu.big_rock_mask(mu.read_mask(config.MSL_NCAM_LABELS_TRAIN / f"{iid}.png"))
    s = rc.compute_stages(b, cfg)
    sol = float(np.mean(s["solidities"])) if s["solidities"] else float("nan")
    return {"semillas": int(len(s["coords"])), "componentes": s["n_raw_components"],
            "rocas": len(s["kept_ids"]), "solidez_media": sol}


def main():
    man = pd.read_csv("manifiestos/calibracion_escenas.csv")
    filas = [{"image_id": r.image_id, "contenido": r.contenido, "config": k, **etapas(r.image_id, cfg)}
             for r in man.itertuples() for k, cfg in CONFIGS.items()]
    tabla = pd.DataFrame(filas)
    tabla.to_csv("outputs/calibracion_tabla.csv", index=False)
    print(tabla.pivot(index="image_id", columns="config", values=["semillas", "rocas"]).to_string())

    # Independencia respecto de la validación humana.
    v2 = set(pd.read_csv("outputs/validacion_manual_v2/clave.csv").image_id)
    piloto = set(pd.read_csv("outputs/validacion_manual/clave.csv").image_id)
    cal = set(man.image_id)

    # Verificación B -> D sobre la población de E2.
    e2 = poblaciones.poblacion_e2(pd.read_csv("outputs/results.csv"))
    rB, rD = [], []
    for iid in e2.image_id:
        rB.append(etapas(iid, CONFIGS["B"])); rD.append(etapas(iid, CONFIGS["D"]))
    v = pd.DataFrame({"image_id": e2.image_id.values,
                      "rocas_B": [x["rocas"] for x in rB], "solidez_B": [x["solidez_media"] for x in rB],
                      "rocas_D": [x["rocas"] for x in rD]})
    baja = v.solidez_B < 0.7; muchas = v.rocas_B > 15; normal = ~(baja | muchas)
    def red(m):
        return float(100 * (1 - v.rocas_D[m].sum() / max(v.rocas_B[m].sum(), 1)))
    out = {"n_e2": int(len(v)),
           "solidez_baja": {"n": int(baja.sum()), "reduccion_pct": red(baja)},
           "mas_de_15": {"n": int(muchas.sum()), "reduccion_pct": red(muchas)},
           "normales": {"n": int(normal.sum()), "sin_cambio": int((v.rocas_B[normal] == v.rocas_D[normal]).sum()),
                        "reduccion_pct": red(normal)},
           "semillas_A_max": int(tabla[tabla.config == "A"].semillas.max()),
           "solapamiento_validacion": len(cal & v2), "solapamiento_piloto": len(cal & piloto)}
    Path("outputs/calibracion_verificacion.json").write_text(json.dumps(out, indent=2, ensure_ascii=False))
    print(json.dumps(out, indent=1, ensure_ascii=False))


if __name__ == "__main__":
    main()
