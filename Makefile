PY ?= python
ifeq ($(OS),Windows_NT)
  SEP := ;
else
  SEP := :
endif
export PYTHONPATH := src$(SEP).
IMAGE ?= estado-capital
DATA ?= $(CURDIR)/data

.PHONY: install etl etl-refresh run test docker-build docker-etl docker-run

install:
	$(PY) -m pip install -e ".[dev,s3]"

etl:
	$(PY) -m etl

etl-refresh:
	$(PY) -m etl --refresh

run:
	$(PY) -m app

test:
	$(PY) -m pytest -q

docker-build:
	docker build -t $(IMAGE) .

docker-etl:
	docker run --rm -v "$(DATA):/app/data" $(IMAGE) python -m etl

docker-run:
	docker run --rm -p 8050:8050 -v "$(DATA):/app/data" $(IMAGE)
