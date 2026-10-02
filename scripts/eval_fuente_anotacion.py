#!/usr/bin/env python
"""¿La diferencia de cobertura entre fuentes de etiqueta viene de la anotación o de las imágenes?

Las máscaras colaborativas (entrenamiento) y las de experto (prueba) cubren conjuntos de
imágenes DISJUNTOS. Comparar sus coberturas mezcla dos efectos posibles: que cada grupo de
anotadores etiquete de forma distinta, o que las dos muestras de imágenes contengan terreno
distinto. Con las etiquetas por sí solas no pueden separarse.

Este guion introduce un instrumento común a ambas muestras: el segmentador entrenado, que es
una función fija de la imagen. Se aplica sobre la REGIÓN ANOTABLE de cada imagen —todo lo que
no es el cuerpo del rover ni está a más de 30 m, según las máscaras del propio conjunto—, que
es idéntica con independencia de quién anotó. Para cada imagen se obtienen:

  cob_etiqueta   cobertura según la anotación (roca / píxeles etiquetados)
  cob_modelo_val cobertura del modelo sobre los MISMOS píxeles que la anotación etiquetó
  cob_modelo_reg cobertura del modelo sobre toda la región anotable
  frac_reg       fracción de la región anotable que la anotación etiquetó

Lectura:
  - Si cob_modelo_reg es similar entre muestras, las imágenes son comparables en contenido y la
    diferencia de cob_etiqueta procede de la anotación.
  - Si cob_modelo_reg difiere, la muestra de imágenes difiere y la comparación de etiquetas está
    confundida con ella.
  - cob_etiqueta frente a cob_modelo_reg, dentro de cada muestra, mide si la parte etiquetada
    es representativa de la región anotable (efecto de selección de lo que se pinta).

La muestra colaborativa excluye las imágenes con que se entrenó el modelo y las que se usaron
para elegir su punto de control. Con ``--muestra prueba`` se toma en cambio solo de los
bloques temporales de prueba (a más de un sol de cualquier imagen de entrenamiento), como
análisis de sensibilidad.

Uso:  python scripts/eval_fuente_anotacion.py [--n-colab 600] [--muestra general|prueba]
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import torch
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src import config, mask_utils as mu  # noqa: E402
from src.segmentation import build_model, predict_mask  # noqa: E402

PESOS = Path("outputs/modelo_deeplab_binario.pt")


def mascara_aux(stem: str, tipo: str) -> np.ndarray | None:
    """Máscara de rover (MXY) o de distancia (RNG) asociada a una imagen; 1 = excluir."""
    base = re.sub(r"_merged$", "", stem)
    nombre = base.replace("EDR", "MXY" if tipo == "mxy" else "RNG") + ".png"
    p = config.MSL_NCAM_IMAGES.parent / ("mxy" if tipo == "mxy" else "rng-30m") / nombre
    return np.asarray(Image.open(p)) > 0 if p.exists() else None


def medir(model, mask_path: Path, device: str) -> dict | None:
    ip = mu.mask_to_image_path(mask_path)
    if ip is None:
        return None
    m = mu.read_mask(mask_path)
    rover, lejos = mascara_aux(mask_path.stem, "mxy"), mascara_aux(mask_path.stem, "rng")
    if rover is None or lejos is None:
        return None
    region = ~rover & ~lejos
    val = m != config.NAV_NULL
    if region.sum() == 0 or val.sum() == 0:
        return None
    pred = predict_mask(model, ip, device=device) == 1
    roca_lab = np.isin(m, config.COVERAGE_CLASSES)
    return {
        "image_id": mask_path.stem,
        "cob_etiqueta": 100 * float((roca_lab & val).sum()) / int(val.sum()),
        "cob_modelo_val": 100 * float((pred & val).sum()) / int(val.sum()),
        "cob_modelo_reg": 100 * float((pred & region).sum()) / int(region.sum()),
        "frac_reg": float((val & region).sum()) / int(region.sum()),
        "frac_region_imagen": float(region.mean()),
    }


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--n-colab", type=int, default=600)
    ap.add_argument("--split", default="outputs/split_deeplab.json",
                    help="reparto del entrenamiento, para excluir esas imágenes")
    ap.add_argument("--device", default="mps")
    ap.add_argument("--muestra", choices=("general", "prueba"), default="general")
    ap.add_argument("--out", default=None)
    args = ap.parse_args()
    if args.out is None:
        args.out = ("outputs/fuente_anotacion.csv" if args.muestra == "general"
                    else "outputs/fuente_anotacion_prueba.csv")

    model = build_model(2, pretrained=False).to(args.device)
    model.load_state_dict(torch.load(PESOS, map_location=args.device)); model.eval()

    sp = json.load(open(args.split))
    colab = sorted(config.MSL_NCAM_LABELS_TRAIN.glob("*.png"))
    if args.muestra == "general":
        vistas = set(sp["train"]) | set(sp["val"])
        colab = [p for p in colab if p.stem not in vistas]
    else:
        prueba = set(sp["test_natural"])
        colab = [p for p in colab if p.stem in prueba]
    rng = np.random.default_rng(0)
    colab = [colab[i] for i in rng.choice(len(colab), args.n_colab, replace=False)]
    experto = sorted((config.MSL_NCAM_LABELS_TRAIN.parent / "test" /
                      "masked-gold-min1-100agree").glob("*.png"))

    filas = []
    for fuente, lista in (("colaborativa", colab), ("experto", experto)):
        for i, p in enumerate(lista, 1):
            r = medir(model, p, args.device)
            if r:
                filas.append({"fuente": fuente, **r})
            if i % 100 == 0:
                print(f"  {fuente}: {i}/{len(lista)}", flush=True)
    d = pd.DataFrame(filas); d.to_csv(args.out, index=False)
    print(f"-> {args.out}  ({len(d)} imágenes con máscaras de rover y distancia)")
    resumir(d, Path(args.out).with_name(Path(args.out).stem + "_resumen.json"))


def resumir(d: pd.DataFrame, destino: Path, n_boot: int = 2000) -> None:
    """Pruebas de diferencia entre muestras y descomposición imagen / anotación."""
    from scipy import stats
    rng = np.random.default_rng(0)
    c, e = d[d.fuente == "colaborativa"], d[d.fuente == "experto"]
    out = {"n_colaborativa": int(len(c)), "n_experto": int(len(e))}
    for col in ("cob_etiqueta", "cob_modelo_val", "cob_modelo_reg", "frac_reg"):
        a, b = c[col].to_numpy(), e[col].to_numpy()
        med = [np.median(rng.choice(a, len(a))) - np.median(rng.choice(b, len(b))) for _ in range(n_boot)]
        out[col] = {"mediana_colab": float(np.median(a)), "mediana_experto": float(np.median(b)),
                    "media_colab": float(a.mean()), "media_experto": float(b.mean()),
                    "dif_mediana": float(np.median(a) - np.median(b)),
                    "ic95_dif_mediana": [float(np.percentile(med, 2.5)), float(np.percentile(med, 97.5))],
                    "mann_whitney_p": float(stats.mannwhitneyu(a, b).pvalue)}
    tot = c.cob_etiqueta.mean() - e.cob_etiqueta.mean()
    bi, ba = [], []
    for _ in range(n_boot):
        cs, es = c.sample(len(c), replace=True, random_state=rng.integers(1 << 31)), \
                 e.sample(len(e), replace=True, random_state=rng.integers(1 << 31))
        bi.append(cs.cob_modelo_reg.mean() - es.cob_modelo_reg.mean())
        ba.append((cs.cob_etiqueta - cs.cob_modelo_reg).mean() - (es.cob_etiqueta - es.cob_modelo_reg).mean())
    img = c.cob_modelo_reg.mean() - e.cob_modelo_reg.mean()
    anot = (c.cob_etiqueta - c.cob_modelo_reg).mean() - (e.cob_etiqueta - e.cob_modelo_reg).mean()
    out["descomposicion"] = {"total": float(tot), "imagenes": float(img), "anotacion": float(anot),
                             "pct_imagenes": float(100 * img / tot), "pct_anotacion": float(100 * anot / tot),
                             "ic95_imagenes": [float(np.percentile(bi, 2.5)), float(np.percentile(bi, 97.5))],
                             "ic95_anotacion": [float(np.percentile(ba, 2.5)), float(np.percentile(ba, 97.5))]}
    for f, s in (("colaborativa", c), ("experto", e)):
        dd = s.cob_etiqueta - s.cob_modelo_reg
        out[f"residuo_{f}"] = {"media": float(dd.mean()), "mediana": float(dd.median()),
                               "wilcoxon_p": float(stats.wilcoxon(s.cob_etiqueta, s.cob_modelo_reg).pvalue)}
    destino.write_text(json.dumps(out, indent=2, ensure_ascii=False))
    print(f"-> {destino}")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--solo-resumen":
        resumir(pd.read_csv("outputs/fuente_anotacion.csv"), Path("outputs/fuente_anotacion_resumen.json"))
    else:
        main()
