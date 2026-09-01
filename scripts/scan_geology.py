#!/usr/bin/env python
"""Detección de rasgos geológicos de interés en las anotaciones M2020_GEO (Perseverance).

Extensión al subconjunto principal del estudio. La taxonomía geológica de Mars 2020
distingue rasgos que la escala de navegación no recoge, entre ellos las **vetas**
(``vein``), depósitos minerales precipitados por circulación de agua y por tanto de
interés científico directo.

Para cada máscara se registra la presencia y extensión de los rasgos relevantes y se emite
un aviso cuando aparece alguno poco frecuente.

Nota de alcance: M2020 queda fuera del subconjunto declarado en la metodología (MSL
NavCam); este análisis se reporta como demostración de la extensibilidad del procedimiento.

Uso:  python scripts/scan_geology.py
"""
from __future__ import annotations

import glob
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from src import config  # noqa: E402

# Clases de la taxonomía geológica agrupadas por interés
VETA = 40
GUIJARROS = 30
COLINA = 50
FLOAT_ROCK = list(range(10, 18))     # bloques sueltos (no anclados al lecho)
BEDROCK = list(range(0, 7))
ARENA = [20, 21, 22]
NULL = 255


def main() -> None:
    root = config.AI4MARS_ROOT / "m2020" / "labels" / "M2020_GEO"
    files = sorted(glob.glob(str(root / "**" / "*.png"), recursive=True))
    if not files:
        sys.exit(f"No se encontraron máscaras en {root}")
    print(f"Analizando {len(files):,} máscaras M2020_GEO...", flush=True)

    filas = []
    for i, f in enumerate(files, 1):
        a = np.asarray(Image.open(f), dtype=np.uint8)
        valid = a != NULL
        nv = int(valid.sum())
        if nv == 0:
            continue
        n_veta = int((a == VETA).sum())
        n_float = int(np.isin(a, FLOAT_ROCK).sum())
        filas.append({
            "image_id": Path(f).stem,
            "frac_valid": round(nv / a.size, 4),
            "pct_veta": round(100 * n_veta / nv, 4),
            "pct_guijarros": round(100 * (a == GUIJARROS).sum() / nv, 2),
            "pct_float_rock": round(100 * n_float / nv, 2),
            "pct_bedrock": round(100 * np.isin(a, BEDROCK).sum() / nv, 2),
            "pct_arena": round(100 * np.isin(a, ARENA).sum() / nv, 2),
            "pct_colina": round(100 * (a == COLINA).sum() / nv, 2),
            "tiene_veta": n_veta > 0,
        })
        if i % 1000 == 0:
            print(f"  ...{i:,}", flush=True)

    df = pd.DataFrame(filas)
    # Aviso de interés científico: presencia de veta; se gradúa por extensión.
    df["alerta_veta"] = np.where(
        df.pct_veta >= 0.5, "veta_destacada",
        np.where(df.tiene_veta, "veta_presente", ""))
    df.to_csv("outputs/geologia_m2020.csv", index=False)

    con_veta = int(df.tiene_veta.sum())
    resumen = {
        "n_mascaras": len(df),
        "con_veta": con_veta,
        "pct_con_veta": round(100 * con_veta / len(df), 2),
        "veta_destacada": int((df.alerta_veta == "veta_destacada").sum()),
        "pct_area_veta_media": round(float(df.pct_veta.mean()), 4),
        "con_float_rock": int((df.pct_float_rock > 0).sum()),
        "con_guijarros": int((df.pct_guijarros > 0).sum()),
    }
    Path("outputs/geologia_m2020_resumen.json").write_text(
        json.dumps(resumen, indent=2, ensure_ascii=False))

    print(f"\n{len(df):,} máscaras con anotación")
    print(f"  con veta            : {con_veta:,} ({resumen['pct_con_veta']} %)")
    print(f"  veta destacada      : {resumen['veta_destacada']:,} (>= 0,5 % del área)")
    print(f"  con bloques sueltos : {resumen['con_float_rock']:,}")
    print("\n-> outputs/geologia_m2020.csv")


if __name__ == "__main__":
    main()
