"""Figuras ilustrativas del pipeline (para calibración y para la tesis, §12).

Genera un panel de etapas: imagen original | máscara AI4Mars | binaria limpia |
transformada de distancia con semillas | resultado del watershed con el conteo.

Usa el backend ``Agg`` (no interactivo) para poder guardar a archivo en cualquier
entorno. Las funciones devuelven la figura de matplotlib.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from . import config, mask_utils as mu, rock_count as rc

# Colores por clase NAV (índices 0,1,2,3 y 255→último).
_NAV_COLORS = {
    config.NAV_SOIL: "#caa472",      # soil  - tostado
    config.NAV_BEDROCK: "#8c5a2b",   # bedrock - marrón
    config.NAV_SAND: "#f2d479",      # sand  - amarillo
    config.NAV_BIG_ROCK: "#d7301f",  # big rock - rojo
    config.NAV_NULL: "#202020",      # null  - gris oscuro
}


_NAV_NOMBRES = {
    config.NAV_SOIL: "suelo",
    config.NAV_BEDROCK: "lecho rocoso",
    config.NAV_SAND: "arena",
    config.NAV_BIG_ROCK: "roca grande",
    config.NAV_NULL: "sin etiqueta",
}


def _plural(n: int, palabra: str) -> str:
    return f"{n} {palabra}" if n == 1 else f"{n} {palabra}s"


def mask_to_rgb(mask: np.ndarray) -> np.ndarray:
    """Convierte una máscara NAV a imagen RGB (uint8) para visualización."""
    rgb = np.zeros((*mask.shape, 3), dtype=np.uint8)
    for val, hexcol in _NAV_COLORS.items():
        h = hexcol.lstrip("#")
        color = tuple(int(h[i : i + 2], 16) for i in (0, 2, 4))
        rgb[mask == val] = color
    return rgb


def plot_pipeline(
    image_path: str | Path,
    mask_path: str | Path,
    params: dict[str, Any] | None = None,
    save_path: str | Path | None = None,
    title: str | None = None,
) -> "plt.Figure":
    """Dibuja las 5 etapas del pipeline de conteo para un par (imagen, máscara)."""
    img = np.asarray(mu.read_mask(image_path))  # NavCam es escala de grises
    mask = mu.read_mask(mask_path)
    rock = mu.big_rock_mask(mask)
    s = rc.compute_stages(rock, params)

    n_rocks = len(s["kept_ids"])
    kept = np.isin(s["labels_ws"], s["kept_ids"]) if s["kept_ids"] else np.zeros_like(rock)

    fig, axes = plt.subplots(1, 5, figsize=(16, 4.4))
    fs = 15

    axes[0].imshow(img, cmap="gray")
    axes[0].set_title("1. Imagen original\n", fontsize=fs)

    axes[1].imshow(mask_to_rgb(mask))
    axes[1].set_title("2. Máscara de AI4Mars\n", fontsize=fs)

    axes[2].imshow(s["clean"], cmap="gray")
    axes[2].set_title(f"3. Roca grande depurada\n({_plural(s['n_raw_components'], 'componente')})",
                      fontsize=fs)

    axes[3].imshow(s["distance"], cmap="magma")
    if len(s["coords"]):
        axes[3].scatter(s["coords"][:, 1], s["coords"][:, 0], s=22,
                        c="cyan", marker="x", linewidths=1.0)
    axes[3].set_title(f"4. Distancia y semillas\n({_plural(len(s['coords']), 'semilla')})",
                      fontsize=fs)

    # Watershed: colorear cada roca aceptada (color aleatorio por label); fondo gris.
    ws_disp = np.where(kept, s["labels_ws"], 0)
    ncol = int(s["labels_ws"].max()) + 1
    rng = np.random.default_rng(0)
    lut = rng.random((max(ncol, 1), 3))
    lut[0] = 0
    axes[4].imshow(s["clean"], cmap="gray", alpha=0.3)
    if ncol > 1:
        overlay = lut[ws_disp]                      # (H,W,3)
        alpha = (ws_disp > 0).astype(float)         # (H,W)
        axes[4].imshow(np.dstack([overlay, alpha]))  # RGBA
    axes[4].set_title(f"5. División de aguas\n({_plural(n_rocks, 'roca')})", fontsize=fs)

    for ax in axes:
        ax.axis("off")

    from matplotlib.patches import Patch
    fig.legend(handles=[Patch(facecolor=_NAV_COLORS[v], edgecolor="#999999", label=lab)
                        for v, lab in _NAV_NOMBRES.items()],
               loc="lower center", ncol=len(_NAV_NOMBRES), fontsize=fs - 2, frameon=False,
               bbox_to_anchor=(0.5, -0.06))

    sup = title or Path(mask_path).stem
    p = s["params"]
    fig.suptitle(
        f"{sup}\nmin_area_frac={p['min_area_frac']}  peak_min_distance={p['peak_min_distance']}"
        f"  distance_sigma={p['distance_sigma']}  max_aspect_ratio={p['max_aspect_ratio']}",
        fontsize=11,
    )
    fig.tight_layout(rect=(0, 0, 1, 0.92))

    if save_path is not None:
        Path(save_path).parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(save_path, dpi=110, bbox_inches="tight")
    return fig
