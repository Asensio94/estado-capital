"""Indicator 2: interest paid by general government vs. its spending on education.

    interest_pc_gdp  = D41PAY[S13, MIO_EUR] / B1GQ × 100           (gov_10a_main)
    education_pc_gdp = TE[S13, COFOG GF09, MIO_EUR] / B1GQ × 100    (gov_10a_exp)
    interest_to_education = D41PAY / TE[GF09]

As in indicator 1, shares are computed from levels; Eurostat's rounded PC_GDP is kept as a
cross-check. Each series keeps its own coverage: COFOG data end a year earlier than the main
aggregates and the EU-27 COFOG series starts in 2010, so those cells stay empty.
"""

from __future__ import annotations

import pandas as pd

from core.config import COUNTRIES
from etl.eurostat import BROWSER_URL
from indicators.common import KEY, Meta, Source, annual_grid, join_flags, last_year, status, wide

META = Meta(
    key="interest_education",
    name="Intereses frente a educación",
    unit="% del PIB",
    definition=(
        "Intereses pagados por las administraciones públicas (S13, D41PAY, después de SIFMI) frente a "
        "su gasto total en la función educación de la clasificación COFOG (GF09, TE), ambos en "
        "porcentaje del PIB. El cociente indica cuántos euros de intereses se pagan por cada euro "
        "de gasto educativo."
    ),
    sources=(
        Source("Eurostat, gov_10a_main", BROWSER_URL.format(dataset="gov_10a_main"), "gov_10a_main"),
        Source("Eurostat, gov_10a_exp (COFOG)", BROWSER_URL.format(dataset="gov_10a_exp"), "gov_10a_exp"),
        Source("Eurostat, nama_10_gdp", BROWSER_URL.format(dataset="nama_10_gdp"), "nama_10_gdp"),
    ),
    caveats=(
        "El gasto en educación es gasto corriente y de capital de todas las administraciones; no "
        "mide resultados ni distingue la inversión en capital humano del resto.",
        "Los intereses dependen del tipo de interés además del volumen de deuda: una bajada de "
        "tipos reduce la carga sin que cambie la deuda.",
        "La serie COFOG de la UE-27 empieza en 2010 y la última publicación COFOG va un año por "
        "detrás de los agregados principales.",
    ),
)

COLUMNS = [
    "geo", "geo_name", "year",
    "interest_meur", "education_meur", "gdp_meur",
    "interest_pc_gdp", "education_pc_gdp", "interest_to_education",
    "interest_pc_gdp_published", "education_pc_gdp_published",
    "obs_flags", "status",
]


def compute(gov: pd.DataFrame, cofog: pd.DataFrame, gdp: pd.DataFrame) -> pd.DataFrame:
    """`gov`: tidy gov_10a_main; `cofog`: tidy gov_10a_exp; `gdp`: tidy nama_10_gdp."""
    gov = gov[gov["sector"] == "S13"]
    cofog = cofog[(cofog["sector"] == "S13") & (cofog["cofog99"] == "GF09")]

    interest, f1 = wide(gov, "MIO_EUR", {"D41PAY": "interest_meur"})
    interest_pub, _ = wide(gov, "PC_GDP", {"D41PAY": "interest_pc_gdp_published"})
    education, f2 = wide(cofog, "MIO_EUR", {"TE": "education_meur"})
    education_pub, _ = wide(cofog, "PC_GDP", {"TE": "education_pc_gdp_published"})
    gdp_w, f3 = wide(gdp, "CP_MEUR", {"B1GQ": "gdp_meur"})

    grid = annual_grid(last_year(interest, education))
    out = grid.join([interest, education, gdp_w, interest_pub, education_pub]).reset_index()
    out["interest_pc_gdp"] = out["interest_meur"] / out["gdp_meur"] * 100
    out["education_pc_gdp"] = out["education_meur"] / out["gdp_meur"] * 100
    out["interest_to_education"] = out["interest_meur"] / out["education_meur"]
    out["status"] = status(out, ["interest_meur", "education_meur", "gdp_meur"])

    out = join_flags(out, f1, f2.assign(flag="GF09_" + f2["flag"]), f3)
    out["geo_name"] = out["geo"].map(COUNTRIES)
    return out[COLUMNS].sort_values(KEY, ignore_index=True)
