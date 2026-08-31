# Correcciones a aplicar al documento de la propuesta

Documento de trabajo interno: lista de cambios concretos que deben aplicarse al texto de
la propuesta (`Mars_Final_Delgado.pdf`, 61 pp) para alinearlo con lo verificado durante la
implementación. Para cada punto se cita el **texto original** y se propone el **texto de
reemplazo**.

> Está en español únicamente porque su función es editar el documento de tesis, que se
> redacta en ese idioma.

---

## Resumen

| # | Prioridad | Sección | Qué cambia |
|:-:|---|---|---|
| C1 | **Crítica** | §8.4, punto 1 | Codificación de clases (valores incorrectos) |
| C2 | **Crítica** | §8.2, criterios de inclusión | Declarar el subconjunto real (MSL NavCam, etiquetas *train*) |
| C3 | Alta | §8.6 | Precisar la interpretación de la cobertura y añadir medidas complementarias |
| C4 | Alta | §8.7, cierre | La sobresegmentación pasa de "se explorará" a resultado documentado |
| C5 | Media | §8.8 | El CSV tiene 24 columnas, no 4 indicadores |
| C6 | Media | §8.9 | Incorporar la validación con etiquetas de experto (ya realizada) |
| C7 | Media | §5.2, E2 | Matizar el alcance del conteo |
| C8 | Baja | §6.2 | Cita con año incorrecto |
| C9 | Baja | §10 | Entradas de referencia duplicadas |
| C10 | — | §9 | Cronograma ya reemplazado (ver `cronograma.md`) |
| C11 | — | nuevas | Añadir capítulos de Resultados y Discusión (ver `resultados_discusion.md`) |

---

## C1 · Codificación de clases (§8.4, punto 1) — **crítica**

**Texto original:**

> «Lectura de máscara original. Se carga la máscara de AI4Mars, donde cada valor entero
> representa una clase (por ejemplo, 0 = fondo o sin etiqueta, 1 = suelo, 2 = arena, 3 =
> lecho rocoso, 4 = roca grande). Los códigos exactos se documentarán según la versión del
> conjunto de datos.»

**Problema.** La codificación real de la escala NAV, verificada contra `label_keys.json`,
la documentación oficial del dataset (versión 0.6) y una comprobación píxel a píxel, es
distinta. De los cinco valores enunciados, solo `2 = arena` coincide; el resto está
desplazado, y el valor de "sin etiqueta" no es 0 sino 255. Mantener el texto haría que la
metodología descrita no correspondiera al procedimiento ejecutado.

**Texto de reemplazo propuesto:**

> «Lectura de máscara original. Se carga la máscara de AI4Mars, una imagen en escala de
> grises donde el valor de cada píxel es un código de clase. La escala de navegación (NAV)
> empleada en este trabajo utiliza los siguientes códigos, verificados contra el archivo
> `label_keys.json` y la documentación de la versión 0.6 del conjunto de datos:
>
> | Valor | Clase |
> |:---:|---|
> | 0 | suelo (*soil*) |
> | 1 | lecho rocoso (*bedrock*) |
> | 2 | arena (*sand*) |
> | 3 | roca grande (*big rock*) |
> | 255 | sin etiqueta (NULL) |
>
> Conviene subrayar dos particularidades. La primera es que el valor reservado a los
> píxeles sin etiqueta es **255** y no 0, de modo que el 0 corresponde a una clase de
> terreno con significado propio. La segunda es que los píxeles sin etiqueta no son
> únicamente errores de anotación: el propio conjunto de datos enmascara con ese valor el
> cuerpo del róver y las distancias superiores a 30 metros. El conjunto de datos incluye
> además una taxonomía geológica distinta (`M2020_GEO`), con subtipos de lecho rocoso,
> fragmentos sueltos y guijarros, que no se emplea en este trabajo.»

**Efecto en cascada.** Con la codificación corregida, las máscaras de trabajo definidas en
§8.4, punto 3, quedan así (conviene explicitarlo en el texto):

- máscara de cobertura: píxeles cuyo valor pertenece a {1, 3};
- máscara de rocas grandes: píxeles cuyo valor es igual a 3;
- píxeles válidos: aquellos cuyo valor es distinto de 255.

---

## C2 · Subconjunto de estudio (§8.2, criterios de inclusión) — **crítica**

**Texto original (tercer criterio):**

> «provengan de cámaras comparables (por ejemplo, cámaras de navegación o cámaras
> frontales) para evitar mezclar geometrías y resoluciones muy diferentes.»

**Problema.** El criterio es correcto pero indeterminado: no fija el subconjunto que
efectivamente se analizó. El documento describe además el conjunto completo («imágenes de
los róveres Spirit, Opportunity y Curiosity», §8.2), lo que no corresponde al análisis
realizado.

**Texto de reemplazo propuesto:**

