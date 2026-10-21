"""Indicator 5: PISA mean scores in mathematics and reading, by edition and birth cohort.

PISA tests 15-year-olds, so edition E describes roughly the cohort born in E − 15. The
reference aggregate is the OECD average (PISA has no EU-27 figure).
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
        "antes. Referencia: media de la OCDE."
    ),
    sources=(Source("OCDE, PISA (importación manual de CSV)", "https://www.oecd.org/en/about/programmes/pisa.html", "pisa"),),
    caveats=(
        "Las tendencias de matemáticas solo son comparables desde 2003 y las de lectura desde "
        "2000; el punto de matemáticas de 2000 se muestra sin unir a la serie.",
        "La edición de 2022 se aplazó un año por la pandemia y recoge sus efectos sobre la escolarización.",
        "La media de la OCDE cambia de composición entre ediciones según los países participantes.",
        "Diferencias de pocos puntos no son significativas: el error típico de cada media ronda "
        "2–4 puntos.",
    ),
)

GEO_NAMES = {"ES": "España", "FR": "Francia", "DE": "Alemania", "IT": "Italia", "PT": "Portugal", "PL": "Polonia", "OECD": "Media OCDE"}
COLUMNS = ["geo", "geo_name", "edition", "cohort", "subject", "mean", "se", "trend_comparable", "status"]


def compute(scores: pd.DataFrame) -> pd.DataFrame:
    grid = pd.MultiIndex.from_product([source.GEOS, source.EDITIONS, source.SUBJECTS], names=["geo", "edition", "subject"])
    out = scores.set_index(["geo", "edition", "subject"])[["mean", "se"]].reindex(grid).reset_index()
    out["cohort"] = out["edition"] - 15
    out["trend_comparable"] = ~((out["subject"] == "math") & (out["edition"] < 2003))
    out["status"] = out["mean"].notna().map({True: "ok", False: "missing"})
    out["geo_name"] = out["geo"].map(GEO_NAMES)
    return out[COLUMNS]
