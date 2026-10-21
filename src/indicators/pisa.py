"""Indicator 5: PISA mean scores in mathematics and reading, by edition and birth cohort.

PISA tests 15-year-olds, so edition E describes roughly the cohort born in E − 15. The
reference aggregate is the OECD average-23, a fixed set of countries comparable across every
cycle (PISA has no EU-27 figure).
"""

from __future__ import annotations

import pandas as pd

from etl import pisa as source
from indicators.common import Meta, Source

META = Meta(
    key="pisa",
    name="Rendimiento educativo (PISA)",
    unit="puntos PISA",
    definition=(
        "Puntuación media de los alumnos de 15 años en matemáticas y en lectura en cada edición "
        "de PISA (OCDE). Cada edición corresponde aproximadamente a la cohorte nacida 15 años "
        "antes. Referencia: media OCDE-23, los 23 países de la OCDE comparables en todas las "
        "ediciones de 2000 a 2022."
    ),
    sources=(Source("OCDE, PISA 2022 Results (Volume I), anexo B1, tablas I.B1.5.4 y I.B1.5.5",
                    "https://stat.link/wh9d4z", "pisa"),),
    caveats=(
        "Las tendencias de matemáticas solo son comparables desde 2003 y las de lectura desde "
        "2000; la tabla de tendencias de la OCDE no incluye matemáticas de 2000.",
        "España no tiene dato de 2018: la OCDE retuvo sus resultados de lectura de esa edición y "
        "las tablas de tendencias de 2022 tampoco recogen los de matemáticas.",
        "La edición de 2022 se aplazó un año por la pandemia y recoge sus efectos sobre la escolarización.",
        "La media OCDE-23 tiene composición fija, así que su evolución no se mezcla con la entrada "
        "de países nuevos; no coincide con la «media OCDE» de cada informe.",
        "Diferencias de pocos puntos no son significativas: el error típico de cada media ronda "
        "2–4 puntos.",
    ),
)

GEO_NAMES = {"ES": "España", "FR": "Francia", "DE": "Alemania", "IT": "Italia", "PT": "Portugal", "PL": "Polonia", "OECD": "Media OCDE-23"}
COLUMNS = ["geo", "geo_name", "edition", "cohort", "subject", "mean", "se", "trend_comparable", "status"]


def compute(scores: pd.DataFrame) -> pd.DataFrame:
    grid = pd.MultiIndex.from_product([source.GEOS, source.EDITIONS, source.SUBJECTS], names=["geo", "edition", "subject"])
    out = scores.set_index(["geo", "edition", "subject"])[["mean", "se"]].reindex(grid).reset_index()
    out["cohort"] = out["edition"] - 15
    out["trend_comparable"] = ~((out["subject"] == "math") & (out["edition"] < 2003))
    out["status"] = out["mean"].notna().map({True: "ok", False: "missing"})
    out["geo_name"] = out["geo"].map(GEO_NAMES)
    return out[COLUMNS]
