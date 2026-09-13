#!/usr/bin/env python
"""Kit de validación manual, segunda ronda, con el diseño corregido.

La primera ronda (``scripts/make_validation_kit.py``) reveló tres defectos del
instrumento, que esta versión corrige:

1. **Banda superior demasiado gruesa.** Con ``10+`` abierta, un método que contaba 84
   rocas donde el observador veía una decena puntuaba como acierto exacto, lo que
   favorecía sistemáticamente a los métodos que sobreestiman. Se sustituye por
   ``10-24``, ``25-49`` y ``50+``.
2. **Escenas con anotación imperceptible.** En siete de las veinticuatro escenas la
   región anotada ocupaba menos del 0,2 % de la imagen, de modo que la zona resaltada era
   apenas visible y la pregunta quedaba mal planteada. Se exige un área mínima.
3. **Zona difícil de examinar.** Se añade un recorte ampliado de la región cuando aporta,
   y el relleno pasa a ser un tinte apenas perceptible: el relleno opaco de la primera
   ronda tapaba justamente la textura que hay que examinar para contar.

Se corrige además el muestreo. La primera ronda estratificaba por la banda del propio
algoritmo, lo que condicionaba la muestra al método evaluado. Aquí se estratifica por
**área de la región anotada**, que es neutral entre los métodos que se comparan.

Las escenas ya empleadas en la primera ronda se excluyen, para que las respuestas no
queden ancladas por el recuerdo.

Uso:  python scripts/make_validation_kit2.py --n 60
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
from scipy import ndimage as ndi

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from src import config, mask_utils as mu  # noqa: E402

BANDAS = ["0", "1-3", "4-9", "10-24", "25-49", "50+"]

# Área mínima de la región anotada para que delimite una zona examinable.
# 2000 px ~ 0,19 % de una escena de 1024x1024.
MIN_PX_ZONA = 2000

# Número de estratos de área; la muestra se reparte por igual entre ellos.
N_ESTRATOS = 6


def recorte(region: np.ndarray, margen: float = 0.12) -> tuple[slice, slice]:
    """Caja envolvente de la región con margen, para el panel ampliado."""
    filas, cols = np.where(region)
    r0, r1 = filas.min(), filas.max()
    c0, c1 = cols.min(), cols.max()
    dr, dc = int((r1 - r0) * margen) + 10, int((c1 - c0) * margen) + 10
    h, w = region.shape
    return (slice(max(0, r0 - dr), min(h, r1 + dr + 1)),
            slice(max(0, c0 - dc), min(w, c1 + dc + 1)))


def panel(gray: np.ndarray, region: np.ndarray, vid: str, destino: Path) -> None:
    """Figura del kit. Muestra la escena y, si aporta, un recorte ampliado de la zona.

    Dos decisiones deliberadas:

    - El relleno es **muy tenue**. La tarea consiste en contar rocas *dentro* de la zona,
      de modo que un relleno opaco taparía precisamente la textura que hay que examinar.
      La delimitación la aporta el contorno amarillo, no el relleno.
    - El recorte solo se añade cuando la caja envolvente de la región es sensiblemente
      menor que la escena. Con regiones dispersas en esquinas opuestas la caja abarca casi
      toda la imagen y el segundo panel sería una copia del primero.
    """
    rs, cs = recorte(region)
    frac_caja = ((rs.stop - rs.start) * (cs.stop - cs.start)) / region.size
    amplia = frac_caja < 0.55

    vistas = [(gray, region, "escena completa")]
    if amplia:
        vistas.append((gray[rs, cs], region[rs, cs], "zona ampliada — cuenta aquí"))

    ancho = 13 if amplia else 8.5
    fig, axes = plt.subplots(1, len(vistas), figsize=(ancho, 6.8), squeeze=False)
    for ax, (g, rg, titulo) in zip(axes[0], vistas):
        ax.imshow(g, cmap="gray")
        overlay = np.zeros((*rg.shape, 4))
        overlay[rg] = [1.00, 0.25, 0.10, 0.16]   # tinte apenas perceptible
        ax.imshow(overlay)
        ax.contour(rg, levels=[0.5], colors="yellow", linewidths=2.0)
        ax.set_title(titulo, fontsize=11)
        ax.axis("off")

    fig.suptitle(f"{vid}  —  ¿cuántas rocas distingues dentro de la zona resaltada?",
                 fontsize=13, y=0.98)
    fig.tight_layout(rect=(0, 0, 1, 0.94))
    fig.savefig(destino, dpi=105, bbox_inches="tight")
    plt.close(fig)


def seleccionar(args) -> pd.DataFrame:
    """Muestra estratificada por área de la región anotada, excluyendo la ronda previa."""
    res = pd.read_csv(args.resultados)
    usadas: set[str] = set()
    previo = Path(args.excluir)
    if previo.exists():
        usadas = set(pd.read_csv(previo).image_id)

    cand = res[(res.quality_flag == "ok")
               & (res.n_bigrock >= MIN_PX_ZONA)
               & (~res.image_id.isin(usadas))].copy()
    if cand.empty:
        sys.exit("No hay escenas candidatas con los criterios dados.")

    cand["_estrato"] = pd.qcut(cand.n_bigrock, N_ESTRATOS, labels=False, duplicates="drop")
    por_estrato = max(1, args.n // cand._estrato.nunique())
    sel = pd.concat([
        g.sample(min(por_estrato, len(g)), random_state=args.seed)
        for _, g in cand.groupby("_estrato")
    ])
    return (sel.sample(frac=1, random_state=args.seed)   # barajar
               .head(args.n).reset_index(drop=True))


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--n", type=int, default=60)
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--resultados", default="outputs/results.csv")
    ap.add_argument("--excluir", default="outputs/validacion_manual/clave.csv",
                    help="clave de una ronda previa, cuyas escenas se excluyen")
    ap.add_argument("--outdir", default="outputs/validacion_manual_v2")
    args = ap.parse_args()

    sel = seleccionar(args)
    outdir = Path(args.outdir)
    imgdir = outdir / "imagenes"
    imgdir.mkdir(parents=True, exist_ok=True)

    filas = []
    for i, row in sel.iterrows():
        vid = f"W{i + 1:02d}"
        mp = config.MSL_NCAM_LABELS_TRAIN / f"{row.image_id}.png"
        ip = mu.mask_to_image_path(mp)
        if ip is None:
            continue
        region = mu.big_rock_mask(mu.read_mask(mp))
        if not region.any():
            continue
        gray = np.asarray(Image.open(ip).convert("L"))
        panel(gray, region, vid, imgdir / f"{vid}.png")
        filas.append({"id": vid, "image_id": row.image_id,
                      "auto": int(row.n_rocks), "px_zona": int(region.sum())})

    pd.DataFrame({"id": [f["id"] for f in filas], "banda": ""}).to_csv(
        outdir / "plantilla.csv", index=False)
    pd.DataFrame(filas).to_csv(outdir / "clave.csv", index=False)

    px = pd.Series([f["px_zona"] for f in filas])
    print(f"Kit v2 preparado en {outdir}/")
    print(f"  {len(filas)} escenas · área de la zona entre {px.min():,} y {px.max():,} px")
    print(f"  bandas: {', '.join(BANDAS)}")
    print(f"  responde con: python scripts/responder_validacion.py --dir {outdir}")
    print("  (no abras clave.csv antes de responder)")


if __name__ == "__main__":
    main()
