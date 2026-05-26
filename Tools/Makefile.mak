.ONESHELL:
install:
	python -m venv .venv && . .venv/bin/activate && pip install -U pip
	. .venv/bin/activate && pip install -e ".[dev]"

fmt:
	. .venv/bin/activate && black src tests

lint:
	. .venv/bin/activate && ruff check .

type:
	. .venv/bin/activate && mypy src

test:
	. .venv/bin/activate && pytest -q --maxfail=1 --disable-warnings --cov=src --cov-report=term-missing

ci: fmt lint type test
