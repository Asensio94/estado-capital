"""Indicator 1: net public investment = GFCF of general government − its consumption of fixed capital.

    net_pc_gdp = (P51G − P51C)[S13, MIO_EUR] / B1GQ[CP_MEUR] × 100

Levels are used instead of Eurostat's PC_GDP series because PC_GDP is published rounded to
one decimal: subtracting two rounded shares carries up to ±0.1 pp of error, which is the
same order as the values whose sign we care about. The published shares are kept in
`*_published` columns as a cross-check.

Every country × year from START_YEAR to the last year with data appears in the output; a row
whose inputs are incomplete has NaN results and status "missing". Nothing is interpolated.
"""

from __future__ import annotations

import pandas as pd

from core.config import COUNTRIES, START_YEAR

NAME = "Inversión pública neta"
UNIT = "% del PIB"
DEFINITION = (
    "Formación bruta de capital fijo de las administraciones públicas (S13, P51G) menos su "
    "consumo de capital fijo (P51C), en porcentaje del PIB a precios corrientes (B1GQ). "
    "Un valor ≤ 0 indica que la inversión no cubre la depreciación estimada del stock público."
)
SOURCES = {
    "gov_10a_main": "Eurostat, Government revenue, expenditure and main aggregates",
    "nama_10_gdp": "Eurostat, GDP and main components",
}
CAVEATS = (
    "El consumo de capital fijo no se mide por inspección: es una estimación del método del "
    "inventario permanente con vidas útiles y perfiles de retiro supuestos (véase METHODOLOGY.md).",
    "La UE-27 es el agregado de composición fija actual (EU27_2020) recalculado hacia atrás.",
    "Las cifras de los últimos años son provisionales y se revisan en cada notificación.",
)

KEY = ["geo", "year"]
COLUMNS = [
    "geo", "geo_name", "year",
    "gfcf_meur", "cfc_meur", "net_meur", "gdp_meur",
    "gfcf_pc_gdp", "cfc_pc_gdp", "net_pc_gdp",
    "gfcf_pc_gdp_published", "cfc_pc_gdp_published",
    "consumes_stock", "obs_flags", "status",
]


def _wide(df: pd.DataFrame, unit: str, rename: dict[str, str]) -> tuple[pd.DataFrame, pd.DataFrame]:
    sub = df[(df["unit"] == unit) & df["na_item"].isin(list(rename))]
    if sub.duplicated(["geo", "year", "na_item"]).any():
        raise ValueError(f"duplicate observations in {unit}")
    values = sub.pivot(index=KEY, columns="na_item", values="value").rename(columns=rename)
    flags = sub.dropna(subset=["flag"]).assign(flag=lambda d: d["na_item"] + ":" + d["flag"])
    return values, flags[KEY + ["flag"]]


def compute(gov: pd.DataFrame, gdp: pd.DataFrame) -> pd.DataFrame:
    """`gov`: tidy gov_10a_main (S13); `gdp`: tidy nama_10_gdp. Both with geo, year, na_item, unit, value, flag."""
    gov = gov[gov["sector"] == "S13"] if "sector" in gov else gov

    levels, f1 = _wide(gov, "MIO_EUR", {"P51G": "gfcf_meur", "P51C": "cfc_meur"})
    published, _ = _wide(gov, "PC_GDP", {"P51G": "gfcf_pc_gdp_published", "P51C": "cfc_pc_gdp_published"})
    gdp_w, f2 = _wide(gdp, "CP_MEUR", {"B1GQ": "gdp_meur"})

    last_year = int(levels.dropna(how="all").index.get_level_values("year").max())
    grid = pd.MultiIndex.from_product([list(COUNTRIES), range(START_YEAR, last_year + 1)], names=KEY)
    out = pd.DataFrame(index=grid).join([levels, gdp_w, published]).reset_index()

    for col in ("gfcf_meur", "cfc_meur", "gdp_meur", "gfcf_pc_gdp_published", "cfc_pc_gdp_published"):
        if col not in out:
            out[col] = float("nan")

    out["net_meur"] = out["gfcf_meur"] - out["cfc_meur"]
    for item in ("gfcf", "cfc", "net"):
        out[f"{item}_pc_gdp"] = out[f"{item}_meur"] / out["gdp_meur"] * 100

    complete = out[["gfcf_meur", "cfc_meur", "gdp_meur"]].notna().all(axis=1)
    out["status"] = complete.map({True: "ok", False: "missing"})
    out["consumes_stock"] = (out["net_pc_gdp"] <= 0).astype("boolean").where(complete, pd.NA)

    flags = pd.concat([f1, f2]).groupby(KEY)["flag"].agg(lambda s: ",".join(sorted(s)))
    out = out.merge(flags.rename("obs_flags"), on=KEY, how="left")
    out["geo_name"] = out["geo"].map(COUNTRIES)
    return out[COLUMNS].sort_values(KEY, ignore_index=True)
