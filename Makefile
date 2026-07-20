PYTHON = python
MAP ?= maps/example.map

.PHONY: install run debug clean lint lint-strict test

install:
	$(PYTHON) -m pip install flake8 mypy pytest

run:
	$(PYTHON) main.py $(MAP)

debug:
	$(PYTHON) -m pdb main.py $(MAP)

clean:
	$(PYTHON) -c "from pathlib import Path; import shutil; [shutil.rmtree(path, ignore_errors=True) for path in Path('.').rglob('__pycache__')]; [shutil.rmtree(path, ignore_errors=True) for path in (Path('.mypy_cache'), Path('.pytest_cache'))]"

lint:
	flake8 .
	mypy . --warn-return-any --warn-unused-ignores --ignore-missing-imports --disallow-untyped-defs --check-untyped-defs

lint-strict:
	flake8 .
	mypy . --strict

test:
	$(PYTHON) -m unittest discover -s tests -v
