"""Read-only access to data/processed for the dashboard."""

from __future__ import annotations

from datetime import datetime
from functools import lru_cache

import pandas as pd

from core import storage
from core.config import PROCESSED_DIR


class NoData(RuntimeError):
    pass


@lru_cache(maxsize=None)
def table(name: str) -> pd.DataFrame:
    if not (PROCESSED_DIR / f"{name}.parquet").exists():
        raise NoData(f"falta data/processed/{name}.parquet: ejecuta `make etl`")
    return storage.read_processed(name)


@lru_cache(maxsize=1)
def manifest() -> dict:
    try:
        return storage.read_manifest()
    except FileNotFoundError:
        return {"sources": {}, "indicators": {}}


def fmt_date(iso: str | None) -> str:
    if not iso:
        return "—"
    return datetime.fromisoformat(iso).strftime("%d/%m/%Y")


def missing_ranges(df: pd.DataFrame, value: str, *, period: str = "year", name: str = "geo_name") -> list[str]:
    """Human-readable list of absent stretches, e.g. 'UE-27: 1995–2009'; geographies with the
    same gaps share one line ('España, Francia: 2025')."""
    out: dict[str, list[str]] = {}
    for geo_name, sub in df.sort_values(period).groupby(name, sort=False):
        periods = list(sub[period])
        absent = [p for p, v in zip(periods, sub[value]) if pd.isna(v)]
        if not absent:
            continue
        runs, start, prev = [], absent[0], absent[0]
        index = {p: i for i, p in enumerate(periods)}
        for p in absent[1:]:
            if index[p] != index[prev] + 1:
                runs.append((start, prev))
                start = p
            prev = p
        runs.append((start, prev))
        out.setdefault(", ".join(str(a) if a == b else f"{a}–{b}" for a, b in runs), []).append(geo_name)
    return [f"{', '.join(names)}: {ranges}" for ranges, names in out.items()]
