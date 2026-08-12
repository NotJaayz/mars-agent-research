# Informe de avance — Conteo de rocas visibles a partir de las máscaras de AI4Mars

- **Estudiante:** Juan Pablo Delgado Castro
- **Programa:** Matemáticas — Ciencia de Datos, Universidad Externado de Colombia
- **Fecha:** agosto de 2026

---

## 1. Resumen ejecutivo

El procedimiento propuesto en el anteproyecto **está implementado y ejecutado en su totalidad** sobre
el subconjunto de estudio: **16 064 imágenes** de la cámara de navegación del rover Curiosity
(MSL NavCam) con máscara disponible. Se obtuvo una tabla de resultados con **24 indicadores por
imagen**, además de figuras del procedimiento y del análisis descriptivo.

Los objetivos **E1 (cobertura de roca)**, **E2 (conteo de rocas)**, **E3 (análisis descriptivo)** y
**E4 (recursos reproducibles)** están cubiertos; **E5 (interpretación y líneas futuras)** está en
curso, con una exploración adicional de aprendizaje automático ya realizada.

Durante la implementación surgieron **tres hallazgos que afectan el documento escrito** y que
requieren su revisión (sección 3). El más importante es una **corrección en la codificación de
clases** del dataset respecto a lo que figura en el anteproyecto.

---

## 2. Estado por objetivo

| Objetivo | Estado | Evidencia |
|---|---|---|
| **E1** Cobertura de roca visible | Completado | 16 064 imágenes procesadas; 10 817 (67 %) contienen roca |
| **E2** Conteo de rocas individuales | Completado | 2 193 imágenes con roca grande; 5 375 rocas contadas |
| **E3** Análisis descriptivo | Completado | Distribuciones, tipología de escenas y variación a lo largo del recorrido |
| **E4** Recursos reproducibles | Completado | Código modular, scripts de ejecución, registro de versiones y parámetros, CSV de resultados |
| **E5** Interpretación y líneas futuras | **En curso** | Casos atípicos identificados; exploración de aprendizaje automático realizada |

### 2.1 Resultados de E1 — cobertura de roca visible

- **10 817 imágenes (67 %)** presentan roca visible (lecho rocoso o roca grande).
- Cobertura mediana **sobre píxeles etiquetados: 96,8 %**; sobre la imagen completa: **42,0 %**.
  Se reportan ambas medidas, junto con la fracción de escena efectivamente etiquetada, para que la
  cifra sea interpretable (véase 3.3).
- 8 339 imágenes superan el 50 % de cobertura.

### 2.2 Resultados de E2 — conteo de rocas individuales

Sobre las 2 193 imágenes que contienen roca grande:

- **5 375 rocas** contadas en total; mediana de **2 rocas por imagen** (máximo 23).
- Distribución por bandas: 1 roca (29 %), 2–3 (28 %), 4–9 (22 %), 10 o más (2 %).
- **Distribución tamaño–frecuencia** (tamaño relativo al área de la imagen): pequeñas 49 %,
  medianas 32 %, grandes 20 %. Es una distribución decreciente, coherente con la forma que reporta
  la literatura de abundancia de rocas (Golombek et al.).

Los parámetros del algoritmo de división de aguas se **calibraron mediante inspección visual** en
escenas de distinto tipo (separación mínima entre máximos = 15 px; suavizado de la transformada de
distancia = 3,0), documentando el efecto de cada ajuste.

### 2.3 Resultados de E3 — análisis descriptivo

Además de los dos indicadores previstos, cada imagen se caracterizó por la **composición de su
terreno**, lo que permitió una tipología de escenas:

| Tipo de escena | Imágenes | % |
|---|---:|---:|
| Rocoso | 7 601 | 47 % |
| Suelo | 5 723 | 36 % |
| Arenoso | 1 742 | 11 % |
| Mixto | 835 | 5 % |

Composición media de los píxeles etiquetados: lecho rocoso 49,8 %, suelo 36,4 %, arena 12,5 % y
roca grande 1,3 %.

