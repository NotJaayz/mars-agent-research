"""Reglas heurísticas de priorización de escenas para revisión.

NO es un sistema de evaluación de riesgo ni de transitabilidad: las reglas no están
calibradas contra incidentes reales ni contra escala métrica, de modo que no permiten
inferir altura física, transitabilidad, daño de ruedas ni probabilidad de atrapamiento.
Ordenan escenas para revisión con un criterio explícito y discutible.

Cada regla declara su umbral, la POBLACIÓN sobre la que se evalúa (E1 o E2, según
:mod:`src.poblaciones`) y la condición del terreno que la inspira. El percentil que cada
umbral representa no se escribe a mano: lo calcula :func:`percentiles_umbral` sobre la
población declarada, y ``scripts/run_priorizacion.py`` lo guarda en el catálogo.

Las reglas se derivan de ``outputs/results.csv``; no requieren reprocesar las máscaras.
"""
from __future__ import annotations

from typing import Any, Callable

import pandas as pd

# --- Umbrales -------------------------------------------------------------------------
UMBRAL_BIGROCK_PCT = 5.0        # roca grande sobre lo etiquetado (%)
UMBRAL_SOLIDEZ = 0.85           # solidez media de las rocas contadas
UMBRAL_ROCA_MAYOR_PCT = 15.0    # área de la roca mayor sobre lo etiquetado (%)
UMBRAL_N_ROCAS = 5              # rocas contadas
UMBRAL_ARENA_PCT = 70.0         # arena sobre lo etiquetado (%)
UMBRAL_COBERTURA_ALTA = 80.0    # cobertura de roca (%)

NIVELES = ["sin_prioridad", "baja", "media", "alta"]


class Regla:
    """Regla de priorización: condición sobre una fila de resultados, con su justificación."""

    def __init__(self, clave: str, titulo: str, peso: int, poblacion: str,
                 condicion: Callable[[Any], bool], criterio: str, motivo: str):
        self.clave = clave
        self.titulo = titulo
        self.peso = peso                # 1 = informativa; 2 y 3 elevan la prioridad
        self.poblacion = poblacion      # "E1", "E2" o "todas"
        self.condicion = condicion
        self.criterio = criterio
        self.motivo = motivo

    def aplica(self, fila: dict[str, Any]) -> bool:
        if self.poblacion == "E1" and not bool(fila.get("is_e1_eligible")):
            return False
        if self.poblacion == "E2" and not bool(fila.get("is_e2_eligible")):
            return False
        return bool(self.condicion(fila))


def _num(v, defecto=0.0) -> float:
    """Valor numérico tolerante a ausencias."""
    try:
        return defecto if v is None or v != v else float(v)
    except (TypeError, ValueError):
        return defecto


REGLAS: list[Regla] = [
    Regla(
        "bloques_angulosos", "Bloques angulosos abundantes", 3, "E2",
        lambda r: (_num(r.get("pct_bigrock")) > UMBRAL_BIGROCK_PCT
                   and _num(r.get("mean_solidity"), 1.0) < UMBRAL_SOLIDEZ),
        f"roca grande > {UMBRAL_BIGROCK_PCT:.0f} % del área etiquetada y solidez media "
        f"< {UMBRAL_SOLIDEZ}",
        "Inspirada en el desgaste de las ruedas de Curiosity sobre roca angulosa. Combina "
        "abundancia de roca grande con contornos irregulares; no mide angulosidad física.",
    ),
    Regla(
        "bloque_dominante", "Bloque dominante en la escena", 3, "E2",
        lambda r: _num(r.get("largest_rock_pct")) > UMBRAL_ROCA_MAYOR_PCT,
        f"la roca mayor ocupa > {UMBRAL_ROCA_MAYOR_PCT:.0f} % del área etiquetada",
        "Un bloque que ocupa buena parte de la escena podría requerir revisión de la ruta; "
        "sin escala métrica no se conoce su altura.",
    ),
    Regla(
        "campo_bloques", "Campo denso de bloques", 2, "E2",
        lambda r: _num(r.get("n_rocks")) >= UMBRAL_N_ROCAS,
        f"{UMBRAL_N_ROCAS} o más rocas individuales contadas",
        "Muchos bloques discretos en la escena.",
    ),
    Regla(
        "arena_predominante", "Arena predominante", 3, "E1",
        lambda r: _num(r.get("pct_sand")) > UMBRAL_ARENA_PCT,
        f"arena > {UMBRAL_ARENA_PCT:.0f} % del área etiquetada",
        "Inspirada en el modo de fallo que inmovilizó a Spirit en arena suelta; no mide "
        "propiedades mecánicas del suelo.",
    ),
    Regla(
        "terreno_rocoso", "Terreno mayoritariamente rocoso", 1, "E1",
        lambda r: _num(r.get("rock_coverage_pct")) > UMBRAL_COBERTURA_ALTA,
        f"cobertura de roca > {UMBRAL_COBERTURA_ALTA:.0f} % de los píxeles etiquetados",
        "Informativa: predominio de roca expuesta. No es un umbral extremo en este corpus.",
    ),
    Regla(
        "escena_no_evaluable", "Escena poco evaluable", 1, "todas",
        lambda r: bool(r.get("is_mostly_null")),
        "más del 95 % de la escena sin etiquetar",
        "La anotación disponible no basta para valorar la escena; se señala para que no se "
        "interprete la ausencia de otras reglas como ausencia de condiciones relevantes.",
    ),
]

