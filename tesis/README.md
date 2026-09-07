# Documento de tesis (LaTeX)

Documento final del trabajo de grado, montado sobre la **plantilla oficial del
Departamento de Matemáticas** de la Universidad Externado de Colombia.

## Compilación

La plantilla está pensada para **Overleaf**. Se sube la carpeta completa y se compila
`main.tex` como archivo principal.

En local, la bibliografía requiere Biber:

```
pdflatex main.tex
biber main
pdflatex main.tex
pdflatex main.tex
```

## Estructura

| Archivo | Contenido |
|---|---|
| `main.tex` | Preámbulo y orden de los capítulos. **No contiene texto del documento.** |
| `config.tex` | Título, autor, tutor, año y modalidad de grado. |
| `references.bib` | 33 entradas, estilo APA 7 vía `biblatex` + `biber`. |
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
Si se obtiene esa autorización, basta cambiar la modalidad en `config.tex` y redactar
`chapters/Chapter4/chapter04.tex`; el sistema de alertas de terreno y la aplicación de
escritorio del proyecto serían el contenido natural de ese capítulo.

## Pendiente

- `\ThesisAdvisors` en `config.tex` dice `Por completar`: falta el nombre del tutor.
- Las secciones opcionales de **declaración** y **agradecimientos** están comentadas, tal
  como la plantilla indica cuando no se usan. Descomentar si el programa las exige.

## Nota sobre las figuras

Las figuras del documento son **propias**, generadas por los guiones del proyecto
(`scripts/make_thesis_figures.py` y `scripts/diagnose_errors.py`). Las Figuras 1 a 10 de
la propuesta eran ilustraciones tomadas de artículos publicados y no se reproducen aquí;
en su lugar el Capítulo 2 describe esos estudios con su cita, y el Capítulo 3 incluye un
diagrama de método original en TikZ.

## Cambio respecto a la plantilla original

Una sola línea, comentada en `main.tex`: el separador de miles de `siunitx` pasó de
`group-separator={.}` a `group-separator={{.}}`. Con llaves simples, siunitx v3 descarta
el valor y usa la coma, que es incorrecta como separador de miles en español (`16,064` en
lugar de `16.064`).
