#!/usr/bin/env python
"""Figuras de validación y análisis avanzado a partir de los CSV de resultados.

Genera en ``outputs/figures/analisis/``:
  5. Validación: composición de clases y cobertura, train (crowdsourced) vs experto.
  6. Análisis temporal: cobertura y presencia de roca a lo largo del recorrido
     (orden por reloj de nave, sclk, extraído del nombre de imagen).

Uso:  python scripts/make_analysis.py
"""
from __future__ import annotations

import argparse
import re
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

plt.rcParams.update({
    "figure.dpi": 120, "savefig.dpi": 120, "font.size": 11,
    "axes.spines.top": False, "axes.spines.right": False,
    "axes.grid": True, "grid.alpha": 0.3,
})
ROCK, BLUE, GREY = "#c0392b", "#2c6fbb", "#9e9e9e"
SCLK_RE = re.compile(r"^N[LR][AB]_(\d+)")


def _class_shares(df: pd.DataFrame) -> dict:
    """Comparte de píxeles etiquetados a partir de columnas del CSV (usa n_bigrock y cobertura)."""
    # Reconstruye desde columnas disponibles no es exacto; en su lugar leemos del CSV agregados.
    return {}


def fig_validacion(outdir: Path) -> None:
    train = pd.read_csv("outputs/results.csv")
    exp = pd.read_csv("outputs/results_test_masked-gold-min1-100agree.csv")

    fig, ax = plt.subplots(1, 2, figsize=(13, 4.8))

    # (a) Distribución de cobertura (válidos) train vs experto, imágenes con roca
    bins = np.linspace(0, 100, 26)
    for d, c, lab in [(train, ROCK, "train (crowdsourced)"), (exp, BLUE, "experto (min1)")]:
        rb = d[d.rock_coverage_pct.fillna(0) > 0]
        ax[0].hist(rb.rock_coverage_pct, bins=bins, density=True, histtype="step",
                   lw=2.2, color=c, label=f"{lab}\n(mediana {rb.rock_coverage_pct.median():.0f}%)")
    ax[0].set(title="Cobertura de roca (válidos): train vs experto",
              xlabel="cobertura de roca (%)", ylabel="densidad")
    ax[0].legend(fontsize=9)

    # (b) % de imágenes con roca al 100% de cobertura
    def pct100(d):
        rb = d[d.rock_coverage_pct.fillna(0) > 0]
        return 100 * (rb.rock_coverage_pct == 100).mean()
    labels = ["train\n(crowdsourced)", "experto\n(min1)"]
    vals = [pct100(train), pct100(exp)]
    bars = ax[1].bar(labels, vals, color=[ROCK, BLUE], alpha=0.85, width=0.6)
    for bar, v in zip(bars, vals):
        ax[1].text(bar.get_x() + bar.get_width() / 2, v, f"{v:.0f}%",
                   ha="center", va="bottom")
    ax[1].set(title="Imágenes con roca al 100% de cobertura\n(síntoma del sesgo de etiquetado)",
              ylabel="% de imágenes con roca")
    ax[1].margins(y=0.18)
    fig.suptitle("Validación con etiquetas de experto: la cobertura crowdsourced está sesgada al alza",
                 fontsize=12.5)
    fig.tight_layout(rect=(0, 0, 1, 0.93))
    fig.savefig(outdir / "05_validacion_experto.png", bbox_inches="tight")
    plt.close(fig)


