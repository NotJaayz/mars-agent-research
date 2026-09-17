# Conteo de rocas visibles en imágenes marcianas (AI4Mars)

**🌐 Idioma:** **Español** · [English](README.en.md)

Trabajo de grado que convierte las máscaras de segmentación del dataset **AI4Mars**
(NASA/JPL) en **indicadores cuantitativos de terreno**, imagen por imagen, mediante
procesamiento clásico de imagen y sin entrenar ningún modelo.

> **Autor:** Juan Pablo Delgado Castro
> **Programa:** Ciencia de Datos · Departamento de Matemáticas · Universidad Externado de Colombia
> **Estado:** procedimiento ejecutado sobre 16 064 escenas · documento de tesis redactado (87 páginas)

---

## La idea en un párrafo

AI4Mars contiene decenas de miles de imágenes de Marte con **mapas de terreno pintados
píxel a píxel** por voluntarios. Ese material se ha usado casi siempre para lo mismo:
*entrenar redes neuronales*, donde el mapa hace de respuesta correcta contra la que se
mide un modelo.

Este trabajo parte de otra observación. Ese mapa no es solo la respuesta de un problema de
aprendizaje: es en sí mismo un **mapa cuantitativo del terreno**. Si un píxel afirma «aquí
hay roca», entonces contar píxeles y agrupar los que se tocan permite medir cuánta roca hay
y cómo está organizada — sin entrenar nada, con cada umbral a la vista y en un portátil.

## Pregunta de investigación

> ¿Cómo cuantificar, a partir de las máscaras etiquetadas de AI4Mars, la cobertura de roca
> visible y el número aproximado de rocas individuales por imagen, mediante un flujo de
> procesamiento de imágenes con parámetros explícitos y resultados reproducibles?

La pregunta tiene dos mitades de dificultad muy distinta. Medir cobertura es contar píxeles
con un denominador bien elegido. Contar rocas exige resolver un problema de segmentación de
instancias sobre una máscara **que no distingue instancias**: cuando dos rocas se tocan,
quedan registradas como una sola región conectada.

El trabajo aborda las dos y reporta con igual detalle dónde cada una funciona y dónde no.

---

## 1. El conjunto de datos

