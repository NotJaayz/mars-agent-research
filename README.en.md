# Counting visible rocks in Martian imagery (AI4Mars)

**🌐 Language:** [Español](README.md) · **English**

Undergraduate thesis that turns the segmentation masks of the **AI4Mars** dataset
(NASA/JPL) into **quantitative terrain indicators**, image by image, using classical image
processing and without training any model.

> **Author:** Juan Pablo Delgado Castro
> **Programme:** Data Science · Department of Mathematics · Universidad Externado de Colombia
> **Status:** procedure run over 16,064 scenes · thesis document revised after the supervisor's corrections

---

## The idea in one paragraph

AI4Mars contains tens of thousands of Mars images with **terrain maps painted pixel by
pixel** by volunteers. That material has been used almost exclusively for one purpose:
*training neural networks*, where the mask acts as the ground truth a model is measured
against.

This work starts from a different observation. That mask is not merely the answer to a
learning problem: it is itself a **quantitative map of the terrain**. If a pixel states
"there is rock here", then counting pixels and grouping the ones that touch makes it
possible to measure how much rock there is and how it is organised — without training
anything, with every threshold in plain sight, on a laptop.

## Research question

> Which quantitative indicators of rock coverage and organisation can be derived reproducibly
> from the AI4Mars masks, and what are the limits of their validity with respect to differences
> in annotation and to human judgement?

The question has two purposes. A **constructive** one: derive indicators with explicit
parameters. A **critical** one: establish how far they inform about the terrain rather than
about how it was annotated. Measuring coverage is counting pixels with a well-chosen
denominator. Counting rocks requires solving an instance-segmentation problem over a mask
**that does not distinguish instances**: when two rocks touch, they are recorded as a single
connected region.

The question was refined during the work: the original proposal asked only *how* to quantify;
the validity limits were added in light of what the validation revealed, and the thesis
documents this.

### Working hypotheses

| | Hypothesis | Outcome |
|---|---|---|
| **H1** | Coverage is derived reproducibly and is not determined by the labelled fraction of the scene | Supported, with weak residual dependence |
| **H2** | The count approximates the number of rocks an observer distinguishes in the annotated region, without one-directional bias | Rejected (exploratory evaluation, one observer) |
| **H3** | The indicators do not depend on the annotation source | Inconclusive for coverage: a small source effect, positive in every variant but distinguishable from zero by sol in only one |
| **H4** | Coverage and count carry different information | Supported: different information, **not** statistical independence |

---

## 1. The dataset

