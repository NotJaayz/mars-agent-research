# Cronograma de trabajo — 1 de agosto a 1 de octubre de 2026

Reemplaza el cronograma de 15 semanas de la propuesta (§9) por un plan de **9 semanas**
ajustado al periodo real de ejecución. Incorpora **3 reuniones con el director**,
espaciadas ~cada 3 semanas (semanas 1, 5 y 8).

> Nota de estado: la base de implementación (entorno reproducible, integración del
> dataset AI4Mars, módulos de cobertura y de conteo con *watershed*, y una primera
> calibración de parámetros) ya está avanzada. Por eso las primeras semanas se dedican
> a **consolidar y verificar** lo construido, y el grueso del periodo a ejecución
> masiva, análisis, figuras y redacción.

## Tabla 1 (revisada). Cronograma 9 semanas.

| Semana | Fechas | Actividades previstas | Reunión director |
|:------:|--------|-----------------------|:----------------:|
| 1 | 1–7 ago | Consolidación del entorno reproducible y del subconjunto de estudio (MSL NavCam, etiquetas *train*). Verificación de la codificación real de clases (NAV) y del emparejamiento imagen–máscara. | **Reunión 1** — acordar alcance (MSL NavCam), corrección de codificación y criterios de inclusión. |
| 2 | 8–14 ago | Cierre del módulo de máscaras binarias y de **cobertura de roca visible (E1)**. Cálculo de cobertura sobre el conjunto y verificación de que los valores son razonables. | |
| 3 | 15–21 ago | Módulo de **conteo (E2)**: componentes conectadas + transformada de distancia + *watershed* + filtros de tamaño/forma. Primeros conteos sobre imágenes con roca. | |
| 4 | 22–28 ago | **Calibración** de parámetros (separación de máximos, suavizado de la distancia, área mínima) con inspección visual en escenas variadas. Registro de la sobresegmentación en bloques continuos. | |
| 5 | 29 ago–4 sep | **Ejecución del pipeline completo** (~16 000 imágenes) → `results.csv`. Estadísticas descriptivas por cámara/sol **(E3)**. | **Reunión 2** — revisar resultados preliminares y el hallazgo de rareza de *big rock*. |
| 6 | 5–11 sep | **Análisis e interpretación (E5)**: distribuciones de cobertura y conteo, casos atípicos (cobertura > 50 %, 0 rocas, sobresegmentación). Figuras *step-by-step* del pipeline (§12). | |
| 7 | 12–18 sep | Redacción de **Metodología y Resultados** con figuras. Incorporación de correcciones al texto: codificación de clases (§8.4) y hallazgos (§8.7 rareza, §8.9 calibración). | |
| 8 | 19–25 sep | **Validación cualitativa** (§8.9): submuestra con conteo manual por bandas vs. algoritmo. Redacción de **Discusión y limitaciones**. | **Reunión 3** — revisión casi final del documento. |
| 9 | 26 sep–1 oct | **Cierre**: revisión completa, verificación de reproducibilidad (`environment.lock.yml`, README, ejecución limpia), armonización de estilo y versión final. **Entrega: 1 de octubre.** | |

## Sentido de cada fase (narrativa)

- **Semanas 1–4 (agosto):** consolidar el terreno técnico. Aunque los módulos ya existen,
  este bloque asegura que el subconjunto, la codificación y los parámetros quedan
  verificados y documentados, cerrando E1 y dejando E2 calibrado.
- **Semanas 5–6 (fin de agosto–inicio septiembre):** producir los resultados a escala y
  empezar a leerlos: es el corazón empírico del trabajo (E3, E5) y la base de las figuras.
- **Semanas 7–8 (septiembre):** escribir. Volcar metodología, resultados y discusión, con
  las correcciones y hallazgos ya identificados, más una validación cualitativa ligera.
- **Semana 9 (fin de septiembre):** cerrar y garantizar reproducibilidad para la entrega.

## Reuniones con el director

Cadencia aproximada de **una cada 3 semanas** (3 en total):
1. **Reunión 1 (semana 1):** alcance y decisiones de diseño (subconjunto, codificación, criterios).
2. **Reunión 2 (semana 5):** resultados preliminares y hallazgos (rareza de *big rock*, sobresegmentación).
3. **Reunión 3 (semana 8):** revisión casi final del documento antes del cierre.

> La cadencia es ajustable. Si el director prefiere reuniones más frecuentes (p. ej. cada
> 2 semanas → 4–5 reuniones) o puntos de control adicionales, se reubican sin cambiar las fases.