| | |
|---|---|
| **Fuente** | [AI4Mars v0.6](https://doi.org/10.5281/zenodo.15995036) (Zenodo) · imágenes del [Planetary Data System](https://pds-imaging.jpl.nasa.gov/) |
| **Subconjunto de estudio** | MSL NavCam (*Curiosity*), etiquetas de entrenamiento |
| **Escenas analizadas** | **16 064** (todas las que tienen máscara) |
| **Resolución** | 1024 × 1024 px, escala de grises; la máscara tiene el mismo tamaño |

### Cómo se produjeron las etiquetas

- **Entrenamiento** (las que usa este trabajo): anotación colaborativa en Zooniverse, con
  mínimo 3 anotadores y **acuerdo de 2 de 3** por píxel. Sin ese acuerdo, el píxel queda
  sin etiqueta.
- **Prueba** (las que se usan para validar): **322 máscaras de especialistas de NASA JPL**,
  con **100 % de acuerdo** exigido, en tres niveles de exigencia.

Se enmascara como *sin etiqueta* el cuerpo del rover y todo lo que esté a más de 30 metros.

### Codificación de la máscara

| Valor | Clase | Descripción |
|:---:|---|---|
| `0` | soil | Regolito compacto transitable |
| `1` | bedrock | Roca expuesta en continuidad con el sustrato |
| `2` | sand | Depósito suelto, riesgo de atrapamiento |
| `3` | big rock | Bloque discreto apoyado sobre el terreno |
| `255` | NULL | Píxel sin clase asignada |

> **Verificación crítica.** La codificación asumida en el anteproyecto era **incorrecta**
> (suponía cinco clases con el fondo en el valor cero). Se verificó de tres formas
> independientes antes de calcular cualquier indicador: contra el archivo de claves del
> dataset, contra su documentación, y píxel a píxel sobre una muestra contrastada con las
> imágenes. Arrastrar ese error habría invalidado todos los resultados **en silencio**.

---

## 2. El procedimiento, paso a paso

### Cobertura de roca visible (E1)

Sea `M` la máscara. Se definen el conjunto de píxeles **etiquetados** y el de **roca**:

```
V = { p : M(p) ≠ 255 }          →  píxeles que recibieron etiqueta
R = { p : M(p) ∈ {1, 3} }       →  píxeles de roca (bedrock + big rock)

C = 100 · |R| / |V|
```

**Ejemplo.** Una imagen de 100 píxeles, de los que 45 recibieron etiqueta y 30 son roca:
`C = 100 · 30/45 = 66,7 %`. Nótese que el denominador es **lo etiquetado**, no la imagen:
sobre la imagen completa serían 30 %. Ambas medidas se reportan, y de esa diferencia surge
el [Hallazgo 1](#hallazgo-1-la-anotación-colaborativa-sobreestima-la-roca).

### Conteo de rocas individuales (E2)

Cinco etapas sobre la máscara binaria de *big rock*:

**1. Máscara binaria.** De los cinco valores posibles se conserva solo la clase 3. Todo lo
demás pasa a ser fondo.

**2. Limpieza morfológica.** Una *apertura* seguida de un *cierre*, con ventana 3×3. La
apertura elimina motas aisladas producto de imprecisiones al trazar los polígonos; el
cierre rellena huecos pequeños.

**3. Transformada de distancia euclidiana.** A cada píxel de roca se le asigna su distancia
al fondo más cercano:

```
D(p) = mín ‖p − q‖   para todo q ∉ B
```

Los centros de las regiones reciben valores altos y los bordes, valores bajos. El resultado
se lee como un **relieve**: cada roca es una colina, y *el punto donde dos rocas se tocan es
un valle*, porque ahí el fondo está cerca por ambos lados.

**4. División de aguas.** Se sitúan semillas en las cimas y se «inunda» el relieve invertido
`−D` hasta que las regiones se encuentran. La frontera queda en el valle. Las semillas se
eligen por **prominencia** (transformada de máximos h): solo se conserva un máximo si su
altura sobre el entorno supera un umbral.

**5. Filtros de tamaño y forma.** Cada región debe superar dos criterios: **área mínima** de
524 px (0,05 % de la imagen) y **relación de aspecto** no mayor que 5.

### El ejemplo que lo explica todo

Dos «rocas» de 3×3 unidas por un puente de un solo píxel:

```
MÁSCARA BINARIA B              TRANSFORMADA DE DISTANCIA D

. . . . . . . . . . .          .    .    .    .    .    .    .    .    .    .    .
. # # # . . . # # # .          .  1,0  1,0  1,0    .    .    .  1,0  1,0  1,0    .
. # # # # # # # # # .          .  1,0 [2,0] 1,4  1,0 [1,0] 1,0  1,4 [2,0] 1,0    .
. # # # . . . # # # .          .  1,0  1,0  1,0    .    .    .  1,0  1,0  1,0    .
. . . . . . . . . . .          .    .    .    .    .    .    .    .    .    .    .
```

Las **componentes conectadas** dan *una sola región*: para ese criterio hay una roca. Pero
`D` revela la estructura: los centros valen **2,0** (las cimas) y el puente vale **1,0** (el
valle), porque ahí el fondo está a un píxel por arriba y por abajo.

La división de aguas devuelve:

```
. . . . . . . . . . .
. 1 1 1 . . . 2 2 2 .
. 1 1 1 1 1 2 2 2 2 .
. 1 1 1 . . . 2 2 2 .
. . . . . . . . . . .
```

**Dos rocas**, con la frontera exactamente en el puente — donde un observador humano también
cortaría. Formalmente, la frontera se sitúa en el mínimo local de `D` entre dos máximos, y
ese mínimo es el estrangulamiento geométrico de la región.

**Y aquí está el límite del método**, que reaparecerá en los hallazgos: la división de aguas
*solo* puede cortar donde `D` presenta un valle. Si la anotación es un polígono amplio y liso
trazado sobre un campo de rocas, `D` forma una **única meseta sin valles** y el procedimiento
devuelve una región, por muchas rocas que contenga.

### Sobre una escena real

![Procedimiento paso a paso](outputs/figures/tesis/Figura_11_procedimiento_paso_a_paso.png)

### Los parámetros y su efecto

Ninguno está fijado dentro de la lógica de cálculo: todos se pasan como argumentos con su
valor por defecto documentado.

| Parámetro | Valor | Qué ocurre si se cambia |
|---|:---:|---|
| Apertura y cierre | 3×3 | Mayor: se pierden rocas pequeñas. Menor: entran motas |
| Suavizado de la distancia | σ = 3,0 | Menor: el contorno irregular genera cimas falsas |
| Prominencia de la semilla | h = 1,0 | Menor: sobresegmenta. Mayor: fusiona rocas distintas |
| Área mínima | 524 px | Mayor: se descartan rocas reales pequeñas |
| Relación de aspecto | 5 | Mayor: entran bandas del horizonte como si fueran rocas |
| Conectividad | 8 vecinos | Con 4, dos rocas unidas en diagonal se separarían |

> **La calibración principal.** El criterio de prominencia sustituyó a la detección de
> máximos por separación mínima. Con el criterio anterior, una losa extensa etiquetada como
> *big rock* generaba decenas de semillas espurias —se observó un caso con **142**— y
> quedaba fragmentada en rocas inexistentes. Se verificó que el criterio nuevo actúa de
> forma **selectiva**: sobre escenas sospechosas reduce el conteo entre un 32 % y un 44 %,
> mientras que en escenas normales no altera ningún conteo.

---

## 3. Resultados

### Composición del conjunto

Cada imagen recibe una bandera de calidad que documenta su aptitud para cada indicador.

| Bandera | Significado | Imágenes | % |
|---|---|---:|---:|
| `ok` | Contiene roca grande; apta para ambos indicadores | 2 193 | 13,7 |
| `no_bigrock` | Contiene roca, pero sin roca grande que contar | 8 458 | 52,7 |
| `no_rock` | Etiquetada, sin roca | 4 950 | 30,8 |
| `mostly_null` | Más del 95 % sin etiqueta | 300 | 1,9 |
| `empty` | Sin ningún píxel etiquetado | 163 | 1,0 |

### Cobertura de roca visible (E1) — funciona

De las 16 064 escenas, **10 817 (67,3 %)** contienen algún píxel de roca. Sobre ellas, la
cobertura tiene una mediana del **96,8 %** sobre píxeles etiquetados y del **42,0 %** sobre
la imagen completa. La distribución es marcadamente **bimodal**.

![Distribución de la cobertura](outputs/figures/tesis/Figura_13_distribucion_cobertura.png)

**El control que había que hacer.** Si la fórmula fuera el problema, las escenas *poco*
etiquetadas tendrían cobertura *alta*, porque el denominador sería pequeño. Se contrastó
explícitamente:

![Cobertura frente a fracción etiquetada](outputs/figures/tesis/Figura_14_cobertura_vs_fraccion_etiquetada.png)

La correlación es de **r = −0,02**: prácticamente nula. Las coberturas altas corresponden a
escenas genuinamente dominadas por lecho rocoso, no a un artefacto del denominador.

### Conteo de rocas (E2) — tiene un techo

Aplicado a las 2 193 escenas con roca grande, arroja **4 204 rocas**, con mediana de 1 por
imagen y máximo de 20.

| Rocas por imagen | Imágenes | % |
|---|---:|---:|
| 0 (descartadas por los filtros) | 453 | 20,7 |
| 1 | 772 | 35,2 |
| 2–3 | 613 | 28,0 |
| 4–9 | 344 | 15,7 |
| 10 o más | 11 | 0,5 |

![Conteo por bandas](outputs/figures/tesis/Figura_15_conteo_por_bandas.png)

La distribución tamaño–frecuencia es **decreciente** —predominan las rocas pequeñas—, lo que
coincide cualitativamente con los estudios de abundancia de rocas en sitios de aterrizaje.
La comparación es de forma, no de magnitud: los tamaños son relativos al campo de visión y
no métricos.

![Distribución tamaño-frecuencia](outputs/figures/tesis/Figura_16_tamano_frecuencia.png)

### Composición del terreno y recorrido (E3)

Composición media: **lecho rocoso 49,8 %, suelo 36,4 %, arena 12,5 %, roca grande 1,3 %**.

![Tipología de escenas](outputs/figures/tesis/Figura_17_tipologia_escenas.png)

Ordenando las escenas por el reloj de nave de su identificador se observa una **alternancia
clara** entre tramos rocosos y tramos de suelo o arena, con concentraciones puntuales de
roca grande que alcanzan el 40 % de las imágenes de un tramo.

![Variación a lo largo del recorrido](outputs/figures/tesis/Figura_18_variacion_recorrido.png)

### Los dos indicadores son independientes

Su correlación es de **r = 0,02**. No es un detalle: significa que miden facetas distintas
del terreno y **ninguno sustituye al otro**. Un afloramiento continuo produce cobertura
máxima y conteo nulo; un campo de bloques dispersos, lo contrario.

---

## 4. Hallazgos

Los tres resultados que el trabajo considera su aporte principal no estaban previstos en la
pregunta: surgieron de validar el procedimiento.

### Hallazgo 1: la anotación colaborativa sobreestima la roca

El dataset incluye 322 máscaras de especialistas. Se ejecutó sobre ellas **el mismo código,
sin cambiar ningún parámetro**.

| Indicador | Colaborativas | Experto |
|---|:---:|:---:|
| Cobertura mediana | 96,8 % | **46,1 %** |
| Escenas con cobertura del 100 % | 41 % | **8 %** |
| Píxeles de suelo y arena | 50 % | **69 %** |
| Píxeles de lecho rocoso | 49 % | 31 % |

![Validación con experto](outputs/figures/tesis/Figura_19_validacion_experto.png)

**El mecanismo.** Es un sesgo de saliencia en la tarea de anotación. La roca es visualmente
prominente y fácil de delimitar; el suelo y la arena son superficies extensas y homogéneas
cuya delimitación resulta tediosa. Al exigirse acuerdo entre anotadores, los píxeles de
suelo y arena sin consenso quedan **sin etiqueta y desaparecen del denominador**, lo que
eleva la fracción de roca. La tercera fila de la tabla lo confirma: los expertos no
encontraron más roca, encontraron **más suelo**.

**Precisión importante.** El procedimiento de cálculo *no* está sesgado: aplicado a las
máscaras de experto entrega valores plausibles. El sesgo reside en los datos de entrada, y
las etiquetas de los píxeles que sí se pintaron son correctas. El sesgo vive en la fórmula
de agregación, no en el contenido de las etiquetas.

> **Por qué esto trasciende el trabajo.** Toda la línea de investigación que emplea AI4Mars
> evalúa sus modelos por el acuerdo con estas máscaras. Documentar que sobreestiman la roca,
> y cuantificar cuánto, es información pertinente para esos trabajos y no solo para este.

### Hallazgo 2: el techo del conteo es la taxonomía, no las imágenes

La explicación intuitiva del bajo desempeño del conteo sería que faltan imágenes mejores. Se
descartó con tres mediciones:

1. **El procedimiento no abre las imágenes**: toda su información proviene de la máscara. Y
   las imágenes ya son de resolución completa, con la máscara del mismo tamaño: no hay
   pérdida por remuestreo.
2. En **13 838 escenas (86,1 %)** la máscara no tiene *ningún* píxel de roca grande. De la
   roca etiquetada en el conjunto, el lecho rocoso aporta el **97,5 %** y la roca grande solo
   el **2,5 %** — y E2 cuenta únicamente esta última.
3. Las máscaras de experto tienen **menos** roca grande, no más: del 16,5 % de escenas al
   1,6 % según se endurece el criterio de acuerdo.

Esta figura lo muestra sin necesidad de explicación: una escena repleta de bloques
individuales evidentes, etiquetada en su totalidad como **una sola región de lecho rocoso**.
El conteo devuelve cero. La imagen es excelente; la etiqueta es el límite.

![Roca visible etiquetada como lecho rocoso](tesis/images/diag_bedrock_no_contado.png)

### Hallazgo 3: la anotación no es exhaustiva

La validación con conteo humano lo reveló. En **36 de 60 escenas**, la clase roca grande
cubre **menos del 20 %** de la roca etiquetada, con una mediana del **9,1 %**: la anotación
marca *algunas* rocas, no todas.

De aquí se sigue una precisión sobre qué mide el indicador: **no estima el número de rocas de
una escena**, sino el de bloques dentro de la fracción que el anotador decidió delimitar como
roca grande. Ambas cantidades pueden diferir en un orden de magnitud, e incluso un
procedimiento perfecto sobre estas máscaras seguiría contando solo lo delimitado.

---

## 5. Validación con conteo humano

Se realizó en dos rondas. En cada escena se resalta la región anotada como roca grande y se
pregunta cuántas rocas se distinguen **dentro de esa región** — acotar la pregunta es lo que
permite atribuir el desacuerdo. El material se presenta con identificadores neutros, en orden
barajado, y el resultado automático no aparece en ningún momento.

**La ronda piloto (24 escenas) resultó defectuosa y se rehízo.** Su banda superior era
abierta en «10 o más», de modo que un procedimiento que contara 84 rocas donde el observador
distinguía una decena puntuaba como **acierto exacto**: la escala favorecía a los métodos que
sobreestiman. Se corrigieron además tres defectos: escenas cuya región anotada era
imperceptible, un relleno opaco que tapaba la textura necesaria para contar, y un muestreo
estratificado por la banda del propio algoritmo, que condicionaba la muestra al método
evaluado.

### Resultado (60 escenas, seis bandas)

| Medida | Valor |
|---|---:|
| Acuerdo exacto de banda | 50 % |
| Kappa de Cohen | 0,13 |
| Kappa ponderado | 0,11 |
| Escenas por debajo / por encima del observador | **28 / 2** |

El 50 % de acuerdo engaña: **26 de las 30 coincidencias** caen en una sola banda.

![Matriz de acuerdo](outputs/figures/tesis/Figura_26_validacion_manual_v2.png)

**El rasgo decisivo son las tres columnas vacías.** En ninguna de las 60 escenas el
procedimiento devuelve más de nueve rocas, mientras el observador identificó diez o más en
doce y veinticinco o más en cinco. No es un sesgo recalibrable mediante umbrales: es un
**techo estructural**.

### Por qué: el mecanismo, visto

![Mecanismo del subconteo](outputs/figures/tesis/Figura_28_mecanismo_subconteo.png)

Arriba, la anotación traza cada bloque por separado: hay regiones distintas con
estrangulamientos claros y el corte funciona (9 rocas, el observador dijo 4–9). Abajo, un
único polígono trazado holgadamente sobre un campo de roca estratificada: la transformada de
distancia forma **una sola meseta** y, por muchas rocas que contenga, no hay por dónde
cortar (3 rocas, el observador dijo 25–49).

Este resultado **corrige la expectativa con la que se calibró el procedimiento**. La
preocupación era la sobresegmentación, y contra ella se introdujo el criterio de prominencia.
El sesgo real va en sentido contrario.

---

## 6. Comparación con aprendizaje automático

### Modelo general, sin entrenamiento específico

Un modelo fundacional de segmentación (FastSAM) aplicado a 50 escenas, restringido a la
región de roca. El acuerdo con el conteo clásico es del **52 %** por bandas, con correlación
de rangos de 0,45 y error absoluto medio de 2,6 rocas. Tiende a subdividir una misma roca
según su textura interna y a no detectar bloques de bajo contraste.

![Matriz de acuerdo con el modelo general](outputs/figures/tesis/Figura_20_matriz_acuerdo.png)

### Modelo entrenado con las propias máscaras

Un segmentador **DeepLabV3** por aprendizaje por transferencia, que distingue roca de no-roca
leyendo la imagen **sin máscara humana**. Entrenado con 2 000 imágenes, 400 de validación y
400 de prueba, seis épocas a 512 px, con aceleración por GPU integrada.

Alcanza **IoU medio de 0,940** y su cobertura correlaciona **0,950** con la humana.

![Cobertura del modelo frente a la humana](outputs/figures/tesis/Figura_21_cobertura_modelo_vs_humano.png)

### Una hipótesis que hubo que poner a prueba

Esa cifra **no puede leerse como acierto**: el modelo se entrenó con máscaras colaborativas y
se evaluó contra máscaras colaborativas, de modo que mide cuánto se parece a la anotación de
la que aprendió. Y como esa anotación sobreestima la roca, lo esperable era que hubiera
aprendido el sesgo junto con la señal.

> **La prueba.** Si heredó el sesgo, al evaluarlo contra las 322 máscaras de experto debería
> **sobreestimar** la cobertura de forma sistemática.
>
> **El resultado.** No sobreestima. La mediana del error es de **+0,0 puntos porcentuales**,
> con un 37 % de escenas por encima y un 30 % por debajo. *Hipótesis descartada.*

| Medida | Contra colaborativas | Contra experto |
|---|:---:|:---:|
| IoU medio | 0,940 | 0,843 |
| Correlación de la cobertura | 0,950 | 0,927 |
| Error absoluto medio | 4,3 p.p. | 7,5 p.p. |
| Mediana del error (sesgo) | — | **+0,0 p.p.** |

![Modelo frente a experto](outputs/figures/tesis/Figura_27_modelo_vs_experto.png)

**Por qué no lo heredó.** Encaja con el mecanismo del sesgo: opera por el *denominador* —el
suelo sin etiquetar que sale del cálculo— y no por error de clase en los píxeles que sí se
etiquetan. Como el entrenamiento excluye los píxeles sin etiqueta de la función de pérdida,
el modelo aprendió apariencia de roca a partir de píxeles correctamente etiquetados.

**Reservas declaradas.** Estima **cobertura, no conteo**: no separa bloques y no sustituye a
E2. Y es fiable **en agregado, no escena por escena**: el 23 % de las escenas supera los diez
puntos de error y cinco superan los cincuenta.

**Lo que abre.** El procedimiento clásico necesita una máscara humana, que no existe cuando
las imágenes llegan a la Tierra. El segmentador lee la imagen directamente. Que estime la
cobertura sin sesgo frente a una referencia de experto sugiere que el indicador definido y
auditado aquí podría calcularse **sin anotación humana en el bucle**.

---

## 7. Extensión aplicada

### Sistema de avisos de terreno

Los indicadores se traducen en seis reglas, cada una con su umbral, su severidad y su
justificación. Los umbrales se fijaron sobre **percentiles de la distribución observada**, no
de forma arbitraria.

| Aviso | Umbral | Sev. | Motivación |
|---|---|:---:|---|
| Daño en ruedas | roca grande > 5 % y solidez < 0,85 | 3 | Bloques con contornos angulosos: la condición asociada al desgaste documentado en *Curiosity* |
| Obstáculo mayor | roca mayor > 15 % | 3 | Un bloque que domina la escena puede superar la altura franqueable |
| Atrapamiento en arena | arena > 70 % | 3 | La arena suelta compromete la tracción; es el modo de fallo que inmovilizó a *Spirit* |
| Campo de bloques | 5 o más rocas | 2 | Muchos bloques reducen las trayectorias viables |
| Terreno rocoso | cobertura > 80 % | 1 | Informativa: buena tracción, superficie irregular |
| Escena poco evaluable | > 95 % sin etiquetar | 1 | Señala que la ausencia de avisos no es ausencia de riesgo |

De las 16 064 escenas: **104 de riesgo alto**, 1 359 medio, 124 bajo, y 14 477 sin aviso
operativo.

![Distribución de avisos](outputs/figures/tesis/Figura_24_alertas_terreno.png)

> Los avisos **heredan las limitaciones de los indicadores** de los que derivan, incluido el
> sesgo de anotación. No son una valoración de transitabilidad validada contra incidentes
> reales —no existe tal registro para este subconjunto— sino una priorización de escenas cuyo
> criterio queda explícito y es por tanto auditable.

### Aplicación de consulta

Aplicación de escritorio en Python que hace consultable el conjunto de resultados sin
programar, con cuatro vistas: resumen descriptivo, distribución de avisos, explorador que
muestra por escena la imagen, la anotación y las rocas detectadas, y una vista de rasgos
geológicos. Las figuras se generan a partir de los mismos archivos que respaldan el
documento.

```bash
python app.py
```

---

## 8. Exploración: detección de vetas (resultado negativo)

Las vetas de sulfato de calcio son depósitos precipitados por circulación de agua y el rasgo
de mayor interés científico presente en las anotaciones. La escala de navegación no las
etiqueta, así que la única vía sería detectarlas desde la imagen. **Se ensayó y no es
viable.**

El método aplicó un filtro de crestas de Meijering sobre la región de lecho rocoso —analiza
los autovalores del Hessiano para realzar estructuras curvilíneas finas, y se usa en
angiografía; una veta es geométricamente el mismo tipo de objeto—, más una variante
ponderada por el cociente azul/rojo.

| Medida | Sin color | Con color |
|---|:---:|:---:|
| Precisión media | 0,261 | 0,267 |
| Recall medio | 0,067 | 0,041 |
| Mejora sobre la tasa base | 9,1× | 10,2× |
| Escenas sin ningún acierto | 11 de 24 | 12 de 24 |

![Exploración de vetas](outputs/figures/tesis/Figura_25_exploracion_vetas.png)

**Hay señal pero el detector es inutilizable**: nueve veces mejor que el azar no es ruido,
pero recupera menos del 7 % de los píxeles de veta y falla por completo en casi la mitad de
las escenas.

**La hipótesis del color quedó refutada por medición propia.** El cociente azul/rojo en las
zonas claras del lecho rocoso resultó ser apenas **1,025 veces** el del conjunto de la roca,
con dirección inconsistente entre escenas. El polvo rojizo recubre también las vetas, y las
imágenes del conjunto son archivos comprimidos con balance de blancos aplicado, no productos
radiométricos calibrados. Añádase que NavCam es un instrumento de navegación: las vetas del
cráter Gale se caracterizaron con MAHLI, ChemCam y MastCam.

Se documenta para que el ensayo no se repita sin conocer sus límites.

---

## 9. Estructura del repositorio

```
├── src/                         módulos de cálculo (12)
│   ├── config.py                rutas del dataset y codificación NAV
│   ├── mask_utils.py            lectura de máscaras y binarización
│   ├── coverage.py              cobertura de roca visible (E1)
│   ├── rock_count.py            conteo con división de aguas (E2)
│   ├── rock_count_hybrid.py     exploración: máscara + gradiente de imagen
│   ├── features.py              composición y geometría de rocas
│   ├── pipeline.py              orquestación: una fila de resultados por imagen
│   ├── alerts.py                sistema de avisos de terreno
│   ├── segmentation.py          segmentador DeepLabV3
│   ├── sam_compare.py           comparación con modelo fundacional
│   └── viz.py                   visualización de máscaras y etapas
│
├── scripts/                     guiones de ejecución (23)
│   ├── run_pipeline.py          procesa el subconjunto → results.csv
│   ├── make_thesis_figures.py   figuras del documento
│   ├── make_mechanism_figure.py figura del mecanismo del subconteo
│   ├── make_validation_kit2.py  prepara la validación humana
│   ├── responder_validacion.py  interfaz para responderla
│   ├── eval_validation.py       acuerdo, kappa simple y ponderado
│   ├── eval_hybrid.py           contraste del conteo híbrido
│   ├── eval_model_expert.py     contraste del segmentador con experto
│   ├── train_segmentation.py    entrena el DeepLabV3
│   ├── run_alerts.py            evalúa las reglas de aviso
│   ├── diagnose_errors.py       paneles por modo de fallo
│   └── explore_vein_detection.py  exploración de vetas
│
├── tesis/                       documento en LaTeX (plantilla institucional)
├── docs/                        documentación de apoyo (11 archivos)
├── outputs/
│   ├── results.csv              24 indicadores × 16 064 escenas
│   ├── figures/tesis/           figuras del documento
│   └── validacion_manual_v2/    respuestas de la validación humana
├── app.py                       aplicación de escritorio
└── environment.yml              entorno conda
```

---

## 10. Reproducir

```bash
# 1. Entorno
conda env create -f environment.yml
conda activate tesis-marte

# 2. Dataset (~16 GB, no se versiona)
#    Descargar de https://doi.org/10.5281/zenodo.15995036 e indicar la ruta:
export AI4MARS_ROOT=/ruta/a/ai4mars-dataset-merged-0.6

# 3. Procedimiento principal → outputs/results.csv
python scripts/run_pipeline.py

# 4. Figuras del documento
python scripts/make_thesis_figures.py
python scripts/make_mechanism_figure.py

# 5. Validación humana
python scripts/eval_validation.py --dir outputs/validacion_manual_v2

# 6. Avisos de terreno
python scripts/run_alerts.py
```

Versiones registradas: Python 3.13, NumPy 2.5.1, SciPy 1.18.0, scikit-image 0.26.0,
pandas 3.0.5, Pillow 12.3.0.

---

## 11. Alcance y limitaciones

**Alcance.** MSL NavCam (*Curiosity*), etiquetas de entrenamiento. Quedan fuera MER,
Perseverance y MastCam. El proyecto no genera máscaras nuevas, no modela evolución temporal
ni usa datos de elevación.

**Limitaciones declaradas:**

- **Las coberturas son relativas al conjunto colaborativo**, no estimaciones absolutas de la
  abundancia de roca en el terreno. Para comparar escenas del mismo conjunto la utilidad se
  mantiene, porque el sesgo actúa en la misma dirección en todas.
- **Sin escala métrica.** Los tamaños son relativos al campo de visión. La cámara es un par
  estéreo, así que la vía existe, pero el subconjunto disponible es casi enteramente
  monocular (16 027 imágenes del ojo izquierdo frente a 37 del derecho).
- **La validación humana empleó un solo observador**, de modo que no permite separar el
  desacuerdo atribuible al procedimiento del inherente a la tarea.
- **El conteo no reproduce el juicio humano** con fidelidad suficiente para leerse como el
  número de rocas de una escena.

---

## Créditos

Dataset **AI4Mars** — Swan, R. M., Atha, D., Leopold, H. A., Gildner, M., Oij, S., Chiu, C.,
y Ono, M. (2021). *AI4Mars: A Dataset for Terrain-Aware Autonomous Driving on Mars.*
IEEE/CVF CVPR Workshops. Imágenes: NASA/JPL-Caltech.

Las máscaras existen gracias al trabajo de miles de voluntarios del proyecto AI4Mars en
Zooniverse. El sesgo que este trabajo documenta es un efecto estructural del diseño de la
tarea de anotación, **no una deficiencia atribuible a quienes la realizaron**.
