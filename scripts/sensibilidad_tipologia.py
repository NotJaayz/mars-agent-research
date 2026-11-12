#!/usr/bin/env python
"""Sensibilidad de la tipología de escenas (E3) a sus umbrales. Genera tesis/cifras_tipologia.tex.

La tipología de src/features.py clasifica cada escena por su composición sobre los píxeles
etiquetados: rocosa si lecho rocoso y roca grande suman al menos el 66 %, arenosa si la arena
llega al 50 %, de suelo si el suelo llega al 50 % y mixta en otro caso. Este guion recalcula
la tipología con los umbrales de roca en {60, 66, 70} y los de arena y suelo en {45, 50, 55}
(nueve combinaciones), y para cada una mide cuántas escenas cambian de tipo y si se mantienen
los dos resultados por tipo que cita el documento: la roca grande es más frecuente en las
escenas mixtas y arenosas que en las rocosas, y en ellas se cuentan más rocas por escena.

Solo emplea la biblioteca estándar y results.csv, como scripts/tabla_tipo_escena.py.

Uso:  python scripts/sensibilidad_tipologia.py
"""
from __future__ import annotations

import csv
import statistics
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
ENTRADA = RAIZ / "outputs" / "results.csv"
SALIDA = RAIZ / "tesis" / "cifras_tipologia.tex"
BASE = (66, 50)
ROCA = (60, 66, 70)
OTRAS = (45, 50, 55)


def es(v: str) -> bool:
    return v == "True"


def tipo(r: dict, u_roca: float, u_otra: float) -> str:
    roca = float(r["pct_bedrock"]) + float(r["pct_bigrock"])
    if roca >= u_roca:
        return "rocoso"
    if float(r["pct_sand"]) >= u_otra:
        return "arenoso"
    if float(r["pct_soil"]) >= u_otra:
        return "suelo"
    return "mixto"


def se_mantiene(e1: list[dict], tipos: dict[str, str]) -> bool:
    """Roca grande más frecuente y más rocas por escena en mixtas y arenosas que en rocosas."""
    def con_big(t):
        g = [r for r in e1 if tipos[r["image_id"]] == t]
        return sum(es(r["has_bigrock"]) for r in g) / len(g) if g else 0.0

    def rocas(t):
        g = [int(r["n_rocks"]) for r in e1 if tipos[r["image_id"]] == t and es(r["is_e2_eligible"])]
        return statistics.mean(g) if g else 0.0

    return all(con_big(t) > con_big("rocoso") and rocas(t) > rocas("rocoso") for t in ("mixto", "arenoso"))


def main() -> None:
    with ENTRADA.open(newline="", encoding="utf-8") as fh:
        filas = list(csv.DictReader(fh))
    e1 = [r for r in filas if es(r["is_e1_eligible"]) and r["scene_type"] != "sin_etiqueta"]
    base = {r["image_id"]: tipo(r, *BASE) for r in e1}
    assert all(base[r["image_id"]] == r["scene_type"] for r in e1), "la tipología base no coincide con results.csv"

    cambios, mantiene = [], 0
    for ur in ROCA:
        for uo in OTRAS:
            if (ur, uo) == BASE:
                continue
            t = {r["image_id"]: tipo(r, ur, uo) for r in e1}
            cambios.append(100 * sum(t[k] != base[k] for k in t) / len(t))
            mantiene += se_mantiene(e1, t)

    macros = {
        "cTipoSensN": len(cambios),
        "cTipoSensCambioMin": f"{min(cambios):.1f}",
        "cTipoSensCambioMax": f"{max(cambios):.1f}",
        "cTipoSensMantiene": mantiene,
        "cTipoSensBaseOk": "si" if se_mantiene(e1, base) else "no",
    }
    lineas = ["% Generado por scripts/sensibilidad_tipologia.py: no editar a mano."]
    for k, v in macros.items():
        valor = rf"\num{{{v}}}" if k != "cTipoSensBaseOk" else v
        lineas.append(rf"\newcommand{{\{k}}}{{{valor}}}")
    SALIDA.write_text("\n".join(lineas) + "\n", encoding="utf-8")
    print(f"Escrito {SALIDA.relative_to(RAIZ)}: {macros}")


if __name__ == "__main__":
    main()