REGLAS_POR_CLAVE = {r.clave: r for r in REGLAS}

# Variable y población de cada umbral, para calcular el percentil que representa.
VARIABLES_UMBRAL = [
    ("bloques_angulosos", "pct_bigrock", UMBRAL_BIGROCK_PCT, "E2"),
    ("bloques_angulosos", "mean_solidity", UMBRAL_SOLIDEZ, "E2"),
    ("bloque_dominante", "largest_rock_pct", UMBRAL_ROCA_MAYOR_PCT, "E2"),
    ("campo_bloques", "n_rocks", UMBRAL_N_ROCAS, "E2"),
    ("arena_predominante", "pct_sand", UMBRAL_ARENA_PCT, "E1"),
    ("terreno_rocoso", "rock_coverage_pct", UMBRAL_COBERTURA_ALTA, "E1"),
]


def evaluar_fila(fila: dict[str, Any]) -> dict[str, Any]:
    """Evalúa las reglas sobre una fila de resultados.

    Returns
    -------
    dict con ``reglas_activadas`` (claves separadas por «|»), ``n_reglas``, ``peso_max`` y
    ``nivel_prioridad`` (sin_prioridad / baja / media / alta).
    """
    activas = [r.clave for r in REGLAS if r.aplica(fila)]
    pesos = [REGLAS_POR_CLAVE[c].peso for c in activas]
    relevantes = [p for p in pesos if p >= 2]   # las informativas no elevan la prioridad
    if not relevantes:
        nivel = "sin_prioridad"
    elif max(relevantes) == 3 and len(relevantes) >= 2:
        nivel = "alta"
    elif max(relevantes) == 3:
        nivel = "media"
    else:
        nivel = "baja"
    return {"reglas_activadas": "|".join(activas), "n_reglas": len(activas),
            "peso_max": max(pesos) if pesos else 0, "nivel_prioridad": nivel}


def evaluar(df: pd.DataFrame) -> pd.DataFrame:
    """Añade las columnas de priorización a una tabla de resultados."""
    ev = pd.DataFrame([evaluar_fila(r) for r in df.to_dict("records")], index=df.index)
    return pd.concat([df, ev], axis=1)


def percentiles_umbral(df: pd.DataFrame) -> pd.DataFrame:
    """Percentil que cada umbral representa en su población declarada.

    El percentil es el porcentaje de escenas de esa población con valor igual o inferior al
    umbral (para la solidez, la regla se activa por debajo, de modo que el percentil indica la
    fracción que queda por debajo).
    """
    from . import poblaciones
    filas = []
    for clave, var, umbral, pob in VARIABLES_UMBRAL:
        base = poblaciones.poblacion_e2(df) if pob == "E2" else poblaciones.poblacion_e1(df)
        x = base[var].dropna()
        filas.append({"clave": clave, "variable": var, "umbral": umbral, "poblacion": pob,
                      "n": int(len(x)), "percentil": float(100 * (x <= umbral).mean()),
                      "pct_supera": float(100 * (x > umbral).mean())})
    return pd.DataFrame(filas)


def catalogo() -> pd.DataFrame:
    """Tabla con la definición de cada regla, para documentar el sistema."""
    return pd.DataFrame([
        {"clave": r.clave, "titulo": r.titulo, "peso": r.peso, "poblacion": r.poblacion,
         "criterio": r.criterio, "motivo": r.motivo}
        for r in REGLAS
    ])
