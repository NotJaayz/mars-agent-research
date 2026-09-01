#!/usr/bin/env python
"""Genera el informe de alertas de terreno a partir de outputs/results.csv.

Produce:
  outputs/alertas.csv          resultados con las columnas de alerta añadidas
  outputs/alertas_catalogo.csv definición de cada regla (criterio y justificación)
  outputs/alertas_resumen.json conteos por nivel y por tipo de alerta

Uso:  python scripts/run_alerts.py
"""
from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from src import alerts  # noqa: E402


def main() -> None:
    df = pd.read_csv("outputs/results.csv")
    out = alerts.evaluar(df)
    out.to_csv("outputs/alertas.csv", index=False)
    alerts.catalogo().to_csv("outputs/alertas_catalogo.csv", index=False)

    conteo = Counter(a for s in out.alertas.fillna("") for a in (s.split("|") if s else []))
    resumen = {
        "n_imagenes": len(out),
        "por_nivel": out.nivel_riesgo.value_counts().to_dict(),
        "por_alerta": dict(conteo),
        "umbrales": {
            "bigrock_pct": alerts.UMBRAL_BIGROCK_PCT,
            "solidez": alerts.UMBRAL_SOLIDEZ,
            "roca_mayor_pct": alerts.UMBRAL_ROCA_MAYOR_PCT,
            "n_rocas": alerts.UMBRAL_N_ROCAS,
            "arena_pct": alerts.UMBRAL_ARENA_PCT,
            "cobertura_alta": alerts.UMBRAL_COBERTURA_ALTA,
        },
    }
    Path("outputs/alertas_resumen.json").write_text(
        json.dumps(resumen, indent=2, ensure_ascii=False))

    print(f"{len(out):,} imágenes evaluadas")
    for k, v in out.nivel_riesgo.value_counts().items():
        print(f"  {k:<12} {v:6,} ({100*v/len(out):.1f} %)")
    print("\nAlertas emitidas:")
    for k, v in conteo.most_common():
        print(f"  {k:<22} {v:6,}")
    print("\n-> outputs/alertas.csv, alertas_catalogo.csv, alertas_resumen.json")


if __name__ == "__main__":
    main()
