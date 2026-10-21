PY ?= python
export PYTHONPATH := src

.PHONY: install etl etl-refresh test

install:
	$(PY) -m pip install -e ".[dev,s3]"

etl:
	$(PY) -m etl

etl-refresh:
	$(PY) -m etl --refresh

test:
	$(PY) -m pytest -q
