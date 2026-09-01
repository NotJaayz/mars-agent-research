# Resumen y conclusiones

**🌐 Idioma:** **Español** · [English](conclusiones.en.md)

> Borrador del resumen y del capítulo de conclusiones. El resumen se coloca al inicio del
> documento; las conclusiones, tras la discusión.

---

## Resumen

La abundancia y la organización de las rocas en la superficie de Marte condicionan la
seguridad de los vehículos de exploración y aportan información sobre los procesos
geológicos del terreno. Los estudios que las cuantifican suelen apoyarse en conteos
manuales o en procedimientos ajustados a un único conjunto de imágenes, mientras que los
conjuntos de datos con anotación por píxel, como AI4Mars, se emplean casi exclusivamente
para entrenar modelos de segmentación y rara vez como fuente directa de medidas.

Este trabajo propone y documenta un procedimiento reproducible que lee esas anotaciones
como mapas cuantitativos y deriva, para cada imagen, dos indicadores: la cobertura de roca
visible y un conteo aproximado de rocas individuales. El primero se obtiene por recuento de
píxeles; el segundo combina componentes conectadas, transformada de distancia y división de
aguas, con supresión de máximos por prominencia y filtros de tamaño y forma. Todos los
umbrales son explícitos y están documentados.

El procedimiento se aplicó a las 16 064 imágenes de la cámara de navegación del rover
Curiosity que disponen de anotación. El 67 % contiene roca visible y el 14 % contiene roca
grande susceptible de ser contada, con un total de 4 204 rocas y una distribución de
tamaños decreciente. Los dos indicadores resultaron estadísticamente independientes, lo que
confirma que describen aspectos distintos del terreno. El contraste con las anotaciones de
especialistas incluidas en el conjunto de datos reveló que las anotaciones colaborativas
sobreestiman de forma sistemática la proporción de roca, un sesgo que afecta a la
interpretación de la cobertura y que se reporta como limitación principal. Como línea
futura se comprobó que un segmentador entrenado con las propias anotaciones reproduce el
indicador de cobertura a partir únicamente de la imagen, con una correlación de 0,95.

**Palabras clave:** Marte, AI4Mars, segmentación de terreno, abundancia de rocas,
división de aguas, procesamiento de imágenes, indicadores reproducibles.

---

## Conclusiones

### 1. Sobre la pregunta de investigación

El trabajo se planteaba cómo cuantificar, a partir de las anotaciones de AI4Mars, la
cobertura de roca visible y el número aproximado de rocas por imagen mediante un flujo con
parámetros explícitos y resultados reproducibles. La respuesta es afirmativa y está
documentada: el procedimiento se definió, se implementó, se calibró y se ejecutó sobre la
totalidad del subconjunto de estudio, produciendo una tabla con veinticuatro indicadores
por imagen acompañada del registro de versiones y parámetros que permite repetir el
análisis.

Conviene precisar el alcance de esa respuesta. La cobertura se obtiene para las 16 064
imágenes; el conteo, en cambio, solo tiene sentido en las 2 193 que contienen la clase roca
grande. El procedimiento cumple lo que se propuso, pero uno de sus dos indicadores se
aplica a un subconjunto reducido por una característica del conjunto de datos que no era
previsible al plantear el estudio.

### 2. Sobre los objetivos específicos

Los cuatro primeros objetivos se cumplieron. La cobertura de roca visible (E1) se estimó
para todas las imágenes con anotación válida; el conteo de rocas (E2) se implementó con las
técnicas previstas y se calibró documentando el efecto de cada parámetro; la exploración
descriptiva (E3) se realizó por composición del terreno, tipología de escenas y variación a
lo largo del recorrido; y los recursos reproducibles (E4) se entregaron como código
modular, guiones de ejecución, registro de versiones y tabla de resultados.

El quinto objetivo, la interpretación y el planteamiento de líneas futuras (E5), se abordó
identificando patrones, casos atípicos y limitaciones, y explorando de forma acotada la vía
del aprendizaje automático que el propio planteamiento del problema anticipaba.

### 3. Sobre los hallazgos

