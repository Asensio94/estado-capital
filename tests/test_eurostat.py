import json
from pathlib import Path

import numpy as np
import pytest

from etl import eurostat

FIXTURE = json.loads((Path(__file__).parent / "fixtures" / "jsonstat_small.json").read_text(encoding="utf-8"))


def test_jsonstat_flattens_sparse_values_and_flags():
    df = eurostat.jsonstat_to_frame(FIXTURE)
    assert list(df.columns) == ["unit", "geo", "time", "value", "flag"]
    # 2 units x 2 geos x 2 years = 8 cells; one has no value and no flag -> absent
    assert len(df) == 7
    es_2024 = df[(df["unit"] == "MIO_EUR") & (df["geo"] == "ES") & (df["time"] == "2024")].iloc[0]
    assert es_2024["value"] == 43253.0 and es_2024["flag"] == "p"
    confidential = df[(df["unit"] == "PC_GDP") & (df["geo"] == "FR") & (df["time"] == "2024")].iloc[0]
    assert np.isnan(confidential["value"]) and confidential["flag"] == "c"


def test_jsonstat_accepts_list_index_and_dense_values():
    payload = {
        "id": ["geo", "time"],
        "size": [1, 2],
        "dimension": {"geo": {"category": {"index": ["ES"]}}, "time": {"category": {"index": ["2023", "2024"]}}},
        "value": [1.5, None],
    }
    df = eurostat.jsonstat_to_frame(payload)
    assert df.to_dict("records") == [{"geo": "ES", "time": "2023", "value": 1.5, "flag": None}]


def test_query_key_is_stable_and_order_independent():
    a = eurostat.Query("x", {"geo": ("ES",), "unit": ("PC_GDP",)}, since=1995)
    b = eurostat.Query("x", {"unit": ("PC_GDP",), "geo": ("ES",)}, since=1995)
    assert a.key() == b.key()
    assert ("sinceTimePeriod", "1995") in a.params()


def test_verify_codes_rejects_unknown_codes(monkeypatch):
    monkeypatch.setattr(eurostat, "available_codes", lambda *a, **k: {"na_item": {"P51G", "D41PAY"}, "geo": {"ES"}})
    eurostat.verify_codes(eurostat.Query("gov_10a_main", {"na_item": ("P51G",), "geo": ("ES",)}))
    with pytest.raises(eurostat.UnknownCodeError, match="D41"):
        eurostat.verify_codes(eurostat.Query("gov_10a_main", {"na_item": ("D41",)}))
    with pytest.raises(eurostat.UnknownCodeError, match="sector"):
        eurostat.verify_codes(eurostat.Query("gov_10a_main", {"sector": ("S13",)}))
