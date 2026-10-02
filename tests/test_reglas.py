"""Pruebas de las reglas deterministas en que descansa la tesis.

Se ejecutan con:  python -m pytest tests/
Todas usan máscaras sintéticas, de modo que no requieren el conjunto de datos.
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from src import config, coverage as cov, mask_utils as mu, pipeline, poblaciones, rock_count as rc  # noqa: E402

SOIL, BED, SAND, BIG, NULL = (config.NAV_SOIL, config.NAV_BEDROCK, config.NAV_SAND,
                              config.NAV_BIG_ROCK, config.NAV_NULL)


def _disco(shape, centro, radio):
    yy, xx = np.ogrid[:shape[0], :shape[1]]
    return (yy - centro[0]) ** 2 + (xx - centro[1]) ** 2 <= radio ** 2


def _fila(mask: np.ndarray, tmp_path: Path) -> dict:
    """Procesa una máscara sintética con el pipeline completo."""
    p = tmp_path / "NLB_123456789EDR_F0000000NCAM00000M1.png"
    Image.fromarray(mask.astype(np.uint8), mode="L").save(p)
    return pipeline.process_image(p, p)


# --- Cobertura (E1) ---------------------------------------------------------------------

def test_null_queda_fuera_del_denominador():
    m = np.full((10, 10), NULL, np.uint8)
    m[:5, :] = BED            # 50 píxeles de roca
    m[5:6, :] = SOIL          # 10 de suelo; el resto, sin etiqueta
    c, d = cov.rock_coverage(m)
    assert d["n_valid"] == 60
    assert math.isclose(c, 100 * 50 / 60)
    assert math.isclose(d["coverage_total_pct"], 50.0)


def test_bedrock_y_bigrock_entran_en_e1_y_solo_bigrock_en_e2():
    m = np.array([[SOIL, BED, SAND, BIG, NULL]], np.uint8)
    assert mu.coverage_mask(m).tolist() == [[False, True, False, True, False]]
    assert mu.big_rock_mask(m).tolist() == [[False, False, False, True, False]]
    c, _ = cov.rock_coverage(m)
    assert math.isclose(c, 50.0)          # 2 de roca sobre 4 etiquetados


def test_mascara_vacia_da_cobertura_nan_y_bandera_empty(tmp_path):
    f = _fila(np.full((64, 64), NULL, np.uint8), tmp_path)
    assert f["rock_coverage_pct"] is None or math.isnan(f["rock_coverage_pct"])
    assert f["quality_flag"] == "empty"
    assert not f["is_e1_eligible"] and not f["is_e2_eligible"]


# --- Poblaciones ------------------------------------------------------------------------

def test_mostly_null_con_bigrock_no_entra_en_el_resumen_de_e2(tmp_path):
    casi_vacia = np.full((200, 200), NULL, np.uint8)
    casi_vacia[:30, :30] = BIG            # 2,25 % etiquetado, todo roca grande
    normal = np.full((200, 200), SOIL, np.uint8)
    normal[_disco((200, 200), (100, 100), 30)] = BIG
    f1, f2 = _fila(casi_vacia, tmp_path), _fila(normal, tmp_path)
    assert f1["quality_flag"] == "mostly_null" and f1["has_bigrock"] and f1["is_mostly_null"]
    assert not f1["is_e2_eligible"] and f1["n_rocks"] >= 1   # se cuenta, pero no es elegible
    assert f2["is_e2_eligible"] and f2["quality_flag"] == "ok"
    r = poblaciones.resumen_e2(pd.DataFrame([f1, f2]))
    assert r["n_escenas"] == 1 and r["n_rocas"] == f2["n_rocks"]


def test_elegibilidad_e2_coincide_con_bandera_ok(tmp_path):
    casos = []
    for relleno in (SOIL, BED):
        m = np.full((100, 100), relleno, np.uint8)
        casos.append(_fila(m, tmp_path))
        m[_disco((100, 100), (50, 50), 15)] = BIG
        casos.append(_fila(m, tmp_path))
    for f in casos:
        assert f["is_e2_eligible"] == (f["quality_flag"] == "ok")


# --- Conteo (E2) ------------------------------------------------------------------------

def test_dos_rocas_unidas_por_un_puente_se_separan():
    b = _disco((200, 200), (100, 55), 30) | _disco((200, 200), (100, 145), 30)
    b[97:104, 55:145] = True                                  # puente de 7 píxeles
    assert rc.compute_stages(b)["n_raw_components"] == 1
    n, n_raw, _, _ = rc.count_rocks(b)
    assert (n, n_raw) == (2, 1)


def test_dos_rocas_separadas_dan_dos_y_una_roca_no_se_fragmenta():
    b = _disco((200, 200), (100, 50), 30) | _disco((200, 200), (100, 150), 30)
    assert rc.count_rocks(b)[:2] == (2, 2)
    assert rc.count_rocks(_disco((200, 200), (100, 100), 40))[0] == 1


def test_area_minima_descarta_de_forma_controlada():
    b = np.zeros((200, 200), bool)
    b[10:30, 10:30] = True                                    # 400 px
    b |= _disco((200, 200), (120, 120), 30)                   # ~2800 px
    assert rc.count_rocks(b, {"min_area_frac": 0.0005})[0] == 2     # umbral 20 px
    assert rc.count_rocks(b, {"min_area_frac": 0.02})[0] == 1       # umbral 800 px
    assert rc.count_rocks(b, {"min_area_frac": 0.1})[0] == 0        # umbral 4000 px


def test_relacion_de_aspecto_descarta_bandas_alargadas():
    b = np.zeros((200, 200), bool)
    b[100:108, 20:180] = True                                 # banda 8 x 160 (aspecto 20)
    assert rc.count_rocks(b, {"max_aspect_ratio": 5.0})[0] == 0
    assert rc.count_rocks(b, {"max_aspect_ratio": 25.0})[0] >= 1


def test_region_sin_semilla_cuenta_como_un_bloque():
    b = np.zeros((200, 200), bool)
    b[10:16, 10:16] = True                                    # 36 px: sin semilla tras suavizar
    b |= _disco((200, 200), (120, 120), 30)
    assert rc.count_rocks(b, {"min_area_frac": 0.0005})[0] == 2     # umbral 20 px
