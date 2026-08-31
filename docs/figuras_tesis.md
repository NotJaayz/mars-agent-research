# Figuras y pies de figura para el documento

**🌐 Idioma:** **Español** · [English](figuras_tesis.en.md)

Las imágenes están en `outputs/figures/tesis/` y se generan con
`python scripts/make_thesis_figures.py`. Se producen **sin título incrustado**, porque en
un documento académico esa función la cumple el pie de figura; basta insertar la imagen y
copiar el pie correspondiente.

La numeración continúa la de la propuesta, que termina en la Figura 10. El anexo recoge los
paneles adicionales del procedimiento, con los que se cumple el compromiso de §8.9 de
documentar al menos cinco imágenes representativas.

| Nº | Archivo | Se cita en |
|:--:|---|---|
| 11 | `Figura_11_procedimiento_paso_a_paso.png` | Resultados, §1 |
| 12 | `Figura_12_banderas_calidad.png` | Resultados, §1 |
| 13 | `Figura_13_distribucion_cobertura.png` | Resultados, §2 |
| 14 | `Figura_14_cobertura_vs_fraccion_etiquetada.png` | Resultados, §2 |
| 15 | `Figura_15_conteo_por_bandas.png` | Resultados, §3 |
| 16 | `Figura_16_tamano_frecuencia.png` | Resultados, §3.1 |
| 17 | `Figura_17_tipologia_escenas.png` | Resultados, §4 |
| 18 | `Figura_18_variacion_recorrido.png` | Resultados, §5 |
| 19 | `Figura_19_validacion_experto.png` | Resultados, §6 |
| 20 | `Figura_20_matriz_acuerdo.png` | Resultados, §7 |
| 21 | `Figura_21_cobertura_modelo_vs_humano.png` | Resultados, §7 |
| 22 | `Figura_22_subdivision_afloramiento.png` | Discusión, §10 |
| A1–A4 | `Figura_A1…A4_procedimiento_anexo_*.png` | Anexo |

---

## Pies de figura

**Figura 11.** *Procedimiento paso a paso aplicado a una escena con varias rocas.*

> Nota. De izquierda a derecha: imagen original de la cámara de navegación; máscara de
> AI4Mars con las cuatro clases de terreno (rojo, roca grande; marrón, lecho rocoso; beige,
> arena; gris oscuro, sin etiqueta); máscara binaria de roca grande tras la limpieza
> morfológica, con las dos componentes conectadas resultantes; transformada de distancia,
> donde los tonos claros indican mayor lejanía del borde, con los cinco máximos locales
> señalados en aspas; y partición final por división de aguas, en la que cada color
> corresponde a una de las cinco rocas contadas. Parámetros: área mínima del 0,05 % del área
> de la imagen, separación mínima entre máximos de 15 píxeles, suavizado de la transformada
> de distancia con σ = 3,0 y relación de aspecto máxima de 5. Imagen
> `NLB_436473759EDR_F0211572NCAM00464M1`. Fuente: elaboración propia a partir de AI4Mars
> (NASA/JPL-Caltech).

**Figura 12.** *Composición del conjunto analizado según la bandera de calidad.*

> Nota. Distribución de las 16 064 imágenes de MSL NavCam con máscara disponible. Solo el
> 13,7 % contiene roca grande y resulta apta para el conteo, mientras que un 52,7 %
> adicional contiene roca sin bloques individuales que contar. El 2,9 % restante se descarta
> por tener más del 95 % de la escena sin etiqueta o por carecer por completo de etiquetas.
> Fuente: elaboración propia.

**Figura 13.** *Distribución de la cobertura de roca visible en sus dos versiones.*

> Nota. Histogramas sobre las 10 817 imágenes que contienen roca. A la izquierda, la
> cobertura calculada sobre los píxeles etiquetados, que es el indicador definido en §8.6; a
> la derecha, la misma magnitud referida a la imagen completa, que constituye una cota
> inferior conservadora. La línea discontinua señala la mediana en cada caso: 96,8 % y
> 42,0 % respectivamente. La distribución es bimodal, con una acumulación marcada en el
> extremo superior correspondiente a 4 471 imágenes cuya área etiquetada es íntegramente
> roca. Fuente: elaboración propia.

**Figura 14.** *Cobertura de roca frente a la fracción de escena etiquetada.*

> Nota. Diagrama de densidad hexagonal, en escala logarítmica de color, para las imágenes
> con etiqueta. La ausencia de estructura y una correlación de r = −0,02 indican que la
> cobertura no depende de la proporción de la escena que recibió etiqueta, lo que permite
> descartar que los valores altos sean un artefacto de imágenes escasamente anotadas.
> Fuente: elaboración propia.

**Figura 15.** *Distribución del número de rocas contadas por imagen.*

> Nota. Sobre las 2 193 imágenes que contienen roca grande. La primera barra corresponde a
> las 421 imágenes en las que existen píxeles de la clase pero ninguna región supera los
> filtros de área mínima y forma. La mediana es de dos rocas por imagen y el máximo
> observado es de 23. Fuente: elaboración propia.

**Figura 16.** *Distribución tamaño–frecuencia de las rocas contadas.*

