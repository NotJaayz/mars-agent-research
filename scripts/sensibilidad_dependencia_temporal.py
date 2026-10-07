#!/usr/bin/env python
"""Sensibilidad de los contrastes principales a la dependencia entre imágenes.

Los intervalos *bootstrap* y los valores p por permutación del análisis principal tratan cada
escena como una observación intercambiable. Las imágenes, sin embargo, se adquieren en
secuencias: las de un mismo sol suelen mostrar el mismo terreno, y la composición alterna por
tramos a lo largo de la misión. Con dependencia secuencial, los intervalos por escena salen
demasiado estrechos y los valores p demasiado pequeños.

Este guion repite los contrastes clave con dos procedimientos que respetan esa estructura:

- **Bootstrap por sol.** Se remuestrean soles completos (todas las escenas de un sol a la vez),
  no escenas sueltas. El sol se obtiene del reloj de nave del identificador
  (``sclk // SOL``), como en el reparto del segmentador.
- **Desplazamiento circular.** Para contrastar la ausencia de relación entre dos variables de
  la misma escena se ordenan las escenas por reloj de nave y se desplaza una de las dos series
  respecto de la otra. Cada serie conserva su autocorrelación y solo se rompe la relación entre
  ambas; los desplazamientos menores del 5 % de la serie se excluyen.

Salida: ``outputs/sensibilidad_dependencia_temporal.json``.

Uso:  python scripts/sensibilidad_dependencia_temporal.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))
sys.path.insert(0, str(RAIZ / "scripts"))
from src import poblaciones  # noqa: E402
from analisis_dependencia import _centrar  # noqa: E402

SOL = 88775.244          # segundos de reloj de nave por sol (como en train_segmentation.py)
N_BOOT = 2000
N_DESP = 999
SEMILLA = 0


def sol_de(ids: pd.Series) -> np.ndarray:
    return (ids.str[4:13].astype(np.int64) // SOL).astype(np.int64).values


def bootstrap_por_sol(df: pd.DataFrame, estadistico, rng, n_boot=N_BOOT) -> list[float]:
    """IC 95 % remuestreando soles completos."""
    grupos = [g.index.values for _, g in df.groupby("sol")]
    vals = []
    for _ in range(n_boot):
        elegidos = rng.integers(0, len(grupos), len(grupos))
        vals.append(estadistico(df.loc[np.concatenate([grupos[i] for i in elegidos])]))
    return [float(np.percentile(vals, 2.5)), float(np.percentile(vals, 97.5))]


def desplazamientos(n: int, rng, k=N_DESP) -> np.ndarray:
    m = max(1, n // 20)
    posibles = np.arange(m, n - m)
    return rng.choice(posibles, min(k, len(posibles)), replace=False)


def p_desplazamiento(x: np.ndarray, y: np.ndarray, estadistico, rng, bilateral=True) -> float:
    """Valor p de ``estadistico(x, y)`` frente a desplazamientos circulares de ``y``."""
    obs = estadistico(x, y)
    nul = np.array([estadistico(x, np.roll(y, k)) for k in desplazamientos(len(y), rng)])
    if bilateral:
        return float((1 + (np.abs(nul) >= abs(obs)).sum()) / (1 + len(nul)))
    return float((1 + (nul >= obs).sum()) / (1 + len(nul)))


def pearson(x, y) -> float:
    return float(np.corrcoef(x, y)[0, 1])


def eta2(y: np.ndarray, g: np.ndarray) -> float:
    s = pd.Series(y); gr = s.groupby(g)
    return float((gr.size() * (gr.mean() - s.mean()) ** 2).sum() / ((s - s.mean()) ** 2).sum())


def main() -> None:
    rng = np.random.default_rng(SEMILLA)
    d = pd.read_csv(RAIZ / "outputs/results.csv")
    out: dict = {"metodo": {"sol_segundos": SOL, "n_boot": N_BOOT, "n_desplazamientos": N_DESP,
                            "desplazamiento_minimo": "5 % de la serie"}}

    # --- H1: fracción etiquetada frente a cobertura (población de E1) --------------------------
    e1 = poblaciones.poblacion_e1(d).sort_values("sclk").reset_index(drop=True)
    e1["sol"] = sol_de(e1.image_id)
    x, y = e1.frac_valid.values, e1.rock_coverage_pct.values
    r = pearson(x, y)
    out["fraccion_cobertura"] = {
        "n": len(e1), "n_soles": int(e1.sol.nunique()),
        "escenas_por_sol_mediana": float(e1.groupby("sol").size().median()),
        "pearson": r,
        "ic95_sol": bootstrap_por_sol(e1, lambda s: pearson(s.frac_valid, s.rock_coverage_pct), rng),
        "p_desplazamiento": p_desplazamiento(x, y, pearson, rng),
    }

    # --- H4: cobertura frente a conteo (población de E2) ---------------------------------------
    e2 = poblaciones.poblacion_e2(d).sort_values("sclk").reset_index(drop=True)
    e2["sol"] = sol_de(e2.image_id)
    x, y = e2.rock_coverage_pct.values.astype(float), e2.n_rocks.values.astype(float)
    a, b = _centrar(x), _centrar(y)
    va, vb = (a * a).mean(), (b * b).mean()

    def dcor_idx(p):
        return float(np.sqrt(max((a * b[np.ix_(p, p)]).mean(), 0) / np.sqrt(va * vb)))

    n2 = len(e2); ident = np.arange(n2)
    dc_obs = dcor_idx(ident)
    nul_dc = np.array([dcor_idx(np.roll(ident, k)) for k in desplazamientos(n2, rng)])
    deciles = pd.qcut(e2.rock_coverage_pct, 10, duplicates="drop").cat.codes.values
    out["cobertura_conteo"] = {
        "n": n2, "n_soles": int(e2.sol.nunique()),
        "escenas_por_sol_mediana": float(e2.groupby("sol").size().median()),
        "pearson": pearson(x, y),
        "ic95_sol": bootstrap_por_sol(e2, lambda s: pearson(s.rock_coverage_pct, s.n_rocks), rng),
        "p_pearson_desplazamiento": p_desplazamiento(x, y, pearson, rng),
        "dcor": dc_obs,
        "p_dcor_desplazamiento": float((1 + (nul_dc >= dc_obs).sum()) / (1 + len(nul_dc))),
        "eta2_conteo": eta2(y, deciles),
        "p_eta2_desplazamiento": p_desplazamiento(deciles, y, lambda g, v: eta2(v, g), rng,
                                                  bilateral=False),
    }

    # --- Fuente de la anotación: componente de anotación y error frente al experto -------------
    fa = pd.read_csv(RAIZ / "outputs/fuente_anotacion.csv")
    fa["sol"] = sol_de(fa.image_id)
    c, e = fa[fa.fuente == "colaborativa"], fa[fa.fuente == "experto"]

    def anot(cs, es):
        return float((cs.cob_etiqueta - cs.cob_modelo_reg).mean() - (es.cob_etiqueta - es.cob_modelo_reg).mean())

    gc = [g.index.values for _, g in c.groupby("sol")]
    ge = [g.index.values for _, g in e.groupby("sol")]
    boot_anot, boot_ba = [], []
    for _ in range(N_BOOT):
        cs = fa.loc[np.concatenate([gc[i] for i in rng.integers(0, len(gc), len(gc))])]
        es = fa.loc[np.concatenate([ge[i] for i in rng.integers(0, len(ge), len(ge))])]
        boot_anot.append(anot(cs, es))
        boot_ba.append(float((es.cob_modelo_val - es.cob_etiqueta).mean()))
    det = json.load(open(RAIZ / "outputs/modelo_detalle.json"))
    ba = float((e.cob_modelo_val - e.cob_etiqueta).mean())
    assert abs(ba - det["experto"]["media"]) < 1e-9
    out["fuente_anotacion"] = {
        "n_colaborativa": len(c), "n_soles_colaborativa": len(gc),
        "n_experto": len(e), "n_soles_experto": len(ge),
        "escenas_por_sol_experto_mediana": float(e.groupby("sol").size().median()),
        "anotacion": anot(c, e),
        "ic95_anotacion_sol": [float(np.percentile(boot_anot, 2.5)), float(np.percentile(boot_anot, 97.5))],
        "error_medio_experto": ba,
        "ic95_error_medio_experto_sol": [float(np.percentile(boot_ba, 2.5)), float(np.percentile(boot_ba, 97.5))],
    }

    # Misma componente con la muestra colaborativa tomada solo de los bloques de prueba.
    fp = pd.read_csv(RAIZ / "outputs/fuente_anotacion_prueba.csv")
    fp["sol"] = sol_de(fp.image_id)
    cp, ep = fp[fp.fuente == "colaborativa"], fp[fp.fuente == "experto"]
    gcp = [g.index.values for _, g in cp.groupby("sol")]
    gep = [g.index.values for _, g in ep.groupby("sol")]
    boot_p = [anot(fp.loc[np.concatenate([gcp[i] for i in rng.integers(0, len(gcp), len(gcp))])],
                   fp.loc[np.concatenate([gep[i] for i in rng.integers(0, len(gep), len(gep))])])
              for _ in range(N_BOOT)]
    out["fuente_anotacion_prueba"] = {
        "n_colaborativa": len(cp), "n_soles_colaborativa": len(gcp), "anotacion": anot(cp, ep),
        "ic95_anotacion_sol": [float(np.percentile(boot_p, 2.5)), float(np.percentile(boot_p, 97.5))],
    }

    destino = RAIZ / "outputs/sensibilidad_dependencia_temporal.json"
    destino.write_text(json.dumps(out, indent=1, ensure_ascii=False))
    print(json.dumps(out, indent=1, ensure_ascii=False))
    print(f"-> {destino.relative_to(RAIZ)}")


if __name__ == "__main__":
    main()
