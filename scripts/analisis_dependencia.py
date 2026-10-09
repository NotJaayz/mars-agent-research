#!/usr/bin/env python
"""Análisis de dependencia entre indicadores, más allá de la correlación lineal.

Un coeficiente de Pearson próximo a cero solo indica ausencia de asociación LINEAL; no
demuestra independencia estadística. Este guion contrasta la relación entre dos variables
con un conjunto de medidas que capturan formas progresivamente más generales de dependencia:

  Pearson r          asociación lineal
  Spearman rho       asociación monótona (sobre rangos)
  Kendall tau        asociación monótona, robusta a empates
  Correlación de     dependencia de CUALQUIER forma: vale cero si y solo si las variables
  distancia (dCor)   son independientes (Székely, Rizzo y Bakirov, 2007)
  Información        dependencia de cualquier forma, en bits, estimada por k vecinos
  mutua (IM)
  Chi-cuadrado       independencia en la tabla de contingencia por tramos

Para cada medida se reporta un intervalo de confianza bootstrap y un valor p por
permutación: se barajan los valores de una variable para romper cualquier dependencia y se
compara el valor observado con esa distribución nula.

Se analizan dos pares:
  1. cobertura (E1) frente a conteo (E2), sobre las escenas aptas para ambos indicadores;
  2. cobertura frente a fracción etiquetada, que es el control del artefacto del
     denominador, sobre las escenas con cobertura calculable.

Uso:  python scripts/analisis_dependencia.py [--perm 999] [--boot 1000]
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats
from sklearn.feature_selection import mutual_info_regression

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from src import poblaciones  # noqa: E402

RNG_SEED = 0


# ----------------------------------------------------------------------------------------
# Correlación de distancia (Székely, Rizzo y Bakirov, 2007)
# ----------------------------------------------------------------------------------------
def _centrar(x: np.ndarray) -> np.ndarray:
    """Matriz de distancias |x_i - x_j| doblemente centrada."""
    d = np.abs(x[:, None] - x[None, :])
    return d - d.mean(axis=0) - d.mean(axis=1)[:, None] + d.mean()


def dcor(x: np.ndarray, y: np.ndarray) -> float:
    a, b = _centrar(x.astype(float)), _centrar(y.astype(float))
    dcov2 = (a * b).mean(); vx = (a * a).mean(); vy = (b * b).mean()
    return float(np.sqrt(max(dcov2, 0) / np.sqrt(vx * vy))) if vx > 0 and vy > 0 else 0.0


def dcor_perm(x, y, n_perm, rng):
    """dCor observado y valor p por permutación, reutilizando las matrices centradas."""
    a, b = _centrar(x.astype(float)), _centrar(y.astype(float))
    vx, vy = (a * a).mean(), (b * b).mean()
    obs = np.sqrt(max((a * b).mean(), 0) / np.sqrt(vx * vy))
    nulos = np.empty(n_perm)
    for k in range(n_perm):
        p = rng.permutation(len(y))
        nulos[k] = np.sqrt(max((a * b[np.ix_(p, p)]).mean(), 0) / np.sqrt(vx * vy))
    return float(obs), float((1 + (nulos >= obs).sum()) / (1 + n_perm)), nulos


def info_mutua(x, y, seed):
    """Información mutua en bits (estimador de k vecinos de Kraskov)."""
    return float(mutual_info_regression(x.reshape(-1, 1), y, n_neighbors=5,
                                        random_state=seed)[0] / np.log(2))


def analizar(x, y, nombre_x, nombre_y, n_perm, n_boot, n_dcor_max, rng):
    n = len(x)
    out = {"par": f"{nombre_x} ~ {nombre_y}", "n": int(n)}

    # Medidas sobre la muestra completa.
    out["pearson"] = stats.pearsonr(x, y)[0]
    out["spearman"] = stats.spearmanr(x, y)[0]
    out["kendall"] = stats.kendalltau(x, y)[0]
    out["im_bits"] = info_mutua(x, y, RNG_SEED)

    # dCor es O(n^2) en memoria: por encima de n_dcor_max se usa una submuestra aleatoria.
    if n > n_dcor_max:
        idx = rng.choice(n, n_dcor_max, replace=False); xs, ys = x[idx], y[idx]
        out["dcor_submuestra"] = int(n_dcor_max)
    else:
        xs, ys = x, y
    out["dcor"], out["p_dcor"], _ = dcor_perm(xs, ys, n_perm, rng)

    # Valores p por permutación para las demás medidas.
    nul = {k: [] for k in ("pearson", "spearman", "kendall", "im_bits")}
    for _ in range(n_perm):
        yp = rng.permutation(y)
        nul["pearson"].append(stats.pearsonr(x, yp)[0])
        nul["spearman"].append(stats.spearmanr(x, yp)[0])
        nul["kendall"].append(stats.kendalltau(x, yp)[0])
    for _ in range(min(n_perm, 199)):          # la IM es costosa: basta un nulo más corto
        nul["im_bits"].append(info_mutua(x, rng.permutation(y), RNG_SEED))
    for k, v in nul.items():
        v = np.abs(np.array(v)); o = abs(out[k])
        out[f"p_{k}"] = float((1 + (v >= o).sum()) / (1 + len(v)))
    out["im_nula_p95"] = float(np.percentile(nul["im_bits"], 95))

    # Intervalos de confianza bootstrap.
    bo = {k: [] for k in ("pearson", "spearman")}
    for _ in range(n_boot):
        i = rng.integers(0, n, n)
        bo["pearson"].append(stats.pearsonr(x[i], y[i])[0])
        bo["spearman"].append(stats.spearmanr(x[i], y[i])[0])
    for k, v in bo.items():
        out[f"ic95_{k}"] = [float(np.percentile(v, 2.5)), float(np.percentile(v, 97.5))]
    return out


def chi2_tramos(x, y, cortes_x, cortes_y):
    """Prueba chi-cuadrado de independencia sobre la tabla de contingencia por tramos."""
    bx = pd.cut(x, cortes_x, include_lowest=True); by = pd.cut(y, cortes_y, include_lowest=True)
    tabla = pd.crosstab(bx, by)
    chi2, p, gl, esperado = stats.chi2_contingency(tabla)
    n = tabla.values.sum(); k = min(tabla.shape) - 1
    return {"chi2": float(chi2), "gl": int(gl), "p": float(p),
            "v_cramer": float(np.sqrt(chi2 / (n * k))) if k > 0 else float("nan"),
            "celdas_esperado_menor_5": int((esperado < 5).sum()),
            "tabla": {str(i): {str(j): int(v) for j, v in fila.items()}
                      for i, fila in tabla.iterrows()}}


def autoverificacion(rng):
    """Comprueba la implementación en casos de respuesta conocida antes de usarla."""
    x = rng.normal(size=600)
    casos = {
        "independientes": (x, rng.normal(size=600)),
        "lineal y = 2x + ruido": (x, 2 * x + rng.normal(scale=0.5, size=600)),
        "no lineal y = x^2": (x, x ** 2 + rng.normal(scale=0.1, size=600)),
    }
    print("Autoverificación (debe: independientes -> dCor ~ 0, p alto;"
          " y = x^2 -> Pearson ~ 0 pero dCor alto, p bajo)")
    for nombre, (a, b) in casos.items():
        d, p, _ = dcor_perm(a, b, 199, rng)
        print(f"  {nombre:24s} Pearson {stats.pearsonr(a, b)[0]:+.3f}   dCor {d:.3f}  p {p:.3f}")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--resultados", default="outputs/results.csv")
    ap.add_argument("--perm", type=int, default=999)
    ap.add_argument("--boot", type=int, default=1000)
    ap.add_argument("--dcor-max", type=int, default=3000)
    ap.add_argument("--out", default="outputs/analisis_dependencia.json")
    args = ap.parse_args()
    rng = np.random.default_rng(RNG_SEED)

    autoverificacion(rng)

    d = pd.read_csv(args.resultados)
    res = {}

    # Par 1: cobertura frente a conteo, sobre las escenas aptas para E2.
    ok = poblaciones.poblacion_e2(d).dropna(subset=["rock_coverage_pct", "n_rocks"])
    x, y = ok.rock_coverage_pct.to_numpy(float), ok.n_rocks.to_numpy(float)
    print(f"\n[1] cobertura ~ conteo   (escenas aptas, n = {len(ok)})")
    res["cobertura_conteo"] = analizar(x, y, "cobertura", "conteo", args.perm, args.boot,
                                       args.dcor_max, rng)
    res["cobertura_conteo"]["chi2"] = chi2_tramos(
        x, y, [0, 50, 80, 95, 99.99, 100], [-0.5, 0.5, 1.5, 3.5, 1e6])  # 4+ fusionado: celdas esperadas >= 5

    # Par 2: cobertura frente a fracción etiquetada (control del denominador).
    cal = poblaciones.poblacion_e1(d)
    x2, y2 = cal.frac_valid.to_numpy(float), cal.rock_coverage_pct.to_numpy(float)
    print(f"[2] fracción etiquetada ~ cobertura   (cobertura calculable, n = {len(cal)})")
    res["frac_cobertura"] = analizar(x2, y2, "frac_valid", "cobertura", args.perm, args.boot,
                                     args.dcor_max, rng)
    # Sensibilidad: la misma relación con la cobertura sobre la imagen completa.
    y3 = cal.coverage_total_pct.to_numpy(float)
    res["frac_cobertura_total"] = analizar(x2, y3, "frac_valid", "cobertura_total",
                                           args.perm, args.boot, args.dcor_max, rng)
    # Cobertura por tramos de fracción etiquetada.
    tramos = pd.cut(cal.frac_valid, [0, .25, .5, .75, 1.0], include_lowest=True)
    res["cobertura_por_tramo_frac"] = {
        str(k): {"n": int(len(g)), "mediana": float(g.rock_coverage_pct.median()),
                 "p25": float(g.rock_coverage_pct.quantile(.25)),
                 "p75": float(g.rock_coverage_pct.quantile(.75)),
                 "mediana_total": float(g.coverage_total_pct.median())}
        for k, g in cal.groupby(tramos, observed=True)}

    Path(args.out).write_text(json.dumps(res, indent=2, ensure_ascii=False, default=str))
    print(f"\n-> {args.out}")
    for k in ("cobertura_conteo", "frac_cobertura", "frac_cobertura_total"):
        r = res[k]
        print(f"\n{r['par']}  (n = {r['n']})")
        print(f"  Pearson  {r['pearson']:+.3f}  IC95 [{r['ic95_pearson'][0]:+.3f}, {r['ic95_pearson'][1]:+.3f}]  p {r['p_pearson']:.3f}")
        print(f"  Spearman {r['spearman']:+.3f}  IC95 [{r['ic95_spearman'][0]:+.3f}, {r['ic95_spearman'][1]:+.3f}]  p {r['p_spearman']:.3f}")
        print(f"  Kendall  {r['kendall']:+.3f}                               p {r['p_kendall']:.3f}")
        print(f"  dCor     {r['dcor']:.3f}{' (submuestra '+str(r['dcor_submuestra'])+')' if 'dcor_submuestra' in r else ''}                p {r['p_dcor']:.3f}")
        print(f"  IM       {r['im_bits']:.4f} bits  (p95 nulo {r['im_nula_p95']:.4f})   p {r['p_im_bits']:.3f}")
    c = res["cobertura_conteo"]["chi2"]
    print(f"\n  chi2 cobertura x conteo: {c['chi2']:.1f}, gl {c['gl']}, p {c['p']:.2g}, V de Cramér {c['v_cramer']:.3f}")


if __name__ == "__main__":
    main()
