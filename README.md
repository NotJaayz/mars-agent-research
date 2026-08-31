# Conteo de rocas visibles en imágenes marcianas (AI4Mars)

**🌐 Idioma:** **Español** · [English](README.en.md)

Investigación de tesis que cuantifica, **imagen por imagen**, cuánta roca hay en la
superficie de Marte y cuántos bloques individuales se distinguen, a partir de las
máscaras de segmentación del dataset **AI4Mars** (NASA/JPL) y del rover *Curiosity*.

> **Autor:** Juan Pablo Delgado Castro · Matemáticas — Ciencia de Datos,
> Universidad Externado de Colombia
> **Estado:** pipeline completo y ejecutado sobre 16 064 imágenes · redacción en curso

---

## Qué hace este proyecto

En lugar de entrenar un modelo para segmentar terreno (el uso habitual de AI4Mars),
este trabajo **lee las máscaras existentes como mapas cuantitativos** y deriva dos
indicadores por imagen:

1. **Cobertura de roca visible** — porcentaje de píxeles etiquetados como lecho rocoso
   (*bedrock*) o roca grande (*big rock*).
2. **Conteo aproximado de rocas individuales** — bloques separados dentro de las zonas
   de roca grande, mediante componentes conectadas → transformada de distancia →
   *watershed* → filtros de tamaño y forma.

El resultado es una tabla con **24 indicadores por imagen**, figuras del procedimiento
y un análisis descriptivo del recorrido del rover.

---

## Resultados principales

Sobre **16 064 imágenes** de MSL NavCam (Curiosity) con máscara disponible:

| Indicador | Resultado |
|---|---|
| Imágenes con roca visible | **10 817 (67 %)** |
| Imágenes con roca grande (aptas para conteo) | 2 193 (14 %) |
| Rocas individuales contadas | **5 375** (mediana 2 por imagen, máx. 23) |
| Cobertura mediana (sobre píxeles etiquetados) | 96,8 % |
| Cobertura mediana (sobre la imagen completa) | 42,0 % |

**Tipología de escena** — rocoso 47 % · suelo 36 % · arenoso 11 % · mixto 5 %

**Distribución tamaño–frecuencia de rocas** — pequeñas 49 % · medianas 32 % · grandes 20 %
(distribución decreciente, coherente con la literatura de abundancia de rocas).

---

## Hallazgos metodológicos

**1. La codificación de clases suele documentarse mal.** Verificada contra
`label_keys.json`, la documentación oficial del dataset y una comprobación píxel a
píxel, la escala **NAV** real es:

| Valor | Clase |
|:---:|---|
| `0` | soil (suelo) |
| `1` | bedrock (lecho rocoso) |
| `2` | sand (arena) |
| `3` | **big rock** (roca grande) |
| `255` | **NULL** (sin etiqueta) |

Es decir: el "sin etiqueta" es **255** (no 0) y la roca grande es **3** (no 4). Esto
corrige el supuesto inicial de la propuesta de tesis.

**2. `big rock` es una clase poco frecuente.** Solo el 13,9 % de las máscaras contienen
algún píxel de roca grande (y apenas el 8,9 % supera el 1 % de su área). La cobertura
dispone de datos abundantes; el conteo se aplica necesariamente a un subconjunto.

**3. Las etiquetas colaborativas están sesgadas hacia la roca.** Ejecutando el mismo
procedimiento sobre las 322 máscaras de experto del dataset (acuerdo del 100 %):

| Indicador | Colaborativas | Experto |
|---|:---:|:---:|
| Cobertura mediana | 96,8 % | **46,1 %** |
| Imágenes con cobertura del 100 % | 42 % | **8 %** |
| Píxeles de suelo + arena | 50 % | **69 %** |

Las personas voluntarias etiquetaron preferentemente la roca —visualmente más
saliente—, dejando suelo y arena sin etiquetar. El método de cálculo es correcto; el
sesgo proviene de la anotación de entrada.

**4. Limitación documentada.** En afloramientos continuos y extensos, el *watershed*
tiende a subdividir una región que geológicamente es un solo bloque. Se reporta con
ejemplos y con una medida de forma (solidez) que señala los casos sospechosos.

