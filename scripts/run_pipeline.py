#!/usr/bin/env python
"""Ejecuta el pipeline sobre el subconjunto MSL NavCam y guarda ``outputs/results.csv``.

Uso:
    python scripts/run_pipeline.py                 # todo el subconjunto train
    python scripts/run_pipeline.py --limit 500     # prueba rápida
    python scripts/run_pipeline.py --out outputs/results.csv

Reproducibilidad (E4): registra versiones de librerías y parámetros usados en un
``.meta.json`` junto al CSV.
"""
from __future__ import annotations

import argparse
import json
import platform
import sys
import time
from pathlib import Path

# Permite ejecutar el script desde la raíz del repo sin instalar el paquete.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src import config, pipeline as pl  # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--labels", default=str(config.MSL_NCAM_LABELS_TRAIN))
    ap.add_argument("--images", default=str(config.MSL_NCAM_IMAGES))
    ap.add_argument("--out", default="outputs/results.csv")
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--no-progress", action="store_true")
    args = ap.parse_args()

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)

    t0 = time.time()
    df = pl.process_subset(
        labels_dir=args.labels,
        images_dir=args.images,
        limit=args.limit,
        progress=not args.no_progress,
    )
    dt = time.time() - t0

    df.to_csv(out, index=False)

    # Metadatos de reproducibilidad
    meta = {
        "n_images": len(df),
        "seconds": round(dt, 1),
        "params": pl.DEFAULT_PARAMS,
        "ai4mars_root": str(config.AI4MARS_ROOT),
        "labels_dir": args.labels,
        "python": platform.python_version(),
        "quality_flag_counts": df["quality_flag"].value_counts().to_dict(),
    }
    try:
        import numpy, pandas, skimage, scipy, PIL  # noqa
        meta["versions"] = {
            "numpy": numpy.__version__, "pandas": pandas.__version__,
            "scikit-image": skimage.__version__, "scipy": scipy.__version__,
            "pillow": PIL.__version__,
        }
    except Exception:
        pass
    Path(str(out) + ".meta.json").write_text(json.dumps(meta, indent=2, ensure_ascii=False))

    print(f"\nOK: {len(df)} filas -> {out}  ({dt:.0f}s)")
    print("quality_flag:", df["quality_flag"].value_counts().to_dict())
    print(f"cobertura media={df['rock_coverage_pct'].mean():.2f}%  "
          f"n_rocks total={int(df['n_rocks'].sum())}")


if __name__ == "__main__":
    main()
