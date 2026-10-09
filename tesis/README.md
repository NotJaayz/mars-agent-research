# Documento de tesis (LaTeX)

Documento final del trabajo de grado, montado sobre la **plantilla oficial del
Departamento de Matemáticas** de la Universidad Externado de Colombia.

## Compilación

La plantilla está pensada para **Overleaf**. Se sube la carpeta completa y se compila
`main.tex` como archivo principal.

En local, la bibliografía requiere Biber en una versión compatible con la de `biblatex`
(por ejemplo, la de TeX Live 2025 con su propio Biber):

```
pdflatex main.tex
biber main
pdflatex main.tex
pdflatex main.tex
```

Con `tectonic` (`make tesis BIBER_DIR=/ruta/a/biber` desde la raíz del repositorio), el
`biblatex` 3.17 que trae tectonic exige exactamente Biber 2.17; con otra versión la
bibliografía no se genera. Biber 2.17 está en el archivo histórico de TeX Live 2021
(`tlnet-final/archive/biber.universal-darwin.tar.xz`). Es la compilación con la que se produce
la versión definitiva, en APA 7.

Todas las cifras del texto proceden de `cifras.tex` y `tabla_error_modelo.tex`, que genera
`scripts/generar_cifras.py` a partir de `outputs/`. No deben editarse a mano.

## Estructura

| Archivo | Contenido |
|---|---|
| `main.tex` | Preámbulo y orden de los capítulos. **No contiene texto del documento.** |
| `config.tex` | Título, autor, tutora (Juliana De Mier Medellin), año y modalidad de grado. |
| `references.bib` | 65 entradas, generadas por `scripts/generar_bibliografia.py` desde los DOI de `referencias.json`; estilo APA 7 vía `biblatex` + `biber`. |
| `cifras.tex`, `tabla_error_modelo.tex` | Cifras y tabla generadas por `scripts/generar_cifras.py`. |
| `abbreviations.tex` | Abreviaturas y siglas. |
| `glossary.tex` | Glosario. |
| `chapters/Chapter1/` | Portada, resúmenes (es/en) e introducción. |
| `chapters/Chapter2/` | Contexto y antecedentes. |
| `chapters/Chapter3/` | Diseño y métodos. |
| `chapters/Chapter4/` | Desarrollo e implementación — **omitido**, ver abajo. |
| `chapters/Chapter5/` | Resultados y evaluación. |
| `chapters/Chapter6/` | Conclusiones y recomendaciones. |
| `chapters/Appendices/` | Material complementario. |
| `images/` | Logo institucional y las figuras del análisis. |

## Modalidad

`config.tex` fija `\ModalidadProyecto{investigacion}`, fiel a la propuesta aprobada. Con
esa modalidad la plantilla **omite automáticamente** el capítulo de Desarrollo e
implementación y renumera el resto, de modo que Resultados es el Capítulo 4 y
Conclusiones el Capítulo 5.

Las instrucciones de la plantilla admiten incluir ese capítulo en un proyecto de
investigación «si la investigación incluye el desarrollo e implementación de un artefacto
sustantivo que justifique un capítulo independiente», pero **con autorización del tutor**.
Por indicación de la dirección, la extensión aplicada (reglas heurísticas de priorización y
aplicación de consulta) no tiene capítulo propio: se documenta en el anexo.

## Secciones opcionales

Las secciones opcionales de **declaración** y **agradecimientos** siguen las indicaciones de
la plantilla; se activan o desactivan en `main.tex`.

## Nota sobre las figuras

Las figuras del documento son **propias** y se regeneran con `make figuras` desde la raíz
del repositorio, que ejecuta los guiones correspondientes y las copia a `images/`. Las Figuras 1 a 10 de
la propuesta eran ilustraciones tomadas de artículos publicados y no se reproducen aquí;
en su lugar el Capítulo 2 describe esos estudios con su cita, y el Capítulo 3 incluye un
diagrama de método original en TikZ.

## Cambio respecto a la plantilla original

Una sola línea, comentada en `main.tex`: el separador de miles de `siunitx` pasó de
`group-separator={.}` a `group-separator={{.}}`. Con llaves simples, siunitx v3 descarta
el valor y usa la coma, que es incorrecta como separador de miles en español (`16,064` en
lugar de `16.064`).
