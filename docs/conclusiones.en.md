# Abstract and conclusions

**🌐 Language:** [Español](conclusiones.md) · **English**

> Draft of the abstract and the conclusions chapter. The abstract goes at the beginning of
> the document; the conclusions, after the discussion.

---

## Abstract

The abundance and organisation of rocks on the Martian surface condition the safety of
exploration vehicles and inform the interpretation of geological processes. Studies that
quantify them usually rely on manual counts or on procedures tailored to a single image
set, whereas pixel-annotated datasets such as AI4Mars are used almost exclusively to train
segmentation models and rarely as a direct source of measurements.

This work proposes and documents a reproducible procedure that reads those annotations as
quantitative maps and derives, for each image, two indicators: visible rock coverage and an
approximate count of individual rocks. The former is obtained by pixel counting; the latter
combines connected components, distance transform and watershed, with prominence-based
suppression of maxima and size and shape filters. All thresholds are explicit and
documented.

The procedure was applied to the 16,064 images from the Curiosity rover's navigation camera
that have annotations. Of these, 67% contain visible rock and 14% contain big rock eligible
for counting, with a total of 4,204 rocks and a decreasing size distribution. The two
indicators proved statistically independent, confirming that they describe different
aspects of the terrain. Contrast with the expert annotations included in the dataset
revealed that crowdsourced annotations systematically overestimate the proportion of rock,
a bias that affects the interpretation of coverage and is reported as the main limitation.
As a future line of work, a segmenter trained on the annotations themselves was shown to
reproduce the coverage indicator from the image alone, with a correlation of 0.95.

**Keywords:** Mars, AI4Mars, terrain segmentation, rock abundance, watershed, image
processing, reproducible indicators.

---

## Conclusions

### 1. On the research question

The work asked how to quantify, from the AI4Mars annotations, visible rock coverage and the
approximate number of rocks per image through a workflow with explicit parameters and
reproducible results. The answer is affirmative and documented: the procedure was defined,
implemented, calibrated and executed over the entire study subset, producing a table with
twenty-four indicators per image together with the record of versions and parameters that
allows the analysis to be repeated.

The scope of that answer deserves precision. Coverage is obtained for all 16,064 images;
counting, by contrast, is only meaningful for the 2,193 that contain the big-rock class.
The procedure delivers what it set out to do, but one of its two indicators applies to a
reduced subset because of a dataset characteristic that was not foreseeable when the study
was designed.

### 2. On the specific objectives

The first four objectives were met. Visible rock coverage (E1) was estimated for every
image with a valid annotation; rock counting (E2) was implemented with the intended
techniques and calibrated while documenting the effect of each parameter; the descriptive
exploration (E3) was carried out by terrain composition, scene typology and variation along
the traverse; and the reproducible resources (E4) were delivered as modular code, execution
scripts, version records and a results table.

The fifth objective — interpretation and future lines of work (E5) — was addressed by
identifying patterns, atypical cases and limitations, and by exploring, in a bounded way,
the machine-learning avenue that the statement of the problem itself anticipated.

### 3. On the findings

**Class encoding must be verified against the data.** The initial assumption about the
annotation values proved incorrect, and only direct verification — against the dataset
documentation and pixel by pixel — brought it to light. Had it been kept, every result
would have been wrong without anything in the execution revealing it. This is a
methodological lesson applicable to any work that reuses third-party datasets.

**Annotation quality limits the indicator more than the algorithm does.** The
furthest-reaching finding comes not from the procedure but from the data: crowdsourced
annotations preferentially label rock and leave part of the soil and sand unlabelled, which
raises the computed coverage. The median goes from 96.8% with crowdsourced annotations to
46.1% with expert ones. The computation is correct in both cases; what changes is the
input. The reported coverages must therefore be read as relative to the crowdsourced set
and valid for comparing scenes with each other, not as absolute estimates of rock
abundance.

**The two indicators are not redundant.** Their correlation is practically null: a scene may
be covered by continuous bedrock and contain no countable rock, or show little coverage and
several isolated blocks. How much rock there is and how it is organised are different
questions, and describing the terrain requires both.

**Oversegmentation admits a targeted solution.** The subdivision of continuous outcrops,
anticipated as a risk in the methodology, was confirmed and corrected through
prominence-based suppression of maxima. Verification showed the correction to be selective:
it reduces the count by between 32% and 44% in scenes flagged as suspicious and alters none
of the correct ones. Adjusting only the geometric parameters would not have achieved this,
because it displaces the problem instead of solving it.

**The size distribution reproduces the expected shape.** The predominance of small rocks and
the decreasing frequency with increasing size agree qualitatively with the distributions
described in the rock-abundance literature, which is an indication of the procedure's
validity, although sizes are relative to the field of view and not metric magnitudes.

### 4. On the contribution

The contribution lies not in a new technique — all those employed are well established —
but in the bridge it builds between existing annotations and quantitative indicators, with
decisions and thresholds documented so that the analysis can be repeated, discussed and
adapted. To this are added three results of independent value: the correction of the class
encoding, the characterisation of the crowdsourced annotation bias, and the verification
that a model trained on those same annotations reproduces the coverage indicator from the
image.

### 5. On the implications

For route planning, having two independent indicators per image distinguishes situations
that a single number conflates: a continuous outcrop and a field of loose blocks pose
different risks to the vehicle and are described here in differentiated terms. For the reuse
of annotated datasets, the work shows that such annotations admit a direct quantitative
reading, but that this reading inherits the biases of whoever annotated, something worth
characterising before drawing substantive conclusions.

### 6. On what remains open

The study does not allow a statement about the absolute rock abundance along the analysed
traverse, because the input annotation is biased and sizes are not metric. Nor can it be
extrapolated to other missions or cameras without repeating the analysis. The most promising
avenues to continue are correcting the bias by exploiting the expert subset, converting to
metric magnitudes by incorporating the dataset's own range products, and extending the
learned approach to counting, which here was only verified for coverage.