---

## Exploración complementaria: aprendizaje automático

El método principal es clásico e interpretable. Como **línea futura**, se exploró si un
modelo podría predecir los indicadores a partir de la imagen:

- **Segment Anything / FastSAM (sin entrenar).** Coincide con el conteo clásico en la
  misma banda solo el **44 %** de las veces (correlación de rangos 0,57): segmenta por
  apariencia y fragmenta una roca según su textura interna. Un modelo general sin ajuste
  al dominio no reproduce el conteo.
- **DeepLabV3 (aprendizaje por transferencia, entrenado con las propias máscaras).**
  Entrenado con 2 000 imágenes durante seis épocas en equipo local: **IoU medio 0,940** en
  el conjunto de prueba (IoU de la clase roca 0,925) y **correlación 0,950** entre la
  cobertura estimada por el modelo y la derivada de las máscaras humanas, con un error
  absoluto medio de 4,3 puntos porcentuales. Un modelo que solo ve la imagen reproduce, por
  tanto, el indicador de cobertura con notable fidelidad.

---

## Estructura del repositorio

```
src/                       # módulos del pipeline (funciones puras, parámetros explícitos)
  config.py                #   rutas del dataset y codificación NAV
  mask_utils.py            #   lectura de máscaras, máscaras binarias, morfología
  coverage.py              #   cobertura de roca visible (E1)
  rock_count.py            #   componentes + distancia + watershed + filtros (E2)
  features.py              #   composición del terreno y geometría de rocas
  pipeline.py              #   process_image / process_subset -> DataFrame
  viz.py                   #   figuras paso a paso del procedimiento
  sam_compare.py           #   comparación watershed vs. FastSAM
  segmentation.py          #   DeepLabV3 (línea futura)
scripts/                   # ejecución reproducible (pipeline, figuras, análisis)
notebooks/                 # exploraciones de aprendizaje automático
outputs/results.csv        # 24 indicadores por imagen (16 064 filas)
docs/                      # informe de avance y cronograma
```

---

## Reproducir

El dataset (~16 GB) **no se incluye** en el repositorio. Descárgalo de
[NASA](https://data.nasa.gov/d/cykx-2qix) o
[Zenodo](https://doi.org/10.5281/zenodo.15995036) y apunta a él con la variable de
entorno `AI4MARS_ROOT`.

```bash
conda env create -f environment.yml
conda activate tesis-marte

export AI4MARS_ROOT=/ruta/a/ai4mars-dataset-merged-0.6
python scripts/run_pipeline.py          # genera outputs/results.csv
python scripts/make_figures.py          # figuras descriptivas
python scripts/make_pipeline_figures.py # figuras paso a paso del pipeline
```

Los parámetros del procedimiento son explícitos y están documentados en
`src/rock_count.py` (`DEFAULT_PARAMS`); cada ejecución registra las versiones de las
bibliotecas y los parámetros usados junto al CSV de resultados.

---

## Documentos

- **[Resultados, discusión y limitaciones](docs/resultados_discusion.md)** — borrador de
  los capítulos, con los resultados sobre las 16 064 imágenes, la interpretación de los
  hallazgos y las limitaciones del estudio.
- [Figuras y pies de figura](docs/figuras_tesis.md) — figuras numeradas en formato tesis
  con sus pies de figura.
- [Correcciones a la propuesta](docs/correcciones_propuesta.md) — lista de cambios
  concretos a aplicar al documento de tesis (en español).
- [Informe de avance](docs/informe_avance.md) · [Cronograma](docs/cronograma.md)

## Alcance

Subconjunto de estudio: **MSL NavCam (Curiosity)**, etiquetas de entrenamiento.
El proyecto no genera máscaras nuevas, no modela evolución temporal del terreno ni
utiliza datos de elevación.

## Créditos

Dataset **AI4Mars** — Swan, R. M., Atha, D., Leopold, H. A., Gildner, M., Oij, S.,
Chiu, C., y Ono, M. (2021). *AI4Mars: A Dataset for Terrain-Aware Autonomous Driving on
Mars.* IEEE/CVF CVPR Workshops. Imágenes: NASA/JPL-Caltech.