> «provengan de una única combinación de misión y cámara, para evitar mezclar geometrías y
> resoluciones diferentes. En concreto, el análisis se restringe a la **cámara de
> navegación del róver Curiosity (MSL NavCam)** con **etiquetas del conjunto de
> entrenamiento**, que es la combinación mejor curada del conjunto de datos y la que
> concentra el mayor número de máscaras disponibles (16 064). Los subconjuntos de las
> misiones MER y Mars 2020, así como la cámara MastCam, quedan fuera del alcance y se
> señalan como posible extensión.»

Conviene además añadir, al describir el conjunto de datos, que las etiquetas de
entrenamiento son colaborativas (acuerdo de dos tercios entre al menos tres anotadores),
mientras que el conjunto de prueba proviene de especialistas con acuerdo del 100 %, ya que
esa distinción es la base de la validación (véase C6).

---

## C3 · Interpretación de la cobertura (§8.6) — alta

**Texto original (punto 1):**

> «Se cuentan los píxeles válidos, es decir, aquellos que en la máscara original tienen
> alguna etiqueta (suelo, arena, lecho rocoso o rocas grandes). Si hay píxeles marcados como
> "sin datos" o "fuera de campo", se excluyen del cálculo.»

**Problema.** La fórmula es correcta y se mantiene sin cambios, pero el texto no advierte
de una consecuencia que resultó relevante: como el denominador son los píxeles etiquetados
—una mediana del 58 % de la escena—, el indicador expresa *qué fracción del terreno
clasificado es roca* y no qué fracción de la fotografía. Sin esa aclaración, valores como el
96,8 % de mediana resultan desconcertantes.

**Añadido propuesto al final de §8.6:**

> «Debe precisarse el significado de este cociente. Como el denominador son los píxeles
> etiquetados, y no la totalidad de la imagen, el indicador expresa qué fracción del terreno
> efectivamente clasificado corresponde a roca. Dado que en este conjunto de datos una parte
> apreciable de cada escena queda sin etiqueta —el cuerpo del róver, el cielo y las
> distancias superiores a 30 metros—, ambas magnitudes difieren de forma sistemática. Para
> que el indicador sea interpretable sin ambigüedad, la tabla de resultados incorpora tres
> columnas: la cobertura sobre píxeles válidos, definida arriba; la cobertura sobre la imagen
> completa, que constituye una cota inferior conservadora; y la fracción de escena
> etiquetada, que permite identificar las imágenes en las que la primera medida se apoya en
> muy pocos píxeles y resulta por tanto menos fiable.»

---

## C4 · Sobresegmentación (§8.7, párrafo de cierre) — alta

**Texto original:**

> «En las pruebas con imágenes reales es frecuente que este esquema produzca cierta
> sobresegmentación […] En el desarrollo del trabajo se reservará un espacio específico para
> explorar formas de reducir ese efecto […] El objetivo no es fijar desde ya un conjunto único
> de parámetros, sino dejar claro que parte del proyecto consistirá en ajustar y documentar
> variantes razonables.»

**Problema.** El párrafo está redactado en futuro, como tarea pendiente. La tarea ya se
realizó y produjo un resultado concreto, con parámetros calibrados y una limitación
caracterizada. Conviene reescribirlo en pasado y remitir al capítulo de resultados.

**Texto de reemplazo propuesto:**

> «En las pruebas con imágenes reales este esquema produce cierta sobresegmentación,
> especialmente cuando la región etiquetada como roca grande es extensa y continua: la
> transformada de distancia presenta entonces varias crestas y el algoritmo subdivide una
> unidad que geológicamente es única. La calibración se realizó por inspección visual sobre
> escenas de distinto tipo, y los valores adoptados —separación mínima entre máximos locales
> de 15 píxeles y suavizado gaussiano de la transformada de distancia con σ = 3,0— reducen
> de forma apreciable los máximos espurios sin sacrificar la separación de cúmulos de rocas
> realmente distintas. Endurecer más estos parámetros disminuye la subdivisión de
> afloramientos, pero a costa de subestimar el conteo en escenas densas, de modo que se trata
> de un compromiso inherente al método. El capítulo de resultados documenta el efecto de cada
> ajuste y presenta una medida de forma (la solidez de cada región) que permite señalar
> automáticamente los casos en los que cabe sospechar subdivisión excesiva.»

---

## C5 · Estructura del conjunto de resultados (§8.8) — media

**Texto original (enumeración):** identificador, misión y cámara, cobertura, número de
rocas e indicadores auxiliares.

**Problema.** El conjunto de resultados generado es sensiblemente más rico: 24 columnas por
imagen. Conviene actualizar la enumeración, agrupada por bloques.

**Texto de reemplazo propuesto:**

