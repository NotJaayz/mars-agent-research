#!/usr/bin/env python
"""Genera tesis/cifras.tex: una macro LaTeX por cada cifra que cita el documento.

Todas las cifras de la tesis se calculan aquí a partir de los archivos de resultados, y el
texto solo referencia las macros. Así una cifra no puede quedar desactualizada respecto de
los datos, ni mezclar dos poblaciones distintas: si cambia un resultado, basta regenerar.

Convenciones:
  - Población de E2: escenas con bandera "ok" (contienen roca grande y menos del 95 % sin
    etiqueta). Las escenas "mostly_null" con roca grande se excluyen de E2.
  - Cobertura "calculable": escenas con al menos un píxel etiquetado.
  - Los números se escriben con siunitx (\\num, \\SI) para respetar la coma decimal.

Uso:  python scripts/generar_cifras.py
"""
from __future__ import annotations

import json
import sys
import re
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import cohen_kappa_score

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from src import poblaciones  # noqa: E402

OUT = Path("tesis/cifras.tex")
BANDAS6 = ["0", "1-3", "4-9", "10-24", "25-49", "50+"]
M: dict[str, str] = {}


def n(x):
    return rf"\num{{{int(round(x))}}}"


def f(x, d=2):
    return rf"\num{{{x:.{d}f}}}"


def s(x, d=1):
    """Número con signo explícito."""
    return (r"\ensuremath{+}" if x >= 0 else "") + rf"\num{{{x:.{d}f}}}"


def p(x, d=1):
    return rf"\SI{{{x:.{d}f}}}{{\percent}}"


def ic(lo, hi, d=2, signo=False):
    g = s if signo else f
    return f"[{g(lo, d)}; {g(hi, d)}]"


def pv(x):
    """Valor p: con tres decimales, o como cota inferior si es muy pequeño."""
    if x < 0.001:
        return r"\num{< 0.001}"
    return f(x, 3)


def m(nombre, valor):
    assert re.fullmatch(r"[A-Za-z]+", nombre), nombre
    M[nombre] = valor


