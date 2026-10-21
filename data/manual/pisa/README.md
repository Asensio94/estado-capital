# PISA: importación manual

PISA no se publica en la API SDMX de la OCDE (comprobado el 2026-10-21), así que estos datos se
descargan a mano y se guardan aquí, en el repositorio, porque no se pueden regenerar con un script.

1. Descarga las puntuaciones medias de **matemáticas** y **lectura** de todas las ediciones
   (2000–2022) para España, Francia, Alemania, Italia, Portugal, Polonia y la media de la OCDE,
   con su error típico. Fuente recomendada: el PISA Data Explorer de la OCDE o las tablas de
   tendencias de cada informe PISA.
2. Copia `pisa.template.csv` a `pisa.csv` con una fila por país, edición y materia:

   | columna   | valores                                     |
   |-----------|---------------------------------------------|
   | `geo`     | `ES`, `FR`, `DE`, `IT`, `PT`, `PL`, `OECD`  |
   | `edition` | 2000, 2003, 2006, 2009, 2012, 2015, 2018, 2022 |
   | `subject` | `math`, `reading`                           |
   | `mean`    | puntuación media publicada, sin redondear más |
   | `se`      | error típico (vacío si la fuente no lo da)   |

   No rellenes huecos: una combinación que falte debe faltar (el panel la mostrará como ausente).
3. Copia `pisa.meta.template.json` a `pisa.meta.json` y anota la **fecha de descarga** y la URL.
   El ETL se niega a cargar `pisa.csv` sin ese fichero.
4. `make etl`.
