"""Synthetic checks for indicators 2–5 and the EIA / PISA loaders (no network)."""

import json

import numpy as np
import pandas as pd
import pytest

from core.config import COUNTRIES, START_YEAR
from etl import eia
from etl import pisa as pisa_source
from indicators import electricity_prices, interest_education, pisa, productivity

YEARS = range(START_YEAR, START_YEAR + 3)


def _gov_cofog_gdp():
    gov, cofog, gdp = [], [], []
    for year in YEARS:
        for geo in COUNTRIES:
            gov.append(dict(sector="S13", na_item="D41PAY", unit="MIO_EUR", geo=geo, year=year, value=30.0, flag=None))
            cofog.append(dict(sector="S13", cofog99="GF09", na_item="TE", unit="MIO_EUR", geo=geo, year=year, value=40.0, flag=None))
            gdp.append(dict(na_item="B1GQ", unit="CP_MEUR", geo=geo, year=year, value=1000.0, flag=None))
    return pd.DataFrame(gov), pd.DataFrame(cofog), pd.DataFrame(gdp)


class TestInterestEducation:
    def test_ratio_and_shares(self):
        out = interest_education.compute(*_gov_cofog_gdp())
        assert not out.duplicated(["geo", "year"]).any() and len(out) == len(COUNTRIES) * len(YEARS)
        np.testing.assert_allclose(out["interest_to_education"], 0.75)
        np.testing.assert_allclose(out["interest_pc_gdp"], 3.0)
        np.testing.assert_allclose(out["education_pc_gdp"], 4.0)
        assert (out["status"] == "ok").all()

    def test_missing_cofog_year_stays_empty(self):
        gov, cofog, gdp = _gov_cofog_gdp()
        cofog = cofog[~((cofog["geo"] == "EU27_2020") & (cofog["year"] == START_YEAR))]
        out = interest_education.compute(gov, cofog, gdp)
        row = out[(out["geo"] == "EU27_2020") & (out["year"] == START_YEAR)].iloc[0]
        assert row["status"] == "partial"
        assert np.isnan(row["interest_to_education"]) and row["interest_pc_gdp"] == pytest.approx(3.0)

    def test_cofog_flags_are_prefixed(self):
        gov, cofog, gdp = _gov_cofog_gdp()
        cofog.loc[(cofog["geo"] == "ES") & (cofog["year"] == START_YEAR), "flag"] = "p"
        out = interest_education.compute(gov, cofog, gdp)
        assert out.loc[(out["geo"] == "ES") & (out["year"] == START_YEAR), "obs_flags"].item() == "GF09_TE:p"


def _prices():
    rows = []
    for geo in COUNTRIES:
        for period, cons, value in (("2006-S2", "MWH2000", 0.06), ("2007-S1", "MWH2000", 0.07),
                                    ("2007-S1", "MWH2000-19999", 0.08), ("2007-S2", "MWH2000-19999", 0.09)):
            rows.append(dict(geo=geo, period=period, nrg_cons=cons, tax="X_VAT", currency="EUR", value=value, flag=None))
    return pd.DataFrame(rows)


class TestElectricity:
    def test_two_methodologies_are_separate_series(self):
        out = electricity_prices.compute(_prices())
        es = out[out["geo"] == "ES"]
        both = es[es["period"] == "2007-S1"].set_index("series")["price_eur_kwh"]
        assert both.to_dict() == {"band_ID": 0.08, "consumer_Ie": 0.07}  # same semester, never merged
        assert not out.duplicated(["geo", "series", "period"]).any()

    def test_consumer_ie_grid_starts_in_start_year_and_is_not_filled(self):
        out = electricity_prices.compute(_prices())
        ie = out[(out["geo"] == "FR") & (out["series"] == "consumer_Ie")]
        assert ie["period"].iloc[0] == f"{START_YEAR}-S1"
        early = ie[ie["period"] < "2006-S2"]
        assert early["price_eur_kwh"].isna().all() and (early["status"] == "missing").all()

    def test_semester_midpoints(self):
        out = electricity_prices.compute(_prices())
        dates = out[out["period"] == "2007-S2"]["date"].unique()
        assert list(dates) == [pd.Timestamp(2007, 10, 1)]

    def test_us_price_converted_with_annual_rate(self):
        fx = pd.DataFrame([dict(currency="USD", statinfo="AVG", year=y, value=1.25) for y in range(START_YEAR, 2003)])
        us = pd.DataFrame({"year": [2001, 2002], "price_usd_cents_kwh": [5.0, np.nan]})
        out = electricity_prices.compute(_prices(), fx, us)
        u = out[out["geo"] == "US"].set_index("period")["price_eur_kwh"]
        assert u["2001"] == pytest.approx(0.04)  # 5 cents / 100 / 1.25 USD per EUR
        assert np.isnan(u["2002"]) and np.isnan(u[str(START_YEAR)])

    def test_duplicates_rejected(self):
        p = _prices()
        with pytest.raises(ValueError, match="duplicate"):
            electricity_prices.compute(pd.concat([p, p.head(1)]))


