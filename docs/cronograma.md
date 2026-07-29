# Cronograma de trabajo — 1 de agosto a 1 de octubre de 2026

**Tesis:** Conteo de rocas visibles a partir de las máscaras de AI4Mars
**Autor:** Juan Pablo Delgado Castro · Universidad Externado de Colombia
**Periodo:** 1 de agosto – 1 de octubre de 2026 (9 semanas)

Este cronograma reemplaza el plan de 15 semanas de la propuesta (§9) por un plan de
9 semanas ajustado al periodo real de ejecución. Incorpora **2 reuniones con la
directora de tesis** (semanas 5 y 8) —la reunión inicial de alcance ya se realizó— y
una fase nueva de **prueba de concepto con Amazon Visual Rekognition** (semanas 6–7)
como validación comparativa y línea de trabajo futuro.

> **Estado actual (contexto para la directora).** La base de implementación ya está
> prototipada y funcionando: entorno reproducible, integración del dataset AI4Mars
> (subconjunto **MSL NavCam** de Curiosity, ~16 000 imágenes), pipeline de **cobertura
> de roca (E1)** y **conteo de rocas por watershed (E2)** calibrado, un `results.csv`
> con 24 indicadores por imagen y figuras descriptivas. Por eso las primeras semanas se
> dedican a **consolidar y validar** lo construido, y el grueso del periodo a la prueba
> con Rekognition, el análisis y la redacción.

## Tabla 1 (revisada). Cronograma 9 semanas.

| Semana | Fechas | Actividades | Reunión directora |
|:------:|--------|-------------|:-----------------:|
| 1 | 1–7 ago | Consolidación del entorno y del subconjunto MSL NavCam. Verificación de la codificación real de clases (NAV) y del emparejamiento imagen–máscara. Cierre del indicador de **cobertura (E1)**. | — |
| 2 | 8–14 ago | Consolidación del **conteo (E2)**: componentes conectadas + transformada de distancia + *watershed* + filtros. Verificación sobre imágenes con roca. | |
| 3 | 15–21 ago | **Calibración** de parámetros del watershed con inspección visual en escenas variadas. Documentación de la sobresegmentación de bloques continuos. | |
| 4 | 22–28 ago | Enriquecimiento de indicadores por imagen: composición del terreno y **distribución tamaño–frecuencia** de rocas. Ejecución del pipeline completo → `results.csv` (24 columnas). | |
| 5 | 29 ago–4 sep | **Análisis descriptivo (E3)** y **validación** con las 322 máscaras de experto (comparación crowdsourced vs. experto). Figuras de resultados. | **Reunión 1** — resultados del pipeline, validación y hallazgos (sesgo de cobertura, rareza de *big rock*, tamaño–frecuencia); confirmación del plan del PoC de Rekognition. |
| 6 | 5–11 sep | **PoC Amazon Visual Rekognition (parte 1):** preparación de una submuestra (~40–60 imágenes con roca), generación automática de *bounding boxes* desde las máscaras, carga a S3 y entrenamiento de un modelo Custom Labels. | |
| 7 | 12–18 sep | **PoC Amazon Visual Rekognition (parte 2):** inferencia y **comparación** del conteo/ detección de Rekognition frente al conteo clásico (watershed). Redacción de metodología y resultados. | |
| 8 | 19–25 sep | **Validación cualitativa** (§8.9): conteo manual por bandas en una submuestra vs. algoritmo. Redacción de **discusión y limitaciones**. | **Reunión 2** — revisión del PoC de Rekognition y revisión casi final del documento. |
| 9 | 26 sep–1 oct | **Cierre:** revisión completa, verificación de reproducibilidad (versiones, ejecución limpia, `results.csv`), armonización de estilo y versión final. **Entrega: 1 de octubre.** | |

## Prueba de concepto con Amazon Visual Rekognition (semanas 6–7)

**Motivación.** La propuesta (§2) plantea que los indicadores obtenidos pueden servir
como *referencia para entrenar modelos automáticos que intenten predecirlos*. Esta
prueba explora justamente esa vía, **sin desplazar el método principal** (clásico e
interpretable): se posiciona como **validación comparativa** y **trabajo futuro (E5)**.

**Enfoque (aprovecha lo ya construido):**
1. El pipeline ya identifica las regiones de *big rock* por imagen; de ellas se generan
   automáticamente las cajas envolventes (*bounding boxes*) que sirven como etiquetas de
   entrenamiento, sin anotación manual.
2. Se entrena un modelo **Amazon Rekognition Custom Labels** (clase "roca") con una
   submuestra pequeña, y se ejecuta inferencia sobre un conjunto de prueba.
3. Se **comparan** el número de rocas y la presencia de roca detectados por Rekognition
   frente a los del conteo clásico (watershed sobre máscaras).

**Alcance y limitaciones.** Es una prueba acotada (pocos datos, costo de AWS limitado),
no un sistema de producción. Rekognition genérico no reconoce rocas marcianas; se usa
la variante entrenable (Custom Labels). El objetivo es medir el grado de acuerdo con el
método clásico y dejar planteada la línea de aprendizaje automático.

## Reuniones con la directora de tesis

La reunión inicial de alcance ya se realizó, por lo que se planean **2 reuniones**
durante el periodo:

1. **Reunión 1 (semana 5):** resultados del pipeline y validación con etiquetas de
   experto; discusión de hallazgos (sesgo de cobertura en etiquetas crowdsourced,
   rareza de *big rock*, distribución tamaño–frecuencia) y confirmación del plan del
   PoC de Amazon Rekognition antes de su desarrollo.
2. **Reunión 2 (semana 8):** revisión de la prueba con Amazon Rekognition y revisión
   casi final del documento antes del cierre.

> La cadencia es ajustable. Si la directora prefiere reuniones adicionales o en otras
> fechas, se reubican sin alterar las fases.

## Entregables al cierre (1 de octubre)

- Documento de tesis con metodología, resultados, discusión y limitaciones.
- Código reproducible (pipeline de cobertura y conteo, scripts de ejecución y figuras).
- `results.csv` con los 24 indicadores por imagen para las ~16 000 imágenes MSL NavCam.
- Figuras del pipeline y del análisis descriptivo, más los resultados del PoC de Rekognition.