**La codificación de clases debe verificarse contra los datos.** El supuesto inicial sobre
los valores de las anotaciones resultó incorrecto, y solo la comprobación directa —contra
la documentación del conjunto de datos y píxel a píxel— permitió detectarlo. De haberse
mantenido, todos los resultados habrían sido erróneos sin que nada en la ejecución lo
delatara. Es una lección metodológica aplicable a cualquier trabajo que reutilice
conjuntos de datos ajenos.

**La calidad de la anotación limita el indicador más que el algoritmo.** El hallazgo de
mayor alcance no proviene del procedimiento sino de los datos: las anotaciones
colaborativas etiquetan preferentemente la roca y dejan sin etiquetar parte del suelo y la
arena, lo que eleva la cobertura calculada. La mediana pasa de 96,8 % con anotaciones
colaborativas a 46,1 % con anotaciones de especialistas. El cálculo es correcto en ambos
casos; lo que cambia es la entrada. Las coberturas reportadas deben leerse, por tanto, como
relativas al conjunto colaborativo y válidas para comparar escenas entre sí, no como
estimaciones absolutas de la abundancia de roca.

**Los dos indicadores no son redundantes.** Su correlación es prácticamente nula: una
escena puede estar cubierta de lecho rocoso continuo y no contener ninguna roca contable, o
mostrar poca cobertura y varios bloques aislados. Cuánta roca hay y cómo está organizada
son preguntas distintas, y describir el terreno exige ambas.

**La sobresegmentación admite una solución dirigida.** La subdivisión de afloramientos
continuos, anticipada como riesgo en la metodología, se confirmó y se corrigió mediante
supresión de máximos por prominencia. La verificación mostró que la corrección es
selectiva: reduce el conteo entre un 32 % y un 44 % en las escenas marcadas como
sospechosas y no altera ninguna de las escenas correctas. Ajustar únicamente los parámetros
geométricos no lo habría conseguido, porque desplaza el problema en lugar de resolverlo.

**La distribución de tamaños reproduce la forma esperada.** El predominio de rocas pequeñas
y la disminución de la frecuencia al aumentar el tamaño coinciden cualitativamente con las
distribuciones descritas en la literatura de abundancia de rocas, lo que constituye un
indicio de validez del procedimiento, si bien los tamaños son relativos al campo de visión
y no magnitudes métricas.

### 4. Sobre la aportación del trabajo

La contribución no reside en una técnica nueva —todas las empleadas están bien
establecidas— sino en el puente que construye entre unas anotaciones existentes y unos
indicadores cuantitativos, con las decisiones y los umbrales documentados de forma que el
análisis pueda repetirse, discutirse y adaptarse. A ello se añaden tres resultados de valor
independiente: la corrección de la codificación de clases, la caracterización del sesgo de
la anotación colaborativa y la verificación de que un modelo entrenado sobre esas mismas
anotaciones reproduce el indicador de cobertura a partir de la imagen.

### 5. Sobre las implicaciones

Para la planificación de rutas, disponer de dos indicadores independientes por imagen
permite distinguir situaciones que un único número confunde: un afloramiento continuo y un
campo de bloques sueltos plantean riesgos distintos al vehículo y aquí quedan descritos de
forma diferenciada. Para el reaprovechamiento de conjuntos de datos anotados, el trabajo
muestra que estas anotaciones admiten una lectura cuantitativa directa, pero que esa
lectura hereda los sesgos de quien anotó, algo que conviene caracterizar antes de derivar
conclusiones sustantivas.

### 6. Sobre lo que queda abierto

El estudio no permite afirmar cuál es la abundancia absoluta de roca en el recorrido
analizado, porque la anotación de partida está sesgada y los tamaños no son métricos.
Tampoco puede extrapolarse a otras misiones o cámaras sin repetir el análisis. Las vías más
prometedoras para continuar son la corrección del sesgo aprovechando el subconjunto de
especialistas, la conversión a magnitudes métricas incorporando los productos de rango del
propio conjunto de datos, y la extensión del enfoque aprendido al conteo, que aquí solo se
verificó para la cobertura.
