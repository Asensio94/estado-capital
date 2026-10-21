"""Build data/manual/pisa/pisa.csv from the OECD's own PISA 2022 trend tables.

PISA has no API, but the PISA 2022 Results (Volume I) report publishes its Annex B1 tables as
an Excel workbook behind a StatLink (a permanent OECD link). Chapter 5 holds the trend tables:

- Table I.B1.5.4  Mean mathematics performance, 2003 through 2022
- Table I.B1.5.5  Mean reading performance, 2000 through 2022

Each has one row per country and a "Mean score" / "S.E." column pair per PISA cycle; "m" marks
missing data. The reference aggregate is "OECD average-23", the average over OECD countries that
can compare performance across all assessments from PISA 2000 to 2022 (a fixed set, unlike the
plain "OECD average", which only exists for 2012, 2015 and 2022).

    python -m etl.pisa_statlink            # download, convert, write pisa.csv + pisa.meta.json
    python -m etl.pisa_statlink FILE.xlsx  # convert a workbook downloaded by hand

Needs openpyxl (`pip install -e ".[pisa]"`). The workbook is kept in data/raw/pisa (not versioned);
its URL, download date and SHA-256 go into pisa.meta.json.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from core.config import RAW_DIR
from etl import pisa
from etl.eurostat import STAMP, make_session

STATLINK = "https://stat.link/wh9d4z"
REPORT = "https://doi.org/10.1787/53f23881-en"
TABLES = {"math": "Table I.B1.5.4", "reading": "Table I.B1.5.5"}
ROWS = {
    "Spain": "ES", "France": "FR", "Germany": "DE", "Italy": "IT",
    "Portugal": "PT", "Poland": "PL", "OECD average-23": "OECD",
}
PLAUSIBLE = (300, 650)


def download() -> tuple[Path, str, datetime]:
    resp = make_session().get(STATLINK, timeout=120)
    resp.raise_for_status()
    now = datetime.now(timezone.utc)
    folder = RAW_DIR / "pisa"
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f"{now.strftime(STAMP)}_{Path(resp.url).name}"
    path.write_bytes(resp.content)
    return path, resp.url, now


def _cycle_columns(header: list) -> dict[int, int]:
    """Column of each cycle's mean score: cells 'PISA 2003', ... before the 'Change in' block."""
    cols = {}
    for i, cell in enumerate(header):
        m = re.fullmatch(r"PISA (\d{4})", str(cell).strip()) if cell is not None else None
        if m and int(m.group(1)) not in cols:
            cols[int(m.group(1))] = i
    return cols


def parse_table(sheet: pd.DataFrame, subject: str) -> tuple[pd.DataFrame, list[str]]:
    header_row = next(i for i in range(15) if (sheet.iloc[i].astype(str).str.strip() == "Mean score").any())
    cols = _cycle_columns(list(sheet.iloc[header_row - 1]))
    for edition, c in cols.items():
        if (str(sheet.iat[header_row, c]).strip(), str(sheet.iat[header_row, c + 1]).strip()) != ("Mean score", "S.E."):
            raise pisa.PisaFormatError(f"{subject}: unexpected header for PISA {edition}")
    labels = sheet.iloc[:, 0].astype(str).str.strip()
    rows, cautions = [], []
    for label, geo in ROWS.items():
        hit = labels[labels.str.rstrip("*") == label]
        if len(hit) != 1:
            raise pisa.PisaFormatError(f"{subject}: expected one row for {label!r}, found {len(hit)}")
        if hit.iloc[0] != label:
            cautions.append(f"{hit.iloc[0]} ({subject})")
        r = hit.index[0]
        for edition, c in cols.items():
            mean, se = (pd.to_numeric(sheet.iat[r, k], errors="coerce") for k in (c, c + 1))  # "m" -> NaN
            rows.append(dict(geo=geo, edition=edition, subject=subject, mean=mean, se=se))
    df = pd.DataFrame(rows)
    out_of_range = df["mean"].notna() & ~df["mean"].between(*PLAUSIBLE)
    if out_of_range.any():
        raise pisa.PisaFormatError(f"{subject}: implausible means\n{df[out_of_range]}")
    return df, cautions


def convert(workbook: Path) -> tuple[pd.DataFrame, list[str]]:
    frames, cautions = [], []
    for subject, table in TABLES.items():
        df, c = parse_table(pd.read_excel(workbook, sheet_name=table, header=None), subject)
        frames.append(df)
        cautions += c
    df = pd.concat(frames, ignore_index=True)
    # Keep only cycles the indicator knows; absent values are dropped, never filled.
    df = df[df["edition"].isin(pisa.EDITIONS)].dropna(subset=["mean"])
    return df.sort_values(["subject", "geo", "edition"], ignore_index=True), cautions


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("workbook", nargs="?", type=Path, help="StatLink workbook downloaded by hand")
    ap.add_argument("--downloaded-on", help="date of a hand download (YYYY-MM-DD)")
    args = ap.parse_args()
    if args.workbook:
        path, url = args.workbook, None
        downloaded = args.downloaded_on or datetime.fromtimestamp(path.stat().st_mtime, timezone.utc).date().isoformat()
    else:
        path, url, now = download()
        downloaded = now.date().isoformat()

    df, cautions = convert(path)
    pisa.FOLDER.mkdir(parents=True, exist_ok=True)
    df.to_csv(pisa.FOLDER / "pisa.csv", index=False, lineterminator="\n")
    meta = {
        "downloaded_on": downloaded,
        "source_url": STATLINK,
        **({"resolved_url": url} if url else {}),
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "tool": "OECD StatLink: PISA 2022 Results (Volume I), Annex B1, chapter 5 workbook",
        "report": REPORT,
        "tables": TABLES,
        "rows": ROWS,
        "notes": (
            "Generated by `python -m etl.pisa_statlink`. Means and standard errors copied at full "
            "precision; 'm' (missing) cells are omitted, not filled. OECD = 'OECD average-23': OECD "
            "countries that can compare performance across all assessments, PISA 2000 to 2022. "
            "Mathematics trend table starts in 2003. Spain 2018 is 'm' in both tables (the OECD "
            "withheld Spain's 2018 reading results; the 2022 trend tables omit its 2018 mathematics too)."
        ),
        "sampling_cautions": cautions,
    }
    (pisa.FOLDER / "pisa.meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    pisa.load()  # validate what was written with the same checks as the ETL
    print(f"pisa.csv: {len(df)} rows from {path.name}; sampling cautions: {cautions or 'none'}")


if __name__ == "__main__":
    main()
