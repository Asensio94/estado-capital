"""Eurostat dissemination API: JSON-stat 2.0 data, SDMX 2.1 code checks and a dated raw cache.

Every download is stored untouched under data/raw/eurostat/<dataset>/<query-hash>/ as
<UTC timestamp>.json plus a .meta.json sidecar (URL, extraction time, Eurostat's own
"updated" stamp). Re-runs reuse the newest file while it is younger than `max_age`; if the
API is unreachable the newest cached file is used and the run logs a warning.
"""

from __future__ import annotations

import hashlib
import json
import logging
import re
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Mapping, Sequence

import numpy as np
import pandas as pd
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from core.config import RAW_DIR

API = "https://ec.europa.eu/eurostat/api/dissemination"
DATA_URL = API + "/statistics/1.0/data/{dataset}"
CONSTRAINT_URL = API + "/sdmx/2.1/contentconstraint/ESTAT/{dataset}"
BROWSER_URL = "https://ec.europa.eu/eurostat/databrowser/view/{dataset}/default/table"

STAMP = "%Y%m%dT%H%M%SZ"
log = logging.getLogger(__name__)


class EurostatError(RuntimeError):
    pass


class UnknownCodeError(EurostatError):
    pass


@dataclass(frozen=True)
class Query:
    dataset: str
    filters: Mapping[str, Sequence[str]]
    since: int | None = None

    def params(self) -> list[tuple[str, str]]:
        params = [("format", "JSON"), ("lang", "EN")]
        for dim in sorted(self.filters):
            params += [(dim, code) for code in self.filters[dim]]
        if self.since is not None:
            params.append(("sinceTimePeriod", str(self.since)))
        return params

    def key(self) -> str:
        return hashlib.sha1(json.dumps(self.params()).encode()).hexdigest()[:10]

    @property
    def browser_url(self) -> str:
        return BROWSER_URL.format(dataset=self.dataset)


@dataclass(frozen=True)
class Extract:
    query: Query
    url: str
    extracted_at: datetime
    source_updated: str | None
    label: str
    path: Path
    frame: pd.DataFrame


def make_session() -> requests.Session:
    retry = Retry(total=4, backoff_factor=2, status_forcelist=(429, 500, 502, 503, 504))
    s = requests.Session()
    s.mount("https://", HTTPAdapter(max_retries=retry))
    s.headers["User-Agent"] = "estado-capital ETL (github.com/Asensio94)"
    return s


def available_codes(dataset: str, session: requests.Session | None = None) -> dict[str, set[str]]:
    """Codes actually present in the cube, per dimension (SDMX "Actual" content constraint).

    The full codelists are shared across datasets (e.g. 643 na_item codes) and say nothing
    about what a given dataset holds; the content constraint does.
    """
    session = session or make_session()
    r = session.get(CONSTRAINT_URL.format(dataset=dataset.upper()), timeout=60)
    r.raise_for_status()
    region = re.search(r'<s:CubeRegion include="true">(.*?)</s:CubeRegion>', r.text, re.S)
    if not region:
        raise EurostatError(f"no content constraint for {dataset}")
    out = {}
    for dim, body in re.findall(r'<c:KeyValue id="([^"]+)">(.*?)</c:KeyValue>', region.group(1), re.S):
        out[dim.lower()] = set(re.findall(r"<c:Value>([^<]+)</c:Value>", body))
    return out


def verify_codes(query: Query, session: requests.Session | None = None) -> None:
    """Fail loudly if any requested code is not in the dataset's metadata."""
    codes = available_codes(query.dataset, session)
    missing = {
        dim: sorted(set(wanted) - codes[dim.lower()])
        for dim, wanted in query.filters.items()
        if dim.lower() in codes and set(wanted) - codes[dim.lower()]
    }
    unknown_dims = sorted(d for d in query.filters if d.lower() not in codes)
    if missing or unknown_dims:
        raise UnknownCodeError(
            f"{query.dataset}: codes not in metadata {missing}; unknown dimensions {unknown_dims}"
        )


