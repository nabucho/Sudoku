PYTHON ?= python3
PY_COMPILE_TARGETS = cli.py sudoku.py sudoku_solver/*.py sudoku_solver/techniques/*.py sudoku_solver/techniques/common/*.py test/benchmark.py test/run_tests.py

.PHONY: help install install-dev test test-all coverage coverage-html typecheck lint format format-check compile check check-all ci benchmark clean

help:
	@echo "Available targets:"
	@echo "  install       Install the package"
	@echo "  install-dev   Install development dependencies"
	@echo "  test          Run regular automated tests"
	@echo "  test-all      Run regular and slow automated tests"
	@echo "  coverage      Run tests with terminal coverage report"
	@echo "  coverage-html Run tests with HTML coverage report"
	@echo "  typecheck     Run mypy type checking"
	@echo "  lint          Run Ruff lint checks"
	@echo "  format        Format with Ruff"
	@echo "  format-check  Check Ruff formatting"
	@echo "  compile       Compile all Python modules"
	@echo "  check         Run compile, lint, typecheck, and regular tests"
	@echo "  check-all     Run check plus slow tests"
	@echo "  ci            Run CI checks"
	@echo "  benchmark     Run strategy benchmark"
	@echo "  clean         Remove generated caches and coverage output"

install:
	$(PYTHON) -m pip install .

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
	$(PYTHON) -m ruff format .

format-check:
	$(PYTHON) -m ruff format --check .

compile:
	PYTHONPYCACHEPREFIX=.pycache $(PYTHON) -m py_compile $(PY_COMPILE_TARGETS)

check: compile
	$(MAKE) lint
	$(MAKE) typecheck
	$(MAKE) test

check-all: check
	$(MAKE) test-all

ci: check

benchmark:
	$(PYTHON) test/benchmark.py

clean:
	rm -rf .coverage htmlcov .mypy_cache .ruff_cache .pycache
	find . -type d -name __pycache__ -prune -exec rm -rf {} +
