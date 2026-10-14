#!/usr/bin/env python
"""Sensibilidad del contraste entre fuentes (H3) al nivel de consenso de las máscaras de experto.

AI4Mars publica las máscaras de especialista en tres niveles (``masked-gold-min{1,2,3}-100agree``):
un píxel entra en el nivel K si al menos K especialistas lo etiquetaron y todos coinciden. El
análisis principal usa el nivel 1; este guion repite con los niveles 2 y 3:

- la comparación directa de la cobertura entre fuentes (escenas con roca, todas las imágenes);
- la descomposición de la diferencia de medias con el instrumento común.

El instrumento no se vuelve a ejecutar. Su cobertura sobre la región anotable
(``cob_modelo_reg``) es una función de la imagen y no depende de la máscara de experto, de modo
que se toma de ``outputs/fuente_anotacion.csv``. Lo único que cambia con el nivel es la cobertura
según la etiqueta, que se recalcula sobre la máscara de ese nivel, y qué imágenes conservan algún
píxel etiquetado. El modelo no interviene en ningún momento con las máscaras de experto.

Salida: ``outputs/sensibilidad_nivel_experto.json``.

Uso:  python scripts/sensibilidad_nivel_experto.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))
sys.path.insert(0, str(RAIZ / "scripts"))
from src import config, mask_utils as mu, poblaciones  # noqa: E402
from sensibilidad_dependencia_temporal import sol_de  # noqa: E402

N_BOOT = 2000
SEMILLA = 0
NIVELES = (1, 2, 3)


def cobertura_etiqueta(mask_path: Path) -> float | None:
    """Roca / píxeles etiquetados, como ``cob_etiqueta`` en eval_fuente_anotacion.py."""
    m = mu.read_mask(mask_path)
    val = m != config.NAV_NULL
    if val.sum() == 0:
        return None
    return 100 * float((np.isin(m, config.COVERAGE_CLASSES) & val).sum()) / int(val.sum())


def descomposicion(fa: pd.DataFrame, rng) -> dict:
    """Componentes de imágenes y de anotación, con IC por escena y por sol."""
    c, e = fa[fa.fuente == "colaborativa"], fa[fa.fuente == "experto"]

    def comp(cs, es):
        img = cs.cob_modelo_reg.mean() - es.cob_modelo_reg.mean()
        anot = (cs.cob_etiqueta - cs.cob_modelo_reg).mean() - (es.cob_etiqueta - es.cob_modelo_reg).mean()
        return float(img), float(anot)

    tot = float(c.cob_etiqueta.mean() - e.cob_etiqueta.mean())
    img, anot = comp(c, e)
    bi, ba = [], []
    for _ in range(N_BOOT):
        bi_, ba_ = comp(c.sample(len(c), replace=True, random_state=rng.integers(1 << 31)),
                        e.sample(len(e), replace=True, random_state=rng.integers(1 << 31)))
        bi.append(bi_); ba.append(ba_)
    gc = [g.index.values for _, g in c.groupby("sol")]
    ge = [g.index.values for _, g in e.groupby("sol")]
    bs = []
    for _ in range(N_BOOT):
        cs = fa.loc[np.concatenate([gc[i] for i in rng.integers(0, len(gc), len(gc))])]
        es = fa.loc[np.concatenate([ge[i] for i in rng.integers(0, len(ge), len(ge))])]
        bs.append(comp(cs, es)[1])
    pct = lambda v: [float(np.percentile(v, 2.5)), float(np.percentile(v, 97.5))]  # noqa: E731
    return {"n_experto": int(len(e)), "n_soles_experto": len(ge),
            "cob_etiqueta_experto_media": float(e.cob_etiqueta.mean()),
            "cob_etiqueta_experto_mediana": float(e.cob_etiqueta.median()),
            "total": tot, "imagenes": img, "anotacion": anot,
            "pct_imagenes": 100 * img / tot, "pct_anotacion": 100 * anot / tot,
            "ic95_imagenes": pct(bi), "ic95_anotacion": pct(ba), "ic95_anotacion_sol": pct(bs)}


def main() -> None:
    base = config.MSL_NCAM_LABELS_TRAIN.parent / "test"
    d = pd.read_csv(RAIZ / "outputs/results.csv")
    colab_roca = poblaciones.poblacion_e1(d)
    colab_roca = colab_roca.loc[colab_roca.rock_coverage_pct > 0, "rock_coverage_pct"].to_numpy()
    muestras = {"general": pd.read_csv(RAIZ / "outputs/fuente_anotacion.csv"),
                "prueba": pd.read_csv(RAIZ / "outputs/fuente_anotacion_prueba.csv")}
    for fa in muestras.values():
        fa["sol"] = sol_de(fa.image_id)

    out: dict = {"metodo": {"n_boot": N_BOOT, "semilla": SEMILLA,
                            "instrumento": "cob_modelo_reg de outputs/fuente_anotacion*.csv, sin reejecutar"},
                 "niveles": {}}
    for k in NIVELES:
        carpeta = base / f"masked-gold-min{k}-100agree"
        # Comparación directa: todas las máscaras de experto del nivel, escenas con roca.
        g = pd.read_csv(RAIZ / f"outputs/results_test_masked-gold-min{k}-100agree.csv")
        ge1 = poblaciones.poblacion_e1(g)
        b = ge1.loc[ge1.rock_coverage_pct > 0, "rock_coverage_pct"].to_numpy()
        rng = np.random.default_rng(SEMILLA)
        dif = [np.median(rng.choice(colab_roca, len(colab_roca))) - np.median(rng.choice(b, len(b)))
               for _ in range(N_BOOT)]
        directa = {"n_escenas": int(len(g)), "n_con_etiqueta": int(len(ge1)), "n_con_roca": int(len(b)),
                   "frac_valid_mediana": float(ge1.frac_valid.median()),
                   "cob_mediana_con_roca": float(np.median(b)),
                   "dif_mediana": float(np.median(colab_roca) - np.median(b)),
                   "ic95_dif_mediana": [float(np.percentile(dif, 2.5)), float(np.percentile(dif, 97.5))],
                   "mann_whitney_p": float(stats.mannwhitneyu(colab_roca, b).pvalue)}
        nivel = {"comparacion_directa": directa}
        # Descomposición con el instrumento común, en las dos muestras colaborativas.
        for nombre, fa in muestras.items():
            fk = fa.copy()
            esp = fk.fuente == "experto"
            cob = {iid: cobertura_etiqueta(carpeta / f"{iid}.png") for iid in fk.loc[esp, "image_id"]}
            if k == 1:   # el nivel 1 debe reproducir exactamente el análisis principal
                assert all(abs(cob[i] - v) < 1e-9 for i, v in zip(fk.loc[esp, "image_id"], fk.loc[esp, "cob_etiqueta"]))
            fk.loc[esp, "cob_etiqueta"] = fk.loc[esp, "image_id"].map(cob)
            fk = fk[~(esp & fk.cob_etiqueta.isna())].copy()
            r = descomposicion(fk, np.random.default_rng(SEMILLA))
            # Componente de anotación con la etiqueta del nivel 1 sobre las mismas imágenes: separa
            # el efecto de las imágenes que el nivel deja sin etiqueta del efecto del consenso.
            c1, e1 = fa[fa.fuente == "colaborativa"], fa[(fa.fuente == "experto") & fa.image_id.isin(fk.image_id)]
            r["anotacion_nivel1_mismas_imagenes"] = float((c1.cob_etiqueta - c1.cob_modelo_reg).mean()
                                                          - (e1.cob_etiqueta - e1.cob_modelo_reg).mean())
            nivel[f"descomposicion_{nombre}"] = r
        out["niveles"][f"nivel{k}"] = nivel

    # Comprobación: el nivel 1 reproduce la descomposición publicada.
    ref = json.load(open(RAIZ / "outputs/fuente_anotacion_resumen.json"))["descomposicion"]
    n1 = out["niveles"]["nivel1"]["descomposicion_general"]
    assert all(abs(n1[c] - ref[c]) < 1e-9 for c in ("total", "imagenes", "anotacion"))

    destino = RAIZ / "outputs/sensibilidad_nivel_experto.json"
    destino.write_text(json.dumps(out, indent=1, ensure_ascii=False))
    print(json.dumps(out, indent=1, ensure_ascii=False))
    print(f"-> {destino.relative_to(RAIZ)}")


if __name__ == "__main__":
    main()
