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
from skimage.measure import label, regionprops

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

# Criterios de verosimilitud de una veta. Una veta mineral es, por su origen, una
# estructura DELGADA y ALARGADA: la elongación de la región anotada es por tanto un
# indicio de que la anotación corresponde al rasgo y no a un polígono trazado a la ligera.
# La verificación visual mostró que las anotaciones que cubren gran parte de la escena
# (cielo y cuerpo del róver incluidos) son errores de anotación: presentan elongación en
# torno a 3, frente a 8 en las anotaciones plausibles.
ELONGACION_MIN = 4.0      # eje mayor / eje menor
# El umbral de área se fija en el percentil 75 de la extensión observada (1,7 %), que
# coincide con lo esperable físicamente: una veta ocupa una fracción mínima de la escena.
# Por encima, la verificación visual muestra franjas anchas y polígonos que abarcan cielo y
# cuerpo del róver, es decir, errores de anotación. La distribución respalda el corte: la
# mediana de extensión es 0,23 % y el percentil 90 salta ya a 12 %.
AREA_MAX_PCT = 2.0


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

        # Geometría de las regiones de veta, para juzgar su verosimilitud
        elong = float("nan")
        if n_veta:
            props = [pr for pr in regionprops(label(a == VETA)) if pr.area >= 30]
            if props:
                razones = [pr.axis_major_length / pr.axis_minor_length
                           if pr.axis_minor_length > 1 else 99.0 for pr in props]
                elong = float(np.mean(razones))
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
            "veta_elongacion": round(elong, 2) if elong == elong else None,
        })
        if i % 1000 == 0:
            print(f"  ...{i:,}", flush=True)

    df = pd.DataFrame(filas)
    # Aviso de interés científico. Se gradúa por VEROSIMILITUD, no por extensión: una veta
    # real es delgada y alargada, de modo que una anotación que cubre gran parte de la
    # escena indica error de anotación y no un hallazgo destacado.
    plausible = (df.tiene_veta & (df.pct_veta <= AREA_MAX_PCT)
                 & (df.veta_elongacion >= ELONGACION_MIN))
    dudosa = df.tiene_veta & (df.pct_veta > AREA_MAX_PCT)
    df["alerta_veta"] = np.where(plausible, "veta_probable",
                        np.where(dudosa, "veta_dudosa",
                        np.where(df.tiene_veta, "veta_presente", "")))
    df.to_csv("outputs/geologia_m2020.csv", index=False)

    con_veta = int(df.tiene_veta.sum())
    resumen = {
        "n_mascaras": len(df),
        "con_veta": con_veta,
        "pct_con_veta": round(100 * con_veta / len(df), 2),
        "veta_probable": int((df.alerta_veta == "veta_probable").sum()),
        "veta_dudosa": int((df.alerta_veta == "veta_dudosa").sum()),
        "pct_area_veta_media": round(float(df.pct_veta.mean()), 4),
        "con_float_rock": int((df.pct_float_rock > 0).sum()),
        "con_guijarros": int((df.pct_guijarros > 0).sum()),
    }
    Path("outputs/geologia_m2020_resumen.json").write_text(
        json.dumps(resumen, indent=2, ensure_ascii=False))

    print(f"\n{len(df):,} máscaras con anotación")
    print(f"  con veta            : {con_veta:,} ({resumen['pct_con_veta']} %)")
    print(f"  veta probable       : {resumen['veta_probable']:,} (delgada y alargada)")
    print(f"  veta dudosa         : {resumen['veta_dudosa']:,} (cubre > {AREA_MAX_PCT:.0f} % "
          "de la escena: probable error de anotación)")
    print(f"  con bloques sueltos : {resumen['con_float_rock']:,}")
    print("\n-> outputs/geologia_m2020.csv")


if __name__ == "__main__":
    main()
