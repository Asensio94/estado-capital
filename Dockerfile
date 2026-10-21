# Dashboard + ETL in one image. Data lives outside the image: mount a volume on /app/data.
#   docker build -t estado-capital .
#   docker run --rm -v "$PWD/data:/app/data" estado-capital python -m etl   # build data
#   docker run --rm -p 8050:8050 -v "$PWD/data:/app/data" estado-capital    # serve
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app/src:/app \
    CAPITAL_DATA_DIR=/app/data

WORKDIR /app
COPY pyproject.toml README.md ./
COPY src ./src
RUN pip install --no-cache-dir ".[s3,serve]"
COPY app ./app

RUN useradd --create-home capital && mkdir -p /app/data && chown capital /app/data
USER capital

EXPOSE 8050
CMD ["gunicorn", "--bind", "0.0.0.0:8050", "--workers", "2", "app.main:server"]
