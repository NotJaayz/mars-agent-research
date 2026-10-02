#!/usr/bin/env python
"""Acuerdo del segmentador con cada fuente de etiqueta: error con signo, IC y Bland-Altman.

Responde a la revisión: una correlación alta no identifica sesgo, ni una mediana de error
próxima a cero basta para declarar un modelo insesgado si la dispersión es grande. Para cada
referencia (muestra aleatoria colaborativa no usada en el entrenamiento, y máscaras de
experto) se reportan:

  - media y mediana del error con signo (modelo - etiqueta), con IC95 bootstrap;
  - error absoluto medio y proporción de escenas con error > 10, 25 y 50 puntos;
  - el error por tramos de cobertura y por tipo de escena;
  - límites de acuerdo de Bland y Altman (media +- 1,96 desviaciones típicas).

La cobertura del modelo se mide sobre los mismos píxeles que la etiqueta, de modo que el
error mide el desacuerdo en la clase asignada y no en la selección de píxeles.

Entrada: outputs/fuente_anotacion.csv (scripts/eval_fuente_anotacion.py).
Uso:  python scripts/eval_modelo_detalle.py
"""
from __future__ import annotations

import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

plt.rcParams.update({"figure.dpi": 200, "savefig.dpi": 200, "font.size": 10,
                     "font.family": "sans-serif", "axes.spines.top": False,
                     "axes.spines.right": False, "axes.grid": True, "grid.alpha": 0.3})
BLUE, ROCK = "#2c6fbb", "#c0392b"
TRAMOS = [-0.01, 0, 25, 50, 75, 99.99, 100]
ETQ = ["0", "0–25", "25–50", "50–75", "75–99,99", "100"]


def ic(v, f, n=2000, seed=0):
    rng = np.random.default_rng(seed)
    b = [f(rng.choice(v, len(v))) for _ in range(n)]
    return [float(np.percentile(b, 2.5)), float(np.percentile(b, 97.5))]


def resumen(e):
    return {"n": int(len(e)), "media": float(e.mean()), "ic95_media": ic(e, np.mean),
            "mediana": float(np.median(e)), "ic95_mediana": ic(e, np.median),
            "mae": float(np.abs(e).mean()), "ic95_mae": ic(np.abs(e), np.mean),
            "de": float(e.std(ddof=1)),
            "loa": [float(e.mean() - 1.96 * e.std(ddof=1)), float(e.mean() + 1.96 * e.std(ddof=1))],
            "pct_mas_10": float(100 * (np.abs(e) > 10).mean()),
            "pct_mas_25": float(100 * (np.abs(e) > 25).mean()),
            "pct_mas_50": float(100 * (np.abs(e) > 50).mean())}


def main():
    d = pd.read_csv("outputs/fuente_anotacion.csv")
    tipos = pd.concat([pd.read_csv("outputs/results.csv")[["image_id", "scene_type"]],
                       pd.read_csv("outputs/results_test_masked-gold-min1-100agree.csv")[["image_id", "scene_type"]]])
    d = d.merge(tipos, on="image_id", how="left")
    d["error"] = d.cob_modelo_val - d.cob_etiqueta
    d["tramo"] = pd.cut(d.cob_etiqueta, TRAMOS, labels=ETQ)

    out = {}
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.3), sharey=True)
    for ax, (fuente, nom) in zip(axes, (("colaborativa", "Referencia colaborativa"),
                                        ("experto", "Referencia de experto"))):
        s = d[d.fuente == fuente]
        r = resumen(s.error.to_numpy())
        r["por_tramo"] = {str(k): {"n": int(len(g)), "media": float(g.error.mean()),
                                   "mae": float(g.error.abs().mean())}
                          for k, g in s.groupby("tramo", observed=True) if len(g)}
        r["por_tipo"] = {str(k): {"n": int(len(g)), "media": float(g.error.mean()),
                                  "mae": float(g.error.abs().mean())}
                         for k, g in s.groupby("scene_type") if len(g) >= 5}
        out[fuente] = r
        m = (s.cob_modelo_val + s.cob_etiqueta) / 2
        ax.scatter(m, s.error, s=14, alpha=0.45, color=BLUE, edgecolor="none")
        ax.axhline(r["media"], color=ROCK, lw=1.4, label=f"media {r['media']:+.1f}".replace(".", ","))
        for y in r["loa"]:
            ax.axhline(y, color=ROCK, lw=1, ls="--")
        ax.axhline(0, color="black", lw=0.6)
        ax.set_title(f"{nom} (n = {r['n']})")
        ax.set_xlabel("media de modelo y etiqueta (%)")
        ax.text(101, r["loa"][1], f" +1,96 DE\n {r['loa'][1]:+.1f}".replace(".", ","), va="center", fontsize=8, color=ROCK)
        ax.text(101, r["loa"][0], f" −1,96 DE\n {r['loa'][0]:+.1f}".replace(".", ","), va="center", fontsize=8, color=ROCK)
        ax.legend(frameon=False, fontsize=8, loc="upper left")
        ax.set_xlim(-3, 100)
    axes[0].set_ylabel("modelo − etiqueta (p.p.)")
    fig.tight_layout()
    from matplotlib.ticker import FixedLocator, ScalarFormatter
    fig.canvas.draw()
    for a in fig.axes:  # coma decimal en las marcas de los ejes
        for axis in (a.xaxis, a.yaxis):
            if isinstance(axis.get_major_formatter(), ScalarFormatter):
                locs = axis.get_majorticklocs()
                et = [t.get_text().replace(".", ",") for t in axis.get_majorticklabels()]
                axis.set_major_locator(FixedLocator(locs)); axis.set_ticklabels(et)
    fp = Path("outputs/figures/tesis/Figura_29_bland_altman.png")
    fig.savefig(fp, bbox_inches="tight"); plt.close(fig)
    Path("outputs/modelo_detalle.json").write_text(json.dumps(out, indent=2, ensure_ascii=False))

    for f, r in out.items():
        print(f"\n[{f}] n={r['n']}")
        print(f"  error medio   {r['media']:+6.2f}  IC95 [{r['ic95_media'][0]:+.2f}, {r['ic95_media'][1]:+.2f}]")
        print(f"  error mediano {r['mediana']:+6.2f}  IC95 [{r['ic95_mediana'][0]:+.2f}, {r['ic95_mediana'][1]:+.2f}]")
        print(f"  MAE {r['mae']:.2f}  IC95 [{r['ic95_mae'][0]:.2f}, {r['ic95_mae'][1]:.2f}]   límites de acuerdo [{r['loa'][0]:+.1f}, {r['loa'][1]:+.1f}]")
        print(f"  |error| > 10: {r['pct_mas_10']:.1f} %   > 25: {r['pct_mas_25']:.1f} %   > 50: {r['pct_mas_50']:.1f} %")
        print("  por tramo de cobertura:", {k: (v['n'], round(v['media'], 1)) for k, v in r["por_tramo"].items()})
        print("  por tipo de escena:    ", {k: (v['n'], round(v['media'], 1)) for k, v in r["por_tipo"].items()})
    print(f"\n-> {fp}")


if __name__ == "__main__":
    main()
