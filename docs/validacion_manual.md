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

---

## Resultado obtenido

Ejecutada sobre 24 escenas con un observador. `python scripts/eval_validation.py`:

| Subconjunto | n | Acuerdo exacto | Kappa | Kappa ponderado |
|---|---:|---:|---:|---:|
| Todas las escenas | 24 | 46 % | 0,28 | 0,40 |
| Anotación apreciable (≥ 2000 px) | 17 | 41 % | 0,16 | 0,31 |
| Anotación mínima (< 2000 px) | 7 | 57 % | 0,28 | 0,11 |

Se reporta el **kappa ponderado** porque las bandas son ordinales y el kappa simple
penaliza igual un desacuerdo de una banda que de tres.

**Excluir las escenas mal planteadas empeora el resultado**, no lo mejora: el kappa cae de
0,28 a 0,16. Tres de las siete escenas de anotación mínima eran acuerdos triviales en la
banda cero, y esos aciertos fáciles inflaban el índice. Que el ponderado se sostenga en
0,31 indica que los desacuerdos son mayoritariamente de una sola banda.

### Dirección del error

El algoritmo queda **por debajo** del observador en 8 casos y por encima en 5. Esto corrige
la expectativa de la calibración: el riesgo que se temía era la sobresegmentación, y el
sesgo residual va en sentido contrario — **subconteo en escenas densas**.

De las 8 escenas subcontadas:

| Mecanismo | Escenas | Origen |
|---|---:|---|
| Polígono único extenso | 3 | La anotación cubre con una sola región un campo de rocas |
| Regiones bajo los filtros | 4 | Pequeñas o muy alargadas, descartadas por área o aspecto |
| Anotación insuficiente | 1 | 411 px en cuatro motas, todas bajo el área mínima |

El caso más claro es una anotación de **una sola región de 199 782 px** (46,8 % del área
etiquetada) donde el observador distinguió más de diez rocas y el algoritmo contó seis. La
división de aguas solo corta donde la transformada de distancia presenta estrechamientos, y
un polígono trazado holgadamente alrededor de un campo de rocas no los tiene.

## Debilidad del instrumento

En **7 de las 24 escenas** la región anotada suma menos de 2000 px, menos del 0,2 % de la
imagen. La zona resaltada es entonces apenas visible y la pregunta «cuántas rocas hay
dentro» queda mal planteada: el observador tiende a contar las rocas de la escena. Una
versión mejorada debería excluir esas escenas o mostrar un recorte ampliado de la región.
El kappa global debe leerse con esa reserva.

## Interfaz para responder

`scripts/responder_validacion.py` muestra las escenas una a una y registra la banda con las
teclas 1 a 4, escribiendo `plantilla.csv` en cada respuesta. No lee `clave.csv` en ningún
momento y no permite volver atrás, salvo deshacer la última respuesta.
