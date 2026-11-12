#!/usr/bin/env python
"""Genera las capas visuales del explorador de la aplicación (``outputs/app_escenas/``).

Para cada escena con señal de prioridad cuya imagen y máscara estén en ``AI4MARS_ROOT``
escribe, a 512 × 512 píxeles:

* ``<id>_img.jpg``  la imagen NavCam original;
* ``<id>_anot.png`` la anotación de AI4Mars con los colores de la tesis (lo no etiquetado,
  transparente);
* ``<id>_rocas.png`` las rocas que cuenta el procedimiento, una por color, con relleno
  translúcido y contorno claro;
* ``<id>_filt.png`` las regiones que descartaron los filtros de área y forma, si las hay;

y un índice (``indice.json``) con el centroide y el área de cada roca, numeradas de arriba
abajo en la imagen (como en la versión 2.0 de la aplicación), para que la aplicación las rotule. Las rocas salen de :func:`src.rock_count.compute_stages`
con los parámetros por defecto, el mismo código que produce ``n_rocks`` en results.csv; el
guion comprueba que el número de rocas coincide escena por escena.

Uso:  python scripts/make_app_escenas.py [--todas]
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np
from PIL import Image

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))
from src import config, mask_utils as mu, rock_count as rc  # noqa: E402
from src.viz import _NAV_COLORS  # noqa: E402

SALIDA = RAIZ / "outputs" / "app_escenas"
LADO = 512
# Paleta de las rocas (la de la versión 2.0): azul, verde azulado y violeta, en ciclo. Contrastan
# con la imagen en grises y con los colores de la anotación.
PALETA = ["#3b6fd8", "#14b8a6", "#7c5cff"]
RELLENO = 170          # opacidad del relleno (0-255): deja ver la textura de la roca debajo


def _rgb(h: str) -> tuple[int, int, int]:
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def _png(rgba: np.ndarray, ruta: Path) -> None:
    Image.fromarray(rgba, "RGBA").resize((LADO, LADO), Image.NEAREST).save(ruta, optimize=True)


def _capa_rocas(lab: np.ndarray, ids: list[int]) -> np.ndarray:
    """Capa RGBA a ``LADO`` píxeles: cada roca con relleno translúcido y un contorno claro de 1 px."""
    lab = np.asarray(Image.fromarray(lab.astype(np.int32)).resize((LADO, LADO), Image.NEAREST))
    capa = np.zeros((LADO, LADO, 4), np.uint8)
    for j, k in enumerate(ids):
        m = lab == k
        borde = m & ~(np.roll(m, 1, 0) & np.roll(m, -1, 0) & np.roll(m, 1, 1) & np.roll(m, -1, 1))
        rgb = np.array(_rgb(PALETA[j % len(PALETA)]))
        capa[m] = (*rgb, RELLENO)
        capa[borde] = (*(rgb + (255 - rgb) * 0.55).astype(np.uint8), 255)
    return capa


def procesar(tarea: tuple[str, str, str, int]) -> tuple[str, dict | None, str | None]:
    image_id, ruta_img, ruta_mask, n_esperado = tarea
    try:
        m = mu.read_mask(ruta_mask)
        gris = Image.open(ruta_img).convert("L")
        gris.resize((LADO, LADO), Image.LANCZOS).save(SALIDA / f"{image_id}_img.jpg", quality=82,
                                                         optimize=True, progressive=True)
        h, w = m.shape
        anot = np.zeros((h, w, 4), np.uint8)
        for val, col in _NAV_COLORS.items():
            if val == config.NAV_NULL:
                continue
            anot[m == val] = (*_rgb(col), 255)
        _png(anot, SALIDA / f"{image_id}_anot.png")

        s = rc.compute_stages(mu.big_rock_mask(m))
        lab, kept = s["labels_ws"], list(s["kept_ids"])
        rocas = []
        for k in kept:
            ys, xs = np.nonzero(lab == k)
            rocas.append((len(ys), float(xs.mean()) / w, float(ys.mean()) / h, k))
        rocas.sort(key=lambda r: (round(r[2], 3), r[1]))      # de arriba abajo, luego de izquierda a derecha
        Image.fromarray(_capa_rocas(lab, [k for *_, k in rocas]), "RGBA").save(SALIDA / f"{image_id}_rocas.png", optimize=True)
        filtradas = [r for r in np.unique(lab) if r and r not in kept]
        if filtradas:
            capa = np.zeros((h, w, 4), np.uint8)
            capa[np.isin(lab, filtradas)] = (230, 236, 245, 255)
            _png(capa, SALIDA / f"{image_id}_filt.png")
        info = {"r": [[round(x, 4), round(y, 4), round(100 * a / m.size, 2)] for a, x, y, _ in rocas],
                "f": len(filtradas), "raw": int(s["n_raw_components"])}
        aviso = None if len(rocas) == n_esperado else f"{image_id}: {len(rocas)} rocas frente a {n_esperado} en results.csv"
        return image_id, info, aviso
    except Exception as exc:  # una escena defectuosa no detiene el resto
        return image_id, None, f"{image_id}: {exc}"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--todas", action="store_true", help="todas las escenas con imagen, no solo las de señal")
    args = ap.parse_args()
    SALIDA.mkdir(parents=True, exist_ok=True)
    with (RAIZ / "outputs" / "priorizacion.csv").open(newline="", encoding="utf-8") as fh:
        filas = list(csv.DictReader(fh))
    tareas = []
    for f in filas:
        if not args.todas and f["nivel_prioridad"] == "sin_prioridad":
            continue
        ruta_mask = config.MSL_NCAM_LABELS_TRAIN / f"{f['image_id']}.png"
        if not ruta_mask.exists():
            ruta_mask = config.MSL_NCAM_LABELS_TRAIN / f"{f['image_id']}_merged.png"
        ruta_img = mu.mask_to_image_path(ruta_mask) if ruta_mask.exists() else None
        if ruta_img is None:
            continue
        n = int(float(f["n_rocks"] or 0))
        tareas.append((f["image_id"], str(ruta_img), str(ruta_mask), n))
    indice, avisos = {}, []
    with ProcessPoolExecutor() as ex:
        for image_id, info, aviso in ex.map(procesar, tareas, chunksize=8):
            if info is not None:
                indice[image_id] = info
            if aviso:
                avisos.append(aviso)
    (SALIDA / "indice.json").write_text(json.dumps(indice, separators=(",", ":")), encoding="utf-8")
    print(f"Escrito {SALIDA.relative_to(RAIZ)}: {len(indice)} escenas de {len(tareas)} con imagen.")
    for a in avisos[:20]:
        print("  aviso:", a)
    if avisos:
        print(f"  {len(avisos)} avisos en total")


if __name__ == "__main__":
    main()
