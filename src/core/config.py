"""Project-wide settings: countries, period and data paths."""

from __future__ import annotations

import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = Path(os.environ.get("CAPITAL_DATA_DIR", ROOT / "data"))
RAW_DIR = DATA_DIR / "raw"
PROCESSED_DIR = DATA_DIR / "processed"

# Eurostat geo codes -> display names. EU27_2020 is the current 27-member aggregate
# (fixed composition, back-calculated to 1995), not the EU as it was each year.
COUNTRIES: dict[str, str] = {
    "ES": "España",
    "FR": "Francia",
    "DE": "Alemania",
    "IT": "Italia",
    "PT": "Portugal",
    "PL": "Polonia",
    "EU27_2020": "UE-27",
}
HIGHLIGHT = ("ES", "FR")

START_YEAR = 1995
