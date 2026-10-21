# Estado del capital

¿Mantiene un país su capital público y humano, o lo está consumiendo? Este proyecto compara
España y Francia con Alemania, Italia, Portugal, Polonia y la UE-27 desde 1995, solo con
fuentes oficiales. Un ETL reproducible descarga y verifica los datos, y un dashboard en Dash los
muestra con su definición, su fuente y sus advertencias.

- **Hallazgos:** [HALLAZGOS.md](HALLAZGOS.md)
- **Metodología y límites:** [METHODOLOGY.md](METHODOLOGY.md)

## Indicadores

| # | Indicador | Definición | Fuente |
|---|---|---|---|
| 1 | Inversión pública neta | (P51G − P51C) / PIB, sector S13. ≤ 0: la inversión no cubre la depreciación estimada | Eurostat `gov_10a_main`, `nama_10_gdp` |
| 2 | Intereses frente a educación | Intereses (D41PAY) / gasto en educación (COFOG GF09), y ambos en % del PIB | Eurostat `gov_10a_main`, `gov_10a_exp` |
| 3 | Electricidad para la industria | EUR/kWh sin IVA, banda ID desde 2007 y consumidor Ie antes; EE. UU. opcional | Eurostat `nrg_pc_205`, `ert_bil_eur_a`; EIA |
| 4 | Productividad por hora | Nivel en PPS (UE-27 = 100) e índice real (1995 = 100) | Eurostat `nama_10_lp_ulc` |
| 5 | PISA por cohortes | Media en matemáticas y lectura, por edición y año de nacimiento | OCDE (CSV manual) |

Los porcentajes del PIB se calculan desde niveles en millones de euros. Los `PC_GDP` de
Eurostat vienen redondeados a una décima y se usan solo como control (véase
[METHODOLOGY.md](METHODOLOGY.md#redondeo)).

### Cambios de código respecto a la especificación

Verificados contra la API el 21/10/2026 y comprobados de nuevo en cada ejecución:

- El PIB (B1GQ) no está en `gov_10a_main`; se toma de `nama_10_gdp` (CP_MEUR).
- D41 no existe en `gov_10a_main`; se usa `D41PAY` (intereses pagados, después de SIFMI).
- `nrg_pc_205_h` ya no existe: la serie anterior a 2007 está en `nrg_pc_205` (`nrg_cons=MWH2000`).
- Productividad: `NLPR_HW` (nivel) y `RLPR_HW` (real, 2015 = 100).

## Cómo reproducirlo

Requiere Python 3.11 o superior.

```bash
make install    # pip install -e ".[dev,s3]"
make etl        # descarga (o reutiliza la caché de menos de 20 h), verifica códigos, calcula
make test
make run        # dashboard en http://127.0.0.1:8050
```

Sin `make`, desde la raíz del repositorio (en Windows, `src;.`):

```bash
PYTHONPATH=src:. python -m etl
PYTHONPATH=src:. python -m app
python -m pytest
```

Opciones del ETL: `--refresh` ignora la caché, `--no-verify` salta la comprobación de códigos
(no recomendado), `--s3` sube el resultado a S3.

### Docker

La imagen contiene el código; los datos se montan como volumen en `/app/data`.

```bash
make docker-build
make docker-etl     # construye data/ desde el contenedor
make docker-run     # dashboard con gunicorn en http://localhost:8050
```

### Variables de entorno

| Variable | Uso |
|---|---|
| `CAPITAL_DATA_DIR` | carpeta de datos (por defecto, `data/`) |
| `EIA_API_KEY` | clave de la API de la EIA; sin ella se usa `DEMO_KEY`, con un límite bajo de peticiones |
| `CAPITAL_S3_BUCKET`, `CAPITAL_S3_PREFIX` | destino de `--s3` (prefijo por defecto: `estado-capital/processed`) |
| `HOST`, `PORT` | dirección del dashboard en `python -m app` |

Las credenciales de AWS no se guardan en el código: `boto3` usa su cadena estándar (variables de
entorno, perfil o rol).

### PISA

PISA no se publica en ninguna API. Hay que descargar el CSV del OECD Data Explorer y guardarlo
en `data/manual/pisa/` junto con un `pisa.meta.json` con la fecha de descarga y la URL. El formato
está en [data/manual/pisa/README.md](data/manual/pisa/README.md). Sin esos ficheros el indicador
aparece como ausente.

## Qué se guarda

- `data/raw/eurostat/<dataset>/<hash de la consulta>/<UTC>.json` (y `data/raw/eia/…`): respuesta íntegra de la API,
  con un `.meta.json` (URL, fecha de extracción y fecha de actualización de la fuente). Si una
  descarga falla, el ETL usa la última copia y lo avisa.
- `data/processed/<indicador>.parquet`: una fila por país y periodo, siempre la rejilla completa,
  con `obs_flags` (flags de Eurostat) y `status` (`ok`, `partial` o `missing`).
- `data/processed/manifest.json`: fecha de construcción, fuentes con sus fechas y filas por
  estado.

`data/raw` y `data/processed` no se versionan; `data/manual` sí.

## Estructura

```
src/core/         configuración (países, periodo, rutas) y almacenamiento (parquet, manifest, S3)
src/etl/          un módulo por fuente: eurostat, eia, pisa; catalog (consultas); run (orquestación)
src/etl/phase2.py fuentes previstas y aún no implementadas
src/indicators/   un módulo por indicador: compute() y META (definición, fuentes, advertencias)
app/              dashboard en Dash: una página por indicador, síntesis y metodología
tests/            identidad contable, unidades, duplicados, parseo y datos procesados
```

## Tests

`make test` ejecuta tests sintéticos (sin red) y, si existe `data/processed`, tests sobre los
datos reales (marcador `data`): rejilla completa sin duplicados por país y periodo, identidad
neta = bruta − consumo de capital fijo, coincidencia con los `PC_GDP` publicados dentro del
redondeo, rangos plausibles y filas ausentes sin valores.

## Limitaciones

- El consumo de capital fijo es una estimación del inventario permanente con vidas útiles
  supuestas, no una medida física del desgaste. No capta el mantenimiento diferido.
- El perímetro de S13 difiere entre países (empresas públicas, concesiones).
- Las cifras recientes son provisionales y se revisan en cada notificación.
- Los precios de la electricidad de antes y después de 2007 no son comparables; el dato de EE. UU.
  no es homogéneo con el europeo.
- Los niveles de productividad en PPS no deben leerse como serie temporal.

El detalle está en [METHODOLOGY.md](METHODOLOGY.md).

## Fase 2 (pendiente)

Estructura preparada en `src/etl/phase2.py`, sin implementar: stock de capital por activo
(Fundación BBVA-Ivie, INSEE), seguridad ferroviaria (`tran_sf_railac`, ERA), informes de Adif
y SNCF Réseau, e inventarios de puentes y presas donde existan.

## Licencia de los datos

Eurostat: reutilización libre con cita de la fuente. EIA: dominio público. OCDE (PISA): según
los términos de la OCDE.