def main():
    d = pd.read_csv("outputs/results.csv")
    ok = poblaciones.poblacion_e2(d)          # población única de E2
    e1 = poblaciones.poblacion_e1(d)
    rb = e1[e1.rock_coverage_pct > 0]
    res2 = poblaciones.resumen_e2(d)
    assert res2["n_rocas"] == int(ok.n_rocks.sum())

    # --- Conjunto --------------------------------------------------------------------
    m("cNEscenas", n(len(d)))
    m("cNImagenes", n(18127))
    assert len(e1) == int(d.rock_coverage_pct.notna().sum())
    m("cNCobCalc", n(len(e1)))
    m("cPctCobCalc", p(100 * len(e1) / len(d)))
    m("cNCobPos", n(len(rb))); m("cPctCobPos", p(100 * len(rb) / len(d)))
    m("cFracValidMed", f(d.frac_valid.median()))
    for flag, nom in (("ok", "Ok"), ("no_bigrock", "NoBig"), ("no_rock", "NoRock"),
                      ("mostly_null", "Null"), ("empty", "Empty")):
        k = int((d.quality_flag == flag).sum())
        m(f"cFlag{nom}", n(k)); m(f"cFlag{nom}Pct", f(100 * k / len(d), 1))
    big = d[d.has_bigrock.astype(bool)]
    m("cNBigAny", n(len(big))); m("cPctBigAny", p(100 * len(big) / len(d)))
    mn = d[d.has_bigrock.astype(bool) & d.is_mostly_null.astype(bool)]
    m("cNNullBig", n(len(mn))); m("cRocasNullBig", n(mn.n_rocks.sum()))
    m("cNOjoIzq", n((d.eye == "L").sum())); m("cNOjoDer", n((d.eye == "R").sum()))

    # --- E1 --------------------------------------------------------------------------
    m("cCobMedVal", p(rb.rock_coverage_pct.median())); m("cCobMediaVal", p(rb.rock_coverage_pct.mean()))
    m("cCobMedTot", p(rb.coverage_total_pct.median())); m("cCobMediaTot", p(rb.coverage_total_pct.mean()))
    k = int((rb.rock_coverage_pct == 100).sum())
    m("cNCobCien", n(k)); m("cPctCobCien", p(100 * k / len(rb)))
    m("cNCobMitad", n((d.rock_coverage_pct > 50).sum()))

    # --- E2 (src.poblaciones: con roca grande y no casi vacía) ------------------------
    m("cNRocas", n(res2["n_rocas"])); m("cRocasMax", n(ok.n_rocks.max()))
    m("cRocasMed", n(ok.n_rocks.median()))
    m("cRawMedio", f(ok.n_raw_components.mean())); m("cRocasMedio", f(ok.n_rocks.mean()))
    bandas = pd.cut(ok.n_rocks, [-1, 0, 1, 3, 9, 10 ** 6], labels=["Cero", "Una", "DosTres", "CuatroNueve", "Diez"])
    for b in ["Cero", "Una", "DosTres", "CuatroNueve", "Diez"]:
        k = int((bandas == b).sum()); m(f"cBanda{b}", n(k)); m(f"cBanda{b}Pct", f(100 * k / len(ok), 1))
    tam = ok[["n_small", "n_medium", "n_large"]].sum(); tt = tam.sum()
    for col, nom in (("n_small", "Peq"), ("n_medium", "Med"), ("n_large", "Gra")):
        m(f"cTam{nom}", n(tam[col])); m(f"cTam{nom}Pct", f(100 * tam[col] / tt, 1))
    con = ok[ok.n_rocks >= 1]
    m("cNConRocas", n(len(con)))
    sol = con.mean_solidity.dropna()
    m("cSolidezMedia", f(sol.mean(), 3)); m("cNSolidezBaja", n((sol < 0.7).sum()))
    sub = con[con.n_rocks > con.n_raw_components]
    m("cNSubdiv", n(len(sub))); m("cPctSubdiv", p(100 * len(sub) / len(con)))
    m("cRocasSubdiv", n(sub.n_rocks.sum()))
    m("cNMayorMitad", n((ok.largest_rock_pct > 50).sum()))

    # --- Composición y tipología ------------------------------------------------------
    for col, nom in (("pct_bedrock", "Bed"), ("pct_soil", "Soil"), ("pct_sand", "Sand"), ("pct_bigrock", "Big")):
        m(f"cComp{nom}", p(d[col].mean()))
    for cls, nom in (("bedrock", "Bed"), ("soil", "Soil"), ("sand", "Sand"), ("bigrock", "Big")):
        m(f"cDom{nom}", n((d.dominant_class == cls).sum()))
    for t, nom in (("rocoso", "Rocoso"), ("suelo", "Suelo"), ("arenoso", "Arenoso"), ("mixto", "Mixto"),
                   ("sin_etiqueta", "SinEtiq")):
        k = int((d.scene_type == t).sum()); m(f"cTipo{nom}", n(k)); m(f"cTipo{nom}Pct", f(100 * k / len(d), 1))

    # --- Diagnóstico del conteo --------------------------------------------------------
    sinbig = d[d.n_bigrock == 0]
    m("cNSinBig", n(len(sinbig))); m("cPctSinBig", p(100 * len(sinbig) / len(d)))
    nb = d[d.quality_flag == "no_bigrock"]
    m("cNoBigBedMed", p(nb.pct_bedrock.median())); m("cNoBigBedOchenta", n((nb.pct_bedrock > 80).sum()))
    roca = d[d.rock_coverage_pct > 1]
    sb, sg = roca.pct_bedrock.sum(), roca.pct_bigrock.sum()
    m("cParteBed", p(100 * sb / (sb + sg))); m("cParteBig", p(100 * sg / (sb + sg)))
    m("cNFiltradas", n((ok.n_rocks == 0).sum()))
    m("cPctFiltradas", p(100 * (ok.n_rocks == 0).sum() / len(d)))
    m("cPctNullBig", p(100 * len(mn) / len(d)))
    m("cPctConRocas", p(100 * (ok.n_rocks > 0).sum() / len(d)))
    m("cNArtefacto", n(((d.largest_rock_pct > 95) & (d.frac_valid < 0.05)).sum()))
    m("cNArtefactoOk", n(((ok.largest_rock_pct > 95) & (ok.frac_valid < 0.05)).sum()))

    # --- Sensibilidad a la versión de la cobertura (sobre la imagen completa) -------------
    from scipy import stats
    cc = d.dropna(subset=["rock_coverage_pct"])
    m("cSensRho", f(stats.spearmanr(cc.rock_coverage_pct, cc.coverage_total_pct)[0]))
    m("cSensMitadTot", n((cc.coverage_total_pct > 50).sum()))
    r1 = stats.pearsonr(ok.coverage_total_pct, ok.n_rocks); r2 = stats.spearmanr(ok.coverage_total_pct, ok.n_rocks)
    m("cSensConteoPearson", s(r1[0], 3)); m("cSensConteoPearsonP", pv(r1[1]))
    m("cSensConteoSpearman", s(r2[0], 3)); m("cSensConteoSpearmanP", pv(r2[1]))
    g1 = pd.read_csv("outputs/results_test_masked-gold-min1-100agree.csv").dropna(subset=["rock_coverage_pct"])
    a, b = cc[cc.rock_coverage_pct > 0].coverage_total_pct, g1[g1.rock_coverage_pct > 0].coverage_total_pct
    m("cSensTotColab", p(a.median())); m("cSensTotExp", p(b.median()))
    m("cSensTotP", pv(stats.mannwhitneyu(a, b).pvalue))

    # --- Máscaras de experto -------------------------------------------------------------
    for k, nom in ((1, "Uno"), (2, "Dos"), (3, "Tres")):
        g = pd.read_csv(f"outputs/results_test_masked-gold-min{k}-100agree.csv")
        m(f"cGold{nom}Big", p(100 * (g.n_bigrock > 0).mean()))
        m(f"cGold{nom}Rocas", f(g.n_rocks.mean()))
        m(f"cGold{nom}CobMed", p(g.rock_coverage_pct.median()))
        if k == 1:
            m("cNGold", n(len(g)))
            m("cGoldCobMedPos", p(g.loc[g.rock_coverage_pct > 0, "rock_coverage_pct"].median()))
            m("cGoldSueloArena", p(g.pct_soil.mean() + g.pct_sand.mean()))
            m("cGoldBed", p(g.pct_bedrock.mean()))
            gr = g[g.rock_coverage_pct > 0]
            m("cGoldPctCien", p(100 * (gr.rock_coverage_pct == 100).mean(), 0))
    m("cColabCobMed", p(d.rock_coverage_pct.median()))
    m("cColabRocas", f(d.n_rocks.mean())); m("cColabSueloArena", p(d.pct_soil.mean() + d.pct_sand.mean()))
    m("cColabBed", p(d.pct_bedrock.mean()))
    m("cColabPctCien", p(100 * (rb.rock_coverage_pct == 100).mean(), 0))

    # --- Fuente de anotación: instrumento común -----------------------------------------
    fa = json.load(open("outputs/fuente_anotacion_resumen.json"))
    m("cFANColab", n(fa["n_colaborativa"])); m("cFANExp", n(fa["n_experto"]))
    for col, nom in (("cob_etiqueta", "Etiq"), ("cob_modelo_reg", "Reg"), ("cob_modelo_val", "Val")):
        r = fa[col]
        m(f"cFA{nom}MedColab", p(r["mediana_colab"])); m(f"cFA{nom}MedExp", p(r["mediana_experto"]))
        m(f"cFA{nom}MediaColab", p(r["media_colab"])); m(f"cFA{nom}MediaExp", p(r["media_experto"]))
        m(f"cFA{nom}P", pv(r["mann_whitney_p"]))
    m("cFAFracColab", f(fa["frac_reg"]["mediana_colab"])); m("cFAFracExp", f(fa["frac_reg"]["mediana_experto"]))
    de = fa["descomposicion"]
    m("cDescTotal", s(de["total"])); m("cDescImg", s(de["imagenes"])); m("cDescAnot", s(de["anotacion"]))
    m("cDescImgPct", p(de["pct_imagenes"], 0)); m("cDescAnotPct", p(de["pct_anotacion"], 0))
    m("cDescImgIC", ic(*de["ic95_imagenes"], 1, True)); m("cDescAnotIC", ic(*de["ic95_anotacion"], 1, True))
    m("cResColab", s(fa["residuo_colaborativa"]["media"])); m("cResExp", s(fa["residuo_experto"]["media"]))

    # Prueba de dos muestras sobre todo el conjunto (escenas con cobertura > 0).
    from scipy import stats
    g1 = pd.read_csv("outputs/results_test_masked-gold-min1-100agree.csv")
    a = rb.rock_coverage_pct.to_numpy(); b = g1.loc[g1.rock_coverage_pct > 0, "rock_coverage_pct"].to_numpy()
    rng = np.random.default_rng(0)
    dif = [np.median(rng.choice(a, len(a))) - np.median(rng.choice(b, len(b))) for _ in range(2000)]
    m("cFuenteDifMed", s(np.median(a) - np.median(b))); m("cFuenteDifIC", ic(*np.percentile(dif, [2.5, 97.5]), 1, True))
    m("cFuenteMWp", pv(stats.mannwhitneyu(a, b).pvalue))
    fv = stats.mannwhitneyu(d.frac_valid.dropna(), g1.frac_valid.dropna()).pvalue
    m("cFracValidGold", f(g1.frac_valid.median())); m("cFracValidP", f(fv, 2))

    # --- Dependencia entre indicadores --------------------------------------------------
    dep = json.load(open("outputs/analisis_dependencia.json"))
    for clave, nom in (("cobertura_conteo", "CC"), ("frac_cobertura", "FC"), ("frac_cobertura_total", "FT")):
        r = dep[clave]
        m(f"cDep{nom}N", n(r["n"]))
        m(f"cDep{nom}Pearson", s(r["pearson"], 3)); m(f"cDep{nom}PearsonIC", ic(*r["ic95_pearson"], 3, True))
        m(f"cDep{nom}PearsonP", pv(r["p_pearson"]))
        m(f"cDep{nom}Spearman", s(r["spearman"], 3)); m(f"cDep{nom}SpearmanIC", ic(*r["ic95_spearman"], 3, True))
        m(f"cDep{nom}SpearmanP", pv(r["p_spearman"]))
        m(f"cDep{nom}Kendall", s(r["kendall"], 3)); m(f"cDep{nom}KendallP", pv(r["p_kendall"]))
        m(f"cDep{nom}Dcor", f(r["dcor"], 3)); m(f"cDep{nom}DcorP", pv(r["p_dcor"]))
        m(f"cDep{nom}IM", f(r["im_bits"], 3)); m(f"cDep{nom}IMNula", f(r["im_nula_p95"], 3))
        m(f"cDep{nom}IMP", pv(r["p_im_bits"]))
    c2 = dep["cobertura_conteo"]["chi2"]
    m("cChiDos", f(c2["chi2"], 1)); m("cChiGl", n(c2["gl"])); m("cChiP", f(c2["p"], 3)); m("cCramer", f(c2["v_cramer"], 3))
    m("cDepDcorSub", n(dep["frac_cobertura"].get("dcor_submuestra", 0)))

    def eta2(y, g):
        mu = y.mean(); gr = y.groupby(g, observed=True)
        return float((gr.size() * (gr.mean() - mu) ** 2).sum() / ((y - mu) ** 2).sum())
    m("cEtaConteo", p(100 * eta2(ok.n_rocks, pd.qcut(ok.rock_coverage_pct, 10, duplicates="drop"))))
    m("cEtaCob", p(100 * eta2(ok.rock_coverage_pct, pd.cut(ok.n_rocks, [-.5, .5, 1.5, 3.5, 9.5, 1e6]))))
    def eta2_perm(y, g, k=999, seed=0):
        rng = np.random.default_rng(seed); obs = eta2(y, g)
        nul = [eta2(pd.Series(rng.permutation(y.values), index=y.index), g) for _ in range(k)]
        return float(np.percentile(nul, 95)), (1 + sum(v >= obs for v in nul)) / (k + 1)
    q95, pe = eta2_perm(ok.n_rocks, pd.qcut(ok.rock_coverage_pct, 10, duplicates="drop"))
    m("cEtaConteoNula", p(100 * q95)); m("cEtaConteoP", f(pe, 3))
    q95, pe = eta2_perm(ok.rock_coverage_pct, pd.cut(ok.n_rocks, [-.5, .5, 1.5, 3.5, 9.5, 1e6]))
    m("cEtaCobNula", p(100 * q95)); m("cEtaCobP", f(pe, 3))
    tramo = pd.cut(ok.rock_coverage_pct, [0, 10, 50, 80, 99.99, 100], include_lowest=True,
                   labels=["A", "B", "C", "D", "E"])
    for t in "ABCDE":
        g = ok[tramo == t]
        m(f"cUN{t}", n(len(g))); m(f"cUMedia{t}", f(g.n_rocks.mean()))
        m(f"cUCero{t}", f(100 * (g.n_rocks == 0).mean(), 1)); m(f"cUCuatro{t}", f(100 * (g.n_rocks >= 4).mean(), 1))
    for k, (rango, v) in enumerate(dep["cobertura_por_tramo_frac"].items()):
        L = "ABCD"[k]
        m(f"cFTN{L}", n(v["n"])); m(f"cFTMed{L}", p(v["mediana"])); m(f"cFTMedTot{L}", p(v["mediana_total"]))

    # --- Validación humana (ronda definitiva) --------------------------------------------
    v = (pd.read_csv("outputs/validacion_manual_v2/plantilla.csv", dtype={"banda": str})
           .merge(pd.read_csv("outputs/validacion_manual_v2/clave.csv"), on="id"))
    def b6(x): return ("0" if x == 0 else "1-3" if x <= 3 else "4-9" if x <= 9 else "10-24" if x <= 24 else "25-49" if x <= 49 else "50+")
    v["ba"] = v.auto.map(b6); idx = {b: i for i, b in enumerate(BANDAS6)}
    dv = v.ba.map(idx) - v.banda.map(idx)
    m("cVN", n(len(v))); m("cVAcuerdo", p(100 * (dv == 0).mean(), 0))
    from scipy.stats import binomtest
    m("cVSignoP", pv(binomtest(int((dv < 0).sum()), int((dv != 0).sum()), 0.5).pvalue))
    kk = cohen_kappa_score(v.banda, v.ba, labels=BANDAS6); kp = cohen_kappa_score(v.banda, v.ba, labels=BANDAS6, weights="linear")
    m("cVKappa", f(kk)); m("cVKappaPond", f(kp))
    bk, bp = [], []
    for _ in range(4000):
        i = rng.integers(0, len(v), len(v)); yy, xx = v.banda.to_numpy()[i], v.ba.to_numpy()[i]
        if len(set(yy)) > 1:
            bk.append(cohen_kappa_score(yy, xx, labels=BANDAS6)); bp.append(cohen_kappa_score(yy, xx, labels=BANDAS6, weights="linear"))
    m("cVKappaIC", ic(*np.percentile(bk, [2.5, 97.5]), 2, True)); m("cVKappaPondIC", ic(*np.percentile(bp, [2.5, 97.5]), 2, True))
    m("cVAbajo", n((dv < 0).sum())); m("cVArriba", n((dv > 0).sum()))
    m("cVMaxAuto", n(v.auto.max()))
    m("cVHumDiez", n((v.banda.map(idx) >= 3).sum())); m("cVHumVeinti", n((v.banda.map(idx) >= 4).sum()))
    coinc = v[dv == 0]
    m("cVCoincUnaTres", n((coinc.banda == "1-3").sum())); m("cVCoinc", n(len(coinc)))
    MIN = {"0": 0, "1-3": 1, "4-9": 4, "10-24": 10, "25-49": 25, "50+": 50}
    MAX = {"0": 0, "1-3": 3, "4-9": 9, "10-24": 24, "25-49": 49, "50+": 99}
    hmin = v.banda.map(MIN); hmax = v.banda.map(MAX)
    m("cVRocasAuto", n(v.auto.sum())); m("cVRocasHumMin", n(hmin.sum())); m("cVRocasHumMax", n(hmax.sum()))
    m("cVRazon", f(hmin.sum() / v.auto.sum(), 1)); m("cVDeficit", n((hmin - v.auto).clip(lower=0).sum()))
    # Anotación no exhaustiva: qué parte de la roca etiquetada es roca grande, en la muestra.
    import sys; sys.path.insert(0, ".")
    from src import config, mask_utils as mu
    fr, zona = [], []
    for r in v.itertuples():
        mk = mu.read_mask(config.MSL_NCAM_LABELS_TRAIN / f"{r.image_id}.png")
        big_, bed_ = (mk == 3), (mk == 1)
        fr.append(100 * big_.sum() / max((big_ | bed_).sum(), 1)); zona.append(100 * big_.sum() / mk.size)
    v["frbig"] = fr; v["zona"] = zona
    m("cVNoExhN", n((v.frbig < 20).sum())); m("cVNoExhMed", p(v.frbig.median()))
    u = v[v.banda == "1-3"]
    m("cVUnaTresN", n(len(u))); m("cVUnaTresZona", p(u.zona.median(), 2)); m("cVUnaTresFr", p(u.frbig.median()))

    sen = pd.read_csv("outputs/sensibilidad_parametros.csv")
    m("cSenN", n(len(sen))); m("cSenMin", f(sen.kappa_pond.min())); m("cSenMax", f(sen.kappa_pond.max()))
    m("cSenMed", f(sen.kappa_pond.median())); m("cSenAbajo", n((sen.abajo >= 20).sum()))
    m("cSenAbajoMin", n(sen.abajo.min())); m("cSenAbajoMax", n(sen.abajo.max()))
    m("cSenArribaMax", n(sen.arriba.max())); m("cSenDiez", n((sen.max_banda != "4-9").sum()))

    # --- Métodos con imagen dentro de la máscara ----------------------------------------
    em = json.load(open("outputs/eval_metodos_imagen.json"))
    for k, nom in (("grad", "Grad"), ("persist", "Persist"), ("sombra", "Sombra"), ("combo", "Combo")):
        r = em["metodos"][k]
        m(f"cMI{nom}Kw", f(r["kappa_pond"])); m(f"cMI{nom}Abajo", n(r["abajo"])); m(f"cMI{nom}Arriba", n(r["arriba"]))
        m(f"cMI{nom}Dif", s(r["dif_vs_e2"], 2)); m(f"cMI{nom}IC", ic(*r["ic95"], 2, True))
        m(f"cMI{nom}ICB", ic(*r["ic_bonferroni"], 2, True))
    sv = [r["kappa_pond"] for k, r in em["metodos"].items() if k.startswith("sombra_s")]
    m("cMISombraVarN", n(len(sv))); m("cMISombraVarMin", f(min(sv))); m("cMISombraVarMax", f(max(sv)))
    m("cMISombraVarBonf", n(sum(r["demostrable_bonferroni"] for k, r in em["metodos"].items() if k.startswith("sombra_s"))))

    # --- Segmentador ---------------------------------------------------------------------
    sc = json.load(open("outputs/split_deeplab_clases.json"))
    for k, nom in (("train", "Train"), ("val", "Val"), ("test", "Test")):
        m(f"cSplitRoca{nom}", p(sc[k]["pct_roca"])); m(f"cSplitIgn{nom}", p(sc[k]["pct_ignorado"]))
    sm = json.load(open("outputs/segmentacion_metricas.json"))
    m("cSegTrain", n(sm["config"]["n_train"])); m("cSegVal", n(sm["config"]["n_val"])); m("cSegTest", n(sm["config"]["n_test"]))
    m("cSegEpocas", n(sm["config"]["epochs"])); m("cSegLado", n(sm["config"]["img_size"]))
    m("cSegLote", n(sm["config"]["batch"])); m("cSegLR", r"\num{1e-4}")
    po = sm["poblacion"]
    m("cSegCandidatas", n(po["candidatas"])); m("cSegElegibles", n(po["elegibles"]))
    m("cSegExcluidas", n(po["excluidas_fraccion"])); m("cSegMargen", n(po["particiones"].get("margen", 0)))
    man = pd.read_csv("outputs/split_deeplab_manifiesto.csv")
    dur = man.groupby("bloque").sclk.agg(lambda x: (x.max() - x.min()) / 88775.244)
    m("cSegSolesBloque", n(dur.median()))
    m("cSegEpocaElegida", n(sm["epoca_elegida"])); m("cSegHash", sm["sha256_modelo"][:16] + "…")
    mv = max(e["miou"] for e in sm["epochs"]); m("cSegValMIoU", f(mv, 3))
    m("cSegValUltima", f(sm["epochs"][-1]["miou"], 3))
    t = sm["test"]
    m("cSegIoUNo", f(t["iou_no_roca"], 3)); m("cSegIoURoca", f(t["iou_roca"], 3)); m("cSegMIoU", f(t["miou"], 3))
    m("cSegRCob", f(t["r_cobertura"], 3)); m("cSegMAE", f(t["mae"], 1)); m("cSegErrMedio", s(t["error_medio"], 1))
    m("cSegDistMin", f(t["distancia_min_soles"], 1)); m("cSegDistMed", n(t["distancia_mediana_soles"]))
    for clave, nom in (("test_natural", "Nat"), ("test_excluidas_fraccion", "Exc")):
        r = sm[clave]
        m(f"cSeg{nom}N", n(r["n"])); m(f"cSeg{nom}MIoU", f(r["miou"], 3)); m(f"cSeg{nom}R", f(r["r_cobertura"], 3))
        m(f"cSeg{nom}MAE", f(r["mae"], 1)); m(f"cSeg{nom}Err", s(r["error_medio"], 1))
        m(f"cSeg{nom}IoURoca", f(r["iou_roca"], 3)); m(f"cSeg{nom}IoUNo", f(r["iou_no_roca"], 3))
    ra = json.load(open("outputs/segmentacion_metricas_reparto_aleatorio.json"))
    m("cAleMIoU", f(ra["test"]["miou"], 3)); m("cAleR", f(ra["prueba_total"]["r_cobertura"], 3))
    m("cAleMAE", f(ra["prueba_total"]["mae"], 1))
    m("cAleMinuto", n(ra["proximidad_prueba"]["menos_de_60s"]))
    m("cAleMinutoPct", p(100 * ra["proximidad_prueba"]["menos_de_60s"] / ra["prueba_total"]["n"], 0))
    ft = json.load(open("outputs/fuga_temporal.json"))
    m("cFugaMinSoles", f(ft["minimo_soles"], 1)); m("cFugaMedGapSoles", n(ft["mediana_gap_s"] / 88775.244))
    for lab, nom in (("1 a 10 soles", "A"), ("10 a 50 soles", "B"), ("más de 50 soles", "C")):
        r = ft["por_tramo"].get(lab)
        m(f"cFugaN{nom}", n(r["n"]) if r else "0")
        m(f"cFugaIoU{nom}", f(r["miou"], 3) if r else "---"); m(f"cFugaR{nom}", f(r["r_cobertura"], 3) if r else "---")
    m("cFugaExpSol", n(ft["experto"]["menos_de_1sol"]))
    m("cFugaExpHora", n(ft["experto"]["menos_de_1h"])); m("cFugaExpSoles", f(ft["experto"]["mediana_soles"], 1))
    ex = json.load(open("outputs/modelo_vs_experto_min1.json"))
    m("cExpIoUNo", f(ex["iou_no_roca"], 3)); m("cExpIoURoca", f(ex["iou_roca"], 3)); m("cExpMIoU", f(ex["miou"], 3))
    m("cExpR", f(ex["r_cobertura"], 3))
    md = json.load(open("outputs/modelo_detalle.json"))
    fa_csv = pd.read_csv("outputs/fuente_anotacion.csv")
    ex_ = fa_csv[fa_csv.fuente == "experto"]; err_ = (ex_.cob_modelo_val - ex_.cob_etiqueta).abs() < 1e-9
    m("cExpExactas", p(100 * err_.mean(), 0)); m("cExpExactasCero", p(100 * (err_ & (ex_.cob_etiqueta == 0)).sum() / max(err_.sum(), 1), 0))
    for k, nom in (("colaborativa", "Col"), ("experto", "Exp")):
        r = md[k]
        m(f"cBA{nom}N", n(r["n"])); m(f"cBA{nom}Media", s(r["media"], 2)); m(f"cBA{nom}MediaIC", ic(*r["ic95_media"], 2, True))
        m(f"cBA{nom}Mediana", s(r["mediana"], 1)); m(f"cBA{nom}MAE", f(r["mae"], 1)); m(f"cBA{nom}MAEIC", ic(*r["ic95_mae"], 1))
        m(f"cBA{nom}LoA", ic(*r["loa"], 1, True))
        m(f"cBA{nom}Diez", p(r["pct_mas_10"])); m(f"cBA{nom}Cincuenta", p(r["pct_mas_50"]))
    tramos = ["0", "0\u201325", "25\u201350", "50\u201375", "75\u201399,99", "100"]
    etiq = {"0": "0", "0\u201325": "0--25", "25\u201350": "25--50", "50\u201375": "50--75",
            "75\u201399,99": "75--99,99", "100": "100"}
    def celda(r):
        return f"{r['n']} & {s(r['media'], 1)} & {f(r['mae'], 1)}"
    filas = [r"\multicolumn{7}{l}{\textit{Por tramo de cobertura de la referencia (\%)}} \\"]
    for t in tramos:
        filas.append(f"{etiq[t]} & {celda(md['colaborativa']['por_tramo'][t])} & "
                     f"{celda(md['experto']['por_tramo'][t])} \\\\")
    filas.append(r"\midrule")
    filas.append(r"\multicolumn{7}{l}{\textit{Por tipo de escena}} \\")
    for t in ("suelo", "arenoso", "rocoso", "mixto"):
        filas.append(f"{t.capitalize()} & {celda(md['colaborativa']['por_tipo'][t])} & "
                     f"{celda(md['experto']['por_tipo'][t])} \\\\")
    cab = [r"\begin{tabular}{lrrrrrr}", r"\toprule",
           r" & \multicolumn{3}{c}{\textbf{Referencia colaborativa}} & \multicolumn{3}{c}{\textbf{Referencia de experto}} \\",
           r"\cmidrule(lr){2-4}\cmidrule(lr){5-7}",
           r" & $n$ & Medio & Absoluto & $n$ & Medio & Absoluto \\", r"\midrule"]
    Path("tesis/tabla_error_modelo.tex").write_text(
        "% ARCHIVO GENERADO por scripts/generar_cifras.py — no editar a mano.\n"
        + "\n".join(cab + filas + [r"\bottomrule", r"\end{tabular}"]) + "\n")
    sam = json.load(open("outputs/comparacion_sam_metricas.json"))
    m("cSamN", n(sam["n"])); m("cSamAcuerdo", p(sam["acuerdo_bandas_pct"], 0)); m("cSamRho", f(sam["spearman"]))
    m("cSamMAE", f(sam["mae"], 1))

    cv = json.load(open("outputs/calibracion_verificacion.json"))
    m("cCalRedBaja", p(cv["solidez_baja"]["reduccion_pct"], 0)); m("cCalNBaja", n(cv["solidez_baja"]["n"]))
    m("cCalRedMuchas", p(cv["mas_de_15"]["reduccion_pct"], 0)); m("cCalNMuchas", n(cv["mas_de_15"]["n"]))
    m("cCalNormN", n(cv["normales"]["n"])); m("cCalNormSinCambio", n(cv["normales"]["sin_cambio"]))
    m("cCalRedNorm", p(cv["normales"]["reduccion_pct"], 0))
    m("cCalSemillasA", n(cv["semillas_A_max"]))
    m("cPruebasN", n(sum(open(t).read().count("\ndef test_") for t in Path("tests").glob("test_*.py"))))
    hb = json.load(open("outputs/prueba_hibrido.json"))
    m("cHibridoN", n(hb["n_bloques"])); m("cHibridoRegion", p(100 * hb["fraccion_region"]))
    fp = json.load(open("outputs/fuente_anotacion_prueba_resumen.json"))
    m("cFPNColab", n(fp["n_colaborativa"]))
    m("cFPDescImg", s(fp["descomposicion"]["imagenes"])); m("cFPDescAnot", s(fp["descomposicion"]["anotacion"]))
    m("cFPDescImgPct", p(fp["descomposicion"]["pct_imagenes"], 0))
    m("cFPDescAnotIC", ic(*fp["descomposicion"]["ic95_anotacion"], 1, True))
    m("cFPRegMedColab", p(fp["cob_modelo_reg"]["mediana_colab"]))
    fv = json.load(open("outputs/fuente_anotacion_resumen_modelo_anterior.json"))
    m("cFVDescImgPct", p(fv["descomposicion"]["pct_imagenes"], 0)); m("cFVDescAnot", s(fv["descomposicion"]["anotacion"]))
    m("cFVDescAnotIC", ic(*fv["descomposicion"]["ic95_anotacion"], 1, True))

    # --- Capa aplicada y vetas ---------------------------------------------------------------
    al = json.load(open("outputs/priorizacion_resumen.json"))
    for k, nom in (("alta", "Alta"), ("media", "Media"), ("baja", "Baja"), ("sin_prioridad", "Sin")):
        m(f"cPrio{nom}", n(al["por_nivel"][k]))
    for k, nom in (("terreno_rocoso", "Rocoso"), ("arena_predominante", "Arena"), ("escena_no_evaluable", "NoEval"),
                   ("bloque_dominante", "Mayor"), ("campo_bloques", "Campo"), ("bloques_angulosos", "Angulosos")):
        m(f"cRegla{nom}", n(al["por_regla"][k]))
    pc = {(r["clave"], r["variable"]): r for r in al["percentiles_umbral"]}
    for (k, v), nom in ((("bloques_angulosos", "pct_bigrock"), "Big"), (("bloques_angulosos", "mean_solidity"), "Sol"),
                        (("bloque_dominante", "largest_rock_pct"), "Mayor"), (("campo_bloques", "n_rocks"), "Campo"),
                        (("arena_predominante", "pct_sand"), "Arena"), (("terreno_rocoso", "rock_coverage_pct"), "Rocoso")):
        m(f"cPerc{nom}", n(pc[(k, v)]["percentil"]))
    m("cRocosoSupera", p(pc[("terreno_rocoso", "rock_coverage_pct")]["pct_supera"], 0))
    ve = pd.read_csv("outputs/exploracion_vetas.csv")
    m("cVetaN", n(len(ve))); m("cVetaPrec", f(ve.precision_gris.mean(), 3)); m("cVetaRec", f(ve.recall_gris.mean(), 3))
    m("cVetaPrecC", f(ve.precision_color.mean(), 3)); m("cVetaRecC", f(ve.recall_color.mean(), 3))
    m("cVetaMejora", f(ve.mejora_gris.mean(), 1)); m("cVetaMejoraC", f(ve.mejora_color.mean(), 1))
    m("cVetaFallos", n((ve.mejora_gris == 0).sum())); m("cVetaFallosC", n((ve.mejora_color == 0).sum()))

    lineas = ["% =============================================================",
              "% ARCHIVO GENERADO — no editar a mano.",
              "% Generador: scripts/generar_cifras.py, a partir de outputs/.",
              "% =============================================================", ""]
    lineas += [rf"\newcommand{{\{k}}}{{{v}}}" for k, v in M.items()]
    OUT.write_text("\n".join(lineas) + "\n")
    print(f"-> {OUT}  ({len(M)} cifras)")


if __name__ == "__main__":
    main()
