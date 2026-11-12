#!/usr/bin/env python
"""Genera la aplicación web de consulta (``outputs/app_ai4mars.html``).

Es un único archivo HTML que se abre con doble clic: no requiere servidor, conexión ni
instalación. Incrusta los indicadores de las escenas, el catálogo de reglas, los parámetros
del procedimiento y las cifras de validación, y recalcula en el navegador la priorización y
los estadísticos, de modo que el usuario puede ajustar los umbrales y ver el efecto al
instante. Las reglas replican exactamente las de :mod:`src.priorizacion`; la propia aplicación
verifica que, con los umbrales por defecto, sus conteos coinciden con
``outputs/priorizacion_resumen.json``.

Solo emplea la biblioteca estándar: los umbrales y los parámetros se leen del código fuente
con :mod:`ast`, sin importar los módulos de cálculo.

Las imágenes del explorador no se incrustan: las escribe ``scripts/make_app_escenas.py`` en
``outputs/app_escenas/``, junto al archivo, y la aplicación las carga por ruta relativa.

Uso:  python scripts/make_app.py
"""
from __future__ import annotations

import ast
import base64
import csv
import json
import re
import subprocess
from datetime import date
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
PLANTILLA = RAIZ / "scripts" / "app_template.html"
SALIDA = RAIZ / "outputs" / "app_ai4mars.html"
ESCENAS = RAIZ / "outputs" / "app_escenas"
SOL = 88775.244  # segundos de reloj de nave por sol marciano

# Columnas de results.csv que viajan a la aplicación, con su nombre corto y sus decimales
# (None = entero o booleano).
NUMERICAS = {
    "sclk": ("sclk", 0), "rock_coverage_pct": ("cov", 4), "coverage_total_pct": ("covt", 4),
    "frac_valid": ("fv", 4), "pct_soil": ("soil", 2), "pct_bedrock": ("bed", 2),
    "pct_sand": ("sand", 2), "pct_bigrock": ("big", 2), "n_bigrock": ("nbig", 0),
    "n_rocks": ("nr", 0), "n_raw_components": ("nraw", 0), "largest_rock_pct": ("lrg", 2),
    "mean_rock_area_px": ("mra", 1), "n_small": ("ns", 0), "n_medium": ("nm", 0),
    "n_large": ("nl", 0), "mean_solidity": ("sol", 3), "n_valid_pixels": ("nvp", 0),
}
BOOLEANAS = {"has_bigrock": "hb", "is_mostly_null": "mn", "is_e1_eligible": "e1",
             "is_e2_eligible": "e2"}
CATEGORICAS = {"scene_type": "st", "quality_flag": "qf", "eye": "eye",
               "dominant_class": "dom"}

# Cifras del documento que muestra la aplicación (tesis/cifras.tex es la única fuente).
CIFRAS = ["cNEscenas", "cPctCobCalc", "cPctCobPos", "cCobMedVal", "cNRocas", "cNGold",
          "cGoldCobMedPos", "cDescImgPct", "cDescAnotPct", "cDescAnot", "cDescImg",
          "cDescTotal", "cVN", "cVAcuerdo", "cVKappaPond", "cVKappa", "cVAbajo", "cVArriba",
          "cVRegUnaAbajo", "cSegMIoU", "cSegMinTotal", "cBAExpMedia", "cSamAcuerdo",
          "cPruebasN", "cEtaConteo", "cFracValidMed", "cPctBigAny"]


def _num(texto: str, decimales: int | None):
    if texto in ("", "nan", "NaN", "None"):
        return None
    v = float(texto)
    if decimales is None or decimales == 0:
        return int(round(v))
    return round(v, decimales)


