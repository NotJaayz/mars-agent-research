#!/usr/bin/env python
"""Compara el conteo manual por bandas con el conteo automático (§8.9).

Lee ``plantilla.csv`` una vez completada y ``clave.csv``, y produce:
  - porcentaje de acuerdo y coeficiente kappa de Cohen (acuerdo corregido por azar),
  - matriz de acuerdo entre bandas,
  - dirección del desacuerdo (si el algoritmo sobreestima o subestima),
  - figura ``Figura_23_validacion_manual.png`` en formato tesis.

Uso:  python scripts/eval_validation.py
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

BANDAS = ["0", "1-3", "4-9", "10+"]


def banda(v: int) -> str:
    return "0" if v == 0 else "1-3" if v <= 3 else "4-9" if v <= 9 else "10+"


def kappa(a: pd.Series, b: pd.Series) -> float:
    """Kappa de Cohen: acuerdo observado corregido por el esperado al azar."""
    cats = BANDAS
    n = len(a)
    po = (a.values == b.values).mean()
    pe = sum((a == c).mean() * (b == c).mean() for c in cats)
    return (po - pe) / (1 - pe) if pe < 1 else float("nan")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--dir", default="outputs/validacion_manual")
    args = ap.parse_args()
    d = Path(args.dir)

    plantilla = pd.read_csv(d / "plantilla.csv", dtype={"banda": str})
    clave = pd.read_csv(d / "clave.csv")
    m = plantilla.merge(clave, on="id")
    m["banda"] = m.banda.astype(str).str.strip()

    sin_responder = m[~m.banda.isin(BANDAS)]
    if len(sin_responder):
        print(f"AVISO: {len(sin_responder)} filas sin banda válida; se excluyen.")
        print(f"       valores admitidos: {', '.join(BANDAS)}")
        m = m[m.banda.isin(BANDAS)]
    if m.empty:
        sys.exit("No hay respuestas válidas en plantilla.csv.")

    m["banda_auto"] = m.auto.map(banda)
    acuerdo = (m.banda == m.banda_auto).mean() * 100
    k = kappa(m.banda, m.banda_auto)

    idx = {b: i for i, b in enumerate(BANDAS)}
    dif = m.banda_auto.map(idx) - m.banda.map(idx)

    print(f"n = {len(m)} escenas evaluadas")
    print(f"Acuerdo exacto de banda : {acuerdo:.0f} %")
    print(f"Kappa de Cohen          : {k:.2f}")
    print(f"El algoritmo sitúa la escena en una banda superior en {int((dif>0).sum())} casos "
          f"e inferior en {int((dif<0).sum())}.")

    M = pd.crosstab(m.banda, m.banda_auto).reindex(index=BANDAS, columns=BANDAS,
                                                   fill_value=0)
    print("\nMatriz de acuerdo (filas = conteo manual, columnas = algoritmo):")
    print(M.to_string())

    fig, ax = plt.subplots(figsize=(4.8, 4.2))
    im = ax.imshow(M.values, cmap="Blues")
    ax.set_xticks(range(len(BANDAS))); ax.set_xticklabels(BANDAS)
    ax.set_yticks(range(len(BANDAS))); ax.set_yticklabels(BANDAS)
    ax.set(xlabel="banda según el algoritmo", ylabel="banda según el conteo manual")
    ax.grid(False)
    for i in range(len(BANDAS)):
        for j in range(len(BANDAS)):
            v = M.values[i, j]
            ax.text(j, i, v, ha="center", va="center", fontsize=11,
                    color="white" if v > M.values.max() / 2 else "black")
    fig.colorbar(im, ax=ax, label="número de escenas"); fig.tight_layout()
    out = Path("outputs/figures/tesis/Figura_23_validacion_manual.png")
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out, dpi=200, bbox_inches="tight")
    print(f"\nFigura -> {out}")


if __name__ == "__main__":
    main()