def fig_temporal(outdir: Path, n_bins: int = 40) -> None:
    df = pd.read_csv("outputs/results.csv")
    df = df[df.quality_flag.isin(["ok", "no_bigrock", "no_rock"])].copy()
    df["sclk"] = df.image_id.str.extract(SCLK_RE)[0].astype(float)
    df = df.dropna(subset=["sclk"]).sort_values("sclk").reset_index(drop=True)

    # Binado por cuantiles del recorrido (cada bin = igual nº de imágenes)
    df["bin"] = pd.qcut(df.sclk, q=n_bins, labels=False, duplicates="drop")
    g = df.groupby("bin")
    cov_med = g.rock_coverage_pct.median()
    frac_rock = g.apply(lambda x: (x.n_bigrock > 0).mean() * 100, include_groups=False)
    sclk_mid = g.sclk.median()
    x = (sclk_mid - sclk_mid.min()) / (sclk_mid.max() - sclk_mid.min()) * 100  # 0-100% recorrido

    fig, ax = plt.subplots(2, 1, figsize=(12, 7), sharex=True)
    ax[0].plot(x, cov_med, "-o", color=ROCK, ms=4)
    ax[0].fill_between(x, cov_med, alpha=0.15, color=ROCK)
    ax[0].set(title="Cobertura de roca a lo largo del recorrido de Curiosity (MSL NavCam)",
              ylabel="cobertura mediana\n(% válidos)")
    ax[1].plot(x, frac_rock, "-s", color=BLUE, ms=4)
    ax[1].fill_between(x, frac_rock, alpha=0.15, color=BLUE)
    ax[1].set(title="Presencia de roca grande a lo largo del recorrido",
              ylabel="% de imágenes\ncon big rock",
              xlabel="progreso temporal del recorrido (0 = inicio, 100 = final)  ·  orden por reloj de nave")
    fig.tight_layout()
    fig.savefig(outdir / "06_temporal_recorrido.png", bbox_inches="tight")
    plt.close(fig)


def fig_scene_types(outdir: Path) -> None:
    df = pd.read_csv("outputs/results.csv")
    order = ["rocoso", "suelo", "arenoso", "mixto", "sin_etiqueta"]
    colors = {"rocoso": ROCK, "suelo": "#c7b299", "arenoso": "#f2d479",
              "mixto": "#7b9e89", "sin_etiqueta": GREY}
    counts = df.scene_type.value_counts().reindex(order).fillna(0).astype(int)
    fig, ax = plt.subplots(figsize=(8.5, 4.6))
    bars = ax.bar(counts.index, counts.values, color=[colors[k] for k in counts.index])
    for bar, v in zip(bars, counts.values):
        ax.text(bar.get_x() + bar.get_width() / 2, v, f"{v:,}\n({100*v/len(df):.0f}%)",
                ha="center", va="bottom", fontsize=9)
    ax.set(title=f"Tipología de escena por composición del terreno (n={len(df):,})",
           ylabel="nº de imágenes")
    ax.margins(y=0.15)
    fig.tight_layout()
    fig.savefig(outdir / "07_tipos_escena.png", bbox_inches="tight")
    plt.close(fig)


def fig_size_freq(outdir: Path) -> None:
    df = pd.read_csv("outputs/results.csv")
    ok = df[df.quality_flag == "ok"]
    s, m, l = int(ok.n_small.sum()), int(ok.n_medium.sum()), int(ok.n_large.sum())
    labels = ["pequeña\n(<0.5%)", "mediana\n(0.5–2%)", "grande\n(≥2%)"]
    vals = [s, m, l]
    T = sum(vals)
    fig, ax = plt.subplots(figsize=(7.5, 4.8))
    bars = ax.bar(labels, vals, color=[ "#f0a58f", "#d7654a", ROCK])
    for bar, v in zip(bars, vals):
        ax.text(bar.get_x() + bar.get_width() / 2, v, f"{v:,}\n({100*v/T:.0f}%)",
                ha="center", va="bottom", fontsize=10)
    ax.set(title=f"Distribución tamaño–frecuencia de rocas (n={T:,} rocas)\n"
                 f"tamaño relativo al área de la imagen",
           ylabel="nº de rocas", xlabel="clase de tamaño")
    ax.margins(y=0.15)
    fig.tight_layout()
    fig.savefig(outdir / "08_tamano_frecuencia.png", bbox_inches="tight")
    plt.close(fig)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--outdir", default="outputs/figures/analisis")
    args = ap.parse_args()
    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    fig_validacion(outdir)
    fig_temporal(outdir)
    fig_scene_types(outdir)
    fig_size_freq(outdir)
    print(f"OK: figuras 05–08 en {outdir}/")


if __name__ == "__main__":
    main()
