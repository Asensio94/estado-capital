"""US Energy Information Administration API v2: average industrial electricity price, US total.

Annual "price" from the electricity/retail-sales route (EIA-861/826: utility revenue divided by
sales, cents per kWh). The key is read from $EIA_API_KEY; without it the public, heavily
rate-limited DEMO_KEY is used. Same dated raw cache layout as the Eurostat module.
"""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pandas as pd

from core.config import RAW_DIR
from etl.eurostat import STAMP, make_session

URL = "https://api.eia.gov/v2/electricity/retail-sales/data/"
BROWSER_URL = "https://www.eia.gov/electricity/data/browser/"
log = logging.getLogger(__name__)


class EIAError(RuntimeError):
    pass


def _params(start: int) -> dict:
    return {
        "frequency": "annual",
        "data[0]": "price",
        "facets[sectorid][]": "IND",
        "facets[stateid][]": "US",
        "start": str(start),
        "sort[0][column]": "period",
        "sort[0][direction]": "asc",
    }


def fetch(start: int, *, refresh: bool = False, max_age: timedelta = timedelta(hours=20)) -> tuple[pd.DataFrame, dict]:
    folder = RAW_DIR / "eia" / "retail_sales_ind_us"
    files = sorted(p for p in folder.glob("*.json") if not p.name.endswith(".meta.json"))
    now = datetime.now(timezone.utc)
    if files and not refresh:
        age = now - datetime.strptime(files[-1].stem, STAMP).replace(tzinfo=timezone.utc)
        if age < max_age:
            return _load(files[-1])

    params = _params(start) | {"api_key": os.environ.get("EIA_API_KEY", "DEMO_KEY")}
    try:
        r = make_session().get(URL, params=params, timeout=60)
        r.raise_for_status()
        payload = r.json()
    except Exception as exc:
        if files:
            log.warning("EIA: download failed (%s); using cache %s", exc, files[-1].name)
            return _load(files[-1])
        raise EIAError(f"EIA download failed and no cache: {exc}") from exc
    if "response" not in payload:
        raise EIAError(f"unexpected EIA response: {str(payload)[:300]}")

    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f"{now.strftime(STAMP)}.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    meta = {
        "url": URL,
        "params": _params(start),  # without the key
        "extracted_at": now.isoformat(),
        "source_updated": None,
    }
    path.with_suffix(".meta.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
    return _load(path)


def _load(path: Path) -> tuple[pd.DataFrame, dict]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    meta = json.loads(path.with_suffix(".meta.json").read_text(encoding="utf-8"))
    meta["raw_file"] = path.name
    return parse(payload), meta


def parse(payload: dict) -> pd.DataFrame:
    rows = payload["response"].get("data", [])
    units = {r.get("price-units") for r in rows}
    if rows and units != {"cents per kilowatt-hour"}:
        raise EIAError(f"unexpected EIA price units {units}")
    df = pd.DataFrame(
        {
            "year": [int(r["period"]) for r in rows],
            "price_usd_cents_kwh": pd.to_numeric([r.get("price") for r in rows], errors="coerce"),
        }
    )
    if df.duplicated("year").any():
        raise EIAError("duplicate EIA periods")
    return df.sort_values("year", ignore_index=True)
