# Counting visible rocks in Martian imagery (AI4Mars)

**🌐 Language:** [Español](README.md) · **English**

Thesis research that quantifies, **image by image**, how much rock is visible on the
Martian surface and how many individual blocks can be distinguished, using the
segmentation masks of the **AI4Mars** dataset (NASA/JPL) and the *Curiosity* rover.

> **Author:** Juan Pablo Delgado Castro · Mathematics — Data Science,
> Universidad Externado de Colombia
> **Status:** pipeline complete and executed over 16,064 images · writing in progress

---

## What this project does

Instead of training a model to segment terrain (the usual application of AI4Mars),
this work **reads the existing masks as quantitative maps** and derives two indicators
per image:

1. **Visible rock coverage** — percentage of pixels labelled as bedrock or big rock.
2. **Approximate count of individual rocks** — separate blocks within big-rock regions,
   obtained through connected components → distance transform → *watershed* → size and
   shape filters.

The output is a table with **24 indicators per image**, step-by-step figures of the
procedure, and a descriptive analysis along the rover's traverse.

---

## Main results

Over **16,064 images** from MSL NavCam (Curiosity) with an available mask:

| Indicator | Result |
|---|---|
| Images containing visible rock | **10,817 (67%)** |
| Images with big rock (eligible for counting) | 2,193 (14%) |
| Individual rocks counted | **4,204** (median 1 per image, max 20) |
| Median coverage (over labelled pixels) | 96.8% |
| Median coverage (over the whole image) | 42.0% |

**Scene typology** — rocky 47% · soil 36% · sandy 11% · mixed 5%

**Rock size–frequency distribution** — small 49% · medium 32% · large 20%
(a decreasing distribution, consistent with the rock-abundance literature).

---

## Methodological findings

**1. The class encoding is often documented incorrectly.** Verified against
`label_keys.json`, the official dataset documentation and a pixel-by-pixel check, the
actual **NAV** scale is:

| Value | Class |
|:---:|---|
| `0` | soil |
| `1` | bedrock |
| `2` | sand |
| `3` | **big rock** |
| `255` | **NULL** (unlabelled) |

That is: "unlabelled" is **255** (not 0) and big rock is **3** (not 4). This corrects
the initial assumption of the thesis proposal.

**2. `big rock` is an infrequent class.** Only 13.9% of the masks contain any big-rock
pixel (and merely 8.9% exceed 1% of their area). Coverage therefore has abundant data,
whereas the count necessarily applies to a reduced subset.

**3. Crowdsourced labels are biased towards rock.** Running the same procedure on the
322 expert masks included in the dataset (100% agreement):

| Indicator | Crowdsourced | Expert |
|---|:---:|:---:|
| Median coverage | 96.8% | **46.1%** |
| Images with 100% coverage | 42% | **8%** |
| Soil + sand pixels | 50% | **69%** |

Volunteers preferentially labelled rock — visually more salient — leaving soil and sand
unlabelled. The computation itself is correct; the bias comes from the input annotation.

**4. Documented limitation.** In large, continuous outcrops the *watershed* tends to
subdivide a region that is geologically a single block. This is reported with examples
and with a shape measure (solidity) that flags the suspicious cases.

---

## Complementary exploration: machine learning

The main method is classical and interpretable. As a **future line of work**, we
explored whether a model could predict the indicators directly from the image:

- **Segment Anything / FastSAM (zero-shot).** Agrees with the classical count in the
  same band only **52%** of the time (rank correlation 0.45): it segments by appearance
  and fragments a single rock according to its internal texture. A general model without
  domain-specific tuning does not reproduce the count.
- **DeepLabV3 (transfer learning, trained on the masks themselves).** Trained on 2,000
  images for six epochs on local hardware: **mean IoU 0.940** on the test set (rock-class
  IoU 0.925) and a **correlation of 0.950** between the coverage estimated by the model and
  the one derived from human masks, with a mean absolute error of 4.3 percentage points. A
  model that only sees the image therefore reproduces the coverage indicator with notable
  fidelity.

