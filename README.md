# Conteo de rocas en imágenes marcianas (AI4Mars)

**Autor:** Juan Pablo Delgado Castro
**Universidad:** Externado de Colombia — Departamento de Matemáticas, Ciencia de Datos

Cuantificación, **por imagen**, de dos indicadores derivados de las máscaras de
segmentación del dataset **AI4Mars**, sin entrenar modelos de aprendizaje profundo:

1. **Cobertura de roca visible** — porcentaje de píxeles etiquetados como
   `bedrock` (lecho rocoso) o `big rock` (roca grande).
2. **Conteo aproximado de rocas individuales** — número de bloques separados en
   zonas de `big rock`, estimado con componentes conectadas + transformada de
   distancia + *watershed*.

El producto final es un CSV con un indicador por imagen más figuras ilustrativas
del pipeline.

---

## Objetivos

- **E1.** Estimar la cobertura de roca visible por imagen.
- **E2.** Estimar el número aproximado de rocas individuales separando bloques
  pegados (componentes conectadas, transformada de distancia, *watershed*).
- **E3.** Explorar de forma descriptiva cómo varían los indicadores entre
  subconjuntos (cámara, misión, rango de soles).
- **E4.** Entregar un pipeline reproducible (código, parámetros, versiones, CSV).
- **E5.** Analizar e interpretar resultados, casos atípicos y limitaciones.

---

## Estructura del repositorio

```
.
├── CLAUDE.md              # Guía del proyecto para Claude Code
├── environment.yml        # Dependencias conda
├── README.md              # Este archivo
├── notebooks/
│   ├── 01_exploracion.ipynb
│   ├── 02_cobertura.ipynb
│   ├── 03_conteo.ipynb
│   └── 04_analisis.ipynb
├── src/
│   ├── mask_utils.py      # Lectura y construcción de máscaras binarias
│   ├── coverage.py        # Cálculo de cobertura por imagen
│   ├── rock_count.py      # Componentes conectadas + watershed + filtros
│   └── pipeline.py        # process_image(...) que orquesta todo
├── data/                  # NO se versiona (ver .gitignore)
│   ├── images/            # imágenes originales .jpg/.png
│   ├── masks/             # máscaras AI4Mars .png
│   └── metadata.csv       # id, rover, cámara, sol
└── outputs/
    ├── results.csv        # indicadores por imagen
    └── figures/           # figuras del pipeline
```

---

## Dataset: AI4Mars

- **Fuente:** https://data.nasa.gov/d/cykx-2qix
- **Versión Zenodo:** https://doi.org/10.5281/zenodo.15995036
- **Rovers:** Spirit, Opportunity, Curiosity · **Cámaras:** Navcam, Hazcam
- **Máscara:** PNG con un entero por píxel:

  | valor | clase        |
  |:-----:|--------------|
  | 0     | sin etiqueta |
  | 1     | soil (suelo) |
  | 2     | bedrock      |
  | 3     | sand (arena) |
  | 4     | big rock     |

> Los códigos exactos se confirman contra la versión descargada del dataset.

Estructura esperada en disco:

```
data/
  images/        # mismo nombre base que la máscara
  masks/
  metadata.csv
```

---

## Instalación

Requiere [Miniforge](https://github.com/conda-forge/miniforge) (recomendado en
Apple Silicon).

```bash
# 1. Crear y activar el entorno
conda env create -f environment.yml
conda activate tesis-marte

# 2. (Reproducibilidad) registrar versiones exactas
conda env export --no-builds > environment.lock.yml

# 3. Registrar el kernel para Jupyter
python -m ipykernel install --user --name tesis-marte
```

---

## Pipeline (resumen)

Para cada par (imagen, máscara):

1. Leer máscara → array 2D de enteros.
2. Máscara de cobertura → píxeles ∈ {2, 4}.
3. Máscara de roca grande → píxeles == 4.
4. Limpieza morfológica (apertura 3×3, cierre 3×3).
5. Cobertura = `píxeles_roca / píxeles_válidos × 100`.
6. Componentes conectadas sobre roca grande + filtros (área, relación de aspecto).
7. Transformada de distancia por componente.
8. *Watershed* guiado por máximos locales → separar rocas pegadas.
9. Filtrar subcomponentes (área, forma).
10. Contar rocas válidas.
11. Guardar fila en CSV.

Procesar una sola imagen de prueba:

```python
from src.pipeline import process_image, DEFAULT_PARAMS

fila = process_image("data/images/EJEMPLO.jpg",
                     "data/masks/EJEMPLO.png",
                     params=DEFAULT_PARAMS)
```

---

## Outputs

`outputs/results.csv` con columnas:

`image_id`, `rover`, `camera`, `sol`, `rock_coverage_pct`, `n_rocks`,
`n_raw_components`, `quality_flag`.

Más histogramas de cobertura/conteo por rover-cámara y figuras *step-by-step*
del pipeline.

---

## Alcance

Este proyecto **no** entrena redes neuronales, **no** genera máscaras nuevas
(usa las de AI4Mars), **no** modela evolución temporal ni hace análisis 3D.
