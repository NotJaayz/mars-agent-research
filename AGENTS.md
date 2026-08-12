# Tesis: Conteo de rocas en imágenes marcianas (AI4Mars)
**Autor:** Juan Pablo Delgado Castro  
**Universidad:** Externado de Colombia — Departamento de Matemáticas, Ciencia de Datos  
**Objetivo:** Cuantificar cobertura de roca visible y contar rocas individuales por imagen usando las máscaras del dataset AI4Mars.

---

## Contexto del proyecto

Este proyecto NO entrena modelos de deep learning. En su lugar, aprovecha las máscaras de segmentación por píxel ya existentes en AI4Mars para derivar dos indicadores por imagen:

1. **Cobertura de roca visible** — porcentaje de píxeles etiquetados como `bedrock` o `big rock`
2. **Conteo aproximado de rocas individuales** — número de bloques separados en zonas de `big rock`, usando componentes conectadas + transformada de distancia + watershed

El resultado final es un CSV con un indicador por imagen, más figuras ilustrativas del pipeline.

---

## Dataset: AI4Mars

- **Fuente:** https://data.nasa.gov/d/cykx-2qix (versión Zenodo: https://doi.org/10.5281/zenodo.15995036)
- **Rovers:** Spirit, Opportunity, Curiosity
- **Cámaras:** Navcam y Hazcam principalmente
- **Formato de máscara:** imagen PNG en escala de grises (modo L), un entero por píxel.
  Codificación **NAV** (verificada contra `label_keys.json` + `info.md` del dataset real v0.6 y comprobada píxel a píxel):
  - `0` = soil (suelo)
  - `1` = bedrock (lecho rocoso)
  - `2` = sand (arena)
  - `3` = big rock (roca grande)
  - `255` = NULL / sin etiqueta
  > ⚠️ Esto CORRIGE la codificación asumida en versiones previas de la propuesta
  > (que decían 0=fondo … 4=big rock). En el dataset real: el "sin etiqueta" es **255**
  > (no 0), soil es **0** (no 1), bedrock es **1**, sand es **2**, big rock es **3**.
  > Existe además una taxonomía geológica distinta `M2020_GEO` (pebbles, float rock, subtipos
  > de bedrock…) que NO es la escala NAV y queda fuera de alcance.

- **Ubicación real en disco:** el dataset (v0.6, ~16 GB) NO se copia al repo. Vive fuera, p.ej.
  `~/Desktop/ai4mars-dataset-merged-0.6/`, y el código lo referencia por una ruta configurable
  (variable de entorno `AI4MARS_ROOT` o config en `src/`). Estructura del dataset:
```
<AI4MARS_ROOT>/
  msl/ncam/images/edr/*.JPG      # Curiosity NavCam (grises) — IMÁGENES (subconjunto del proyecto)
  msl/ncam/labels/train/*.png    # máscaras crowdsourced (acuerdo 2/3 de ≥3 anotadores)
  msl/ncam/labels/test/masked-gold-min{1,2,3}-100agree/*.png   # máscaras de expertos (validación)
  msl/mcam/...                   # MastCam (color) — fuera de alcance principal
  mer/...                        # Spirit/Opportunity — fuera de alcance
  m2020/...                      # Perseverance (NAV + GEO) — fuera de alcance
  label_keys.json, info.md, changelog.md
```
  Emparejamiento imagen↔máscara: **mismo nombre base**; la imagen es `.JPG` y la máscara `.png`
  (a veces con sufijo `_merged`). No todas las imágenes tienen máscara (18 127 imágenes vs 16 064 labels).

---

## Stack tecnológico

- **Python 3.11+** con entorno conda (Miniforge recomendado en Apple Silicon)
- **Aceleración:** PyTorch con backend MPS (Apple M4 Pro) — solo si se necesita; el pipeline principal es CPU con NumPy/scikit-image
- **Librerías principales:**
  - `numpy` — operaciones sobre arrays
  - `opencv-python` (cv2) — lectura de imágenes, operaciones morfológicas
  - `scikit-image` — componentes conectadas (`label`), transformada de distancia (`distance_transform_edt`), watershed (`watershed`), propiedades de regiones (`regionprops`)
  - `pandas` — construcción del CSV de resultados
  - `matplotlib` — visualizaciones y figuras del pipeline
  - `tqdm` — progreso al procesar miles de imágenes
- **Entorno:** Jupyter Notebooks + scripts `.py` modulares
- **Control de versiones:** Git + GitHub (repositorio privado)

---

## Estructura del repositorio

```
/
├── AGENTS.md                  # este archivo
├── environment.yml            # dependencias conda
├── notebooks/
│   ├── 01_exploracion.ipynb   # visualización inicial de imágenes y máscaras
│   ├── 02_cobertura.ipynb     # cálculo de cobertura de roca visible
│   ├── 03_conteo.ipynb        # pipeline de conteo con watershed
│   └── 04_analisis.ipynb      # estadísticas descriptivas y figuras finales
├── src/
│   ├── mask_utils.py          # lectura y construcción de máscaras binarias
│   ├── coverage.py            # cálculo de cobertura por imagen
│   ├── rock_count.py          # componentes conectadas + watershed + filtros
│   └── pipeline.py            # función principal que procesa una imagen completa
├── data/                      # NO incluir en git (agregar a .gitignore)
│   ├── images/
│   ├── masks/
│   └── metadata.csv
├── outputs/
│   ├── results.csv            # indicadores por imagen (cobertura + conteo)
│   └── figures/               # figuras ilustrativas del pipeline
└── README.md
```