> «Una vez definidos los dos indicadores, se generó un conjunto de resultados con una fila
> por imagen y veinticuatro columnas, organizadas en cinco bloques:
>
> - **Identificación:** identificador de la imagen, misión, cámara, ojo del par estéreo y sol
>   cuando está disponible.
> - **Cobertura:** cobertura sobre píxeles válidos, cobertura sobre la imagen completa y
>   fracción de escena etiquetada.
> - **Composición del terreno:** porcentaje de cada una de las cuatro clases sobre los
>   píxeles válidos, clase dominante y tipo de escena.
> - **Conteo y geometría de rocas:** número de píxeles de roca grande, conteo de rocas,
>   número de componentes conectadas antes de la división de aguas, tamaño de la roca mayor,
>   área media, conteo por clases de tamaño y solidez media.
> - **Calidad:** una bandera que resume la aptitud de la imagen para cada indicador.
>
> Cada ejecución registra además, en un archivo adjunto, las versiones de las bibliotecas
> empleadas y los valores de todos los parámetros, de modo que el resultado sea reproducible.»

---

## C6 · Validación (§8.9) — media

**Texto original:**

> «Si el tiempo lo permite, se realizará además una validación cualitativa con una pequeña
> submuestra de imágenes. En esa submuestra se harán conteos manuales aproximados de rocas en
> bandas […]»

**Problema.** Se realizó una validación adicional que la propuesta no contemplaba y que
resultó ser uno de los hallazgos principales: ejecutar el mismo procedimiento sobre las 322
máscaras de experto incluidas en el conjunto de datos y comparar los indicadores. Conviene
incorporarla como parte del diseño, manteniendo el conteo manual como tarea de cierre.

**Añadido propuesto:**

> «A la validación cualitativa prevista se añadió una validación cuantitativa que aprovecha
> una característica del propio conjunto de datos: además de las etiquetas colaborativas
> empleadas en el análisis, AI4Mars distribuye un conjunto de prueba de 322 máscaras
> etiquetadas por especialistas con acuerdo del 100 %. Ejecutar el mismo procedimiento, sin
> modificar parámetros, sobre ambos conjuntos permite separar lo que depende del método de lo
> que depende de la calidad de la anotación de entrada. El capítulo de resultados presenta
> esta comparación, cuya conclusión —una sobreestimación sistemática de la cobertura en las
> etiquetas colaborativas— constituye la limitación principal del estudio.»

---

## C7 · Alcance del objetivo E2 (§5.2) — media

**Texto original:**

> «E2. Estimar, para cada imagen, el número aproximado de rocas individuales presentes en las
> zonas etiquetadas como roca grande […]»

**Problema.** «Para cada imagen» resultó inexacto: la clase roca grande aparece solo en el
13,9 % de las máscaras. El objetivo se cumplió, pero sobre un subconjunto.

**Ajuste propuesto:** sustituir «para cada imagen» por «para cada imagen que contenga la
clase roca grande», y añadir una nota al pie o una frase en el alcance advirtiendo que dicha
clase es poco frecuente en el subconjunto analizado, de modo que el conteo se reporta como
análisis sobre esas escenas y la cobertura actúa como indicador principal.

---

## C8 · Cita con año incorrecto (§6.2) — baja

**Texto original:**

> «En estas máscaras se distingue entre suelo, arena, roca expuesta, roca grande y otras
> clases relevantes para la navegación (Swan et al., 2017) [23].»

**Problema.** El conjunto AI4Mars se publicó en 2021; no existe una referencia de Swan et
al. de 2017, y la propia lista de referencias solo recoge entradas de 2021 y 2022.

**Corrección:** reemplazar por `(Swan et al., 2021)` y ajustar el número de referencia para
que apunte a la entrada correcta.

---

## C9 · Referencias duplicadas (§10) — baja

Se detectaron entradas repetidas en la lista de referencias:

| Referencia | Entradas | Observación |
|---|:---:|---|
| Swan et al. | 4 | El artículo de 2021, el de 2022 y el conjunto de datos aparecen con solapamientos |
| Golombek et al. | 3 | La selección del sitio de MSL (2012) figura dos veces, una en forma abreviada y otra completa |
| Sun et al. (2024) | 2 | Mismo artículo sobre Zhurong, con dos formatos de enlace |
| Dai et al. (2022) | 2 | Mismo artículo (SegMarsViT), idéntico DOI, con distinta capitalización del título |

**Corrección:** unificar cada obra en una sola entrada y revisar que la numeración entre
corchetes del cuerpo del texto apunte de forma coherente a la entrada resultante. Conviene
además verificar la coherencia general de esa numeración, ya que una misma obra de Golombek
aparece citada con números distintos en la introducción y en la justificación.

---

## C10 · Cronograma (§9)

Reemplazado por el plan de nueve semanas (1 de agosto – 1 de octubre) con dos reuniones de
seguimiento. Véase `docs/cronograma.md`.

## C11 · Capítulos nuevos

La propuesta no contiene capítulos de resultados ni de discusión, por ser un anteproyecto.
Los borradores están en `docs/resultados_discusion.md`, con la numeración de figuras
continuando la del documento actual (que termina en la Figura 10).
