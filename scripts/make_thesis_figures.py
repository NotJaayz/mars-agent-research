#!/usr/bin/env python
"""Genera las figuras en formato tesis: sin título incrustado y con nombre numerado.

En un documento académico el pie de figura cumple la función del título, de modo que
incrustarlo en la imagen resulta redundante. Este script regenera las figuras del
análisis sin título y copia los paneles del procedimiento sin el encabezado, dejándolas
en ``outputs/figures/tesis/`` con la numeración que usan los capítulos (Figura 11–22 y
un anexo A1–A4).

Los pies de figura correspondientes están en ``docs/figuras_tesis.md``.

Uso:  python scripts/make_thesis_figures.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from src import config, mask_utils as mu, viz  # noqa: E402

plt.rcParams.update({
    "figure.dpi": 200, "savefig.dpi": 200, "font.size": 10,
    "font.family": "sans-serif",
    "axes.spines.top": False, "axes.spines.right": False,
    "axes.grid": True, "grid.alpha": 0.3, "axes.titlesize": 10,
})
ROCK, BLUE, GREY = "#c0392b", "#2c6fbb", "#9e9e9e"
OUT = Path("outputs/figures/tesis")


def save(fig, n: int, slug: str) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    path = OUT / f"Figura_{n}_{slug}.png"
    fig.savefig(path, bbox_inches="tight")
    plt.close(fig)
    print(f"  Figura {n:>2}  {path.name}")


# ---------------------------------------------------------------- paneles del pipeline
def panel(n: int, slug: str, image_id: str) -> None:
    """Panel de 5 etapas sin el encabezado (id y parámetros van en el pie de figura)."""
    msk = config.MSL_NCAM_LABELS_TRAIN / f"{image_id}.png"
    img = mu.mask_to_image_path(msk)
    if img is None:
        print(f"  Figura {n}: sin imagen para {image_id}, se omite"); return
    fig = viz.plot_pipeline(img, msk, params=None, save_path=None, title="")
    if fig._suptitle is not None:
        fig._suptitle.set_visible(False)
    fig.tight_layout()
    save(fig, n, slug)


# ------------------------------------------------------------- figuras del análisis
def fig_quality(df, n):
    order = ["ok", "no_bigrock", "no_rock", "mostly_null", "empty"]
    colors = {"ok": ROCK, "no_bigrock": "#e08214", "no_rock": "#c7b299",
              "mostly_null": GREY, "empty": "#4d4d4d"}
    c = df.quality_flag.value_counts().reindex(order).fillna(0).astype(int)
    fig, ax = plt.subplots(figsize=(7, 3.4))
    bars = ax.barh(c.index[::-1], c.values[::-1], color=[colors[k] for k in c.index[::-1]])
    for b, v in zip(bars, c.values[::-1]):
        ax.text(v, b.get_y() + b.get_height() / 2, f" {v:,} ({100*v/len(df):.0f} %)",
                va="center", fontsize=8.5)
    ax.set_xlabel("número de imágenes"); ax.margins(x=0.18); ax.grid(axis="y")
    save(fig, n, "banderas_calidad")


def fig_coverage(df, n):
    rb = df[df.rock_coverage_pct.fillna(0) > 0]
    bins = np.linspace(0, 100, 41)
    fig, ax = plt.subplots(1, 2, figsize=(9.5, 3.4))
    for a, col, color, lab in [(ax[0], "rock_coverage_pct", ROCK, "sobre píxeles etiquetados"),
                               (ax[1], "coverage_total_pct", BLUE, "sobre la imagen completa")]:
        a.hist(rb[col], bins=bins, color=color, alpha=0.85)
        a.axvline(rb[col].median(), color="k", ls="--", lw=1)
        a.set(xlabel=f"cobertura de roca (%)\n({lab})", ylabel="número de imágenes")
    save(fig, n, "distribucion_cobertura")


def fig_cov_vs_valid(df, n):
    rb = df[df.rock_coverage_pct.notna() & df.frac_valid.notna()]
    fig, ax = plt.subplots(figsize=(5.6, 4.4))
    hb = ax.hexbin(rb.frac_valid * 100, rb.rock_coverage_pct, gridsize=42,
                   cmap="magma", mincnt=1, bins="log")
    fig.colorbar(hb, ax=ax, label="número de imágenes (escala log)")
    ax.set(xlabel="fracción de la escena etiquetada (%)",
           ylabel="cobertura de roca sobre píxeles válidos (%)")
    save(fig, n, "cobertura_vs_fraccion_etiquetada")


def fig_counts(df, n):
    ok = df[df.quality_flag == "ok"]
    bands = [("0", (ok.n_rocks == 0).sum()), ("1", (ok.n_rocks == 1).sum()),
             ("2–3", ((ok.n_rocks >= 2) & (ok.n_rocks <= 3)).sum()),
             ("4–9", ((ok.n_rocks >= 4) & (ok.n_rocks <= 9)).sum()),
             ("10 o más", (ok.n_rocks >= 10).sum())]
    fig, ax = plt.subplots(figsize=(6.2, 3.6))
    bars = ax.bar([b[0] for b in bands], [int(b[1]) for b in bands], color=ROCK, alpha=0.88)
    for b, v in zip(bars, [int(x[1]) for x in bands]):
        ax.text(b.get_x() + b.get_width()/2, v, f"{v}\n({100*v/len(ok):.0f} %)",
                ha="center", va="bottom", fontsize=8.5)
    ax.set(xlabel="rocas contadas por imagen", ylabel="número de imágenes"); ax.margins(y=0.18)
    save(fig, n, "conteo_por_bandas")


def fig_size_freq(df, n):
    ok = df[df.quality_flag == "ok"]
    vals = [int(ok.n_small.sum()), int(ok.n_medium.sum()), int(ok.n_large.sum())]
    labs = ["pequeña\n(< 0,5 %)", "mediana\n(0,5 – 2 %)", "grande\n(≥ 2 %)"]
    T = sum(vals)
    fig, ax = plt.subplots(figsize=(5.6, 3.6))
    bars = ax.bar(labs, vals, color=["#f0a58f", "#d7654a", ROCK])
    for b, v in zip(bars, vals):
        ax.text(b.get_x() + b.get_width()/2, v, f"{v:,}\n({100*v/T:.0f} %)",
                ha="center", va="bottom", fontsize=8.5)
    ax.set(xlabel="clase de tamaño (fracción del área de la imagen)",
           ylabel="número de rocas"); ax.margins(y=0.18)
    save(fig, n, "tamano_frecuencia")


def fig_scenes(df, n):
    order = ["rocoso", "suelo", "arenoso", "mixto"]
    colors = {"rocoso": ROCK, "suelo": "#c7b299", "arenoso": "#f2d479", "mixto": "#7b9e89"}
    c = df.scene_type.value_counts().reindex(order).fillna(0).astype(int)
    fig, ax = plt.subplots(figsize=(6.2, 3.5))
    bars = ax.bar(c.index, c.values, color=[colors[k] for k in c.index])
    for b, v in zip(bars, c.values):
        ax.text(b.get_x() + b.get_width()/2, v, f"{v:,}\n({100*v/len(df):.0f} %)",
                ha="center", va="bottom", fontsize=8.5)
    ax.set(xlabel="tipo de escena", ylabel="número de imágenes"); ax.margins(y=0.18)
    save(fig, n, "tipologia_escenas")


def fig_traverse(df, n, n_bins=40):
    import re
    d = df[df.quality_flag.isin(["ok", "no_bigrock", "no_rock"])].copy()
    d["sclk"] = d.image_id.str.extract(r"^N[LR][AB]_(\d+)")[0].astype(float)
    d = d.dropna(subset=["sclk"]).sort_values("sclk")
    d["bin"] = pd.qcut(d.sclk, q=n_bins, labels=False, duplicates="drop")
    g = d.groupby("bin")
    cov = g.rock_coverage_pct.median()
    presence = g.apply(lambda x: (x.n_bigrock > 0).mean() * 100, include_groups=False)
    mid = g.sclk.median()
    x = (mid - mid.min()) / (mid.max() - mid.min()) * 100
    fig, ax = plt.subplots(2, 1, figsize=(8.5, 4.8), sharex=True)
    ax[0].plot(x, cov, "-o", color=ROCK, ms=3.2)
    ax[0].fill_between(x, cov, alpha=0.15, color=ROCK)
    ax[0].set_ylabel("cobertura mediana\n(% de píxeles válidos)")
    ax[1].plot(x, presence, "-s", color=BLUE, ms=3.2)
    ax[1].fill_between(x, presence, alpha=0.15, color=BLUE)
    ax[1].set(ylabel="imágenes con\nroca grande (%)",
              xlabel="progreso relativo del recorrido (%), según el reloj de nave")
    fig.tight_layout()
    save(fig, n, "variacion_recorrido")


def fig_validation(df, n):
    exp_path = Path("outputs/results_test_masked-gold-min1-100agree.csv")
    if not exp_path.exists():
        print(f"  Figura {n}: falta {exp_path.name}, se omite"); return
    exp = pd.read_csv(exp_path)
    fig, ax = plt.subplots(1, 2, figsize=(9.5, 3.5))
    bins = np.linspace(0, 100, 26)
    for d, c, lab in [(df, ROCK, "colaborativas"), (exp, BLUE, "de experto")]:
        rb = d[d.rock_coverage_pct.fillna(0) > 0]
        ax[0].hist(rb.rock_coverage_pct, bins=bins, density=True, histtype="step",
                   lw=2, color=c, label=f"{lab} (mediana {rb.rock_coverage_pct.median():.0f} %)")
    ax[0].set(xlabel="cobertura de roca (%)", ylabel="densidad"); ax[0].legend(fontsize=8)
    def p100(d):
        rb = d[d.rock_coverage_pct.fillna(0) > 0]
        return 100 * (rb.rock_coverage_pct == 100).mean()
    vals = [p100(df), p100(exp)]
    bars = ax[1].bar(["colaborativas", "de experto"], vals, color=[ROCK, BLUE],
                     alpha=0.88, width=0.55)
    for b, v in zip(bars, vals):
        ax[1].text(b.get_x() + b.get_width()/2, v, f"{v:.0f} %", ha="center",
                   va="bottom", fontsize=9)
    ax[1].set(ylabel="imágenes con cobertura del 100 % (%)",
              xlabel="tipo de etiqueta"); ax[1].margins(y=0.2)
    save(fig, n, "validacion_experto")


def fig_agreement(n):
    p = Path("outputs/comparacion_watershed_sam.csv")
    if not p.exists():
        print(f"  Figura {n}: falta {p.name}, se omite"); return
    comp = pd.read_csv(p)
    band = lambda v: "0" if v == 0 else "1–3" if v <= 3 else "4–9" if v <= 9 else "10+"
    order = ["0", "1–3", "4–9", "10+"]
    comp["wb"] = comp.watershed.map(band); comp["sb"] = comp.sam.map(band)
    M = pd.crosstab(comp.wb, comp.sb).reindex(index=order, columns=order, fill_value=0)
    fig, ax = plt.subplots(figsize=(4.8, 4.2))
    im = ax.imshow(M.values, cmap="Reds")
    ax.set_xticks(range(4)); ax.set_xticklabels(order)
    ax.set_yticks(range(4)); ax.set_yticklabels(order)
    ax.set(xlabel="banda según el modelo general", ylabel="banda según el procedimiento clásico")
    ax.grid(False)
    for i in range(4):
        for j in range(4):
            v = M.values[i, j]
            ax.text(j, i, v, ha="center", va="center", fontsize=11,
                    color="white" if v > M.values.max()/2 else "black")
    fig.colorbar(im, ax=ax, label="número de imágenes"); fig.tight_layout()
    save(fig, n, "matriz_acuerdo")


def fig_model_coverage(n):
    p = Path("outputs/cobertura_modelo_vs_humano.csv")
    if not p.exists():
        print(f"  Figura {n}: pendiente (se genera al terminar el entrenamiento)"); return
    cov = pd.read_csv(p)
    r = cov.human_cov.corr(cov.pred_cov)
    fig, ax = plt.subplots(figsize=(4.8, 4.6))
    ax.plot([0, 100], [0, 100], "--", color="gray", lw=1, label="igualdad")
    ax.scatter(cov.human_cov, cov.pred_cov, c=BLUE, s=18, alpha=0.6)
    ax.set(xlabel="cobertura desde la máscara humana (%)",
           ylabel="cobertura desde la máscara predicha (%)", xlim=(0, 100), ylim=(0, 100))
    ax.legend(fontsize=8); ax.text(0.04, 0.94, f"r = {r:.2f}", transform=ax.transAxes,
                                   fontsize=10, va="top")
    save(fig, n, "cobertura_modelo_vs_humano")


def main() -> None:
    df = pd.read_csv("outputs/results.csv")
    print("Generando figuras en formato tesis (sin título incrustado):")
    # Procedimiento
    panel(11, "procedimiento_paso_a_paso", "NLB_436473759EDR_F0211572NCAM00464M1")
    # Resultados
    fig_quality(df, 12); fig_coverage(df, 13); fig_cov_vs_valid(df, 14)
    fig_counts(df, 15); fig_size_freq(df, 16); fig_scenes(df, 17)
    fig_traverse(df, 18); fig_validation(df, 19); fig_agreement(20); fig_model_coverage(21)
    # Limitación
    panel(22, "subdivision_afloramiento", "NLB_614913932EDR_F0761384NCAM00294M1")
    # Anexo: resto de paneles del procedimiento (§8.9 pide al menos cinco)
    for i, iid in enumerate([
        "NLB_448901529EDR_F0300740NCAM00256M1",
        "NLB_547801039EDR_F0630346NCAM07753M1",
        "NLB_550010635EDR_F0632582NCAM00282M1",
        "NLA_407351345EDR_F0050406NCAM00340M1"], start=1):
        panel(f"A{i}", f"procedimiento_anexo_{i}", iid)
    print(f"\nListas en {OUT}/")


if __name__ == "__main__":
    main()
