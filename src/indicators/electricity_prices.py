"""Indicator 3: electricity price for industry (EUR/kWh, excluding VAT and recoverable taxes).

Two Eurostat methodologies coexist in nrg_pc_205 and are kept as separate series, never spliced:
- until 2007: "standard consumer" Ie (2 GWh/year, 500 kW, 4 000 h), nrg_cons=MWH2000;
- from 2007: consumption band ID (2–20 GWh/year), nrg_cons=MWH2000-19999.

Optional US comparison: EIA annual average industrial price (cents of USD per kWh) converted
to euro with Eurostat's annual average EUR/USD rate (ert_bil_eur_a; ECU before 1999).
Semesters are plotted at their midpoint and US years at mid-year; nothing is averaged.
"""

from __future__ import annotations

import pandas as pd

from core.config import COUNTRIES, START_YEAR
from etl import eia
from etl.eurostat import BROWSER_URL
from indicators.common import Meta, Source

META = Meta(
    key="electricity_prices",
    name="Precio de la electricidad para la industria",
    unit="EUR/kWh",
    definition=(
        "Precio medio de la electricidad para consumidores no domésticos de la banda ID "
        "(2 000–19 999 MWh al año), sin IVA ni otros impuestos recuperables, en euros por kWh y "
        "por semestre. Antes de 2007 se muestra el consumidor tipo Ie (2 000 MWh al año), de "
        "metodología distinta. Estados Unidos: precio medio industrial anual de la EIA convertido "
        "a euros con el tipo de cambio medio anual."
    ),
    sources=(
        Source("Eurostat, nrg_pc_205", BROWSER_URL.format(dataset="nrg_pc_205"), "nrg_pc_205"),
        Source("EIA, Electricity retail sales (API v2)", eia.BROWSER_URL, "eia"),
        Source("Eurostat, ert_bil_eur_a (EUR/USD)", BROWSER_URL.format(dataset="ert_bil_eur_a"), "ert_bil_eur_a"),
    ),
    caveats=(
        "La serie anterior a 2007 (consumidor tipo Ie) y la posterior (banda ID) no son "
        "comparables: cambian la definición del consumidor y el método de recogida.",
        "El precio de la EIA es el ingreso medio por kWh vendido a la industria en todo el país "
        "(todas las bandas de consumo, sin desglose de impuestos homogéneo con Eurostat): sirve "
        "para comparar órdenes de magnitud, no décimas de céntimo.",
        "En euros, el precio de Polonia y de EE. UU. incorpora las variaciones del tipo de cambio.",
    ),
)

SERIES = {
    "band_ID": "Banda ID, 2–20 GWh (desde 2007)",
    "consumer_Ie": "Consumidor Ie, 2 GWh (hasta 2007)",
    "us_eia": "EE. UU. (EIA, anual)",
}
NRG_CONS = {"MWH2000-19999": "band_ID", "MWH2000": "consumer_Ie"}
COLUMNS = ["geo", "geo_name", "series", "series_label", "period", "date", "price_eur_kwh", "obs_flags", "status"]


def _semester_date(period: str) -> pd.Timestamp:
    year, half = period.split("-S")
    return pd.Timestamp(int(year), 4 if half == "1" else 10, 1)


def _semesters(first: str, last: str) -> list[str]:
    (y0, s0), (y1, s1) = (map(int, p.split("-S")) for p in (first, last))
    return [f"{y}-S{s}" for y in range(y0, y1 + 1) for s in (1, 2) if (y, s) >= (y0, s0) and (y, s) <= (y1, s1)]


def compute(prices: pd.DataFrame, fx: pd.DataFrame | None = None, us: pd.DataFrame | None = None) -> pd.DataFrame:
    """`prices`: tidy nrg_pc_205 (period column); `fx`: tidy ert_bil_eur_a; `us`: eia.parse output."""
    p = prices[(prices["tax"] == "X_VAT") & (prices["currency"] == "EUR") & prices["nrg_cons"].isin(list(NRG_CONS))]
    p = p.assign(series=p["nrg_cons"].map(NRG_CONS))
    if p.duplicated(["geo", "series", "period"]).any():
        raise ValueError("duplicate electricity price observations")

    frames = []
    for series in ("consumer_Ie", "band_ID"):
        sub = p[p["series"] == series]
        if sub.empty:
            continue
        observed = sub.dropna(subset=["value"])["period"]
        first = f"{START_YEAR}-S1" if series == "consumer_Ie" else observed.min()
        grid = pd.MultiIndex.from_product([list(COUNTRIES), _semesters(first, observed.max())], names=["geo", "period"])
        s = sub.set_index(["geo", "period"])[["value", "flag"]].reindex(grid).reset_index()
        frames.append(s.assign(series=series))
    eu = pd.concat(frames, ignore_index=True).rename(columns={"value": "price_eur_kwh", "flag": "obs_flags"})
    eu["date"] = eu["period"].map(_semester_date)

    out = [eu]
    if us is not None and not us.empty:
        rate = fx[(fx["currency"] == "USD") & (fx["statinfo"] == "AVG")].set_index("year")["value"]
        years = range(START_YEAR, int(us["year"].max()) + 1)
        u = us.set_index("year").reindex(years)
        usd_per_eur = rate.reindex(years)
        out.append(
            pd.DataFrame(
                {
                    "geo": "US",
                    "series": "us_eia",
                    "period": [str(y) for y in years],
                    "date": [pd.Timestamp(y, 7, 1) for y in years],
                    "price_eur_kwh": (u["price_usd_cents_kwh"] / 100 / usd_per_eur).to_numpy(),
                    "obs_flags": None,
                }
            )
        )

    df = pd.concat(out, ignore_index=True)
    df["geo_name"] = df["geo"].map(COUNTRIES | {"US": "EE. UU."})
    df["series_label"] = df["series"].map(SERIES)
    df["status"] = df["price_eur_kwh"].notna().map({True: "ok", False: "missing"})
    return df[COLUMNS].sort_values(["series", "geo", "date"], ignore_index=True)
