# Estado del capital

¿Mantiene un país sus stocks de capital público o se los está comiendo? Este proyecto compara
España y Francia con Alemania, Italia, Portugal, Polonia y la UE-27 desde 1995, solo con
fuentes oficiales.

> En construcción. Fase 1 hecha: ETL del indicador 1 (inversión pública neta) y sus tests.

## Indicador 1: inversión pública neta (% del PIB)

Formación bruta de capital fijo de las administraciones públicas (`gov_10a_main`, S13, P51G)
menos su consumo de capital fijo (P51C), dividida por el PIB a precios corrientes
(`nama_10_gdp`, B1GQ, CP_MEUR). Si es ≤ 0, la inversión no cubre la depreciación estimada.

Se calcula desde niveles en millones de euros, no restando los `PC_GDP` de Eurostat, porque
estos vienen redondeados a una décima y el error (±0,1 pp) es del orden de los valores cuyo
signo importa. Los `PC_GDP` publicados se conservan como control.

## Cómo reproducirlo

```bash
make install
make etl      # descarga (o reutiliza la caché del día), verifica códigos y escribe data/processed
make test
```

Sin `make`: `PYTHONPATH=src python -m etl` y `python -m pytest`.

- `data/raw/eurostat/<dataset>/<hash de la consulta>/<UTC>.json`: respuesta íntegra de la API,
  con un `.meta.json` (URL, fecha de extracción, fecha de actualización de Eurostat).
- `data/processed/*.parquet` y `manifest.json`.
- `python -m etl --s3` sube `data/processed` a `s3://$CAPITAL_S3_BUCKET/$CAPITAL_S3_PREFIX`
  con las credenciales estándar de AWS.
