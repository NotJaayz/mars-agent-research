#!/usr/bin/env python
"""Genera el panel de visualización (archivo HTML autocontenido).

El panel se abre con doble clic: no requiere servidor, conexión ni ejecutar código. Los
datos se incrustan en el propio archivo y las gráficas se dibujan en SVG, de modo que
funcione sin dependencias externas.

Los logotipos se toman de ``assets/logo_externado.png`` y ``assets/logo_nasa.png`` si
existen; si no, se muestra un encabezado de texto equivalente.

Uso:  python scripts/make_dashboard.py
"""
from __future__ import annotations

import base64
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from src import poblaciones, priorizacion as pz  # noqa: E402

SALIDA = Path("outputs/panel_ai4mars.html")


def _logo(nombre: str) -> str:
    """Devuelve el logotipo en base64 si el archivo existe."""
    p = Path("assets") / nombre
    if p.exists():
        return "data:image/png;base64," + base64.b64encode(p.read_bytes()).decode()
    return ""


def construir_datos() -> dict:
    df = pd.read_csv("outputs/priorizacion.csv")
    lab = df[df.frac_valid > 0]
    rb = df[df.rock_coverage_pct.fillna(0) > 0]
    ok = poblaciones.poblacion_e2(df)

    # Histograma de cobertura
    bins = np.linspace(0, 100, 21)
    h_cov, _ = np.histogram(rb.rock_coverage_pct.dropna(), bins=bins)

    # Serie a lo largo de la secuencia de adquisición (reloj de nave)
    d = df[df.quality_flag.isin(["ok", "no_bigrock", "no_rock"])].copy()
    d = d.dropna(subset=["sclk"]).sort_values("sclk")
    d["bin"] = pd.qcut(d.sclk, q=40, labels=False, duplicates="drop")
    g = d.groupby("bin")
    secuencia = {
        "cobertura": [round(float(v), 1) for v in g.rock_coverage_pct.median()],
        "priorizadas": [round(100 * float(v), 1) for v in
                    g.apply(lambda x: (x.nivel_prioridad != "sin_prioridad").mean(),
                            include_groups=False)],
    }

    # Escenas con alguna regla de prioridad, ordenadas por nivel (para la tabla explorable)
    orden = {"alta": 0, "media": 1, "baja": 2}
    pri = df[df.nivel_prioridad != "sin_prioridad"].copy()
    pri["_o"] = pri.nivel_prioridad.map(orden)
    pri = pri.sort_values(["_o", "n_reglas"], ascending=[True, False]).head(300)
    tabla = pri[["image_id", "nivel_prioridad", "reglas_activadas", "rock_coverage_pct",
                        "n_rocks", "largest_rock_pct", "pct_sand", "scene_type"]].fillna(0)

    datos = {
        "kpi": {
            "imagenes": int(len(df)),
            "con_roca": int(len(rb)),
            "rocas": poblaciones.resumen_e2(df)["n_rocas"],
            "prioridad_alta": int((df.nivel_prioridad == "alta").sum()),
            "priorizadas": int((df.nivel_prioridad != "sin_prioridad").sum()),
        },
        "cobertura_hist": {"bins": [round(b) for b in bins[:-1]], "vals": h_cov.tolist()},
        "escenas": lab.scene_type.value_counts().to_dict(),
        "tamanos": {"Pequeña": int(ok.n_small.sum()), "Mediana": int(ok.n_medium.sum()),
                    "Grande": int(ok.n_large.sum())},
        "niveles": df.nivel_prioridad.value_counts().to_dict(),
        "conteo_reglas": {r.clave: int(df.reglas_activadas.fillna("").str.contains(r.clave).sum())
                          for r in pz.REGLAS},
        "catalogo": [{"clave": r.clave, "titulo": r.titulo, "peso": r.peso,
                      "criterio": r.criterio, "motivo": r.motivo} for r in pz.REGLAS],
        "secuencia": secuencia,
        "tabla": tabla.to_dict("records"),
    }

    # Geología M2020, si el análisis se ha ejecutado
    geo = Path("outputs/geologia_m2020_resumen.json")
    datos["geologia"] = json.loads(geo.read_text()) if geo.exists() else None
    return datos


def main() -> None:
    datos = construir_datos()
    plantilla = Path("scripts/dashboard_template.html").read_text(encoding="utf-8")
    html = (plantilla
            .replace("__DATOS__", json.dumps(datos, ensure_ascii=False))
            .replace("__LOGO_EXTERNADO__", _logo("logo_externado.png"))
            .replace("__LOGO_NASA__", _logo("logo_nasa.png")))
    SALIDA.parent.mkdir(parents=True, exist_ok=True)
    SALIDA.write_text(html, encoding="utf-8")
    kb = SALIDA.stat().st_size / 1024
    print(f"Panel generado: {SALIDA}  ({kb:.0f} KB)")
    print("Ábrelo con doble clic; no requiere servidor ni conexión.")
    for n in ("logo_externado.png", "logo_nasa.png"):
        if not (Path("assets") / n).exists():
            print(f"  (falta assets/{n}: se usa encabezado de texto)")


if __name__ == "__main__":
    main()
