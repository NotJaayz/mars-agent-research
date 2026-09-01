#!/usr/bin/env python
"""Exploración: ¿se pueden detectar vetas minerales desde la imagen? (resultado negativo)

Las vetas de sulfato de calcio son depósitos precipitados por agua y constituyen el rasgo
de mayor interés científico entre los que aparecen en las anotaciones. La escala NAV que
usa el subconjunto de estudio no las etiqueta, de modo que la única vía para inventariarlas
en las imágenes de Curiosity sería detectarlas a partir de la propia imagen.

Este guion documenta ese intento y su resultado, que fue NEGATIVO. Se conserva para que
quede constancia de lo medido y no se repita el ensayo sin conocer sus límites.

MÉTODO
------
1. Región de interés: los píxeles de lecho rocoso según la anotación, que es donde las
   vetas aparecen (cortan la roca, no la arena).
2. Filtro de crestas de Meijering sobre la luminancia. Analiza los autovalores del
   Hessiano para realzar estructuras curvilíneas finas; se emplea habitualmente en
   angiografía y una veta es geométricamente el mismo tipo de objeto.
3. Variante con color: pondera la respuesta por el cociente azul/rojo normalizado, bajo la
   hipótesis de que el sulfato, blanquecino, resulta menos rojizo que el polvo marciano.
4. Filtrado por forma: se conservan las componentes alargadas (eje mayor/menor >= 3) y de
   área reducida, el mismo criterio validado sobre las vetas anotadas de M2020.

VALIDACIÓN
----------
Al no existir verdad de campo de vetas en MSL, la evaluación se hizo sobre las escenas de
M2020 cuya anotación de veta se consideró plausible, midiendo la precisión frente a la
tasa base (proporción de veta dentro de la región de interés).

RESULTADOS MEDIDOS (24 escenas, MastCam-Z de Perseverance)
---------------------------------------------------------
                        sin color      con color
    precisión media       0,261          0,267
    recall medio          0,067          0,041
    mejora sobre azar      9,1x          10,2x
    escenas sin acierto   11/24          12/24

Interpretación: hay señal —diez veces mejor que el azar no es ruido—, pero el detector es
inutilizable en la práctica: recupera un 5 % de los píxeles de veta y falla por completo en
la mitad de las escenas. La variante con color NO aporta mejora: la precisión apenas cambia,
el recall empeora y el número de fallos aumenta; mejora en 6 escenas y empeora en 5, lo que
es indistinguible del azar.

POR QUÉ FALLA
-------------
La hipótesis del color resultó incorrecta. Medido sobre MastCam de Curiosity, el cociente
azul/rojo en las zonas claras del lecho rocoso solo es 1,025 veces el del conjunto de la
roca, con dirección inconsistente entre escenas. Dos causas plausibles: el polvo rojizo
recubre también las vetas y borra el contraste espectral; y las imágenes de AI4Mars son
JPEG con balance de blancos aplicado, no productos radiométricos calibrados, de modo que la
información espectral fina que permitiría discriminar el sulfato ya no está presente.

Añádase que NavCam, la cámara del subconjunto de estudio, es un instrumento de navegación:
campo amplio, escala de grises y resolución modesta. Las vetas del cráter Gale se
caracterizaron con MAHLI, ChemCam y MastCam, no con NavCam.

CONCLUSIÓN
----------
Detectar vetas a partir de las imágenes de AI4Mars no es viable. Perseguir esta línea
exigiría datos espectrales calibrados (ChemCam o los productos radiométricos del Planetary
Data System), que constituyen otro conjunto de datos y otro trabajo. Lo que sí funciona es
inventariar las vetas ya anotadas, que es lo que hace ``scripts/scan_geology.py``.

Uso:  python scripts/explore_vein_detection.py --n 12
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from PIL import Image
from skimage.filters import meijering
from skimage.measure import label, regionprops

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from src import config  # noqa: E402

BEDROCK_GEO = list(range(0, 7))
VETA = 40


def detectar(rgb: np.ndarray, roi: np.ndarray, usar_color: bool,
             percentil: float = 99.0, elongacion_min: float = 3.0,
             area_min: int = 40) -> np.ndarray:
    """Candidatas a veta: crestas finas y alargadas dentro de la región de interés."""
    gris = rgb.mean(axis=2) / 255.0
    resp = meijering(gris, sigmas=range(1, 5), black_ridges=False)
    if usar_color:
        R, B = rgb[..., 0], rgb[..., 2]
        br = np.divide(B, R, out=np.zeros_like(B), where=R > 0)
        if roi.any():
            z = (br - br[roi].mean()) / (br[roi].std() + 1e-6)
            resp = resp * np.clip(1.0 + 0.5 * z, 0.2, 3.0)
    resp = np.where(roi, resp, 0)
    if not roi.any():
        return np.zeros_like(roi)
    cand = (resp >= np.percentile(resp[roi], percentil)) & roi
    lab = label(cand)
    keep = []
    for pr in regionprops(lab):
        menor = pr.axis_minor_length
        razon = pr.axis_major_length / menor if menor > 1 else 99.0
        if pr.area >= area_min and razon >= elongacion_min:
            keep.append(pr.label)
    return np.isin(lab, keep)


def _imagen_m2020(image_id: str) -> Path | None:
    base = image_id.split("_merged")[0]
    for sub in ("ncam", "mcam"):
        for ext in (".jpg", ".jpeg"):
            p = config.AI4MARS_ROOT / "m2020" / "images" / sub / f"{base}{ext}"
            if p.exists():
                return p
    return None


def main() -> None:
    ap = argparse.ArgumentParser(description="Reproduce la evaluación del detector.")
    ap.add_argument("--n", type=int, default=24)
    args = ap.parse_args()

    g = pd.read_csv("outputs/geologia_m2020.csv")
    sel = (g[g.alerta_veta == "veta_probable"]
           .sort_values("pct_veta", ascending=False).head(args.n))
    raiz = config.AI4MARS_ROOT / "m2020" / "labels" / "M2020_GEO"

    filas = []
    for _, r in sel.iterrows():
        mp = next(raiz.rglob(f"{r.image_id}.png"), None)
        ip = _imagen_m2020(r.image_id)
        if mp is None or ip is None:
            continue
        m = np.asarray(Image.open(mp), dtype=np.uint8)
        rgb = np.asarray(Image.open(ip).convert("RGB"), dtype=float)
        h = min(m.shape[0], rgb.shape[0]); w = min(m.shape[1], rgb.shape[1])
        m, rgb = m[:h, :w], rgb[:h, :w]
        veta = m == VETA
        roi = np.isin(m, BEDROCK_GEO) | veta
        if veta.sum() < 50 or roi.sum() < 5000:
            continue
        base = veta[roi].mean()
        fila = {"image_id": r.image_id, "tasa_base": base}
        for etq, color in (("gris", False), ("color", True)):
            det = detectar(rgb, roi, color)
            prec = veta[det].mean() if det.any() else 0.0
            fila[f"precision_{etq}"] = round(prec, 4)
            fila[f"recall_{etq}"] = round(det[veta].mean(), 4)
            fila[f"mejora_{etq}"] = round(prec / base, 2) if base > 0 else 0.0
        filas.append(fila)

    d = pd.DataFrame(filas)
    d.to_csv("outputs/exploracion_vetas.csv", index=False)
    print(f"escenas evaluadas: {len(d)}\n")
    print("                     sin color     con color")
    print(f"  precisión media    {d.precision_gris.mean():.3f}         {d.precision_color.mean():.3f}")
    print(f"  recall medio       {d.recall_gris.mean():.3f}         {d.recall_color.mean():.3f}")
    print(f"  mejora sobre azar  {d.mejora_gris.mean():.1f}x          {d.mejora_color.mean():.1f}x")
    print(f"  escenas sin acierto {int((d.precision_gris == 0).sum())}/{len(d)}           "
          f"{int((d.precision_color == 0).sum())}/{len(d)}")
    print("\nResultado negativo: el detector no es utilizable y el color no aporta mejora.")
    print("Véase la documentación del módulo para la interpretación completa.")
    print("-> outputs/exploracion_vetas.csv")


if __name__ == "__main__":
    main()