Se construyó también una **lectura del recorrido**: ordenando las imágenes por el reloj de nave se
observa la alternancia entre tramos francamente rocosos y tramos arenosos, con concentraciones
puntuales de roca grande. Esto responde de forma directa a la pregunta motivadora del capítulo
introductorio (en qué tramos del trayecto hay más roca visible).

---

## 3. Hallazgos que requieren revisión del documento escrito

### 3.1 Corrección de la codificación de clases (afecta §8.4)

El anteproyecto asume que la máscara codifica `0 = fondo/sin etiqueta`, `1 = suelo`, `2 = lecho
rocoso`, `3 = arena`, `4 = roca grande`. Al verificar el dataset real (versión 0.6, contra el
archivo `label_keys.json`, la documentación oficial y una comprobación píxel a píxel), la
codificación es:

| Valor | Clase real |
|:---:|---|
| 0 | suelo (*soil*) |
| 1 | lecho rocoso (*bedrock*) |
| 2 | arena (*sand*) |
| 3 | **roca grande** (*big rock*) |
| 255 | **sin etiqueta** (NULL) |

Es decir, el "sin etiqueta" es **255** y no 0, y la roca grande es **3** y no 4. El código ya opera
con los valores correctos; **queda pendiente corregir la redacción de §8.4**.

### 3.2 La clase "roca grande" es poco frecuente (afecta el alcance de E2)

Solo el **13,9 %** de las máscaras contienen algún píxel de roca grande, y apenas el **8,9 %**
superan el 1 % de su área. En contraste, el lecho rocoso aparece en cerca del 65 % de las imágenes.

**Implicación:** la cobertura (E1) dispone de datos abundantes, mientras que el conteo de rocas (E2)
se aplica necesariamente a un subconjunto reducido (~2 200 imágenes). Se propone reportarlo de forma
explícita como una característica del dataset y presentar la cobertura como indicador principal y el
conteo como análisis sobre las imágenes que contienen roca grande.

### 3.3 Sesgo de las etiquetas colaborativas frente a las de experto (validación)

Se ejecutó el mismo procedimiento sobre las **322 máscaras de experto** (acuerdo del 100 %) que
incluye el dataset, y se comparó con las máscaras colaborativas empleadas en el análisis:

| Indicador | Colaborativas (*train*) | Experto |
|---|:---:|:---:|
| Cobertura mediana | 96,8 % | **46,1 %** |
| Imágenes con cobertura del 100 % | 42 % | **8 %** |
| Píxeles de lecho rocoso | 49 % | 31 % |
| Píxeles de suelo + arena | 50 % | **69 %** |

**Interpretación:** las personas voluntarias etiquetaron preferentemente la roca —visualmente más
saliente— dejando parte del suelo y la arena sin etiqueta. Esto **eleva la cobertura calculada** a
partir de las máscaras colaborativas. El procedimiento de cálculo es correcto; el sesgo proviene de
la anotación de entrada. Se propone incorporarlo como resultado de validación y como limitación.

Se verificó además que la cobertura alta **no** es un artefacto de imágenes escasamente etiquetadas:
la correlación entre la cobertura y la fracción de escena etiquetada es prácticamente nula
(r ≈ −0,02). Por ello **se mantiene la fórmula del anteproyecto** (roca / píxeles válidos),
acompañada de medidas complementarias que facilitan su interpretación.

---

## 4. Limitación metodológica documentada

En regiones **continuas y extensas** etiquetadas como roca grande (por ejemplo un afloramiento), el
algoritmo de división de aguas tiende a **subdividirlas**, aunque geológicamente no correspondan a
bloques separados. Endurecer los parámetros reduce este efecto, pero entonces se subestima el conteo
en escenas con cúmulos de rocas realmente distintas. Se trata de un compromiso inherente al método,
ya anticipado en §8.7, que se documenta con ejemplos gráficos. Como indicador auxiliar se incorporó
una medida de forma (solidez) que permite señalar automáticamente los casos sospechosos.

