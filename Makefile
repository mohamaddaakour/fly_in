PYTHON = python
MAP ?= maps/example.map

.PHONY: install run debug clean lint lint-strict

install:
	$(PYTHON) -m pip install flake8 mypy pytest

run:
	$(PYTHON) main.py $(MAP)

debug:
	$(PYTHON) -m pdb main.py $(MAP)

clean:
	$(PYTHON) -c "import shutil; [shutil.rmtree(path, ignore_errors=True) for path in ('__pycache__', '.mypy_cache', '.pytest_cache', 'fly_in/__pycache__')]"

lint:
	flake8 .
	mypy . --warn-return-any --warn-unused-ignores --ignore-missing-imports --disallow-untyped-defs --check-untyped-defs

lint-strict:
	flake8 .
	mypy . --strict
