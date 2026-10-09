"""Poblaciones de análisis: la única definición de qué escenas entran en E1 y en E2.

Todos los guiones, tablas y figuras obtienen sus subconjuntos de aquí, en lugar de repetir
filtros propios. Así no pueden mezclarse poblaciones distintas: el conteo se calcula para
todas las escenas (columna ``n_rocks``), pero solo las elegibles para E2 entran en sus
resúmenes.
"""
from __future__ import annotations

import pandas as pd

BANDAS_CONTEO = [(0, 0, "0"), (1, 1, "1"), (2, 3, "2-3"), (4, 9, "4-9"), (10, 10**9, "10+")]


def poblacion_e1(df: pd.DataFrame) -> pd.DataFrame:
    """Escenas con cobertura definida: al menos un píxel etiquetado."""
    return df[df.is_e1_eligible.astype(bool)]


def poblacion_secuencia(df: pd.DataFrame) -> pd.DataFrame:
    """Escenas con etiqueta útil para describir la secuencia de adquisición.

    Excluye las casi vacías y las vacías (banderas ``mostly_null`` y ``empty``), cuya
    composición no es interpretable, y las ordena por reloj de nave.
    """
    return df[df.is_e1_eligible.astype(bool) & ~df.is_mostly_null.astype(bool)].sort_values("sclk")


def poblacion_e2(df: pd.DataFrame) -> pd.DataFrame:
    """Escenas aptas para el conteo: con roca grande y no casi vacías."""
    return df[df.is_e2_eligible.astype(bool)]


def resumen_e2(df: pd.DataFrame) -> dict:
    """Resumen oficial del conteo, siempre sobre la población de E2."""
    e2 = poblacion_e2(df)
    bandas = {lab: int(((e2.n_rocks >= lo) & (e2.n_rocks <= hi)).sum()) for lo, hi, lab in BANDAS_CONTEO}
    return {"n_escenas": int(len(e2)), "n_rocas": int(e2.n_rocks.sum()), "bandas": bandas,
            "tamanos": {c: int(e2[c].sum()) for c in ("n_small", "n_medium", "n_large")}}
