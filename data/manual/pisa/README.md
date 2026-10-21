# PISA: datos de la OCDE

PISA no se publica en la API SDMX de la OCDE ni en el OECD Data Explorer (comprobado el
2026-10-21: ninguno de sus 1.550 dataflows es PISA). La fuente legible por máquina es el libro
Excel que el informe *PISA 2022 Results (Volume I)* enlaza con un StatLink permanente:

- <https://stat.link/wh9d4z> (anexo B1, capítulo 5)
- Tabla I.B1.5.4: matemáticas, 2003–2022
- Tabla I.B1.5.5: lectura, 2000–2022

`pisa.csv` y `pisa.meta.json` se generan con el conversor, no a mano:

```
pip install -e ".[pisa]"
python -m etl.pisa_statlink                    # descarga el libro y convierte
python -m etl.pisa_statlink libro.xlsx --downloaded-on AAAA-MM-DD   # libro bajado a mano
```

El libro queda en `data/raw/pisa/` (no se versiona); su URL, fecha y SHA-256 van al
`pisa.meta.json`. Los dos ficheros resultantes sí se versionan, porque la fuente es un Excel de
un informe y no una API.

## Formato de `pisa.csv`

| columna   | valores                                     |
|-----------|---------------------------------------------|
| `geo`     | `ES`, `FR`, `DE`, `IT`, `PT`, `PL`, `OECD` (media OCDE-23) |
| `edition` | 2000, 2003, 2006, 2009, 2012, 2015, 2018, 2022 |
| `subject` | `math`, `reading`                           |
| `mean`    | puntuación media, con la precisión del libro |
| `se`      | error típico                                |

Las celdas `m` (sin dato) no generan fila: el panel las muestra como ausentes. Faltan, por la
propia fuente, matemáticas de 2000 (la tabla de tendencias empieza en 2003) y España 2018 en
las dos materias. `pisa.template.csv` y `pisa.meta.template.json` documentan el formato por si
algún día hay que cargar otra fuente; el ETL no carga `pisa.csv` sin su `pisa.meta.json`.
