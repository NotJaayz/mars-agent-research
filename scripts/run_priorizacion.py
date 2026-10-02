#!/usr/bin/env python
"""Aplica las reglas heurísticas de priorización a outputs/results.csv.

Produce:
  outputs/priorizacion.csv           resultados con las columnas de priorización añadidas
  outputs/priorizacion_catalogo.csv  definición de cada regla, población y percentil del umbral
  outputs/priorizacion_resumen.json  conteos por nivel de prioridad y por regla

Uso:  python scripts/run_priorizacion.py
"""
from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from src import priorizacion as pz  # noqa: E402


def main() -> None:
    df = pd.read_csv("outputs/results.csv")
    out = pz.evaluar(df)
    out.to_csv("outputs/priorizacion.csv", index=False)
    perc = pz.percentiles_umbral(df)
    cat = pz.catalogo().merge(
        perc.groupby("clave").apply(
            lambda g: "; ".join(f"{r.variable} {r.umbral:g}: percentil {r.percentil:.0f} en {r.poblacion}"
                                for r in g.itertuples()), include_groups=False).rename("percentiles"),
        left_on="clave", right_index=True, how="left")
    cat.to_csv("outputs/priorizacion_catalogo.csv", index=False)

    conteo = Counter(a for s in out.reglas_activadas.fillna("") for a in (s.split("|") if s else []))
    resumen = {"n_imagenes": len(out),
               "por_nivel": {n: int((out.nivel_prioridad == n).sum()) for n in pz.NIVELES},
               "por_regla": {r.clave: int(conteo.get(r.clave, 0)) for r in pz.REGLAS},
               "percentiles_umbral": perc.to_dict("records")}
    Path("outputs/priorizacion_resumen.json").write_text(json.dumps(resumen, indent=2, ensure_ascii=False))
    print(f"{len(out)} escenas evaluadas")
    for n in pz.NIVELES[::-1]:
        print(f"  {n:<14} {resumen['por_nivel'][n]:6d}")
    print(perc.to_string(index=False))
    print("\n-> outputs/priorizacion.csv, priorizacion_catalogo.csv, priorizacion_resumen.json")


if __name__ == "__main__":
    main()
