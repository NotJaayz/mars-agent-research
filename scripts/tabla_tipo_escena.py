#!/usr/bin/env python
"""Genera tesis/tabla_tipo_escena.tex: los dos indicadores según el tipo de escena (E3).

Para cada tipo de la tipología de escenas (columna ``scene_type``) resume la cobertura sobre
la población de E1 y el conteo sobre la población de E2, usando las columnas de elegibilidad
de results.csv (las mismas que src/poblaciones.py). Solo emplea la biblioteca estándar, de
modo que se ejecuta sin el entorno de cálculo ni el conjunto de datos.

Uso:  python scripts/tabla_tipo_escena.py
"""
from __future__ import annotations

import csv
import statistics
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
ENTRADA = RAIZ / "outputs" / "results.csv"
SALIDA = RAIZ / "tesis" / "tabla_tipo_escena.tex"
TIPOS = [("rocoso", "Rocoso"), ("arenoso", "Arenoso"), ("suelo", "Suelo"), ("mixto", "Mixto")]


def num(x: float, d: int = 0) -> str:
    return rf"\num{{{x:.{d}f}}}"


def pct(x: float, d: int = 1) -> str:
    return rf"\SI{{{x:.{d}f}}}{{\percent}}"


def es(v: str) -> bool:
    return v == "True"


def main() -> None:
    with ENTRADA.open(newline="", encoding="utf-8") as fh:
        filas = list(csv.DictReader(fh))
    lineas = []
    for clave, nombre in TIPOS:
        e1 = [r for r in filas if r["scene_type"] == clave and es(r["is_e1_eligible"])]
        e2 = [r for r in e1 if es(r["is_e2_eligible"])]
        cob = [float(r["rock_coverage_pct"]) for r in e1]
        rocas = [int(r["n_rocks"]) for r in e2]
        con_big = sum(es(r["has_bigrock"]) for r in e1)
        celdas = [
            nombre,
            num(len(e1)),
            pct(statistics.median(cob)),
            pct(100 * con_big / len(e1)),
            num(len(e2)),
            num(statistics.mean(rocas), 2) if rocas else "---",
            num(sum(rocas)) if rocas else "---",
        ]
        lineas.append("    " + " & ".join(celdas) + r" \\")
    e1 = [r for r in filas if es(r["is_e1_eligible"]) and r["scene_type"] != "sin_etiqueta"]
    e2 = [r for r in e1 if es(r["is_e2_eligible"])]
    rocas = [int(r["n_rocks"]) for r in e2]
    total = [
        r"\textbf{Total}",
        num(len(e1)),
        pct(statistics.median(float(r["rock_coverage_pct"]) for r in e1)),
        pct(100 * sum(es(r["has_bigrock"]) for r in e1) / len(e1)),
        num(len(e2)),
        num(statistics.mean(rocas), 2),
        num(sum(rocas)),
    ]
    # \bottomrule va en el propio archivo: tras un \input, LaTeX abre una celda y la regla
    # quedaría fuera de lugar.
    cuerpo = "\n".join(lineas) + "\n    \\midrule\n    " + " & ".join(total) + r" \\" + "\n    \\bottomrule"
    SALIDA.write_text(
        "% Generado por scripts/tabla_tipo_escena.py a partir de outputs/results.csv. No editar a mano.\n"
        + cuerpo + "\n",
        encoding="utf-8",
    )
    print(f"Escrito {SALIDA.relative_to(RAIZ)}")


if __name__ == "__main__":
    main()