class TestEIAParse:
    def test_parse(self):
        payload = {"response": {"data": [
            {"period": "2002", "price": "4.88", "price-units": "cents per kilowatt-hour"},
            {"period": "2001", "price": None, "price-units": "cents per kilowatt-hour"},
        ]}}
        df = eia.parse(payload)
        assert df["year"].tolist() == [2001, 2002]
        assert np.isnan(df["price_usd_cents_kwh"].iloc[0]) and df["price_usd_cents_kwh"].iloc[1] == 4.88

    def test_unexpected_units_rejected(self):
        payload = {"response": {"data": [{"period": "2002", "price": "48.8", "price-units": "dollars per megawatt-hour"}]}}
        with pytest.raises(eia.EIAError):
            eia.parse(payload)


def _lp():
    rows = []
    for geo in COUNTRIES:
        for i, year in enumerate(YEARS):
            rows.append(dict(na_item="NLPR_HW", unit="PC_EU27_2020_MPPS_CP", geo=geo, year=year, value=90.0, flag=None))
            rows.append(dict(na_item="RLPR_HW", unit="I15", geo=geo, year=year, value=80.0 + 8 * i, flag=None))
    return pd.DataFrame(rows)


class TestProductivity:
    def test_rebased_to_start_year(self):
        out = productivity.compute(_lp())
        es = out[out["geo"] == "ES"].set_index("year")["real_index_1995"]
        assert es.tolist() == pytest.approx([100.0, 110.0, 120.0])

    def test_no_base_year_means_no_rebased_series(self):
        lp = _lp()
        lp = lp[~((lp["geo"] == "PT") & (lp["na_item"] == "RLPR_HW") & (lp["year"] == START_YEAR))]
        out = productivity.compute(lp)
        assert out.loc[out["geo"] == "PT", "real_index_1995"].isna().all()


class TestPisa:
    def _write(self, folder, rows, meta=True):
        csv = "geo,edition,subject,mean,se\n" + "".join(f"{r}\n" for r in rows)
        (folder / "pisa.csv").write_text(csv, encoding="utf-8")
        if meta:
            (folder / "pisa.meta.json").write_text(
                json.dumps({"downloaded_on": "2026-10-21", "source_url": "https://data-explorer.oecd.org/"}), encoding="utf-8")

    def test_no_file_means_empty(self, tmp_path):
        df, meta = pisa_source.load(tmp_path)
        assert df.empty and meta is None

    def test_meta_is_required(self, tmp_path):
        self._write(tmp_path, ["ES,2022,math,473,1.8"], meta=False)
        with pytest.raises(pisa_source.PisaFormatError, match="download date"):
            pisa_source.load(tmp_path)

    def test_unknown_values_rejected(self, tmp_path):
        self._write(tmp_path, ["XX,2021,science,500,2"])
        with pytest.raises(pisa_source.PisaFormatError, match="unexpected"):
            pisa_source.load(tmp_path)

    def test_grid_cohorts_and_comparability(self, tmp_path):
        self._write(tmp_path, ["ES,2000,math,476,3.1", "ES,2022,Math,473,1.8"])
        df, meta = pisa_source.load(tmp_path)
        out = pisa.compute(df)
        assert len(out) == len(pisa_source.GEOS) * len(pisa_source.EDITIONS) * len(pisa_source.SUBJECTS)
        es = out[(out["geo"] == "ES") & (out["subject"] == "math")].set_index("edition")
        assert es.loc[2022, "cohort"] == 2007 and es.loc[2022, "mean"] == 473
        assert not es.loc[2000, "trend_comparable"] and es.loc[2003, "trend_comparable"]
        assert np.isnan(es.loc[2003, "mean"]) and es.loc[2003, "status"] == "missing"


class TestStatLink:
    """The converter for the OECD's PISA 2022 trend workbook, on a synthetic sheet."""

    def _sheet(self, spain_label="Spain"):
        from etl.pisa_statlink import ROWS
        head = [[None] * 5 for _ in range(5)]
        head += [[None, "PISA 2003", None, "PISA 2022", None], [None, "Mean score", "S.E.", "Mean score", "S.E."]]
        body = [[spain_label if geo == "ES" else label, 480.5, 2.4, "m", "m"] for label, geo in ROWS.items()]
        return pd.DataFrame(head + body)

    def test_parse_drops_nothing_and_keeps_m_as_missing(self):
        from etl.pisa_statlink import parse_table
        df, cautions = parse_table(self._sheet(), "math")
        assert len(df) == 7 * 2 and not cautions
        es = df[df["geo"] == "ES"].set_index("edition")
        assert es.loc[2003, "mean"] == 480.5 and es.loc[2003, "se"] == 2.4
        assert np.isnan(es.loc[2022, "mean"]) and np.isnan(es.loc[2022, "se"])

    def test_sampling_caution_marker_is_recorded(self):
        from etl.pisa_statlink import parse_table
        _, cautions = parse_table(self._sheet("Spain*"), "reading")
        assert cautions == ["Spain* (reading)"]

    def test_missing_country_row_rejected(self):
        from etl.pisa_statlink import parse_table
        with pytest.raises(pisa_source.PisaFormatError, match="Spain"):
            parse_table(self._sheet("España"), "math")
