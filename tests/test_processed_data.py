"""Checks on the real processed data. Skipped until the ETL has produced it."""

import numpy as np
import pytest

from core.config import COUNTRIES, PROCESSED_DIR, START_YEAR
from core.storage import read_processed

pytestmark = [
    pytest.mark.data,
    pytest.mark.skipif(not (PROCESSED_DIR / "net_investment.parquet").exists(), reason="run `make etl` first"),
]

# Eurostat's PC_GDP is rounded to 0.1, so an exact share may differ from it by up to 0.05.
ROUNDING = 0.05 + 1e-9


@pytest.fixture(scope="module")
def ni():
    return read_processed("net_investment")


def test_no_duplicates_and_full_grid(ni):
    assert not ni.duplicated(["geo", "year"]).any()
    assert set(ni["geo"]) == set(COUNTRIES)
    years = sorted(ni["year"].unique())
    assert years[0] == START_YEAR and years == list(range(years[0], years[-1] + 1))
    assert len(ni) == len(COUNTRIES) * len(years)


def test_identity(ni):
    ok = ni[ni["status"] == "ok"]
    np.testing.assert_allclose(ok["net_meur"], ok["gfcf_meur"] - ok["cfc_meur"], rtol=0, atol=1e-6)
    np.testing.assert_allclose(ok["net_pc_gdp"], ok["gfcf_pc_gdp"] - ok["cfc_pc_gdp"], rtol=0, atol=1e-9)


def test_shares_match_eurostat_published_pc_gdp(ni):
    """Same unit as Eurostat's own % of GDP: confirms numerator and denominator are consistent."""
    for item in ("gfcf", "cfc"):
        both = ni[[f"{item}_pc_gdp", f"{item}_pc_gdp_published"]].dropna()
        diff = (both.iloc[:, 0] - both.iloc[:, 1]).abs()
        assert diff.max() <= ROUNDING, f"{item}: max diff {diff.max():.3f} pp"


def test_shares_in_plausible_range(ni):
    ok = ni[ni["status"] == "ok"]
    assert ok["gfcf_pc_gdp"].between(0, 10).all()
    assert ok["cfc_pc_gdp"].between(0, 10).all()
    assert ok["net_pc_gdp"].between(-5, 5).all()


def test_missing_rows_have_no_values(ni):
    missing = ni[ni["status"] != "ok"]
    assert missing["net_pc_gdp"].isna().all()
    assert ni.loc[ni["status"] == "ok", "net_pc_gdp"].notna().all()


def test_source_tables_have_no_duplicates():
    gov = read_processed("eurostat_gov_10a_main")
    gdp = read_processed("eurostat_nama_10_gdp")
    assert not gov.duplicated(["geo", "year", "sector", "na_item", "unit"]).any()
    assert not gdp.duplicated(["geo", "year", "na_item", "unit"]).any()


# COFOG uses an earlier GDP vintage than nama_10_gdp: up to 0.083 pp observed (DE), see METHODOLOGY.md.
COFOG_ROUNDING = 0.1


@pytest.mark.parametrize(
    "name, key",
    [
        ("interest_education", ["geo", "year"]),
        ("productivity", ["geo", "year"]),
        ("electricity_prices", ["geo", "series", "period"]),
        ("pisa", ["geo", "edition", "subject"]),
    ],
)
def test_indicator_tables_have_one_row_per_key(name, key):
    df = read_processed(name)
    assert not df.duplicated(key).any()
    assert set(df["status"]) <= {"ok", "partial", "missing"}


def test_interest_education_units_and_cross_check():
    ie = read_processed("interest_education")
    ok = ie[ie["status"] == "ok"]
    np.testing.assert_allclose(ok["interest_to_education"], ok["interest_pc_gdp"] / ok["education_pc_gdp"])
    for col, tol in (("interest", ROUNDING), ("education", COFOG_ROUNDING)):
        both = ie[[f"{col}_pc_gdp", f"{col}_pc_gdp_published"]].dropna()
        assert (both.iloc[:, 0] - both.iloc[:, 1]).abs().max() <= tol
    assert ok["education_pc_gdp"].between(2, 8).all()
    assert ok["interest_pc_gdp"].between(0, 15).all()


def test_productivity_rebased_to_start_year():
    p = read_processed("productivity")
    base = p[p["year"] == START_YEAR]
    np.testing.assert_allclose(base["real_index_1995"].dropna(), 100)
    eu = p[(p["geo"] == "EU27_2020") & (p["status"] == "ok")]
    np.testing.assert_allclose(eu["level_pc_eu27_pps"], 100, atol=0.05)


def test_electricity_series_are_not_spliced():
    e = read_processed("electricity_prices")
    ie = e[e["series"] == "consumer_Ie"]["period"]
    band = e[e["series"] == "band_ID"]["period"]
    assert ie.max() <= "2007-S2" and band.min() >= "2007-S1"
    ok = e[e["status"] == "ok"]
    assert ok["price_eur_kwh"].between(0.01, 1).all()
