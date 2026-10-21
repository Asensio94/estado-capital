"""Eurostat queries used by the indicators.

Codes were checked against the API's content constraints on 2026-10-21 and are re-checked on
every run (`eurostat.verify_codes`). Changes with respect to the original specification:

- GDP (B1GQ) is not in gov_10a_main, despite that dataset offering a PC_GDP unit. It comes
  from nama_10_gdp, unit CP_MEUR (current prices, million euro).
- Interest: plain D41 does not exist in gov_10a_main; the series is D41PAY ("Interest,
  expenditure", after FISIM allocation).
- nrg_pc_205 now holds the pre-2007 "standard consumer" series as well (the former
  nrg_pc_205_h no longer exists): consumer Ie is nrg_cons=MWH2000, band ID is MWH2000-19999.
- Productivity per hour: NLPR_HW (nominal, PPS, % of EU-27) and RLPR_HW (real, I15).
"""

from __future__ import annotations

from core.config import COUNTRIES, START_YEAR
from etl.eurostat import Query

GEOS = tuple(COUNTRIES)

GOV_MAIN = Query(
    dataset="gov_10a_main",
    filters={
        "freq": ("A",),
        "sector": ("S13",),  # general government
        # P51G gross fixed capital formation, P51C consumption of fixed capital, D41PAY interest
        "na_item": ("P51G", "P51C", "D41PAY"),
        "unit": ("MIO_EUR", "PC_GDP"),  # PC_GDP is kept only as a cross-check (rounded to 0.1)
        "geo": GEOS,
    },
    since=START_YEAR,
)

GOV_COFOG = Query(
    dataset="gov_10a_exp",
    filters={
        "freq": ("A",),
        "sector": ("S13",),
        "cofog99": ("GF09",),  # education
        "na_item": ("TE",),  # total expenditure
        "unit": ("MIO_EUR", "PC_GDP"),
        "geo": GEOS,
    },
    since=START_YEAR,
)

GDP = Query(
    dataset="nama_10_gdp",
    filters={"freq": ("A",), "na_item": ("B1GQ",), "unit": ("CP_MEUR",), "geo": GEOS},
    since=START_YEAR,
)

ELECTRICITY = Query(
    dataset="nrg_pc_205",
    filters={
        "freq": ("S",),
        "siec": ("E7000",),  # electricity
        "nrg_cons": ("MWH2000-19999", "MWH2000"),
        "unit": ("KWH",),
        "tax": ("X_VAT",),  # excluding VAT and other recoverable taxes
        "currency": ("EUR",),
        "geo": GEOS,
    },
    since=START_YEAR,
)

EUR_USD = Query(
    dataset="ert_bil_eur_a",
    filters={"freq": ("A",), "statinfo": ("AVG",), "unit": ("NAC",), "currency": ("USD",)},
    since=START_YEAR,
)

PRODUCTIVITY = Query(
    dataset="nama_10_lp_ulc",
    filters={
        "freq": ("A",),
        "na_item": ("NLPR_HW", "RLPR_HW"),
        "unit": ("PC_EU27_2020_MPPS_CP", "I15"),
        "geo": GEOS,
    },
    since=START_YEAR,
)

ALL = (GOV_MAIN, GOV_COFOG, GDP, ELECTRICITY, EUR_USD, PRODUCTIVITY)
