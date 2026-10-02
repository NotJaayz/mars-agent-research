#!/usr/bin/env python
"""Figuras de la extensión aplicada: reglas de priorización y exploración de vetas.

Continúa la numeración de ``make_thesis_figures.py``. Genera:

  Figura 24 — distribución de escenas por nivel de prioridad y reglas por tipo.
  Figura 25 — desempeño del detector de vetas frente a la tasa base, por escena.

Uso:  python scripts/make_extension_figures.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

plt.rcParams.update({
    "figure.dpi": 200, "savefig.dpi": 200, "font.size": 10,
    "font.family": "sans-serif",
    "axes.spines.top": False, "axes.spines.right": False,
    "axes.grid": True, "grid.alpha": 0.3, "axes.titlesize": 10,
})
ROCK, BLUE, GREY = "#c0392b", "#2c6fbb", "#9e9e9e"
OUT = Path("outputs/figures/tesis")

# Nombre legible de cada regla, para no rotular con la clave interna.
from src import priorizacion as pz  # noqa: E402
TITULOS = {r.clave: r.titulo for r in pz.REGLAS}
NIVELES = pz.NIVELES
ETIQ_NIVEL = {"sin_prioridad": "sin prioridad", "baja": "baja", "media": "media", "alta": "alta"}


def miles(v) -> str:
    """Entero con la norma del documento: sin separador hasta cuatro cifras, punto desde cinco."""
    v = int(v)
    return str(v) if abs(v) < 10000 else f"{v:,}".replace(",", ".")


def save(fig, n: int, slug: str) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    path = OUT / f"Figura_{n}_{slug}.png"
    fig.savefig(path, bbox_inches="tight")
    plt.close(fig)
    print(f"  Figura {n:>2}  {path.name}")


def figura_priorizacion(resumen: dict) -> None:
    fig, ax = plt.subplots(1, 2, figsize=(11, 4.2))

    niveles = [n for n in NIVELES if n in resumen["por_nivel"]]
    vals = [resumen["por_nivel"][n] for n in niveles]
    colores = {"sin_prioridad": GREY, "baja": BLUE, "media": "#e67e22", "alta": ROCK}
    b = ax[0].bar([ETIQ_NIVEL[n] for n in niveles], vals,
                  color=[colores[n] for n in niveles])
    ax[0].bar_label(b, labels=[miles(v) for v in vals], padding=2, fontsize=9)
    ax[0].set_yscale("log")   # sin_prioridad domina por dos órdenes de magnitud
    ax[0].set_ylabel("escenas (escala logarítmica)")
    ax[0].set_title("Escenas por nivel de prioridad")

    por = pd.Series(resumen["por_regla"]).sort_values()
    b2 = ax[1].barh([TITULOS.get(k, k) for k in por.index], por.values, color=BLUE)
    ax[1].bar_label(b2, labels=[miles(v) for v in por.values], padding=3, fontsize=9)
    ax[1].set_xlabel("escenas que activan la regla")
    ax[1].set_title("Reglas activadas por tipo")
    ax[1].set_xlim(0, por.max() * 1.18)

    fig.tight_layout()
    save(fig, 24, "priorizacion")


def figura_vetas(d: pd.DataFrame) -> None:
    fig, ax = plt.subplots(1, 2, figsize=(11, 4.2))

    o = d.sort_values("mejora_gris", ascending=False).reset_index(drop=True)
    x = np.arange(len(o))
    ax[0].bar(x, o.mejora_gris, color=[GREY if v == 0 else BLUE for v in o.mejora_gris])
    ax[0].axhline(1, color=ROCK, lw=1.2, ls="--", label="nivel del azar")
    ax[0].set_xlabel("escenas, ordenadas por desempeño")
    ax[0].set_ylabel("precisión / tasa base")
    ax[0].set_title("Mejora sobre el azar por escena")
    ax[0].legend(frameon=False, fontsize=9)
    n0 = int((o.mejora_gris == 0).sum())
    ax[0].annotate(f"{n0} de {len(o)} escenas\nsin ningún acierto",
                   xy=(len(o) - n0 / 2, 0), xytext=(len(o) * 0.55, o.mejora_gris.max() * 0.45),
                   fontsize=9, color=GREY,
                   arrowprops=dict(arrowstyle="->", color=GREY, lw=1))

    ax[1].scatter(d.recall_gris, d.precision_gris, s=42, color=BLUE,
                  edgecolor="white", linewidth=0.6, label="sin color")
    ax[1].scatter(d.recall_color, d.precision_color, s=42, color=ROCK, marker="^",
                  edgecolor="white", linewidth=0.6, label="con color")
    ax[1].set_xlabel("recall")
    ax[1].set_ylabel("precisión")
    ax[1].set_title("Precisión frente a recall")
    ax[1].legend(frameon=False, fontsize=9)

    fig.tight_layout()
    save(fig, 25, "exploracion_vetas")


def main() -> None:
    resumen_p = Path("outputs/priorizacion_resumen.json")
    vetas_p = Path("outputs/exploracion_vetas.csv")
    if not resumen_p.exists():
        sys.exit("Falta outputs/priorizacion_resumen.json; ejecuta scripts/run_priorizacion.py")
    if not vetas_p.exists():
        sys.exit("Falta outputs/exploracion_vetas.csv; "
                 "ejecuta scripts/explore_vein_detection.py")

    figura_priorizacion(json.loads(resumen_p.read_text()))
    figura_vetas(pd.read_csv(vetas_p))


if __name__ == "__main__":
    main()
