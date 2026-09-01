"""Sistema de alertas de riesgo de terreno a partir de los indicadores por imagen.

Convierte los indicadores descriptivos (cobertura, conteo, geometría y composición) en
avisos operativos sobre las condiciones que la literatura de exploración planetaria asocia
a riesgo para un vehículo, y en un aviso de interés científico.

Cada regla declara su umbral, el percentil de la distribución observada al que corresponde
y la justificación que la motiva, de modo que el criterio sea discutible y ajustable en
lugar de quedar oculto en el código.

Las alertas se derivan de ``outputs/results.csv``; no requieren reprocesar las máscaras.
"""
from __future__ import annotations

from typing import Any, Callable

import pandas as pd

# --- Umbrales -------------------------------------------------------------------------
# Fijados sobre los percentiles de la distribución observada en el subconjunto de estudio,
# no de forma arbitraria. Se indica el percentil aproximado entre paréntesis.
UMBRAL_BIGROCK_PCT = 5.0        # p70 de las imágenes con roca grande
UMBRAL_SOLIDEZ = 0.85           # p10: por debajo, contornos marcadamente irregulares
UMBRAL_ROCA_MAYOR_PCT = 15.0    # p90 de largest_rock_pct
UMBRAL_N_ROCAS = 5              # p95 del conteo
UMBRAL_ARENA_PCT = 70.0         # arena claramente dominante en la escena
UMBRAL_COBERTURA_ALTA = 80.0    # cobertura de roca muy alta

NIVELES = ["sin_alerta", "bajo", "medio", "alto"]


class Regla:
    """Regla de alerta: condición sobre una fila de resultados, con su justificación."""

    def __init__(self, clave: str, titulo: str, severidad: int,
                 condicion: Callable[[Any], bool], criterio: str, motivo: str):
        self.clave = clave
        self.titulo = titulo
        self.severidad = severidad      # 1 = informativa, 2 = relevante, 3 = crítica
        self.condicion = condicion
        self.criterio = criterio
        self.motivo = motivo


def _num(v, defecto=0.0) -> float:
    """Valor numérico tolerante a ausencias."""
    try:
        return defecto if v is None or v != v else float(v)
    except (TypeError, ValueError):
        return defecto


REGLAS: list[Regla] = [
    Regla(
        "dano_ruedas", "Riesgo de daño en ruedas", 3,
        lambda r: (_num(r.get("pct_bigrock")) > UMBRAL_BIGROCK_PCT
                   and _num(r.get("mean_solidity"), 1.0) < UMBRAL_SOLIDEZ),
        f"roca grande > {UMBRAL_BIGROCK_PCT:.0f} % del área etiquetada y solidez media "
        f"< {UMBRAL_SOLIDEZ}",
        "Combina abundancia de roca grande con contornos irregulares. La solidez baja "
        "indica formas angulosas y salientes, que es la condición asociada al desgaste "
        "prematuro observado en las ruedas del rover Curiosity.",
    ),
    Regla(
        "obstaculo_mayor", "Obstáculo de gran tamaño", 3,
        lambda r: _num(r.get("largest_rock_pct")) > UMBRAL_ROCA_MAYOR_PCT,
        f"la roca mayor ocupa > {UMBRAL_ROCA_MAYOR_PCT:.0f} % del área etiquetada",
        "Un bloque que domina la escena puede superar la altura franqueable del vehículo "
        "y obligar a rodearlo.",
    ),
    Regla(
        "campo_bloques", "Campo denso de bloques", 2,
        lambda r: _num(r.get("n_rocks")) >= UMBRAL_N_ROCAS,
        f"{UMBRAL_N_ROCAS} o más rocas individuales detectadas",
        "Muchos bloques discretos reducen las trayectorias viables aunque ninguno sea "
        "individualmente infranqueable.",
    ),
    Regla(
        "atrapamiento_arena", "Riesgo de atrapamiento en arena", 3,
        lambda r: _num(r.get("pct_sand")) > UMBRAL_ARENA_PCT,
        f"arena > {UMBRAL_ARENA_PCT:.0f} % del área etiquetada",
        "Las superficies dominadas por arena suelta comprometen la tracción. Es el modo "
        "de fallo que dejó inmovilizado al rover Spirit.",
    ),
    Regla(
        "terreno_rocoso", "Terreno mayoritariamente rocoso", 1,
        lambda r: _num(r.get("rock_coverage_pct")) > UMBRAL_COBERTURA_ALTA,
        f"cobertura de roca > {UMBRAL_COBERTURA_ALTA:.0f} % de los píxeles etiquetados",
        "Predominio de roca expuesta. Informativa: suele implicar buena tracción, pero "
        "también superficie irregular.",
    ),
    Regla(
        "escena_no_evaluable", "Escena poco evaluable", 1,
        lambda r: str(r.get("quality_flag")) in {"mostly_null", "empty"},
        "más del 95 % de la escena sin etiquetar",
        "La anotación disponible no basta para sostener una valoración; se señala para "
        "que no se interprete la ausencia de alertas como ausencia de riesgo.",
    ),
]

REGLAS_POR_CLAVE = {r.clave: r for r in REGLAS}


def evaluar_fila(fila: dict[str, Any]) -> dict[str, Any]:
    """Evalúa las reglas sobre una fila de resultados.

    Returns
    -------
    dict con ``alertas`` (lista de claves), ``n_alertas``, ``severidad_max`` y
    ``nivel_riesgo`` (sin_alerta / bajo / medio / alto).
    """
    activas = [r.clave for r in REGLAS if r.condicion(fila)]
    severidades = [REGLAS_POR_CLAVE[c].severidad for c in activas]
    # Solo las reglas de severidad 2 o 3 elevan el nivel de riesgo; las informativas no.
    relevantes = [s for s in severidades if s >= 2]
    if not relevantes:
        nivel = "sin_alerta"
    elif max(relevantes) == 3 and len(relevantes) >= 2:
        nivel = "alto"
    elif max(relevantes) == 3:
        nivel = "medio"
    else:
        nivel = "bajo"
    return {
        "alertas": "|".join(activas),
        "n_alertas": len(activas),
        "severidad_max": max(severidades) if severidades else 0,
        "nivel_riesgo": nivel,
    }


def evaluar(df: pd.DataFrame) -> pd.DataFrame:
    """Añade las columnas de alerta a una tabla de resultados."""
    ev = pd.DataFrame([evaluar_fila(r) for r in df.to_dict("records")], index=df.index)
    return pd.concat([df, ev], axis=1)


def catalogo() -> pd.DataFrame:
    """Tabla con la definición de cada regla, para documentar el sistema."""
    return pd.DataFrame([
        {"clave": r.clave, "titulo": r.titulo, "severidad": r.severidad,
         "criterio": r.criterio, "motivo": r.motivo}
        for r in REGLAS
    ])
