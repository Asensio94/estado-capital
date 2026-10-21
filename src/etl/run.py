"""ETL entry point: download (or reuse cache), tidy, compute indicators, write parquet."""

from __future__ import annotations

import logging
from datetime import datetime, timezone

import pandas as pd

from core import storage
from etl import catalog, eurostat
from indicators import net_investment

log = logging.getLogger(__name__)


def tidy(extract: eurostat.Extract) -> pd.DataFrame:
    """Annual observations with provenance columns; `year` replaces JSON-stat's `time`."""
    df = extract.frame.drop(columns=["freq"], errors="ignore").rename(columns={"time": "year"})
    df["year"] = df["year"].astype(int)
    df["dataset"] = extract.query.dataset
    df["extracted_at"] = extract.extracted_at
    df["source_updated"] = extract.source_updated
    return df


def run(*, refresh: bool = False, verify: bool = True, s3: bool = False) -> dict:
    session = eurostat.make_session()
    sources = {}
    tables = {}
    for query in catalog.INDICATOR_1:
        if verify:
            eurostat.verify_codes(query, session)
        extract = eurostat.fetch(query, refresh=refresh)
        tables[query.dataset] = tidy(extract)
        storage.write_processed(tables[query.dataset], f"eurostat_{query.dataset}")
        sources[query.dataset] = {
            "label": extract.label,
            "url": extract.url,
            "browser_url": query.browser_url,
            "extracted_at": extract.extracted_at.isoformat(),
            "source_updated": extract.source_updated,
            "raw_file": extract.path.name,
        }

    ni = net_investment.compute(tables["gov_10a_main"], tables["nama_10_gdp"])
    storage.write_processed(ni, "net_investment")

    manifest = {
        "built_at": datetime.now(timezone.utc).isoformat(),
        "sources": sources,
        "indicators": {
            "net_investment": {
                "rows": len(ni),
                "missing": int((ni["status"] == "missing").sum()),
                "first_year": int(ni["year"].min()),
                "last_year": int(ni["year"].max()),
            }
        },
    }
    storage.write_manifest(manifest)
    if s3:
        storage.upload_processed_to_s3()
    return manifest