> Nota. Clasificación de las 5 297 rocas medidas según su área relativa al tamaño de la
> imagen. La forma decreciente —predominio de rocas pequeñas y disminución de la frecuencia
> al aumentar el tamaño— coincide cualitativamente con las distribuciones descritas en los
> estudios de abundancia de rocas en sitios de aterrizaje, si bien aquí los tamaños son
> relativos al campo de visión y no magnitudes métricas. Fuente: elaboración propia.

**Figura 17.** *Tipología de escenas según la composición del terreno.*

> Nota. Clasificación de las 16 064 imágenes a partir de la proporción de cada clase sobre
> sus píxeles válidos: rocoso cuando la roca alcanza al menos el 66 %, arenoso o de suelo
> cuando la clase correspondiente supera el 50 %, y mixto cuando ninguna predomina. Casi la
> mitad de las escenas resultan rocosas. Fuente: elaboración propia.

**Figura 18.** *Cobertura de roca y presencia de roca grande a lo largo del recorrido.*

> Nota. Las imágenes se ordenaron por el reloj de nave contenido en su identificador, que
> crece de forma monótona con el tiempo, y se agruparon en cuarenta tramos de igual número
> de imágenes. El panel superior muestra la cobertura mediana de cada tramo y el inferior el
> porcentaje de imágenes con roca grande. Se aprecia una alternancia entre tramos
> francamente rocosos y tramos de suelo o arena, con concentraciones puntuales de roca
> grande. El eje horizontal refleja el orden de adquisición y no el sol ni la distancia
> recorrida, de modo que debe leerse como una ordenación relativa. Fuente: elaboración
> propia.

**Figura 19.** *Comparación de la cobertura entre etiquetas colaborativas y de experto.*

> Nota. A la izquierda, distribuciones normalizadas de la cobertura para las máscaras
> colaborativas empleadas en el análisis y para las 322 máscaras de experto con acuerdo del
> 100 % incluidas en el conjunto de datos. A la derecha, porcentaje de imágenes en las que
> la totalidad del área etiquetada es roca. La discrepancia es sistemática: la mediana pasa
> de 96,8 % a 46,1 % y la proporción de coberturas totales cae del 42 % al 8 %, lo que
> evidencia un sesgo hacia la roca en la anotación colaborativa. Fuente: elaboración propia.

**Figura 20.** *Matriz de acuerdo entre el procedimiento clásico y un modelo general de segmentación.*

> Nota. Cada celda indica el número de imágenes, de una muestra de cincuenta con roca
> grande, cuyo conteo cae en la banda de la fila según el procedimiento clásico y en la de
> la columna según el modelo general sin entrenamiento específico. La diagonal reúne los
> casos de coincidencia, que representan el 44 % del total. Las celdas por encima de la
> diagonal corresponden a sobreconteo del modelo y las situadas por debajo a subconteo.
> Fuente: elaboración propia.

**Figura 21.** *Cobertura estimada por el modelo entrenado frente a la derivada de la anotación humana.*

> Nota. Cada punto es una imagen del conjunto de prueba, no empleada durante el
> entrenamiento. El eje horizontal recoge la cobertura calculada sobre la máscara de
> AI4Mars y el vertical la calculada sobre la máscara predicha por el segmentador
> DeepLabV3 a partir únicamente de la imagen. La línea discontinua marca la igualdad
> perfecta. Fuente: elaboración propia.

**Figura 22.** *Subdivisión de una región continua etiquetada como roca grande.*

> Nota. Escena con regiones alargadas y de contorno cóncavo. Aunque la anotación delimita
> unas pocas franjas continuas, la transformada de distancia presenta varias crestas y la
> división de aguas las separa en cuatro regiones, lo que ilustra la limitación descrita en
> la discusión. La solidez media de las regiones aceptadas, incluida en la tabla de
> resultados, permite señalar automáticamente este tipo de casos. Imagen
> `NLB_614913932EDR_F0761384NCAM00294M1`. Fuente: elaboración propia a partir de AI4Mars
> (NASA/JPL-Caltech).

---

## Anexo

**Figura A1.** *Procedimiento paso a paso: escena con una única roca aislada.*

> Nota. Caso más sencillo del procedimiento: la máscara delimita un solo bloque, la
> transformada de distancia presenta un único máximo y la división de aguas no introduce
> ninguna partición. Imagen `NLB_448901529EDR_F0300740NCAM00256M1`.

**Figura A2.** *Procedimiento paso a paso: cúmulo de rocas contiguas.*

> Nota. Varias rocas aparecen en contacto y forman una misma mancha en la máscara binaria.
> Los máximos locales de la transformada de distancia permiten separarlas, que es
> precisamente la situación que justifica el uso de la división de aguas. Imagen
> `NLB_547801039EDR_F0630346NCAM07753M1`.

**Figura A3.** *Procedimiento paso a paso: escena densa en rocas.*

> Nota. Escena con el mayor número de rocas del conjunto analizado. Ilustra el
> comportamiento del procedimiento en el extremo superior del rango de conteo. Imagen
> `NLB_550010635EDR_F0632582NCAM00282M1`.

**Figura A4.** *Procedimiento paso a paso: escena de alta cobertura dominada por lecho rocoso.*

> Nota. La cobertura de roca es prácticamente total, pero la clase roca grande ocupa una
> extensión reducida, de modo que el conteo es bajo. Ejemplifica la independencia entre los
> dos indicadores discutida en los resultados. Imagen
> `NLA_407351345EDR_F0050406NCAM00340M1`.
