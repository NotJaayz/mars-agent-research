# ¿Hacen falta mejores imágenes? Atribución de los errores del conteo

**Pregunta:** el conteo a veces marca rocas donde no las hay y a veces no detecta
rocas evidentes. ¿El límite está en la calidad de las imágenes?

**Respuesta corta: no.** El pipeline de E1/E2 **no abre las imágenes**: `process_image`
recibe `image_path` solo para fijar el `image_id` y todo el análisis se hace sobre la
máscara PNG (`src/pipeline.py`, `src/mask_utils.py`). Sustituir las imágenes por otras
mejores no cambiaría ni un dígito de `outputs/results.csv`. Además las imágenes ya son
NavCam a resolución completa, 1024×1024 en escala de grises, y la máscara tiene
exactamente la misma resolución: no hay pérdida por remuestreo.

El límite real está en la **etiqueta**, y en particular en la clase 3 (`big rock`).

## Atribución cuantitativa (16 064 escenas MSL NavCam *train*)

### Por qué "no se detectan rocas" (89,0 % de las escenas dan `n_rocks = 0`)

| Causa | Escenas | Naturaleza |
|---|---|---|
| La máscara no tiene **ningún** píxel de `big rock` | 13 838 (86,1 %) | límite de la **etiqueta** |
| Hay píxeles de `big rock` pero los filtros los descartan | 460 (2,9 %) | límite de **mis umbrales** |

De las 13 838, el grupo más importante son las 8 458 escenas con bandera
`no_bigrock`: **sí hay roca visible, pero el anotador la etiquetó `bedrock`**. La
mediana de `pct_bedrock` en ese grupo es 99,7 %, y 5 762 escenas tienen más del 80 %
de `bedrock` y cero `big rock`.

El desequilibrio es estructural: sobre las escenas con roca, **`bedrock` aporta el
97,5 % de la roca etiquetada y `big rock` solo el 2,5 %** — y E2 cuenta únicamente
la clase 3.

Las 460 escenas del segundo grupo se revisaron una a una y los filtros **aciertan**:
son motas de pocos píxeles (un ejemplo tiene una única región de 12 px frente al
umbral de 524 px) o bandas muy alargadas trazadas sobre el horizonte, descartadas por
relación de aspecto. No conviene bajar los umbrales.

### Por qué "hay rocas donde no las hay"

| Causa | Magnitud | Naturaleza |
|---|---|---|
| Escenas donde el watershed parte una región en varias (`n_rocks > n_componentes`) | 423 de 1 766 (24,0 %) · aportan 1 717 de 4 204 rocas | **algoritmo** |
| "Roca" que ocupa > 50 % del área válida, con `frac_valid` muy baja | 43 escenas | **artefacto de anotación** |
| Solidez media < 0,70 (contorno irregular) | 46 escenas (2,6 %) | algoritmo |
| Anotación en forma de contorno hueco (anillo) | ~0,2 % de las escenas con `big rock` (~4) | anecdótico |

Los artefactos de anotación son el falso positivo más llamativo: en
`NLB_626010959EDR_F0771070NCAM00223M1` solo el 2,0 % de la escena está etiquetada y
todo ese 2 % se marcó `big rock`, así que la "roca mayor" ocupa el 100 % de lo válido
(`largest_rock_pct` se mide sobre píxeles válidos, no sobre la escena).

El contorno hueco se midió sobre 600 escenas con `big rock` y resultó **raro**
(1 región de 1 019): la figura `sobresegmentacion.png` es un caso atípico y no debe
generalizarse.

## Las etiquetas de experto no resuelven el conteo

Los conjuntos *gold* del propio dataset (anotados por expertos, 322 escenas) tienen
**menos** `big rock`, no más:

| Fuente | Escenas | Con `big rock` | `n_rocks` medio | Cobertura mediana |
|---|---|---|---|---|
| `train` (crowdsourced) | 16 064 | 13,9 % | 0,26 | 58,6 % |
| gold min1 (experto) | 322 | 16,5 % | 0,30 | 12,5 % |
| gold min2 (experto) | 322 | 6,2 % | 0,10 | 7,7 % |
| gold min3 (experto) | 322 | 1,6 % | 0,03 | 0,8 % |

Conclusión: la rareza de `big rock` **no es un defecto de los anotadores no expertos
que se corrija con mejores anotadores**. Es la taxonomía NAV: `bedrock` describe
afloramiento continuo y absorbe la mayoría de los bloques que un lector humano
contaría como rocas individuales. El techo de E2 es la definición de la clase.

## La vía que sí levantaría el techo: usar la imagen

No hacen falta imágenes *mejores*; hace falta **usar** las que ya hay. La máscara dice
**dónde** hay roca (y lo hace bien: E1 tiene datos abundantes); la imagen dice
**cuántos** bloques hay dentro de esa región.

Prueba de concepto sobre `NLB_559866561EDR_F0660816NCAM00385M1`, la escena de
`bedrock_no_contado.png` — 98,8 % de la escena etiquetada como roca, 0 px de
`big rock`, E2 cuenta 0:

- Gradiente de intensidad (Sobel sobre la imagen suavizada) como relieve.
- Semillas por h-máxima en los interiores planos, **restringidas a la región de roca
  de la máscara**.
- Watershed sobre el gradiente, con los mismos filtros de área que E2.

Resultado: **456 bloques**, con fronteras que siguen las fracturas reales visibles en
la imagen (`outputs/figures/diagnostico/prueba_hibrido.png`). Sigue sin entrenar
ninguna red: es procesamiento clásico, coherente con el alcance de la tesis.

Advertencia honesta: 456 es con toda probabilidad un **sobreconteo** y el método
necesita calibración y validación humana antes de reportarse como indicador. Pero
demuestra que la información que E2 no está viendo está en la imagen, no ausente.

## Reproducir

```
python scripts/diagnose_errors.py
```

Genera en `outputs/figures/diagnostico/` un panel (imagen | máscara | rocas contadas)
por cada modo de fallo: `bedrock_no_contado`, `artefacto_anotacion`,
`sobresegmentacion`, `bajo_umbral_area` y `filtro_aspecto`.
