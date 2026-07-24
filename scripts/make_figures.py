#!/usr/bin/env python
"""Figuras descriptivas (E3) a partir de ``outputs/results.csv``.

Genera en ``outputs/figures/analisis/``:
  1. Distribución de la cobertura de roca visible (válidos vs. total).
  2. Distribución del conteo de rocas (por bandas) en imágenes con big rock.
  3. Cobertura vs. fracción etiquetada (evidencia de que la cobertura no es artefacto).
  4. Composición del conjunto por bandera de calidad.

Uso:  python scripts/make_figures.py [--csv outputs/results.csv]
"""
from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

plt.rcParams.update({
    "figure.dpi": 120, "savefig.dpi": 120, "font.size": 11,
    "axes.spines.top": False, "axes.spines.right": False, "axes.grid": True,
    "grid.alpha": 0.3,
})
ROCK = "#c0392b"     # rojo (roca)
BLUE = "#2c6fbb"


def fig_cobertura(df: pd.DataFrame, outdir: Path) -> None:
    rb = df[df.rock_coverage_pct.fillna(0) > 0]
    fig, ax = plt.subplots(1, 2, figsize=(13, 4.5))
    bins = np.linspace(0, 100, 41)
    ax[0].hist(rb.rock_coverage_pct, bins=bins, color=ROCK, alpha=0.85)
    ax[0].axvline(rb.rock_coverage_pct.median(), color="k", ls="--", lw=1,
                  label=f"mediana {rb.rock_coverage_pct.median():.1f}%")
    ax[0].set(title="Cobertura sobre píxeles válidos (indicador E1)",
              xlabel="cobertura de roca (%)", ylabel="nº de imágenes")
    ax[0].legend()
    ax[1].hist(rb.coverage_total_pct, bins=bins, color=BLUE, alpha=0.85)
    ax[1].axvline(rb.coverage_total_pct.median(), color="k", ls="--", lw=1,
                  label=f"mediana {rb.coverage_total_pct.median():.1f}%")
    ax[1].set(title="Cobertura sobre la imagen completa (cota inferior)",
              xlabel="cobertura de roca (%)", ylabel="nº de imágenes")
    ax[1].legend()
    fig.suptitle(f"Distribución de la cobertura de roca visible  (n={len(rb):,} imágenes con roca)",
                 fontsize=13)
    fig.tight_layout(rect=(0, 0, 1, 0.95))
    fig.savefig(outdir / "01_cobertura_hist.png", bbox_inches="tight")
    plt.close(fig)


def fig_conteo(df: pd.DataFrame, outdir: Path) -> None:
    ok = df[df.quality_flag == "ok"]
    bands = [("1", (ok.n_rocks == 1).sum()),
             ("2–3", ((ok.n_rocks >= 2) & (ok.n_rocks <= 3)).sum()),
             ("4–9", ((ok.n_rocks >= 4) & (ok.n_rocks <= 9)).sum()),
             ("10+", (ok.n_rocks >= 10).sum())]
    labels = [b[0] for b in bands]
    vals = [int(b[1]) for b in bands]
    fig, ax = plt.subplots(figsize=(7.5, 4.8))
    bars = ax.bar(labels, vals, color=ROCK, alpha=0.85)
    for bar, v in zip(bars, vals):
        ax.text(bar.get_x() + bar.get_width() / 2, v, f"{v}\n({100*v/len(ok):.0f}%)",
                ha="center", va="bottom", fontsize=10)
    ax.set(title=f"Conteo de rocas por imagen (n={len(ok):,} con big rock)\n"
                 f"media={ok.n_rocks.mean():.2f}  mediana={int(ok.n_rocks.median())}  máx={int(ok.n_rocks.max())}",
           xlabel="nº de rocas detectadas", ylabel="nº de imágenes")
    ax.margins(y=0.15)
    fig.tight_layout()
    fig.savefig(outdir / "02_conteo_bandas.png", bbox_inches="tight")
    plt.close(fig)


def fig_cov_vs_valid(df: pd.DataFrame, outdir: Path) -> None:
    rb = df[(df.rock_coverage_pct.notna()) & (df.frac_valid.notna())]
    x = rb.frac_valid * 100
    y = rb.rock_coverage_pct
    r = np.corrcoef(x, y)[0, 1]
    fig, ax = plt.subplots(figsize=(7.5, 5.5))
    hb = ax.hexbin(x, y, gridsize=45, cmap="magma", mincnt=1, bins="log")
    fig.colorbar(hb, ax=ax, label="nº de imágenes (log)")
    ax.set(title=f"La cobertura NO depende de cuánto se etiquetó  (r = {r:.03f})",
           xlabel="fracción de la escena etiquetada (%)",
           ylabel="cobertura de roca / válidos (%)")
    fig.tight_layout()
    fig.savefig(outdir / "03_cobertura_vs_fracvalid.png", bbox_inches="tight")
    plt.close(fig)


def fig_quality(df: pd.DataFrame, outdir: Path) -> None:
    order = ["ok", "no_bigrock", "no_rock", "mostly_null", "empty"]
    counts = df.quality_flag.value_counts().reindex(order).fillna(0).astype(int)
    colors = {"ok": ROCK, "no_bigrock": "#e08214", "no_rock": "#c7b299",
              "mostly_null": "#9e9e9e", "empty": "#4d4d4d"}
    fig, ax = plt.subplots(figsize=(8.5, 4.5))
    bars = ax.barh(counts.index[::-1], counts.values[::-1],
                   color=[colors[k] for k in counts.index[::-1]])
    for bar, v in zip(bars, counts.values[::-1]):
        ax.text(v, bar.get_y() + bar.get_height() / 2, f" {v:,} ({100*v/len(df):.0f}%)",
                va="center", fontsize=10)
    ax.set(title=f"Composición del conjunto por calidad (n={len(df):,})",
           xlabel="nº de imágenes")
    ax.margins(x=0.15)
    ax.grid(axis="y")
    fig.tight_layout()
    fig.savefig(outdir / "04_quality_flags.png", bbox_inches="tight")
    plt.close(fig)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--csv", default="outputs/results.csv")
    ap.add_argument("--outdir", default="outputs/figures/analisis")
    args = ap.parse_args()

    df = pd.read_csv(args.csv)
    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    fig_cobertura(df, outdir)
    fig_conteo(df, outdir)
    fig_cov_vs_valid(df, outdir)
    fig_quality(df, outdir)
    print(f"OK: 4 figuras en {outdir}/")


if __name__ == "__main__":
    main()
