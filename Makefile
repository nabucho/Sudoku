PYTHON ?= python3

.PHONY: help install-dev test test-all coverage coverage-html typecheck lint format check benchmark clean

help:
	@echo "Available targets:"
	@echo "  install-dev   Install development dependencies"
	@echo "  test          Run regular automated tests"
	@echo "  test-all      Run regular and slow automated tests"
	@echo "  coverage      Run tests with terminal coverage report"
	@echo "  coverage-html Run tests with HTML coverage report"
	@echo "  typecheck     Run mypy type checking"
	@echo "  lint          Run Ruff lint checks"
	@echo "  format        Format with Ruff and Black"
	@echo "  check         Run compile, lint, typecheck, and tests"
	@echo "  benchmark     Run strategy benchmark"
	@echo "  clean         Remove generated caches and coverage output"

install-dev:
	$(PYTHON) -m pip install -r requirements-dev.txt

test:
	$(PYTHON) -m pytest -vv -s -m "not slow"

test-all:
	$(PYTHON) -m pytest -vv -s

coverage:
	$(PYTHON) -m coverage run -m pytest -vv -s -m "not slow"
	$(PYTHON) -m coverage report

coverage-html:
	$(PYTHON) -m coverage run -m pytest -vv -s -m "not slow"
	$(PYTHON) -m coverage html

typecheck:
	$(PYTHON) -m mypy sudoku_solver cli.py sudoku.py test/benchmark.py test/run_tests.py

lint:
	$(PYTHON) -m ruff check .

format:
	$(PYTHON) -m ruff check --fix .
	$(PYTHON) -m black .

check:
	PYTHONPYCACHEPREFIX=.pycache $(PYTHON) -m py_compile cli.py sudoku.py sudoku_solver/*.py sudoku_solver/techniques/*.py test/benchmark.py test/run_tests.py
	$(MAKE) lint
	$(MAKE) typecheck
	$(MAKE) test

benchmark:
	$(PYTHON) test/benchmark.py

clean:
	rm -rf .coverage htmlcov .mypy_cache .ruff_cache .pycache
	find . -type d -name __pycache__ -prune -exec rm -rf {} +
