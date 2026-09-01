#!/usr/bin/env python
"""Prepara el kit de validación manual por bandas (§8.9 de la tesis).

Genera una muestra de escenas con roca grande en las que la región anotada aparece
resaltada sobre la imagen original, **sin mostrar el resultado del algoritmo**, para que
una persona cuente las rocas que distingue y se compare después con el conteo automático.

Diseño:
  - Las imágenes se renombran con identificadores neutros (V01, V02, …) y se barajan, de
    modo que no pueda inferirse nada del nombre ni del orden.
  - Se resalta la región etiquetada como roca grande, que es sobre la que opera el
    algoritmo; así la comparación responde a la misma pregunta para ambos.
  - La correspondencia con la imagen real queda en un archivo aparte (clave.csv) que no
    hace falta abrir para completar la validación.

Salida en ``outputs/validacion_manual/``:
  imagenes/V01.png …   escenas a evaluar
  plantilla.csv        formulario a completar (columna "banda")
  clave.csv            correspondencia V## -> image_id (no abrir antes de responder)

Uso:  python scripts/make_validation_kit.py --n 25
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
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from src import config, mask_utils as mu  # noqa: E402

BANDAS = ["0", "1-3", "4-9", "10+"]


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--csv", default="outputs/results.csv")
    ap.add_argument("--outdir", default="outputs/validacion_manual")
    ap.add_argument("--n", type=int, default=25)
    ap.add_argument("--seed", type=int, default=7)
    args = ap.parse_args()

    df = pd.read_csv(args.csv)
    ok = df[df.quality_flag == "ok"].copy()
    rng = np.random.default_rng(args.seed)

    # Muestreo estratificado por banda del conteo automático, para cubrir todo el rango
    # sin que la selección favorezca ningún resultado.
    def banda(v):
        return "0" if v == 0 else "1-3" if v <= 3 else "4-9" if v <= 9 else "10+"
    ok["_b"] = ok.n_rocks.map(banda)
    por_banda = max(1, args.n // len(BANDAS))
    sel = []
    for b in BANDAS:
        sub = ok[ok._b == b]
        if len(sub):
            sel.append(sub.sample(min(por_banda, len(sub)), random_state=args.seed))
    sel = pd.concat(sel).sample(frac=1, random_state=args.seed)  # barajar
    sel = sel.head(args.n).reset_index(drop=True)

    outdir = Path(args.outdir); imgdir = outdir / "imagenes"
    imgdir.mkdir(parents=True, exist_ok=True)

    filas = []
    for i, row in sel.iterrows():
        vid = f"V{i+1:02d}"
        mp = config.MSL_NCAM_LABELS_TRAIN / f"{row.image_id}.png"
        ip = mu.mask_to_image_path(mp)
        if ip is None:
            continue
        gray = np.asarray(Image.open(ip).convert("L"))
        rock = mu.big_rock_mask(mu.read_mask(mp))

        fig, ax = plt.subplots(figsize=(8, 8))
        ax.imshow(gray, cmap="gray")
        overlay = np.zeros((*rock.shape, 4))
        overlay[rock] = [1.00, 0.20, 0.10, 0.55]   # rojo translúcido
        ax.imshow(overlay)
        ax.contour(rock, levels=[0.5], colors="yellow", linewidths=2.0)
        ax.set_title(f"{vid}  —  ¿cuántas rocas distingues en la zona resaltada?",
                     fontsize=12)
        ax.axis("off")
        fig.savefig(imgdir / f"{vid}.png", dpi=110, bbox_inches="tight")
        plt.close(fig)

        filas.append({"id": vid, "image_id": row.image_id, "auto": int(row.n_rocks)})

    # Plantilla sin la respuesta del algoritmo
    pd.DataFrame({"id": [f["id"] for f in filas], "banda": ""}).to_csv(
        outdir / "plantilla.csv", index=False)
    # Clave con la correspondencia y el conteo automático
    pd.DataFrame(filas).to_csv(outdir / "clave.csv", index=False)

    print(f"Kit preparado en {outdir}/")
    print(f"  {len(filas)} escenas en imagenes/")
    print(f"  completa la columna 'banda' de plantilla.csv con: {', '.join(BANDAS)}")
    print("  (no abras clave.csv antes de responder)")


if __name__ == "__main__":
    main()