def leer_resultados() -> tuple[dict, dict]:
    """Lee results.csv en formato columnar para que el archivo final sea compacto."""
    with (RAIZ / "outputs" / "results.csv").open(newline="", encoding="utf-8") as fh:
        filas = list(csv.DictReader(fh))
    cols: dict[str, list] = {"id": [f["image_id"] for f in filas]}
    for col, (corto, dec) in NUMERICAS.items():
        cols[corto] = [_num(f[col], dec) for f in filas]
    for col, corto in BOOLEANAS.items():
        cols[corto] = [1 if f[col] == "True" else 0 for f in filas]
    cats: dict[str, list[str]] = {}
    for col, corto in CATEGORICAS.items():
        valores = sorted({f[col] for f in filas})
        cats[corto] = valores
        indice = {v: i for i, v in enumerate(valores)}
        cols[corto] = [indice[f[col]] for f in filas]
    # Sol de adquisición contado desde la primera escena del conjunto, con la misma
    # conversión del reloj de nave que scripts/sensibilidad_dependencia_temporal.py.
    soles = [None if s is None else int(s // SOL) for s in cols["sclk"]]
    s0 = min(s for s in soles if s is not None)
    cols["dia"] = [None if s is None else s - s0 for s in soles]
    return cols, cats


def leer_constantes(ruta: Path, prefijo: str) -> dict[str, float]:
    """Constantes de módulo (``UMBRAL_* = 5.0``) leídas con ast, sin importar el módulo."""
    arbol = ast.parse(ruta.read_text(encoding="utf-8"))
    out = {}
    for nodo in arbol.body:
        if isinstance(nodo, ast.Assign) and isinstance(nodo.targets[0], ast.Name):
            nombre = nodo.targets[0].id
            if nombre.startswith(prefijo):
                out[nombre] = ast.literal_eval(nodo.value)
    return out


def leer_parametros() -> list[dict]:
    """DEFAULT_PARAMS de src/rock_count.py con el comentario que documenta cada parámetro."""
    texto = (RAIZ / "src" / "rock_count.py").read_text(encoding="utf-8")
    bloque = re.search(r"DEFAULT_PARAMS[^=]*=\s*\{(.*?)\n\}", texto, re.S).group(1)
    params = []
    for linea in bloque.splitlines():
        m = re.match(r'\s*"(\w+)":\s*([^,]+),\s*#\s*(.*)', linea)
        if m:
            params.append({"clave": m.group(1), "valor": ast.literal_eval(m.group(2)),
                           "desc": m.group(3).strip()})
    return params


def leer_cifras() -> dict[str, str]:
    """Macros de tesis/cifras.tex convertidas a texto legible (coma decimal)."""
    texto = (RAIZ / "tesis" / "cifras.tex").read_text(encoding="utf-8")
    out = {}
    for nombre in CIFRAS:
        m = re.search(r"\\newcommand\{\\" + nombre + r"\}\{(.*)\}\s*$", texto, re.M)
        if not m:
            continue
        v = m.group(1)
        v = re.sub(r"\\ensuremath\{\+\}", "+", v)
        v = re.sub(r"\\SI\{([^}]*)\}\{\\percent\}", r"\1 %", v)
        v = re.sub(r"\\num\{([^}]*)\}", r"\1", v)
        v = re.sub(r"(\d)\.(\d)", r"\1,\2", v)
        out[nombre] = v.strip()
    return out


def leer_catalogo() -> list[dict]:
    with (RAIZ / "outputs" / "priorizacion_catalogo.csv").open(newline="", encoding="utf-8") as fh:
        reglas = list(csv.DictReader(fh))
    for r in reglas:
        r["peso"] = int(r["peso"])
    return reglas


def imagen(ruta: Path) -> str:
    if not ruta.exists():
        return ""
    return "data:image/png;base64," + base64.b64encode(ruta.read_bytes()).decode("ascii")


def commit() -> str:
    try:
        return subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=RAIZ,
                              capture_output=True, text=True, check=True).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return "sin git"


def main() -> None:
    cols, cats = leer_resultados()
    leer_json = lambda n: json.loads((RAIZ / "outputs" / n).read_text(encoding="utf-8"))
    resumen = leer_json("priorizacion_resumen.json")
    umbrales = leer_constantes(RAIZ / "src" / "priorizacion.py", "UMBRAL_")
    datos = {
        "meta": {"generado": date.today().isoformat(), "commit": commit(),
                 "n": len(cols["id"]),
                 "sha256": leer_json("segmentacion_metricas.json").get("sha256_modelo", ""),
                 "repo": "https://github.com/NotJaayz/mars-agent-research"},
        "cols": cols, "cats": cats,
        "reglas": leer_catalogo(),
        "umbrales": umbrales,
        "ref": {"por_nivel": resumen["por_nivel"], "por_regla": resumen["por_regla"]},
        "geo": leer_json("geologia_m2020_resumen.json"),
        # Capas del explorador (scripts/make_app_escenas.py); rutas relativas a este archivo.
        "escenas": json.loads((ESCENAS / "indice.json").read_text(encoding="utf-8")) if (ESCENAS / "indice.json").exists() else {},
        "rutaEscenas": ESCENAS.name + "/",
        "cifras": leer_cifras(),
        "params": leer_parametros(),
        "img": {"nasa": imagen(RAIZ / "assets" / "logo_nasa.png"),
                "externado": imagen(RAIZ / "assets" / "logo_externado_app.png"),
                "pipeline": imagen(RAIZ / "tesis" / "images" / "Figura_11_procedimiento_paso_a_paso.png")},
    }
    carga = json.dumps(datos, ensure_ascii=False, separators=(",", ":"))
    # "</" dentro de un <script> cerraría la etiqueta antes de tiempo.
    carga = carga.replace("</", "<\\/")
    html = PLANTILLA.read_text(encoding="utf-8").replace("/*__DATOS__*/null", carga)
    SALIDA.write_text(html, encoding="utf-8")
    print(f"Escrito {SALIDA.relative_to(RAIZ)} ({SALIDA.stat().st_size / 1e6:.1f} MB, "
          f"{datos['meta']['n']} escenas)")


if __name__ == "__main__":
    main()