def _latest_cached(folder: Path) -> Path | None:
    files = sorted(p for p in folder.glob("*.json") if not p.name.endswith(".meta.json"))
    return files[-1] if files else None


def fetch(query: Query, *, refresh: bool = False, max_age: timedelta = timedelta(hours=20)) -> Extract:
    folder = RAW_DIR / "eurostat" / query.dataset.lower() / query.key()
    cached = _latest_cached(folder)
    now = datetime.now(timezone.utc)

    if cached and not refresh:
        age = now - datetime.strptime(cached.stem, STAMP).replace(tzinfo=timezone.utc)
        if age < max_age:
            return _load(query, cached)

    url = DATA_URL.format(dataset=query.dataset)
    try:
        r = make_session().get(url, params=query.params(), timeout=120)
        r.raise_for_status()
        payload = r.json()
    except (requests.RequestException, ValueError) as exc:
        if cached:
            log.warning("%s: download failed (%s); using cache %s", query.dataset, exc, cached.name)
            return _load(query, cached)
        raise EurostatError(f"{query.dataset}: download failed and no cache") from exc

    if "error" in payload:
        raise EurostatError(f"{query.dataset}: {payload['error']}")
    if payload.get("class") != "dataset":
        # Large requests are answered asynchronously; ours are small enough not to be.
        raise EurostatError(f"{query.dataset}: unexpected response {str(payload)[:300]}")

    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f"{now.strftime(STAMP)}.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    meta = {
        "dataset": query.dataset,
        "url": r.url,
        "params": query.params(),
        "extracted_at": now.isoformat(),
        "source_updated": payload.get("updated"),
    }
    path.with_suffix(".meta.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
    log.info("%s: downloaded %d observations", query.dataset, len(payload.get("value", {})))
    return _load(query, path)


def _load(query: Query, path: Path) -> Extract:
    payload = json.loads(path.read_text(encoding="utf-8"))
    meta = json.loads(path.with_suffix(".meta.json").read_text(encoding="utf-8"))
    return Extract(
        query=query,
        url=meta["url"],
        extracted_at=datetime.fromisoformat(meta["extracted_at"]),
        source_updated=meta.get("source_updated"),
        label=payload.get("label", query.dataset),
        path=path,
        frame=jsonstat_to_frame(payload),
    )


def _sparse(obj: dict | list | None) -> dict[int, object]:
    if not obj:
        return {}
    if isinstance(obj, list):
        return {i: v for i, v in enumerate(obj) if v is not None}
    return {int(k): v for k, v in obj.items()}


def jsonstat_to_frame(payload: dict) -> pd.DataFrame:
    """Flatten a JSON-stat 2.0 dataset into one row per observation.

    Columns: one per dimension (codes), `value` (float, NaN when Eurostat gives only a flag)
    and `flag` (Eurostat status letter or None). Cells with neither value nor flag are absent
    from the payload and therefore absent here: nothing is filled in.
    """
    ids, sizes = payload["id"], payload["size"]
    codes = []
    for dim in ids:
        index = payload["dimension"][dim]["category"]["index"]
        codes.append(np.array(index if isinstance(index, list) else sorted(index, key=index.get)))

    values, status = _sparse(payload.get("value")), _sparse(payload.get("status"))
    positions = np.array(sorted(set(values) | set(status)), dtype=np.int64)
    if positions.size == 0:
        return pd.DataFrame(columns=[*ids, "value", "flag"])

    coords = np.unravel_index(positions, sizes)
    df = pd.DataFrame({dim: codes[i][coords[i]] for i, dim in enumerate(ids)})
    df["value"] = pd.to_numeric(pd.Series([values.get(p) for p in positions]), errors="coerce")
    df["flag"] = [status.get(p) for p in positions]
    return df
