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
python scripts/make_validation_kit2.py --n 60
```

Genera en `outputs/validacion_manual_v2/`:

| Archivo | Contenido |
|---|---|
| `imagenes/W01.png` … | las escenas a evaluar |
| `plantilla.csv` | formulario con una fila por escena y la columna `banda` vacía |
| `clave.csv` | correspondencia con la imagen real y el conteo automático |

Decisiones del diseño, todas orientadas a que el resultado sea interpretable:

- Identificadores neutros y orden barajado: no puede inferirse nada del nombre.
- **El resultado del algoritmo no aparece** en el material que se consulta al responder.
- Solo escenas cuya región anotada supere los 2000 px, para que la zona sea examinable.
- Muestreo estratificado por **área de la región**, no por la banda del algoritmo, de modo
  que la muestra no quede condicionada al método que se evalúa.
- Se excluyen las escenas de rondas anteriores, para que el recuerdo no ancle las
  respuestas.

> No abras `clave.csv` hasta haber completado la plantilla: contiene el conteo automático
> y conocerlo invalidaría la validación.

## Cómo completarlo

```bash
python scripts/responder_validacion.py --dir outputs/validacion_manual_v2
```

Muestra las escenas una a una y registra la banda con las teclas 1 a 6, escribiendo
`plantilla.csv` en cada respuesta: el progreso sobrevive a un cierre y la sesión se retoma
donde quedó. No lee `clave.csv` en ningún momento y no permite volver atrás, salvo deshacer
la última respuesta.

Las seis bandas:

| Banda | Significado |
|:---:|---|
| `0` | ninguna roca distinguible en la zona |
| `1-3` | entre una y tres |
| `4-9` | entre cuatro y nueve |
| `10-24` | entre diez y veinticuatro |
| `25-49` | entre veinticinco y cuarenta y nueve |
| `50+` | cincuenta o más |

Se responde por bandas y no con una cifra exacta porque el objetivo no es medir la
precisión del conteo —imposible sin verdad de campo— sino comprobar si el algoritmo sitúa
las escenas en el mismo orden de magnitud que un observador. La banda superior se subdivide
hasta `50+` porque cerrarla antes premiaría a los métodos que sobreestiman.

Conviene responder de corrido, sin volver atrás y sin consultar resultados del análisis.

## Evaluación

```bash
python scripts/eval_validation.py --dir outputs/validacion_manual_v2
```

Informa el acuerdo exacto de banda, el **coeficiente kappa de Cohen** simple y **ponderado**
—este último es el apropiado, porque las bandas son ordinales y el simple penaliza igual un
fallo de una banda que de tres—, la dirección del desacuerdo y la matriz de acuerdo. Genera
además la figura en formato tesis, con numeración distinta por ronda para que una no
sobrescriba a la otra.

Para contrastar el conteo basado en máscara con el híbrido máscara+imagen:

```bash
python scripts/eval_hybrid.py --dir outputs/validacion_manual_v2
```

---

# Ronda definitiva (n = 60)

La ronda de 24 escenas sirvió de **prueba piloto**: reveló cuatro defectos del instrumento,
corregidos en `scripts/make_validation_kit2.py`. El resultado que se reporta en la tesis es
el de esta segunda ronda.

## Defectos corregidos

| Defecto de la ronda piloto | Corrección |
|---|---|
| Banda superior abierta en `10+`: un conteo de 84 frente a una decena observada puntuaba como acierto exacto, favoreciendo a los métodos que sobreestiman | Bandas `10-24`, `25-49`, `50+` |
| 7 de 24 escenas con región anotada imperceptible (<0,2 % de la imagen) | Se exige ≥ 2000 px |
| Relleno rojo opaco que tapaba la textura necesaria para contar | Tinte tenue (alfa 0,16) y recorte ampliado cuando aporta |
| Muestreo estratificado por la banda del propio algoritmo | Estratificado por área de la región, neutral entre métodos |

## Resultado

```
python scripts/eval_validation.py --dir outputs/validacion_manual_v2
```

| Medida | Valor |
|---|---:|
| n | 60 |
| Acuerdo exacto | 50 % |
| Kappa de Cohen | 0,13 |
| Kappa ponderado (lineal) | 0,11 |
| Escenas por debajo / por encima | **28 / 2** |

El 50 % de acuerdo engaña: **26 de las 30 coincidencias** caen en la banda `1-3`.

### El techo estructural

La matriz tiene **tres columnas vacías**. En ninguna de las 60 escenas el procedimiento
devuelve más de nueve rocas, mientras el observador identificó 10 o más en doce escenas y
25 o más en cinco. No es un sesgo recalibrable mediante umbrales.

### La causa: la anotación no es exhaustiva

| Medición | Valor |
|---|---:|
| Escenas donde `roca grande` es < 20 % de la roca etiquetada | 36 de 60 |
| Mediana de `roca grande` sobre la roca etiquetada | 9,1 % |
| Tamaño de la zona en las 27 escenas marcadas `1-3` | 1,11 % de la imagen |

La anotación **no marca todas las rocas de la escena, sino algunas**; el resto de la roca
queda como `bedrock`. En consecuencia, el conteo no estima el número de rocas de una escena
sino el de bloques dentro de la fracción que el anotador decidió delimitar. Ambas
cantidades pueden diferir en un orden de magnitud, y ni siquiera un procedimiento perfecto
sobre estas máscaras contaría más que lo delimitado.

### Qué corrige este resultado

La calibración se hizo temiendo la **sobresegmentación**, y contra ella se introdujo el
criterio de prominencia. El sesgo real va en sentido contrario y es mayor de lo que la
ronda piloto sugería.

---

# Ronda piloto (n = 24) — se conserva por trazabilidad

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
