"""PISA (OECD) mean scores, imported from a manually downloaded CSV.

PISA results are not published through the OECD SDMX API (checked 2026-10-21: no PISA
dataflow in sdmx.oecd.org), so they are downloaded by hand and normalised to
data/manual/pisa/pisa.csv with a pisa.meta.json recording when and where. See
data/manual/pisa/README.md. Without those files the indicator is reported as absent.
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from core.config import DATA_DIR

FOLDER = DATA_DIR / "manual" / "pisa"
EDITIONS = (2000, 2003, 2006, 2009, 2012, 2015, 2018, 2022)
SUBJECTS = ("math", "reading")
GEOS = ("ES", "FR", "DE", "IT", "PT", "PL", "OECD")
COLUMNS = ["geo", "edition", "subject", "mean", "se"]
REQUIRED_META = ("downloaded_on", "source_url")


class PisaFormatError(ValueError):
    pass


def load(folder: Path = FOLDER) -> tuple[pd.DataFrame, dict | None]:
    csv, meta_path = folder / "pisa.csv", folder / "pisa.meta.json"
    if not csv.exists():
        return pd.DataFrame(columns=COLUMNS), None
    if not meta_path.exists():
        raise PisaFormatError(f"{csv} has no {meta_path.name}: the download date must be documented")
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    if missing := [k for k in REQUIRED_META if not meta.get(k)]:
        raise PisaFormatError(f"{meta_path.name} lacks {missing}")

    df = pd.read_csv(csv, dtype={"geo": str, "subject": str}, comment="#")
    if list(df.columns) != COLUMNS:
        raise PisaFormatError(f"expected columns {COLUMNS}, got {list(df.columns)}")
    df["subject"] = df["subject"].str.strip().str.lower()
    problems = {
        "geo": sorted(set(df["geo"]) - set(GEOS)),
        "edition": sorted(set(df["edition"]) - set(EDITIONS)),
        "subject": sorted(set(df["subject"]) - set(SUBJECTS)),
    }
    if any(problems.values()):
        raise PisaFormatError(f"unexpected values {problems}")
    if df.duplicated(["geo", "edition", "subject"]).any():
        raise PisaFormatError("duplicate geo/edition/subject rows")
    meta["file"] = csv.name
    return df, meta
