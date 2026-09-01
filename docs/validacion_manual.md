# Validación manual por bandas (§8.9)

La metodología comprometía un contraste entre el conteo automático y un conteo manual
aproximado. Este documento describe cómo realizarlo. Es la única parte del procedimiento
que requiere intervención humana.

## Qué se valida exactamente

El algoritmo cuenta rocas **dentro de la región que AI4Mars etiquetó como roca grande**.
Si se pidiera contar rocas sobre la fotografía sin más, la comparación mezclaría dos
cuestiones distintas: si la anotación es completa y si el algoritmo la subdivide bien.

Por eso, en cada escena del kit **la región anotada aparece resaltada** en rojo
translúcido con su contorno en amarillo, y la pregunta es cuántas rocas se distinguen
*dentro de esa zona*. Así ambos —persona y algoritmo— responden a lo mismo, y la
validación mide lo que interesa: si la partición coincide con la percepción humana.

## Preparación

```bash
python scripts/make_validation_kit.py --n 25
```

Genera en `outputs/validacion_manual/`:

| Archivo | Contenido |
|---|---|
| `imagenes/V01.png` … | las escenas a evaluar |
| `plantilla.csv` | formulario con una fila por escena y la columna `banda` vacía |
| `clave.csv` | correspondencia con la imagen real y el conteo automático |

Dos decisiones para evitar sesgos: los identificadores son neutros (`V01`, `V02`…) y el
orden está barajado, de modo que no puede inferirse nada; y **el resultado del algoritmo
no aparece por ninguna parte** del material que se consulta al responder.

> No abras `clave.csv` hasta haber completado la plantilla: contiene el conteo automático
> y conocerlo invalidaría la validación.

## Cómo completarlo

Abre cada imagen de `imagenes/` y anota en `plantilla.csv`, en la columna `banda`, cuántas
rocas distingues dentro de la zona resaltada, usando una de estas cuatro categorías:

| Banda | Significado |
|:---:|---|
| `0` | la zona resaltada no corresponde a rocas distinguibles |
| `1-3` | entre una y tres rocas |
| `4-9` | entre cuatro y nueve rocas |
| `10+` | diez o más |

Se responde por bandas y no con una cifra exacta porque el objetivo no es medir la
precisión del conteo —imposible de establecer sin verdad de campo— sino comprobar si el
algoritmo tiende a situar las escenas en el mismo orden de magnitud que un observador.

Conviene responder de corrido, sin volver atrás a revisar respuestas anteriores, y sin
consultar los resultados del análisis mientras se completa.

## Evaluación

```bash
python scripts/eval_validation.py
```

Informa el porcentaje de acuerdo exacto de banda, el **coeficiente kappa de Cohen** —que
corrige el acuerdo esperable por azar, más informativo que el porcentaje a secas—, la
dirección del desacuerdo (si el algoritmo tiende a situarse por encima o por debajo) y una
matriz de acuerdo. Genera además la figura correspondiente en formato tesis.

## Interpretación

Como referencia habitual para el coeficiente kappa: por debajo de 0,20 el acuerdo es
escaso; entre 0,21 y 0,40 aceptable; entre 0,41 y 0,60 moderado; entre 0,61 y 0,80
sustancial; y por encima de 0,80 casi perfecto.

Un acuerdo moderado o superior respaldaría el uso del indicador para comparar escenas.
Un acuerdo bajo, acompañado de un sesgo sistemático en una dirección, indicaría que el
procedimiento sobreestima o subestima de forma consistente, lo que también es un resultado
informativo y debe reportarse como tal.

El tamaño de muestra es reducido por diseño —veinticinco escenas—, de modo que el
resultado debe leerse como una comprobación cualitativa y no como una medición con
intervalos de confianza estrechos.
