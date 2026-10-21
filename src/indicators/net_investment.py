"""Indicator 1: net public investment = GFCF of general government − its consumption of fixed capital.

    net_pc_gdp = (P51G − P51C)[S13, MIO_EUR] / B1GQ[CP_MEUR] × 100

Levels are used instead of Eurostat's PC_GDP series because PC_GDP is published rounded to
one decimal: subtracting two rounded shares carries up to ±0.1 pp of error, which is the
same order as the values whose sign we care about. The published shares are kept in
`*_published` columns as a cross-check.

Every country × year from START_YEAR to the last year with data appears in the output; a row
whose inputs are incomplete has NaN results and status "partial" or "missing". Nothing is
interpolated.
"""

from __future__ import annotations

import pandas as pd

from core.config import COUNTRIES
from etl.eurostat import BROWSER_URL
from indicators.common import KEY, Meta, Source, annual_grid, join_flags, last_year, status, wide

META = Meta(
    key="net_investment",
    name="Inversión pública neta",
    unit="% del PIB",
    definition=(
        "Formación bruta de capital fijo de las administraciones públicas (S13, P51G) menos su "
        "consumo de capital fijo (P51C), en porcentaje del PIB a precios corrientes (B1GQ). "
        "Un valor ≤ 0 indica que la inversión no cubre la depreciación estimada del stock público."
    ),
    sources=(
        Source("Eurostat, gov_10a_main", BROWSER_URL.format(dataset="gov_10a_main"), "gov_10a_main"),
        Source("Eurostat, nama_10_gdp", BROWSER_URL.format(dataset="nama_10_gdp"), "nama_10_gdp"),
    ),
    caveats=(
        "El consumo de capital fijo no se mide por inspección: es una estimación del método del "
        "inventario permanente con vidas útiles y perfiles de retiro supuestos (véase METHODOLOGY.md).",
        "Valores entre −0,1 y +0,1 pp no permiten afirmar el signo: el margen de error del consumo "
        "de capital fijo es mayor que eso.",
        "La UE-27 es el agregado de composición fija actual (EU27_2020) recalculado hacia atrás.",
        "Las cifras de los últimos años son provisionales y se revisan en cada notificación.",
    ),
)

COLUMNS = [
    "geo", "geo_name", "year",
    "gfcf_meur", "cfc_meur", "net_meur", "gdp_meur",
    "gfcf_pc_gdp", "cfc_pc_gdp", "net_pc_gdp",
    "gfcf_pc_gdp_published", "cfc_pc_gdp_published",
    "consumes_stock", "obs_flags", "status",
]


def compute(gov: pd.DataFrame, gdp: pd.DataFrame) -> pd.DataFrame:
    """`gov`: tidy gov_10a_main; `gdp`: tidy nama_10_gdp. Both with geo, year, na_item, unit, value, flag."""
    gov = gov[gov["sector"] == "S13"] if "sector" in gov else gov

    levels, f1 = wide(gov, "MIO_EUR", {"P51G": "gfcf_meur", "P51C": "cfc_meur"})
    published, _ = wide(gov, "PC_GDP", {"P51G": "gfcf_pc_gdp_published", "P51C": "cfc_pc_gdp_published"})
    gdp_w, f2 = wide(gdp, "CP_MEUR", {"B1GQ": "gdp_meur"})

    out = annual_grid(last_year(levels)).join([levels, gdp_w, published]).reset_index()
    out["net_meur"] = out["gfcf_meur"] - out["cfc_meur"]
    for item in ("gfcf", "cfc", "net"):
        out[f"{item}_pc_gdp"] = out[f"{item}_meur"] / out["gdp_meur"] * 100

    out["status"] = status(out, ["gfcf_meur", "cfc_meur", "gdp_meur"])
    complete = out["status"] == "ok"
    out["consumes_stock"] = (out["net_pc_gdp"] <= 0).astype("boolean").where(complete, pd.NA)

    out = join_flags(out, f1, f2)
    out["geo_name"] = out["geo"].map(COUNTRIES)
    return out[COLUMNS].sort_values(KEY, ignore_index=True)