| | |
|---|---|
| **Source** | [AI4Mars v0.6](https://doi.org/10.5281/zenodo.15995036) (Zenodo) · imagery from the [Planetary Data System](https://pds-imaging.jpl.nasa.gov/) |
| **Study subset** | MSL NavCam (*Curiosity*), training labels |
| **Scenes analysed** | **16,064** (every scene with a mask) |
| **Resolution** | 1024 × 1024 px, greyscale; the mask has the same size |

### How the labels were produced

- **Training** (used by this work): crowdsourced annotation on Zooniverse, with a minimum of
  3 labellers and **2-of-3 agreement** per pixel. Without that agreement the pixel is left
  unlabelled.
- **Test** (used for validation): **322 masks from NASA JPL specialists**, requiring
  **100% agreement**, in three levels of strictness.

The rover body and everything beyond 30 metres are masked as *unlabelled*.

### Mask encoding

| Value | Class | Description |
|:---:|---|---|
| `0` | soil | Compact, traversable regolith |
| `1` | bedrock | Rock exposed in continuity with the substrate |
| `2` | sand | Loose deposit, entrapment risk |
| `3` | big rock | Discrete block resting on the terrain |
| `255` | NULL | Pixel with no class assigned |

> **A critical verification.** The encoding assumed in the project proposal was **wrong**
> (it posited five classes with background at value zero). It was verified three independent
> ways before computing any indicator: against the dataset's class-key file, against its
> documentation, and pixel by pixel on a sample cross-checked with the imagery. Carrying
> that error forward would have invalidated every result **silently**.

---

## 2. The procedure, step by step

### Visible rock coverage (E1)

Let `M` be the mask. Define the set of **labelled** pixels and the set of **rock** pixels:

```
V = { p : M(p) ≠ 255 }          →  pixels that received a label
R = { p : M(p) ∈ {1, 3} }       →  rock pixels (bedrock + big rock)

C = 100 · |R| / |V|
```

**Example.** An image of 100 pixels, 45 of which were labelled and 30 are rock:
`C = 100 · 30/45 = 66.7%`. Note the denominator is **what was labelled**, not the image:
over the full image it would be 30%. Both measures are reported, and that difference is the
origin of the [denominator check](#visible-rock-coverage-e1).

### Counting individual rocks (E2)

Five stages over the binary *big rock* mask:

**1. Binary mask.** Of the five possible values, only class 3 is kept. Everything else
becomes background.

**2. Morphological cleaning.** An *opening* followed by a *closing*, with a 3×3 window. The
opening removes isolated specks produced by imprecision in tracing the annotation polygons;
the closing fills small holes.

**3. Euclidean distance transform.** Each rock pixel is assigned its distance to the nearest
background pixel:

```
D(p) = min ‖p − q‖   for all q ∉ B
```

Region centres receive high values and edges low ones. The result reads as a **relief map**:
each rock is a hill, and *the point where two rocks touch is a valley*, because there the
background is close on both sides.

**4. Watershed.** Seeds are placed on the peaks and the inverted relief `−D` is "flooded"
until the regions meet. The boundary settles in the valley. Seeds are selected by
**prominence** (h-maxima transform): a maximum is kept only if its height above its
surroundings exceeds a threshold.

**5. Size and shape filters.** Each region must pass two criteria: a **minimum area** of
524 px (0.05% of the image) and an **aspect ratio** no greater than 5.

### The example that explains everything

Two 3×3 "rocks" joined by a single-pixel bridge:

```
BINARY MASK B                  DISTANCE TRANSFORM D

. . . . . . . . . . .          .    .    .    .    .    .    .    .    .    .    .
. # # # . . . # # # .          .  1.0  1.0  1.0    .    .    .  1.0  1.0  1.0    .
. # # # # # # # # # .          .  1.0 [2.0] 1.4  1.0 [1.0] 1.0  1.4 [2.0] 1.0    .
. # # # . . . # # # .          .  1.0  1.0  1.0    .    .    .  1.0  1.0  1.0    .
. . . . . . . . . . .          .    .    .    .    .    .    .    .    .    .    .
```

**Connected components** return *a single region*: by that criterion there is one rock. But
`D` reveals the structure: the centres are **2.0** (the peaks) and the bridge is **1.0** (the
valley), because there the background is one pixel away above and below.

The watershed returns:

```
. . . . . . . . . . .
. 1 1 1 . . . 2 2 2 .
. 1 1 1 1 1 2 2 2 2 .
. 1 1 1 . . . 2 2 2 .
. . . . . . . . . . .
```

**Two rocks**, with the boundary exactly at the bridge — where a human observer would also
cut. Formally, the boundary sits at the local minimum of `D` between two maxima, and that
minimum is the geometric constriction of the region.

**And here lies the method's limit**, which reappears in the findings: the watershed can
*only* cut where `D` presents a valley. If the annotation is a broad, smooth polygon traced
over a field of rocks, `D` forms a **single plateau with no valleys** and the procedure
returns one region, however many rocks it contains.

### On a real scene

![Step-by-step procedure](outputs/figures/tesis/Figura_11_procedimiento_paso_a_paso.png)

### Parameters and their effect

None is hard-coded inside the computation: all are passed as arguments with a documented
default.

| Parameter | Value | What happens if changed |
|---|:---:|---|
| Opening and closing | 3×3 | Larger: small rocks are lost. Smaller: specks get in |
| Distance smoothing | σ = 3.0 | Smaller: irregular contours generate false peaks |
| Seed prominence | h = 1.0 | Smaller: oversegments. Larger: merges distinct rocks |
| Minimum area | 524 px | Larger: genuine small rocks are discarded |
| Aspect ratio | 5 | Larger: horizon bands enter as if they were rocks |
| Connectivity | 8-neighbour | With 4, diagonally joined rocks would separate |

> **The main calibration.** The prominence criterion replaced local-maximum detection by
> minimum separation. With the initial criterion one scene produced **142** seeds, mostly along
> an elongated band. `scripts/calibracion.py` rebuilds the calibration from a manifest of six
> scenes and shows that the change was **not selective**: it cut the count by 21 % in scenes
> with low solidity, by 41 % in those with more than fifteen rocks, and also by 21 % in the
> rest. It lowered counts across the board, consistent with the undercount the human
> validation revealed.

---

## 3. Results

### Analysis populations

Each image receives a quality flag documenting its suitability for each indicator.

| Flag | Meaning | Images | % |
|---|---|---:|---:|
| `ok` | Contains big rock; suitable for both indicators | 2,193 | 13.7 |
| `no_bigrock` | Contains rock, but no big rock to count | 8,458 | 52.7 |
| `no_rock` | Labelled, no rock | 4,950 | 30.8 |
| `mostly_null` | More than 95 % unlabelled | 300 | 1.9 |
| `empty` | No labelled pixel at all | 163 | 1.0 |

- **Coverage (E1):** the 15,901 scenes with at least one labelled pixel (all but `empty`).
- **Count (E2):** the **2,193 `ok` scenes**. The 33 `mostly_null` scenes that contain some big
  rock (63 rocks) are excluded: with more than 95 % of the scene unlabelled, the region is an
  isolated fragment, and annotation artefacts concentrate there.

### Visible rock coverage (E1)

Coverage could be computed for **15,901 of the 16,064 scenes (99.0 %)**; **10,817 scenes
(67.3 % of the total)** had rock coverage greater than zero. Among the latter, the median
coverage over labelled pixels was **96.8 %** (42.0 % over the full image). The distribution is
markedly **bimodal**.

![Coverage distribution](outputs/figures/tesis/Figura_13_distribucion_cobertura.png)

**Denominator check.** If sparsely labelled scenes mostly retained rock, they would have high
coverage by construction.

![Coverage vs labelled fraction](outputs/figures/tesis/Figura_14_cobertura_vs_fraccion_etiquetada.png)

The linear association between coverage and labelled fraction is practically nil
(**r = −0.020**, 95 % CI [−0.036; −0.004]): with 15,901 scenes the by-scene interval excludes
zero, but it explains less than a thousandth of the variance and is no longer distinguishable
from zero once the sequential acquisition of the images is taken into account (bootstrap by
sol [−0.047; +0.008]; circular shift, p = 0.62). Distance correlation (0.062) detects a weak
non-linear dependence. By labelled-fraction band, median coverage does **not** follow the
pattern the artefact would produce (it is not highest in the least-labelled scenes):

| Labelled fraction | Scenes | Median coverage (over labelled) | (over image) |
|---|---:|---:|---:|
| up to 0.25 | 1,895 | 48.2 % | 3.4 % |
| 0.25 – 0.50 | 4,249 | 59.2 % | 22.0 % |
| 0.50 – 0.75 | 5,680 | 69.3 % | 42.8 % |
| above 0.75 | 4,077 | 32.6 % | 26.6 % |

The conclusions hold with full-image coverage (rank correlation between both versions: 0.90).

### Rock counting (E2)

Over the 2,193 `ok` scenes: **4,142 rocks**, median 1 per image, maximum 20.

| Rocks per image | Images | % |
|---|---:|---:|
| 0 (discarded by filters) | 453 | 20.7 |
| 1 | 772 | 35.2 |
| 2–3 | 613 | 28.0 |
| 4–9 | 344 | 15.7 |
| 10 or more | 11 | 0.5 |

![Count by band](outputs/figures/tesis/Figura_15_conteo_por_bandas.png)

**Decreasing** size–frequency distribution (1,806 small, 1,317 medium, 1,019 large), consistent
in shape —not magnitude: sizes are relative to the field of view— with rock-abundance studies.

![Size-frequency distribution](outputs/figures/tesis/Figura_16_tamano_frecuencia.png)

### Relationship between coverage and count (H4)

A Pearson coefficient near zero only rules out *linear* association; it does not prove
independence. The relationship was therefore measured with progressively more general
statistics (2,193 scenes):

| Measure | Detects | Value | p |
|---|---|---:|---:|
| Pearson r | linear | +0.022 [−0.015; +0.059] | 0.286 |
| Spearman ρ | monotone | +0.020 [−0.019; +0.060] | 0.351 |
| Distance correlation | any | 0.074 | 0.002 |
| Mutual information | any | 0.123 bits (null 0.023) | 0.005 |

**Practically no linear association, but not independence**: there is a weak **inverted-U**
dependence —few rocks at very low coverage (partly by construction, since big rock is in the
coverage numerator), a peak between 10 % and 50 %, and little big rock to count in scenes at
full coverage, whose rock is labelled almost entirely as bedrock—. Coverage bands explain
**5.6 %** of the count variance. The dependence survives control for sequential structure
(circular shift: distance correlation p = 0.026). The two indicators carry different
information, although the relationship between them is not nil.

### Terrain composition and acquisition sequence (E3)

Mean composition: **bedrock 49.8 %, soil 36.4 %, sand 12.5 %, big rock 1.3 %**.

![Scene typology](outputs/figures/tesis/Figura_17_tipologia_escenas.png)

Temporal order comes from the **spacecraft clock** (`sclk` column), extracted from each image
identifier. Ordered this way, scenes alternate between rocky and soil or sand segments. This is
variation **along the acquisition sequence, not in space**: the rover may take many images from
one location, and the dataset does not include the position of each shot.

![Variation along the acquisition sequence](outputs/figures/tesis/Figura_18_variacion_secuencia.png)

---

## 4. Comparison with expert masks (H3)

The dataset includes 322 expert masks, on **images different** from the training ones. With the
same code and parameters:

| Indicator | Crowdsourced | Expert |
|---|:---:|:---:|
| Median coverage (scenes with rock) | 96.8 % | 46.1 % |
| Scenes with 100 % coverage | 41 % | 8 % |
| Labelled fraction of the scene (median) | 0.58 | 0.59 |

![Coverage by source](outputs/figures/tesis/Figura_19_validacion_experto.png)

**The difference cannot simply be attributed to annotation**: the two sources cover different
images, and AI4Mars does not distribute crowdsourced masks for the expert images. To separate
the effects, a **common instrument** was used: the trained segmenter (a fixed function of the
image) applied to the labellable region of 593 crowdsourced scenes not used in its training or
validation and of the 322 expert ones.

![Common instrument](outputs/figures/tesis/Figura_30_instrumento_comun.png)

| Decomposition of the mean difference | p.p. | 95 % CI by scene | 95 % CI by sol |
|---|---:|---|---|
| Total difference according to labels | +20.4 | | |
| Attributable to the **images** | **+18.2 (89 %)** | [+12.4; +23.8] | |
| Attributable to the **annotation** | **+2.2 (11 %)** | [+0.02; +4.54] | [−1.0; +5.5] |

1. **The expert mask set consists of far less rocky scenes**: measured by the same instrument,
   its median coverage is 5.8 % versus 72.5 %. This is a property of the dataset relevant to
   anyone evaluating against that set.
2. The annotation component is small, positive in every variant and **uncertain**: +3.2
   [+1.0; +5.4] if the crowdsourced sample is drawn only from the test blocks, and +4.4
   [+2.1; +6.5] with the previous model. The expert images are concentrated in 48 sols; with a
   bootstrap that resamples whole sols, the interval of the main sample includes zero
   ([−1.0; +5.5]) and that of the test blocks barely excludes it ([+0.2; +6.3]). It is
   **compatible** with the hypothesis of a salience bias, but the design does not allow that
   mechanism to be identified causally.
3. The mechanism of a denominator reduced by unlabelled soil **finds no support**: the labelled
   fraction is the same in both sources (p = 0.24).

The decomposition assumes that the instrument's error is the same in both samples. A common bias
cancels out in the subtraction; what would bias it is an error that depends on scene
composition, and it does depend on the coverage band. The annotation figure is therefore
approximate, and the direction of its bias cannot be determined from these data.

---

## 5. Validation against human counting (H2) — exploratory evaluation

A single observer counted, by bands, the rocks they distinguish **within the region annotated**
as big rock in 60 scenes (neutral identifiers, shuffled order, automatic result hidden).
Parameters were frozen before the first answer and no calibration scene is in the sample. A
pilot round of 24 scenes served to fix instrument defects (its open "10 or more" band favoured
methods that overestimate).

| Measure | Value |
|---|---:|
| Exact band agreement | 50 % |
| Cohen's kappa | 0.13 [0.00; 0.27] |
| Weighted kappa | 0.11 [0.01; 0.22] |
| Scenes below / above the observer | **28 / 2** (sign test p < 0.001) |

![Agreement matrix](outputs/figures/tesis/Figura_26_validacion_manual_v2.png)

With the frozen parameters the procedure never exceeds 9 rocks; the observer saw 10 or more in
12 scenes. **It is not a calibration artefact**: across the 36 combinations of prominence,
smoothing and minimum area tested, the procedure falls below the observer in 23 to 29 scenes.

**Why.** The observer counted within the same region as the procedure, so the disagreement is
explained mainly by **regions lacking the geometric information needed to separate instances**:
the watershed only cuts where the region narrows, and a polygon enclosing a field of touching
blocks offers nowhere to cut. Apart from that disagreement, **the annotation is not exhaustive**
(in 36 of 60 scenes big rock is less than 20 % of labelled rock; median 9.1 %): not even an exact
count of the region would equal the rocks in the scene.

![Undercounting mechanism](outputs/figures/tesis/Figura_28_mecanismo_subconteo.png)

> **Scope of the indicator.** The procedure produces a reproducible count of the geometrically
> separable instances within the *big rock* class, but that count cannot be interpreted as a
> valid estimate of the total number of rocks visible in the scene. The exploratory evaluation
> with one observer suggests systematic undercounting. With a single observer, algorithm–person
> disagreement cannot be separated from between-person variability; confirming it requires at
> least two independent observers.

**The limit lies in the semantic representation.** Bedrock contributes 97.5 % of labelled rock
and big rock 2.5 %. On the **same** 322 images, the share of scenes with big rock falls from
16.5 % to 1.6 % as agreement among experts is tightened: only 20 % of its pixels survive, versus
44 % for bedrock and over 67 % for soil and sand. It is the class with the least consensus among
experts too. The evidence indicates that the main limitation for instance counting
comes from the semantic representation and the granularity of the labels, rather than from an
evident lack of image resolution (consensus, perspective, scale, occlusion and parametrisation
also play a part).

![Visible rock labelled as bedrock](tesis/images/diag_bedrock_no_contado.png)

### Exploration: using the image within the region

Four image-derived reliefs were compared (fine gradient, coarse gradient, shadows via black
top-hat, and a combination), with the same protocol and the parameter chosen by leave-one-out
cross-validation:

| Relief | Weighted κ | Difference vs E2 | 95 % CI | Bonferroni CI |
|---|---:|---:|---|---|
| Fine gradient | 0.18 | +0.06 | [−0.14; +0.28] | [−0.19; +0.33] |
| Coarse gradient | 0.08 | −0.03 | [−0.20; +0.13] | [−0.24; +0.17] |
| Shadows | 0.37 | +0.26 | [+0.03; +0.47] | [−0.03; +0.53] |
| Combined | 0.27 | +0.15 | [−0.05; +0.36] | [−0.11; +0.41] |

**None improves on E2 demonstrably** once the number of methods tested is corrected for, and all
shift the error towards overestimation. The hybrid approach remains a **proof of concept** and
future work.

---

## 6. Comparison with machine learning

**General model without specific training (FastSAM)**, 50 scenes restricted to the rock region:
52 % band agreement with the classical count, rank correlation 0.45.

**DeepLabV3 segmenter (ResNet-50)** trained on the crowdsourced masks (rock / non-rock; Adam,
lr 1e-4, batch 4, 512 px, 6 epochs; no augmentation; seed 0). Design fixed before training:

- **Population:** scenes with labelled fraction ≥ 0.20 (14,490; 1,111 excluded).
- **Temporal-block split:** 30 consecutive spacecraft-clock blocks (~75 sols each) randomly
  assigned to training, validation and test, with a one-sol margin: no test image is less than
  a sol away from a training image. The manifest `outputs/split_deeplab_manifiesto.csv`
  records each scene's block and partition.
- **Checkpoint:** best validation mIoU (epoch 4, 0.957); the test set is evaluated once.

| Test | n | Mean IoU | Coverage correlation | Mean absolute error |
|---|---:|---:|---:|---:|
| Balanced sample | 400 | 0.940 | 0.971 | 3.5 |
| Natural distribution of the test blocks | 2,323 | 0.932 | 0.971 | 3.7 |
| Excluded by labelled fraction < 0.20 | 178 | 0.815 | 0.869 | 10.4 |

![Model coverage vs human](outputs/figures/tesis/Figura_21_cobertura_modelo_vs_humano.png)

**Information leakage.** A previous version, with a random per-image split, had 75 test images
less than a minute from a training image and gave a mean IoU of 0.940 and a correlation of
0.971: practically the same as the block split. That proximity did not inflate performance.

**Against the expert** (mean IoU 0.836; correlation 0.924):

| Coverage error (model − label) | Crowdsourced (593) | Expert (322) |
|---|:---:|:---:|
| Mean error, 95 % CI | +0.93 [−0.08; +1.90] | +3.12 [+1.36; +4.95] |
| Mean absolute error | 4.3 | 8.5 |
| Limits of agreement (Bland–Altman) | [−23.3; +25.2] | [−29.3; +35.6] |
| Scenes with error > 10 p.p. | 11.1 % | 28.0 % |

![Bland–Altman](outputs/figures/tesis/Figura_29_bland_altman.png)

On average the model reproduces the annotation it learnt from, but **overestimates against the
expert** by about three points, the expected direction if it inherited that annotation's
criterion. Individual errors are large and range-dependent, so it describes sets of scenes, not
individual scenes. It estimates coverage, not counts.

---

## 7. Applied extension (thesis appendix)

**Heuristic prioritisation rules.** Six rules with explicit thresholds rank scenes for review: 98 high priority, 1,343 medium,
124 low. Count-based rules are evaluated only on the E2 population, and the percentile each
threshold represents is computed by the script.
**They are not calibrated for navigation**: without metric scale, a pixel percentage cannot
support inferences about block height, traversability, wheel damage or entrapment probability.

**Query application.** A desktop application that makes the results consultable without
programming (summary, prioritisation, scene explorer, geology).

```bash
python app.py
```

**Vein exploration** (negative result, in the appendix): a ridge filter improves nine-fold on
the base rate but recovers less than 7 % of vein pixels; colour does not help.

---

## 9. Repository structure

```
├── src/                         computation modules
│   ├── config.py                dataset paths and NAV encoding
│   ├── mask_utils.py            mask reading and binarisation
│   ├── coverage.py              visible rock coverage (E1)
│   ├── rock_count.py            watershed-based counting (E2)
│   ├── poblaciones.py           single definition of the E1 and E2 populations
│   ├── rock_count_hybrid.py     exploration: mask + image gradient
│   ├── features.py              composition and rock geometry
│   ├── pipeline.py              orchestration: one result row per image
│   ├── priorizacion.py          heuristic prioritisation rules
│   ├── segmentation.py          DeepLabV3 segmenter
│   ├── sam_compare.py           comparison with a foundation model
│   └── viz.py                   mask and stage visualisation
│
├── scripts/                     execution scripts
│   ├── run_pipeline.py          processes the subset → results.csv
│   ├── calibracion.py           reconstructs the count calibration
│   ├── sensibilidad_parametros.py  36 combinations of h, σ and minimum area
│   ├── analisis_dependencia.py  Pearson, Spearman, distance correlation, mutual information
│   ├── eval_validation.py       agreement with the observer: simple and weighted kappa
│   ├── eval_metodos_imagen.py   image reliefs with cross-validation and Bonferroni
│   ├── train_segmentation.py    trains DeepLabV3 with a temporal-block split
│   ├── eval_model_expert.py     segmenter versus expert masks (per scene)
│   ├── eval_fuga_temporal.py    spacecraft-clock distance between test and training
│   ├── eval_fuente_anotacion.py common instrument: images versus annotation
│   ├── eval_modelo_detalle.py   signed error, bootstrap and Bland–Altman for the segmenter
│   ├── compare_sam.py           comparison with FastSAM
│   ├── run_priorizacion.py      applies the prioritisation rules
│   ├── make_thesis_figures.py   document figures
│   ├── make_mechanism_figure.py undercounting-mechanism figure
│   ├── make_extension_figures.py  prioritisation and vein figures
│   ├── make_hybrid_figure.py    hybrid proof-of-concept figure
│   ├── diagnose_errors.py       panels by failure mode
│   ├── explore_vein_detection.py  vein exploration
│   ├── make_validation_kit2.py  prepares the human validation
│   ├── responder_validacion.py  interface to answer it
│   ├── generar_cifras.py        every number in the thesis → tesis/cifras.tex
│   └── generar_bibliografia.py  bibliography from Crossref/DataCite → tesis/references.bib
│
├── tests/                       tests of the deterministic rules
├── manifiestos/                 calibration scenes
├── tesis/                       LaTeX document (institutional template)
├── docs/                        earlier working documentation
├── outputs/
│   ├── results.csv              24 indicators + 4 eligibility columns × 16,064 scenes
│   ├── split_deeplab_manifiesto.csv  block and partition of each scene for the segmenter
│   ├── figures/tesis/           document figures
│   └── validacion_manual_v2/    human-validation responses
├── Makefile                     full reproduction, in order
├── app.py                       desktop application
├── environment.yml              environment with the final-run versions
└── requirements-lock.txt        exact record of every package
```

---

## 10. Reproducing

```bash
# 1. Environment (final-run versions; exact record in requirements-lock.txt)
conda env create -f environment.yml
conda activate tesis-marte

# 2. Dataset (~16 GB, not versioned)
#    Download from https://doi.org/10.5281/zenodo.15995036 and point to it:
export AI4MARS_ROOT=/path/to/ai4mars-dataset-merged-0.6

# 3. Everything, in order: tests, results, calibration, analyses, validation, segmenter,
#    evaluations, figures, thesis numbers and document
make todo

# Without retraining the segmenter (~2 h), reusing the trained model:
make resultados

# Tests only
make pruebas
```

The trained model (~170 MB) is not stored in git: download it from the published release
[modelo-deeplab-v2](https://github.com/NotJaayz/mars-agent-research/releases/tag/modelo-deeplab-v2) and copy it to `outputs/`. Its SHA-256 fingerprint is in
`outputs/segmentacion_metricas.json`. The document's result figures are not typed by hand:
`scripts/generar_cifras.py` extracts them from `outputs/` and writes `tesis/cifras.tex`.
Two files are frozen outputs of the previous model, kept only for the comparison with the random
split and not regenerated: `outputs/segmentacion_metricas_reparto_aleatorio.json` and
`outputs/fuente_anotacion_resumen_modelo_anterior.json`.

---

## 11. Scope and limitations

**Scope.** MSL NavCam (*Curiosity*), training labels. MER, Perseverance and MastCam are out
of scope. The project does not generate new masks, model terrain evolution over time, or use
elevation data.

**Declared limitations:**

- **Coverages describe the terrain as recorded by the crowdsourced annotation**; with expert
  masks they would be somewhat lower. They serve to compare scenes within the same set.
- **No metric scale.** Sizes are relative to the field of view; the subset is almost entirely
  monocular (16,027 left-eye images against 37 right-eye).
- **A single observer** in the count validation: conclusions about H2 are exploratory.
- **The count** measures geometrically separable instances within the *big rock* class, not the
  number of visible rocks.

---

## Credits

**AI4Mars** dataset — Swan, R. M., Atha, D., Leopold, H. A., Gildner, M., Oij, S., Chiu, C.,
& Ono, M. (2021). *AI4Mars: A Dataset for Terrain-Aware Autonomous Driving on Mars.*
IEEE/CVF CVPR Workshops. Imagery: NASA/JPL-Caltech.

The masks exist thanks to the work of thousands of volunteers on the AI4Mars project at
Zooniverse. The differences between annotation sources documented here are properties of the
dataset and task design, **not a deficiency attributable to those who performed it**.
