"""Eurostat queries used by each indicator.

Codes were checked against the API's content constraints on 2026-10-21 and are re-checked on
every run (`eurostat.verify_codes`). Changes with respect to the original specification:

- GDP (B1GQ) is not in gov_10a_main, despite that dataset offering a PC_GDP unit. It comes
  from nama_10_gdp, unit CP_MEUR (current prices, million euro).
- Indicator 2 (not yet implemented): interest is D41PAY ("Interest, expenditure") in
  gov_10a_main; plain D41 does not exist in that cube.
"""

from __future__ import annotations

from core.config import COUNTRIES, START_YEAR
from etl.eurostat import Query

GEOS = tuple(COUNTRIES)

# Indicator 1: net public investment.
GOV_CAPITAL = Query(
    dataset="gov_10a_main",
    filters={
        "freq": ("A",),
        "sector": ("S13",),  # general government
        "na_item": ("P51G", "P51C"),  # gross fixed capital formation, consumption of fixed capital
        "unit": ("MIO_EUR", "PC_GDP"),  # PC_GDP is kept only as a cross-check (rounded to 0.1)
        "geo": GEOS,
    },
    since=START_YEAR,
)

GDP = Query(
    dataset="nama_10_gdp",
    filters={"freq": ("A",), "na_item": ("B1GQ",), "unit": ("CP_MEUR",), "geo": GEOS},
    since=START_YEAR,
)

INDICATOR_1 = (GOV_CAPITAL, GDP)