---

## 5. Exploración complementaria: aprendizaje automático (línea futura, E5)

El anteproyecto señala (§2) que los indicadores obtenidos podrían servir de referencia para
*entrenar modelos automáticos que intenten predecirlos*. Se exploró esa vía **sin desplazar el
método principal**, que sigue siendo el procedimiento clásico e interpretable.

**Nota sobre infraestructura:** se intentó utilizar Amazon Rekognition, pero los permisos
disponibles en la cuenta institucional no lo habilitan. La exploración se realizó por tanto en
**equipo local**, sin costo, aprovechando la aceleración por GPU del computador de trabajo.

**a) Modelo pre-entrenado sin ajuste (Segment Anything / FastSAM).** Segmenta la imagen por
apariencia visual. Comparado con el conteo clásico en 50 imágenes, coincide en la misma banda de
conteo en el **44 %** de los casos (correlación de rangos 0,57). Tiende a fragmentar una misma roca
según su textura interna. **Conclusión:** un modelo general sin entrenamiento específico del dominio
no reproduce el conteo de forma fiable.

**b) Modelo entrenado con las propias máscaras (DeepLabV3, aprendizaje por transferencia).** Se
entrenó un segmentador que, a partir únicamente de la imagen, predice qué píxeles son roca. En una
prueba preliminar reducida (200 imágenes de entrenamiento, 2 épocas) se obtuvo:

- **IoU medio 0,79** (IoU de la clase roca: 0,73).
- **Correlación de 0,84** entre la cobertura estimada por el modelo y la obtenida de las máscaras
  humanas, con un error absoluto medio de 9,9 puntos porcentuales.

**Lectura:** un modelo entrenado sobre este dataset **reproduce razonablemente el indicador de
cobertura** a partir de la imagen. Es un resultado preliminar (queda pendiente el entrenamiento con
la configuración completa), pero sostiene con evidencia la línea futura planteada en el
anteproyecto.

---

## 6. Productos disponibles

- Tabla de resultados con 24 indicadores por imagen para las 16 064 imágenes del subconjunto.
- Código modular documentado, con parámetros explícitos y registro de versiones de las bibliotecas.
- Figuras del procedimiento paso a paso (imagen, máscara, máscara depurada, transformada de
  distancia y resultado del conteo) para escenas representativas.
- Figuras del análisis descriptivo: distribuciones de cobertura y conteo, tipología de escenas,
  distribución tamaño–frecuencia, validación con etiquetas de experto y variación a lo largo del
  recorrido.

---

## 7. Próximos pasos

1. Incorporar al documento las correcciones y hallazgos de la sección 3 (codificación de clases,
   frecuencia de la clase roca grande y sesgo de las etiquetas colaborativas).
2. Completar el entrenamiento del modelo de segmentación con la configuración ampliada y cerrar la
   comparación entre método clásico y modelo aprendido.
3. Realizar la validación cualitativa prevista en §8.9 (conteo manual por bandas sobre una
   submuestra) y contrastarla con el resultado del algoritmo.
4. Redactar los capítulos de resultados, discusión y limitaciones.

---

## 8. Puntos que agradecería consultar con usted

1. **Alcance del conteo (E2).** Dado que la clase roca grande aparece en el 14 % de las imágenes,
   ¿le parece adecuado presentar la cobertura como indicador principal y el conteo como análisis
   sobre el subconjunto con roca grande, documentando esta característica del dataset?
2. **Tratamiento del sesgo de anotación.** ¿Prefiere que la validación con etiquetas de experto se
   presente como una sección propia de validación, o integrada en la discusión de limitaciones?
3. **Peso de la exploración de aprendizaje automático.** ¿Considera pertinente incluirla como
   sección de trabajo futuro, o preferiría dejarla únicamente mencionada para no ampliar el alcance
   del trabajo?
