"""Helpers shared by the indicator calculations."""

from __future__ import annotations

from dataclasses import dataclass, field

import pandas as pd

from core.config import COUNTRIES, START_YEAR

KEY = ["geo", "year"]


@dataclass(frozen=True)
class Source:
    label: str
    url: str
    dataset: str | None = None  # key in manifest["sources"], for the extraction date


@dataclass(frozen=True)
class Meta:
    """Everything the dashboard needs to document an indicator next to its chart."""

    key: str
    name: str
    unit: str
    definition: str
    sources: tuple[Source, ...]
    caveats: tuple[str, ...] = field(default_factory=tuple)


def wide(
    df: pd.DataFrame, unit: str, rename: dict[str, str], *, item_col: str = "na_item", index=KEY
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Pivot tidy observations of one unit to columns; also return their flags as 'ITEM:flag'."""
    sub = df[(df["unit"] == unit) & df[item_col].isin(list(rename))]
    if sub.duplicated([*index, item_col]).any():
        raise ValueError(f"duplicate observations in {unit}")
    values = sub.pivot(index=index, columns=item_col, values="value").rename(columns=rename)
    for col in rename.values():
        if col not in values:
            values[col] = float("nan")
    flags = sub.dropna(subset=["flag"]).assign(flag=lambda d: d[item_col] + ":" + d["flag"])
    return values, flags[[*index, "flag"]]


def annual_grid(last_year: int) -> pd.DataFrame:
    """Every configured country × year from START_YEAR: absent data stays visible as NaN rows."""
    idx = pd.MultiIndex.from_product([list(COUNTRIES), range(START_YEAR, last_year + 1)], names=KEY)
    return pd.DataFrame(index=idx)


def last_year(*frames: pd.DataFrame) -> int:
    years = [f.dropna(how="all").index.get_level_values("year").max() for f in frames if len(f)]
    return int(max(years))


def join_flags(out: pd.DataFrame, *flag_frames: pd.DataFrame, index=KEY) -> pd.DataFrame:
    flags = pd.concat(flag_frames)
    if flags.empty:
        out["obs_flags"] = None
        return out
    agg = flags.groupby(index)["flag"].agg(lambda s: ",".join(sorted(s))).rename("obs_flags")
    return out.merge(agg, on=index, how="left")


def status(out: pd.DataFrame, required: list[str]) -> pd.Series:
    """'ok' when all required inputs exist, 'partial' when some do, 'missing' when none."""
    present = out[required].notna().sum(axis=1)
    return pd.Series(
        ["ok" if n == len(required) else "missing" if n == 0 else "partial" for n in present],
        index=out.index,
    )
