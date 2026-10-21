"""ETL entry point: download (or reuse cache), tidy, compute indicators, write parquet."""

from __future__ import annotations

import logging
from datetime import datetime, timezone

import pandas as pd

from core import storage
from core.config import START_YEAR
from etl import catalog, eia, eurostat, pisa
from indicators import electricity_prices, interest_education, net_investment, pisa as pisa_ind, productivity

log = logging.getLogger(__name__)


def tidy(extract: eurostat.Extract) -> pd.DataFrame:
    """Observations with provenance columns. Annual `time` becomes int `year`; other
    frequencies (e.g. semesters, "2024-S1") keep it as string `period`."""
    df = extract.frame.drop(columns=["freq"], errors="ignore")
    if df["time"].str.fullmatch(r"\d{4}").all():
        df = df.rename(columns={"time": "year"}).astype({"year": int})
    else:
        df = df.rename(columns={"time": "period"})
    df["dataset"] = extract.query.dataset
    df["extracted_at"] = extract.extracted_at
    df["source_updated"] = extract.source_updated
    return df


def _summary(df: pd.DataFrame) -> dict:
    return {"rows": len(df), "by_status": df["status"].value_counts().to_dict()}


def run(*, refresh: bool = False, verify: bool = True, s3: bool = False) -> dict:
    session = eurostat.make_session()
    sources: dict[str, dict] = {}
    t: dict[str, pd.DataFrame] = {}
    for query in catalog.ALL:
        if verify:
            eurostat.verify_codes(query, session)
        extract = eurostat.fetch(query, refresh=refresh)
        t[query.dataset] = tidy(extract)
        storage.write_processed(t[query.dataset], f"eurostat_{query.dataset}")
        sources[query.dataset] = {
            "label": extract.label,
            "url": extract.url,
            "browser_url": query.browser_url,
            "extracted_at": extract.extracted_at.isoformat(),
            "source_updated": extract.source_updated,
            "raw_file": extract.path.name,
        }

    # Optional sources: their absence leaves the corresponding series empty, never the run broken.
    try:
        us, us_meta = eia.fetch(START_YEAR, refresh=refresh)
        sources["eia"] = {"label": "EIA electricity retail sales, industrial, US total", "browser_url": eia.BROWSER_URL, **us_meta}
    except eia.EIAError as exc:
        log.warning("EIA comparison skipped: %s", exc)
        us = None

    scores, pisa_meta = pisa.load()
    if pisa_meta:
        sources["pisa"] = {"label": "OECD PISA (manual CSV)", "browser_url": pisa_meta["source_url"],
                           "extracted_at": pisa_meta["downloaded_on"], **pisa_meta}
    else:
        log.warning("PISA: no data/manual/pisa/pisa.csv; indicator 5 will be shown as absent")

    gov, cofog, gdp = t["gov_10a_main"], t["gov_10a_exp"], t["nama_10_gdp"]
    results = {
        "net_investment": net_investment.compute(gov, gdp),
        "interest_education": interest_education.compute(gov, cofog, gdp),
        "electricity_prices": electricity_prices.compute(t["nrg_pc_205"], t["ert_bil_eur_a"], us),
        "productivity": productivity.compute(t["nama_10_lp_ulc"]),
        "pisa": pisa_ind.compute(scores),
    }
    for name, df in results.items():
        storage.write_processed(df, name)

    manifest = {
        "built_at": datetime.now(timezone.utc).isoformat(),
        "sources": sources,
        "indicators": {name: _summary(df) for name, df in results.items()},
    }
    storage.write_manifest(manifest)
    if s3:
        storage.upload_processed_to_s3()
    return manifest