---

## Pipeline principal (flujo de procesamiento)

Para cada par (imagen, máscara):

1. **Leer máscara** → array 2D de enteros (codificación NAV)
2. **Construir máscara de cobertura** → píxeles donde valor ∈ {1, 3} (bedrock + big rock)
3. **Construir máscara de rocas grandes** → píxeles donde valor == 3
4. **Limpiar con morfología** → apertura (3×3) para eliminar ruido, cierre (3×3) para rellenar huecos
5. **Calcular cobertura** → `sum(mask_cov) / sum(mask_valida) * 100`, donde `mask_valida = (valor != 255)`
6. **Componentes conectadas** sobre máscara de big rock → filtrar por área mínima (0.05% de imagen) y relación de aspecto (< 5)
7. **Transformada de distancia** sobre cada componente grande → `distance_transform_edt`
8. **Watershed** guiado por máximos locales de la distancia → separar rocas pegadas
9. **Filtrar subcomponentes** → área mínima y forma
10. **Contar rocas** → número de subcomponentes válidas
11. **Guardar fila en CSV** → id, rover, cámara, sol, cobertura_pct, n_rocas, n_componentes_raw, flags

---

## Convenciones de código

- Funciones puras: cada función recibe arrays numpy y devuelve arrays o números — sin efectos secundarios
- Parámetros explícitos: todos los umbrales (área mínima, tamaño kernel morfológico, min_distance del watershed) se pasan como argumentos con defaults documentados, NO hardcodeados dentro de las funciones
- Reproducibilidad: fijar semilla aleatoria donde aplique; registrar versiones de librerías en `environment.yml`
- Figuras del pipeline: para cada etapa guardar una figura de ejemplo con: imagen original | máscara AI4Mars | máscara binaria limpia | componentes conectadas | resultado watershed

---

## Criterios de inclusión de imágenes

Una imagen se incluye en el análisis si:
- Tiene máscara AI4Mars disponible (no todas las imágenes la tienen)
- Tiene más del 1% de píxeles válidos etiquetados como roca (bedrock o big rock)
- **Subconjunto de la tesis: MSL NavCam (Curiosity), etiquetas `train`.** (Decisión de alcance
  fiel a la propuesta; MER/M2020/MastCam quedan fuera.)

> **Hallazgo a documentar (limitación de E2):** `big rock` (clase 3) es una etiqueta RARA.
> En una muestra aleatoria de 400 máscaras de MSL NavCam train, solo ~14% contienen alguna
> `big rock` (mediana ~1.3% del área etiquetada), mientras que `bedrock` aparece en ~65%.
> Por tanto la **cobertura (E1)** tiene datos abundantes, pero el **conteo de rocas (E2)**
> aplica a un subconjunto reducido de imágenes; esto debe reportarse explícitamente y motiva
> usar la cobertura como indicador principal y el conteo como análisis sobre imágenes con roca.

---

## Outputs esperados

- `outputs/results.csv` — una fila por imagen. Esquema enriquecido (24 columnas):
  - **Identificación:** `image_id`, `rover`, `camera`, `eye` (L/R del par estéreo NavCam), `sol`
  - **Cobertura (E1):** `rock_coverage_pct` (roca/válidos), `coverage_total_pct` (roca/total, cota inferior), `frac_valid` (fracción de escena etiquetada)
  - **Composición del terreno:** `pct_soil`, `pct_bedrock`, `pct_sand`, `pct_bigrock` (sobre válidos), `dominant_class`, `scene_type` (suelo/arenoso/rocoso/mixto)
  - **Conteo y geometría de rocas (E2):** `n_bigrock`, `n_rocks`, `n_raw_components`, `largest_rock_pct`, `mean_rock_area_px`, `n_small`/`n_medium`/`n_large` (clases de tamaño), `mean_solidity` (forma; baja ⇒ posible sobresegmentación)
  - **Calidad:** `quality_flag` (ok / no_bigrock / no_rock / mostly_null / empty)
- Histogramas de distribución de cobertura y conteo por rover/cámara
- Figuras step-by-step del pipeline para al menos 5 imágenes representativas
- Casos extremos documentados: imágenes con cobertura > 50%, imágenes con 0 rocas, casos de sobresegmentación

---

## Lo que este proyecto NO hace

- No entrena redes neuronales
- No genera máscaras nuevas (usa las de AI4Mars directamente)
- No modela evolución temporal del terreno
- No hace análisis 3D ni usa datos de elevación

---

## Preguntas frecuentes para Codex

**"¿Cómo proceso una sola imagen de prueba?"**  
→ Usar `src/pipeline.py` con la función `process_image(image_path, mask_path, params=DEFAULT_PARAMS)`

**"¿Qué hago si el watershed sobreSegmenta?"**  
→ Aumentar `min_distance` en la detección de máximos locales, o aplicar suavizado gaussiano a la transformada de distancia antes de buscar picos

**"¿Cómo sé si un parámetro está bien calibrado?"**  
→ Comparar visualmente el resultado del watershed con la imagen original en al menos 10 imágenes de distinto tipo de terreno
