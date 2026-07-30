#!/usr/bin/env python
"""Figuras step-by-step del pipeline (§12) para imágenes representativas.

Selecciona ~6 escenas variadas a partir de ``outputs/results.csv`` y genera, para
cada una, el panel de 5 etapas (imagen | máscara AI4Mars | binaria limpia |
transformada de distancia + semillas | resultado del watershed) con
``src.viz.plot_pipeline`` y los parámetros calibrados por defecto.

Uso:  python scripts/make_pipeline_figures.py
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

# Permite ejecutar el script desde la raíz del repo sin instalar el paquete.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src import config, mask_utils as mu, viz  # noqa: E402


def _pick(df: pd.DataFrame, mask, exclude: set, sort_by: str, ascending: bool = False):
    """Primera fila que cumple la máscara booleana y no está ya elegida."""
    cand = df[mask & ~df.image_id.isin(exclude)].sort_values(sort_by, ascending=ascending)
    return cand.iloc[0] if len(cand) else None


def select_representative(df: pd.DataFrame) -> list[tuple[str, str]]:
    """Devuelve [(image_id, título)] de escenas representativas para §12."""
    ok = df[df.quality_flag == "ok"].copy()
    chosen: list[tuple[str, str]] = []
    used: set = set()

    specs = [
        ("una roca aislada",
         (ok.n_rocks == 1) & (ok.largest_rock_pct.between(2, 12)), "largest_rock_pct"),
        ("cúmulo pequeño bien separado",
         (ok.n_rocks.between(3, 5)) & (ok.mean_solidity > 0.92), "n_rocks"),
        ("cúmulo grande de rocas",
         (ok.n_rocks.between(8, 14)), "n_rocks"),
        ("muchas rocas (denso)",
         (ok.n_rocks >= 15), "n_rocks"),
        ("escena rocosa de alta cobertura",
         (ok.scene_type == "rocoso") & (ok.rock_coverage_pct > 90) & (ok.n_rocks >= 2),
         "rock_coverage_pct"),
        ("posible sobresegmentación (solidez baja)",
         (ok.n_rocks >= 4) & (ok.mean_solidity < 0.85), "mean_solidity"),
    ]
    for title, mask, sort_by in specs:
        asc = sort_by == "mean_solidity"
        row = _pick(ok, mask, used, sort_by, ascending=asc)
        if row is not None:
            used.add(row.image_id)
            chosen.append((row.image_id, title))
    return chosen


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--csv", default="outputs/results.csv")
    ap.add_argument("--outdir", default="outputs/figures/pipeline")
    args = ap.parse_args()

    df = pd.read_csv(args.csv)
    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    picks = select_representative(df)
    for i, (image_id, title) in enumerate(picks, 1):
        msk = config.MSL_NCAM_LABELS_TRAIN / f"{image_id}.png"
        img = mu.mask_to_image_path(msk)
        if img is None:
            print(f"  [{i}] {image_id}: sin imagen, se omite")
            continue
        row = df[df.image_id == image_id].iloc[0]
        subtitle = (f"{image_id}  ·  {title}  ·  cobertura {row.rock_coverage_pct:.0f}%  "
                    f"·  {int(row.n_rocks)} rocas")
        fig = viz.plot_pipeline(img, msk, params=None, save_path=outdir / f"{i:02d}_{image_id}.png",
                                title=subtitle)
        plt.close(fig)
        print(f"  [{i}] {title:<42} {image_id}  (n_rocks={int(row.n_rocks)})")
    print(f"\nOK: {len(picks)} figuras en {outdir}/")


if __name__ == "__main__":
    main()
