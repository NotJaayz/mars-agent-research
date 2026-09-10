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


def kappa(a: pd.Series, b: pd.Series, weights: str | None = None) -> float:
    """Kappa de Cohen, opcionalmente ponderado.

    Las bandas son **ordinales**, de modo que el kappa sin ponderar penaliza por igual un
    desacuerdo de una banda y uno de tres. Con ``weights="linear"`` el desacuerdo pesa en
    proporción a la distancia entre bandas, que es la medida apropiada para esta escala.
    Se reportan ambos para que el lector juzgue.
    """
    idx = {c: i for i, c in enumerate(BANDAS)}
    ia, ib = a.map(idx).to_numpy(), b.map(idx).to_numpy()
    k = len(BANDAS)
    if weights == "linear":
        w = np.abs(np.subtract.outer(np.arange(k), np.arange(k))) / (k - 1)
    else:
        w = 1.0 - np.eye(k)

    obs = np.zeros((k, k))
    for x, y in zip(ia, ib):
        obs[x, y] += 1
    obs /= obs.sum()
    pa = np.array([(ia == i).mean() for i in range(k)])
    pb = np.array([(ib == i).mean() for i in range(k)])
    esp = np.outer(pa, pb)

    d_obs = float((w * obs).sum())
    d_esp = float((w * esp).sum())
    return 1.0 - d_obs / d_esp if d_esp > 0 else float("nan")


# Umbral de píxeles por debajo del cual la región anotada no delimita una zona
# apreciable en la imagen (< 0,2 % de una escena de 1024x1024). En esos casos la
# pregunta "cuántas rocas hay dentro de la zona" queda mal planteada y el acuerdo
# no es comparable con el del resto.
MIN_PX_ZONA = 2000


def _particion_por_anotacion(m: pd.DataFrame) -> None:
    """Reporta el acuerdo separando las escenas cuya anotación delimita una zona."""
    try:
        sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
        from src import config, mask_utils as mu
    except ImportError:
        return

    px = []
    for iid in m.image_id:
        ruta = config.MSL_NCAM_LABELS_TRAIN / f"{iid}.png"
        px.append(int(mu.big_rock_mask(mu.read_mask(ruta)).sum()) if ruta.exists() else -1)
    m = m.assign(px_anotados=px)
    if (m.px_anotados < 0).any():
        return

    print(f"\nPartición según el tamaño de la región anotada (umbral {MIN_PX_ZONA} px):")
    for etiqueta, sub in (("zona apreciable", m[m.px_anotados >= MIN_PX_ZONA]),
                          ("anotación mínima", m[m.px_anotados < MIN_PX_ZONA])):
        if sub.empty:
            continue
        a = (sub.banda == sub.banda_auto).mean() * 100
        print(f"  {etiqueta:17s} n={len(sub):3d}  acuerdo {a:3.0f} %  "
              f"kappa {kappa(sub.banda, sub.banda_auto):.2f}  "
              f"ponderado {kappa(sub.banda, sub.banda_auto, weights='linear'):.2f}")


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
    kw = kappa(m.banda, m.banda_auto, weights="linear")

    idx = {b: i for i, b in enumerate(BANDAS)}
    dif = m.banda_auto.map(idx) - m.banda.map(idx)

    print(f"n = {len(m)} escenas evaluadas")
    print(f"Acuerdo exacto de banda : {acuerdo:.0f} %")
    print(f"Kappa de Cohen          : {k:.2f}")
    print(f"Kappa ponderado (lineal): {kw:.2f}   <- medida apropiada para bandas ordinales")
    print(f"El algoritmo sitúa la escena en una banda superior en {int((dif>0).sum())} casos "
          f"e inferior en {int((dif<0).sum())}.")

    _particion_por_anotacion(m)

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