---

## Application

The final deliverable is a desktop application bringing together the indicators, the risk
alerts and a scene explorer, using NASA's institutional palette on a dark theme:

```bash
pip install customtkinter   # the only additional dependency
python app.py
```

Four sections: **Summary** (indicators and distributions), **Alerts** (levels and the rule
catalogue with its justification), **Scene explorer** (original image, terrain annotation
and detected rocks for each flagged scene) and **Geology** (features of scientific interest
in the Perseverance set, including mineral veins).

An equivalent single-file HTML panel is also available for sharing with people who do not
run code: generate it with `python scripts/make_dashboard.py` and open it by double-click,
with no server or connection required.

Institutional logos are loaded from `assets/` when present; see
[assets/README.md](assets/README.md).

## Repository structure

```
src/                       # pipeline modules (pure functions, explicit parameters)
  config.py                #   dataset paths and NAV encoding
  mask_utils.py            #   mask reading, binary masks, morphology
  coverage.py              #   visible rock coverage (objective E1)
  rock_count.py            #   components + distance + watershed + filters (E2)
  features.py              #   terrain composition and rock geometry
  pipeline.py              #   process_image / process_subset -> DataFrame
  viz.py                   #   step-by-step figures of the procedure
  sam_compare.py           #   watershed vs. FastSAM comparison
  segmentation.py          #   DeepLabV3 (future line of work)
scripts/                   # reproducible execution (pipeline, figures, analysis)
notebooks/                 # machine-learning explorations
outputs/results.csv        # 24 indicators per image (16,064 rows)
outputs/figures/tesis/     # numbered thesis-format figures
docs/                      # results and discussion chapters, corrections to the
                           #   proposal, figure captions, progress report and schedule
```

---

## Reproducing

The dataset (~16 GB) is **not included** in this repository. Download it from
[NASA](https://data.nasa.gov/d/cykx-2qix) or
[Zenodo](https://doi.org/10.5281/zenodo.15995036) and point to it with the
`AI4MARS_ROOT` environment variable.

```bash
conda env create -f environment.yml
conda activate tesis-marte

export AI4MARS_ROOT=/path/to/ai4mars-dataset-merged-0.6
python scripts/run_pipeline.py          # generates outputs/results.csv
python scripts/make_figures.py          # descriptive figures
python scripts/make_pipeline_figures.py # step-by-step pipeline figures
```

All procedure parameters are explicit and documented in `src/rock_count.py`
(`DEFAULT_PARAMS`); every run records the library versions and the parameters used
alongside the results CSV.

---

## Documents

- **[Results, discussion and limitations](docs/resultados_discusion.en.md)** — draft of the
  chapters, with the results over the 16,064 images, the interpretation of the findings and
  the limitations of the study.
- **[Abstract and conclusions](docs/conclusiones.en.md)** — summary of the work and the
  conclusions chapter.
- [Figures and captions](docs/figuras_tesis.en.md) — numbered thesis-format figures with
  their captions.
- Manual band-based validation protocol (in Spanish):
  [validación manual](docs/validacion_manual.md)
- Corrections to the proposal (in Spanish):
  [correcciones a la propuesta](docs/correcciones_propuesta.md)
- Progress report and schedule (in Spanish): [informe de avance](docs/informe_avance.md) ·
  [cronograma](docs/cronograma.md)

## Scope

Study subset: **MSL NavCam (Curiosity)**, training labels. The project does not generate
new masks, does not model the temporal evolution of the terrain, and does not use
elevation data.

## Credits

**AI4Mars** dataset — Swan, R. M., Atha, D., Leopold, H. A., Gildner, M., Oij, S.,
Chiu, C., & Ono, M. (2021). *AI4Mars: A Dataset for Terrain-Aware Autonomous Driving on
Mars.* IEEE/CVF CVPR Workshops. Imagery: NASA/JPL-Caltech.
