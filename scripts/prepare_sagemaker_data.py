#!/usr/bin/env python
"""Prepara un subconjunto MSL NavCam en el formato de SageMaker Semantic Segmentation.

Estructura de salida (lista para subir a S3):

    <outdir>/
      train/                 imágenes de entrenamiento (.jpg, RGB)
      train_annotation/      máscaras de entrenamiento (.png, clases 0-3, 255=ignore)
      validation/            imágenes de validación
      validation_annotation/ máscaras de validación
      test/                  imágenes de prueba (para inferencia posterior)
      test_annotation/       máscaras de prueba (ground truth para comparar)
      test_ids.csv           ids del conjunto de prueba (para la comparación local)
      label_map.json         nombres de clase

Las máscaras NAV de AI4Mars (0=soil,1=bedrock,2=sand,3=big rock,255=null) ya son
compatibles: clases contiguas 0..3 y 255 = etiqueta "ignore" (por defecto en el
algoritmo). Las imágenes NavCam son escala de grises; se convierten a RGB (3 canales).

Uso:
  python scripts/prepare_sagemaker_data.py --n-train 600 --n-val 150 --n-test 150
"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from src import config, mask_utils as mu  # noqa: E402

LABELS = {0: "soil", 1: "bedrock", 2: "sand", 3: "big_rock"}


def _copy_rgb(image_path: Path, dst: Path) -> None:
    """Copia la imagen convertida a RGB de 3 canales (el algoritmo espera color)."""
    with Image.open(image_path) as im:
        im.convert("RGB").save(dst, format="JPEG", quality=95)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--csv", default="outputs/results.csv")
    ap.add_argument("--outdir", default="outputs/sagemaker_data")
    ap.add_argument("--n-train", type=int, default=600)
    ap.add_argument("--n-val", type=int, default=150)
    ap.add_argument("--n-test", type=int, default=150)
    ap.add_argument("--min-frac-valid", type=float, default=0.2)
    ap.add_argument("--seed", type=int, default=0)
    args = ap.parse_args()

    df = pd.read_csv(args.csv)
    rng = np.random.default_rng(args.seed)

    # Pool: imágenes con suficiente etiqueta y no vacías.
    pool = df[(df.frac_valid >= args.min_frac_valid)
              & (df.quality_flag.isin(["ok", "no_bigrock", "no_rock"]))].copy()

    # Priorizar la representación de big rock (clase rara): incluir primero las 'ok'.
    n_total = args.n_train + args.n_val + args.n_test
    ok_ids = pool[pool.quality_flag == "ok"].image_id.tolist()
    rng.shuffle(ok_ids)
    other_ids = pool[pool.quality_flag != "ok"].image_id.tolist()
    rng.shuffle(other_ids)

    n_ok = min(len(ok_ids), n_total // 2)          # hasta la mitad con big rock
    selected = ok_ids[:n_ok] + other_ids[: n_total - n_ok]
    rng.shuffle(selected)
    selected = selected[:n_total]
    if len(selected) < n_total:
        print(f"AVISO: solo hay {len(selected)} imágenes en el pool (pedidas {n_total}).")

    splits = {
        "train": selected[: args.n_train],
        "validation": selected[args.n_train: args.n_train + args.n_val],
        "test": selected[args.n_train + args.n_val:],
    }

    outdir = Path(args.outdir)
    if outdir.exists():
        shutil.rmtree(outdir)
    for split in splits:
        (outdir / split).mkdir(parents=True, exist_ok=True)
        (outdir / f"{split}_annotation").mkdir(parents=True, exist_ok=True)

    counts = {}
    for split, ids in splits.items():
        n = 0
        for iid in ids:
            msk = config.MSL_NCAM_LABELS_TRAIN / f"{iid}.png"
            img = mu.mask_to_image_path(msk)
            if img is None or not msk.exists():
                continue
            _copy_rgb(img, outdir / split / f"{iid}.jpg")
            shutil.copy(msk, outdir / f"{split}_annotation" / f"{iid}.png")
            n += 1
        counts[split] = n

    # Ids de test para la comparación local posterior.
    pd.DataFrame({"image_id": splits["test"]}).to_csv(outdir / "test_ids.csv", index=False)
    (outdir / "label_map.json").write_text(json.dumps(LABELS, indent=2))

    print("Subconjunto preparado en", outdir)
    for split, n in counts.items():
        print(f"  {split:<11}: {n} imágenes")
    print(f"  clases: {LABELS}  (255 = ignore)")
    print(f"  num_classes para el entrenamiento: {len(LABELS)}")
    print(f"  num_training_samples: {counts['train']}")


if __name__ == "__main__":
    main()
