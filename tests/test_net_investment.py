import numpy as np
import pandas as pd
import pytest

from core.config import COUNTRIES, START_YEAR
from indicators import net_investment


def test_identity_net_equals_gross_minus_cfc(inputs):
    out = net_investment.compute(*inputs)
    np.testing.assert_allclose(out["net_meur"], out["gfcf_meur"] - out["cfc_meur"])
    np.testing.assert_allclose(out["net_pc_gdp"], out["gfcf_pc_gdp"] - out["cfc_pc_gdp"])


def test_shares_are_percent_of_gdp(inputs):
    out = net_investment.compute(*inputs)
    np.testing.assert_allclose(out["gfcf_pc_gdp"], out["gfcf_meur"] / out["gdp_meur"] * 100)
    first = out[out["year"] == START_YEAR].iloc[0]
    assert first["net_pc_gdp"] == pytest.approx(0.2)  # (30 - 28) / 1000 * 100


def test_one_row_per_country_year(inputs):
    out = net_investment.compute(*inputs)
    assert not out.duplicated(["geo", "year"]).any()
    assert len(out) == len(COUNTRIES) * 3


def test_missing_input_is_kept_as_missing_not_filled(inputs):
    gov, gdp = inputs
    gap = (gov["geo"] == "ES") & (gov["year"] == START_YEAR + 1) & (gov["na_item"] == "P51C")
    out = net_investment.compute(gov[~gap], gdp)
    row = out[(out["geo"] == "ES") & (out["year"] == START_YEAR + 1)].iloc[0]
    assert row["status"] == "partial"
    assert np.isnan(row["cfc_meur"]) and np.isnan(row["net_pc_gdp"])
    assert pd.isna(row["consumes_stock"])
    assert (out.drop(row.name)["status"] == "ok").all()


def test_country_without_government_data_still_appears(inputs):
    gov, gdp = inputs
    out = net_investment.compute(gov[gov["geo"] != "PT"], gdp)
    pt = out[out["geo"] == "PT"]
    assert len(pt) == 3 and (pt["status"] == "partial").all()
    assert pt["net_pc_gdp"].isna().all()


def test_country_without_any_data_is_missing(inputs):
    gov, gdp = inputs
    out = net_investment.compute(gov[gov["geo"] != "PT"], gdp[gdp["geo"] != "PT"])
    pt = out[out["geo"] == "PT"]
    assert len(pt) == 3 and (pt["status"] == "missing").all()


def test_consumes_stock_includes_exactly_zero(inputs):
    gov, gdp = inputs
    gov = gov.copy()
    zero = (gov["na_item"] == "P51G") & (gov["unit"] == "MIO_EUR") & (gov["year"] == START_YEAR)
    gov.loc[zero, "value"] = 28.0
    out = net_investment.compute(gov, gdp)
    assert out.loc[out["year"] == START_YEAR, "consumes_stock"].all()
    assert not out.loc[out["year"] > START_YEAR, "consumes_stock"].any()


def test_duplicate_source_rows_are_rejected(inputs):
    gov, gdp = inputs
    with pytest.raises(ValueError, match="duplicate"):
        net_investment.compute(pd.concat([gov, gov.head(1)]), gdp)


def test_flags_are_carried_through(inputs):
    gov, gdp = inputs
    gdp = gdp.copy()
    gdp.loc[(gdp["geo"] == "FR") & (gdp["year"] == START_YEAR), "flag"] = "p"
    out = net_investment.compute(gov, gdp)
    assert out.loc[(out["geo"] == "FR") & (out["year"] == START_YEAR), "obs_flags"].item() == "B1GQ:p"
    assert out["obs_flags"].notna().sum() == 1
