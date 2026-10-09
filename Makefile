# Reproducción completa de la tesis, en orden.
#
#   make todo         todo: resultados, modelo, evaluaciones, figuras, cifras y documento
#   make resultados   todo salvo reentrenar el segmentador (usa el modelo ya entrenado)
#   make pruebas      pruebas unitarias de las reglas deterministas
#
# Requisitos: entorno de environment.yml y el conjunto AI4Mars en AI4MARS_ROOT
# (ver README). El modelo entrenado (~170 MB) se descarga de la versión publicada
# modelo-deeplab-v2 del repositorio; su SHA-256 queda en outputs/segmentacion_metricas.json.

PY ?= python
GOLD = $(shell $(PY) -c "import sys; sys.path.insert(0,'.'); from src import config; print(config.MSL_NCAM_LABELS_TRAIN.parent / 'test')")

.PHONY: todo resultados pruebas pipeline calibracion analisis validacion modelo \
        evaluacion-modelo comparaciones priorizacion figuras cifras bibliografia tesis

todo: pruebas pipeline calibracion analisis validacion modelo evaluacion-modelo \
      comparaciones priorizacion figuras cifras tesis

resultados: pruebas pipeline calibracion analisis validacion evaluacion-modelo \
            comparaciones priorizacion figuras cifras tesis

pruebas:
	$(PY) -m pytest tests/ -q

# 1. Indicadores por imagen (E1, E2) sobre las máscaras colaborativas y las de experto.
pipeline:
	$(PY) scripts/run_pipeline.py --no-progress
	for k in 1 2 3; do \
	  $(PY) scripts/run_pipeline.py --no-progress --labels "$(GOLD)/masked-gold-min$$k-100agree" \
	    --out outputs/results_test_masked-gold-min$$k-100agree.csv || exit 1; \
	done

# 2. Calibración del conteo y sensibilidad de sus parámetros.
calibracion:
	$(PY) scripts/calibracion.py
	$(PY) scripts/sensibilidad_parametros.py

# 3. Dependencia entre indicadores y control del denominador.
analisis:
	$(PY) scripts/analisis_dependencia.py
	$(PY) scripts/consenso_experto.py

# 4. Validación con conteo humano (ronda piloto y definitiva) y relieves de imagen.
validacion:
	$(PY) scripts/eval_validation.py --dir outputs/validacion_manual
	$(PY) scripts/eval_validation.py --dir outputs/validacion_manual_v2
	$(PY) scripts/eval_metodos_imagen.py

# 5. Segmentador DeepLabV3 (reparto por bloques temporales; ~2 h en Apple M4 Pro).
modelo:
	$(PY) scripts/train_segmentation.py

# 6. Evaluaciones que dependen del modelo.
evaluacion-modelo:
	$(PY) scripts/eval_model_expert.py --nivel 1
	$(PY) scripts/eval_fuga_temporal.py
	$(PY) scripts/eval_fuente_anotacion.py --muestra general
	$(PY) scripts/eval_fuente_anotacion.py --muestra prueba
	$(PY) scripts/eval_modelo_detalle.py
	$(PY) scripts/sensibilidad_dependencia_temporal.py

# 7. Comparación con el modelo fundacional y exploración de vetas.
comparaciones:
	$(PY) scripts/compare_sam.py --n 50
	$(PY) scripts/scan_geology.py
	$(PY) scripts/explore_vein_detection.py

# 8. Reglas heurísticas de priorización.
priorizacion:
	$(PY) scripts/run_priorizacion.py
	$(PY) scripts/make_dashboard.py

# 9. Figuras del documento (se copian a tesis/images/).
figuras:
	$(PY) scripts/make_thesis_figures.py
	$(PY) scripts/make_mechanism_figure.py
	$(PY) scripts/make_extension_figures.py
	$(PY) scripts/make_hybrid_figure.py
	$(PY) scripts/diagnose_errors.py
	cp outputs/figures/tesis/*.png tesis/images/
	for f in bedrock_no_contado artefacto_anotacion bajo_umbral_area filtro_aspecto sobresegmentacion; do \
	  cp outputs/figures/diagnostico/$$f.png tesis/images/diag_$$f.png || exit 1; \
	done

# 10. Todas las cifras del documento, desde outputs/ (tesis/cifras.tex y tablas generadas).
cifras:
	$(PY) scripts/generar_cifras.py

# Bibliografía desde Crossref/DataCite (requiere conexión; no forma parte de "todo").
bibliografia:
	$(PY) scripts/generar_bibliografia.py

# 11. Documento, en APA 7. El biblatex 3.17 de tectonic exige Biber 2.17 (por ejemplo, el de
# TeX Live 2021: archive/biber.universal-darwin.tar.xz); BIBER_DIR apunta a su carpeta bin.
BIBER_DIR ?=
tesis:
	cd tesis && PATH="$(BIBER_DIR):$$PATH" tectonic -X compile main.tex
