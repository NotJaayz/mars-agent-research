#!/usr/bin/env python
"""Conteo dentro de la máscara usando la imagen: comparación de relieves contra el conteo humano.

El conteo E2 solo usa la geometría de la máscara, y la validación humana mostró que subcuenta
cuando un polígono cubre un campo de rocas sin estrangulamientos. La información que separa
esas rocas solo puede venir de la imagen. Este guion compara cuatro formas de construir el
relieve sobre el que corta la división de aguas DENTRO de la región anotada:

  grad     gradiente de la imagen a escala fina
  persist  gradiente a escala gruesa (la textura interna se borra, el borde real persiste)
  sombra   top-hat negro: realza líneas oscuras finas, es decir, sombras entre rocas
  combo    mitad geometría de la máscara (distancia) y mitad gradiente

Protocolo, idéntico para todos: misma región, mismas semillas por prominencia, mismo filtro
final que E2. El único parámetro (h) se elige por validación cruzada dejando una escena fuera.
La diferencia con E2 se contrasta por bootstrap, primero al 95 % y después con corrección de
Bonferroni por el número de variantes probadas: con varios intentos, que uno resulte
significativo por azar es esperable, y eso debe descontarse.

Uso:  python scripts/eval_metodos_imagen.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from PIL import Image
from scipy import ndimage as ndi
from skimage.filters import gaussian, sobel
from skimage.measure import label, regionprops
from skimage.morphology import black_tophat, disk, h_maxima
from skimage.segmentation import watershed
from sklearn.metrics import cohen_kappa_score

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from src import config, mask_utils as mu  # noqa: E402
from src.rock_count import _aspect_ratio  # noqa: E402

BANDAS = ["0", "1-3", "4-9", "10-24", "25-49", "50+"]
H_GRID = [0.02, 0.04, 0.08, 0.15, 0.25]
MIN_AREA = 0.0005 * 1024 * 1024
METODOS = ["grad", "persist", "sombra", "combo"]
# Variantes del método de sombras para la sensibilidad (suavizado previo, radio del top-hat).
SOMBRA_VARIANTES = [(s, r) for s in (0.5, 1.0, 2.0) for r in (3, 5, 7, 9, 12)]


def banda(n):
    return ("0" if n == 0 else "1-3" if n <= 3 else "4-9" if n <= 9
            else "10-24" if n <= 24 else "25-49" if n <= 49 else "50+")


def kw(y, x, w="linear"):
    return float("nan") if len(set(y)) < 2 else cohen_kappa_score(y, x, labels=BANDAS, weights=w)


def norm(R, region):
    v = R[region]; p = np.percentile(v, 99) if v.size else 1.0
    return np.clip(R / p, 0, 1) if p > 0 else R * 0


def recorte(region, m=20):
    f, c = np.where(region); h, w = region.shape
    return (slice(max(0, f.min() - m), min(h, f.max() + m + 1)),
            slice(max(0, c.min() - m), min(w, c.max() + m + 1)))


def contar(R, region, h):
    seeds = h_maxima(gaussian(-R, sigma=1.0), h).astype(bool) & region
    ws = watershed(R, label(seeds) if seeds.any() else label(region), mask=region)
    return sum(1 for g in regionprops(ws) if g.area >= MIN_AREA and _aspect_ratio(g) <= 5.0)


def relieves(img, region):
    I = img.astype(float); I = (I - I.min()) / max(I.max() - I.min(), 1e-9)
    D = ndi.distance_transform_edt(region); G2 = sobel(gaussian(I, 2.0))
    out = {"grad": norm(G2, region),
           "persist": norm(sobel(gaussian(I, 5.0)), region),
           "sombra": norm(black_tophat(gaussian(I, 1.0), disk(7)), region),
           "combo": 0.5 * (1 - D / max(D.max(), 1e-9)) + 0.5 * norm(G2, region)}
    for s, r in SOMBRA_VARIANTES:
        out[f"sombra_s{s}_r{r}"] = norm(black_tophat(gaussian(I, s), disk(r)), region)
    return out


def loo(res, ids, y, m):
    x = []
    for j, i in enumerate(ids):
        resto = [k for k in range(len(ids)) if k != j]; yr = [y[k] for k in resto]
        hb = max(H_GRID, key=lambda h: kw(yr, [banda(res[ids[k]][m][h]) for k in resto]))
        x.append(banda(res[i][m][hb]))
    return np.array(x)


def boot_dif(y, xm, xe, alfa, n=4000, seed=0):
    rng = np.random.default_rng(seed); ya = np.array(y); dif = []
    for _ in range(n):
        b = rng.integers(0, len(ya), len(ya)); a, c = kw(ya[b], xm[b]), kw(ya[b], xe[b])
        if not (np.isnan(a) or np.isnan(c)):
            dif.append(a - c)
    dif = np.array(dif)
    return float(dif.mean()), [float(np.percentile(dif, 100 * alfa / 2)),
                              float(np.percentile(dif, 100 * (1 - alfa / 2)))], float((dif > 0).mean())


def main():
    d = (pd.read_csv("outputs/validacion_manual_v2/plantilla.csv", dtype={"banda": str})
           .merge(pd.read_csv("outputs/validacion_manual_v2/clave.csv"), on="id"))
    res = {}
    for r in d.itertuples():
        reg_f = mu.big_rock_mask(mu.read_mask(config.MSL_NCAM_LABELS_TRAIN / f"{r.image_id}.png"))
        with Image.open(config.MSL_NCAM_IMAGES / f"{r.image_id}.JPG") as im:
            img_f = np.asarray(im.convert("L"))
        rs, cs = recorte(reg_f)
        Rs = relieves(img_f[rs, cs], reg_f[rs, cs])
        res[r.id] = {m: {h: contar(R, reg_f[rs, cs], h) for h in H_GRID} for m, R in Rs.items()}
        res[r.id]["_e2"] = int(r.auto)
    ids = list(d.id); y = list(d.banda)
    xe = np.array([banda(res[i]["_e2"]) for i in ids])
    idx = {b: k for k, b in enumerate(BANDAS)}
    alfa_bonf = 0.05 / len(METODOS)

    out = {"n": len(ids), "e2": {"kappa_pond": kw(y, list(xe))}, "metodos": {}}
    for m in METODOS + [f"sombra_s{s}_r{r}" for s, r in SOMBRA_VARIANTES]:
        x = loo(res, ids, y, m)
        dif = np.array([idx[a] for a in x]) - np.array([idx[b] for b in y])
        media, ic95, gana = boot_dif(y, x, xe, 0.05)
        _, icb, _ = boot_dif(y, x, xe, alfa_bonf)
        out["metodos"][m] = {"acuerdo": float(np.mean(x == np.array(y))), "kappa": kw(y, list(x), None),
                             "kappa_pond": kw(y, list(x)), "abajo": int((dif < 0).sum()),
                             "arriba": int((dif > 0).sum()), "dif_vs_e2": media, "ic95": ic95,
                             "ic_bonferroni": icb, "gana_pct": 100 * gana,
                             "demostrable_95": ic95[0] > 0, "demostrable_bonferroni": icb[0] > 0}
    Path("outputs/eval_metodos_imagen.json").write_text(json.dumps(out, indent=2, ensure_ascii=False))
    print(f"E2: kappa ponderado {out['e2']['kappa_pond']:.2f}")
    for m in METODOS:
        r = out["metodos"][m]
        print(f"  {m:8s} kw {r['kappa_pond']:.2f}  abajo/arriba {r['abajo']}/{r['arriba']}  "
              f"dif {r['dif_vs_e2']:+.2f} IC95 [{r['ic95'][0]:+.2f},{r['ic95'][1]:+.2f}]  "
              f"Bonf. [{r['ic_bonferroni'][0]:+.2f},{r['ic_bonferroni'][1]:+.2f}]")
    sv = [out["metodos"][f"sombra_s{s}_r{r}"]["kappa_pond"] for s, r in SOMBRA_VARIANTES]
    print(f"  sombra, {len(sv)} variantes: kw {min(sv):.2f}–{max(sv):.2f}; "
          f"demostrables con Bonferroni: {sum(out['metodos'][f'sombra_s{s}_r{r}']['demostrable_bonferroni'] for s, r in SOMBRA_VARIANTES)}")


if __name__ == "__main__":
    main()
