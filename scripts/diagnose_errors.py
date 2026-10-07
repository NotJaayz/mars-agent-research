#!/usr/bin/env python
"""Diagnóstico de los modos de fallo del conteo: ¿imagen, etiqueta o umbrales?

Genera un panel (imagen | máscara AI4Mars | rocas contadas) para cada uno de los
tres modos de fallo observados, de modo que la atribución numérica del informe se
pueda verificar visualmente:

1. ``bedrock_no_contado``  — hay roca evidente en la imagen, pero el anotador la
   etiquetó ``bedrock`` (clase 1) y no ``big rock`` (clase 3); E2 no la cuenta.
2. ``artefacto_anotacion`` — casi toda la escena quedó sin etiquetar y el poco
   etiquetado se marcó ``big rock``; produce una "roca" que ocupa ~100% de lo válido.
3. ``sobresegmentacion``   — una región continua se parte en varias rocas
   (n_rocks > n_raw_components y solidez media baja).
4. ``bajo_umbral_area``    — hay píxeles de ``big rock`` pero por debajo de
   ``min_area_frac``, así que el conteo queda en 0.
5. ``filtro_aspecto``      — la región de ``big rock`` es una banda muy alargada
   (típicamente el horizonte trazado a mano), descartada por relación de aspecto.

Uso:  python scripts/diagnose_errors.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.colors import BoundaryNorm, ListedColormap, to_rgb
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from skimage.measure import regionprops  # noqa: E402

from src import config, mask_utils as mu, rock_count as rc, viz  # noqa: E402

OUT = Path("outputs/figures/diagnostico")

# Paleta y nombres de la escala NAV: los mismos que los paneles del procedimiento (src/viz.py).
_ORDEN = [config.NAV_SOIL, config.NAV_BEDROCK, config.NAV_SAND, config.NAV_BIG_ROCK, config.NAV_NULL]
NAV_CMAP = ListedColormap([viz._NAV_COLORS[v] for v in _ORDEN])
NAV_NORM = BoundaryNorm([-0.5, 0.5, 1.5, 2.5, 3.5, 4.5], NAV_CMAP.N)
NAV_NAMES = [viz._NAV_NOMBRES[v] for v in _ORDEN]
FS = 15


def _es(texto: str) -> str:
    """Coma decimal en los números de los rótulos."""
    import re
    return re.sub(r"(\d)\.(\d)", r"\1,\2", texto)


# Colores saturados fijos para el overlay de rocas contadas. Se ciclan por region;
# usar un colormap continuo fallaba cuando habia una sola roca (quedaba negra).
ROCK_COLORS = ["#fc3d21", "#00e5ff", "#ffe600", "#00ff5f", "#ff00c8",
               "#ff8c00", "#7cf", "#b5ff00"]


def _rock_overlay(labels_ws: np.ndarray, kept_ids) -> np.ndarray:
    """RGBA donde cada roca aceptada recibe un color brillante distinto."""
    rgba = np.zeros((*labels_ws.shape, 4), dtype=float)
    for i, lid in enumerate(kept_ids):
        r, g, b = to_rgb(ROCK_COLORS[i % len(ROCK_COLORS)])
        sel = labels_ws == lid
        rgba[sel] = (r, g, b, 0.80)
    return rgba


def _nav_for_plot(mask: np.ndarray) -> np.ndarray:
    """Reasigna NULL (255) a 4 para poder pintarlo con una paleta discreta."""
    m = mask.copy()
    m[m == 255] = 4
    return m


def _causa_rechazo(image_id: str) -> tuple[str | None, str]:
    """Reproduce los filtros de :func:`rc.compute_stages` y nombra la causa real
    de que una escena con píxeles de *big rock* acabe con ``n_rocks == 0``."""
    mask_p = config.MSL_NCAM_LABELS_TRAIN / f"{image_id}.png"
    if not mask_p.exists():
        return None, ""
    mask = mu.read_mask(mask_p)
    p = rc.DEFAULT_PARAMS
    st = rc.compute_stages(mu.big_rock_mask(mask), p)
    min_area = p["min_area_frac"] * mask.size

    n_area = n_aspecto = 0
    mayor = 0
    for reg in regionprops(st["labels_ws"]):
        mayor = max(mayor, int(reg.area))
        if reg.area < min_area:
            n_area += 1
        elif rc._aspect_ratio(reg) > p["max_aspect_ratio"]:
            n_aspecto += 1
    if n_aspecto:
        return ("filtro_aspecto",
                f"{n_aspecto} región(es) descartadas por relación de aspecto mayor que "
                f"{p['max_aspect_ratio']:.0f}: banda alargada, no una roca")
    if n_area:
        return ("bajo_umbral_area",
                f"{n_area} región(es) por debajo del área mínima "
                f"({min_area:.0f} px, el {100*p['min_area_frac']:.2f} % de la imagen); "
                f"la mayor tenía {mayor} px")
    return None, ""


def select_cases(df: pd.DataFrame) -> list[tuple[str, str, str]]:
    """Devuelve [(image_id, modo, subtítulo)] con un ejemplo claro de cada fallo."""
    cases: list[tuple[str, str, str]] = []

    # 1. Roca abundante etiquetada como bedrock, sin ninguna big rock que contar.
    c = df[(df.quality_flag == "no_bigrock") & (df.pct_bedrock > 90) & (df.frac_valid > 0.5)]
    if len(c):
        r = c.nlargest(1, "frac_valid").iloc[0]
        cases.append((r.image_id, "bedrock_no_contado",
                      f"lecho rocoso: {r.pct_bedrock:.1f} % de lo etiquetado · roca grande: 0 %"))

    # 2. Artefacto de anotación: escena casi sin etiquetar, lo poco etiquetado es big rock.
    c = df[(df.largest_rock_pct > 95) & (df.frac_valid < 0.05)]
    if len(c):
        r = c.nlargest(1, "largest_rock_pct").iloc[0]
        cases.append((r.image_id, "artefacto_anotacion",
                      f"solo el {100*r.frac_valid:.1f} % de la escena está etiquetado · "
                      f"la roca mayor ocupa el {r.largest_rock_pct:.1f} % de lo etiquetado"))

    # 3. Sobresegmentación: el watershed multiplica una región continua.
    c = df[(df.n_rocks > 3 * df.n_raw_components.clip(lower=1)) & (df.mean_solidity < 0.75)]
    if len(c):
        r = c.nlargest(1, "n_rocks").iloc[0]
        cases.append((r.image_id, "sobresegmentacion",
                      f"{r.n_rocks} rocas a partir de {r.n_raw_components} región(es) · "
                      f"solidez media {r.mean_solidity:.2f}"))

    # 4 y 5. Hay big rock pero el conteo queda en 0: distinguir la causa real
    # (área bajo el mínimo vs. relación de aspecto excesiva) inspeccionando las
    # regiones rechazadas, en vez de suponerla.
    rechazo = df[(df.n_bigrock > 0) & (df.n_rocks == 0)]
    por_causa: dict[str, str] = {}
    for r in rechazo.sort_values("n_bigrock").itertuples():
        causa, detalle = _causa_rechazo(r.image_id)
        if causa and causa not in por_causa:
            por_causa[causa] = detalle
            cases.append((r.image_id, causa, detalle))
        if len(por_causa) == 2:
            break

    return cases


def render(image_id: str, modo: str, subtitulo: str, bandera: str = "ok") -> Path | None:
    """Panel de 3 columnas para una escena; devuelve la ruta guardada."""
    img_p = config.MSL_NCAM_IMAGES / f"{image_id}.JPG"
    mask_p = config.MSL_NCAM_LABELS_TRAIN / f"{image_id}.png"
    if not mask_p.exists() or not img_p.exists():
        print(f"  [omitida] falta imagen o máscara: {image_id}")
        return None

    mask = mu.read_mask(mask_p)
    with Image.open(img_p) as im:
        img = np.asarray(im.convert("L"))

    stages = rc.compute_stages(mu.big_rock_mask(mask), rc.DEFAULT_PARAMS)
    ws = stages["labels_ws"]
    kept = np.isin(ws, stages["kept_ids"])

    fig, axes = plt.subplots(1, 3, figsize=(14, 5.4))
    fig.patch.set_facecolor("white")

    axes[0].imshow(img, cmap="gray")
    axes[0].set_title("1. Imagen original", fontsize=FS)

    axes[1].imshow(_nav_for_plot(mask), cmap=NAV_CMAP, norm=NAV_NORM, interpolation="nearest")
    axes[1].set_title("2. Máscara colaborativa de AI4Mars", fontsize=FS)

    axes[2].imshow(img, cmap="gray")
    if kept.any():
        axes[2].imshow(_rock_overlay(ws, stages["kept_ids"]))
        axes[2].contour(kept, levels=[0.5], colors="white", linewidths=1.2)
    n = len(stages["kept_ids"])
    rocas = f"{n} roca" if n == 1 else f"{n} rocas"
    if bandera == "ok":
        titulo = f"3. Rocas contadas: {rocas}"
    elif bandera == "mostly_null":
        titulo = f"3. Conteo si se incluyera: {rocas}\n(escena casi sin etiquetar, excluida de E2)"
    else:
        titulo = f"3. Rocas contadas: {rocas}\n(sin roca grande en la máscara)"
    axes[2].set_title(titulo, fontsize=FS)

    for ax in axes:
        ax.set_xticks([]); ax.set_yticks([])

    handles = [plt.Rectangle((0, 0), 1, 1, fc=NAV_CMAP(i), ec="#999999") for i in range(5)]
    fig.legend(handles, NAV_NAMES, loc="lower center", bbox_to_anchor=(0.5, -0.02),
               ncol=5, frameon=False, fontsize=FS - 2)

    fig.suptitle(_es(subtitulo[:1].upper() + subtitulo[1:]), fontsize=FS, y=0.99)
    fig.tight_layout(rect=(0, 0.05, 1, 0.94))

    OUT.mkdir(parents=True, exist_ok=True)
    out = OUT / f"{modo}.png"
    fig.savefig(out, dpi=130, bbox_inches="tight")
    plt.close(fig)
    return out


def main() -> None:
    df = pd.read_csv("outputs/results.csv")
    cases = select_cases(df)
    print(f"casos seleccionados: {len(cases)}")
    bandera = dict(zip(df.image_id, df.quality_flag))
    for image_id, modo, sub in cases:
        p = render(image_id, modo, sub, bandera.get(image_id, "ok"))
        if p:
            print(f"  {modo:22s} -> {p}")


if __name__ == "__main__":
    main()
