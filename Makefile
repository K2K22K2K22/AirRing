PYTHON ?= python3
PIO ?= pio

.PHONY: test simulate firmware upload

test:
	PYTHONPATH=desktop/src $(PYTHON) -m pytest -q desktop/tests
	$(PYTHON) -m compileall -q desktop/src desktop/tools

simulate:
	PYTHONPATH=desktop/src $(PYTHON) desktop/tools/simulate_controller.py

firmware:
	cd firmware/airring && $(PIO) run

upload:
	cd firmware/airring && $(PIO) run -t upload
