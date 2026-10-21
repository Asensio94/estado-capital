"""Indicator 4: labour productivity per hour worked (nama_10_lp_ulc).

Two complementary views, both straight from Eurostat:
- level: nominal productivity per hour in PPS, as % of EU-27 (NLPR_HW, PC_EU27_2020_MPPS_CP);
- growth: real productivity per hour (RLPR_HW, index 2015=100), rebased here to 1995=100 by
  dividing by the country's own 1995 value. The rebasing is the only transformation; without a
  1995 value the rebased series stays empty.
"""

from __future__ import annotations

import pandas as pd

from core.config import COUNTRIES, START_YEAR
from etl.eurostat import BROWSER_URL
from indicators.common import KEY, Meta, Source, annual_grid, join_flags, last_year, status

META = Meta(
    key="productivity",
    name="Productividad por hora trabajada",
    unit="UE-27 = 100 / índice 1995 = 100",
    definition=(
        "Nivel: PIB por hora trabajada en paridades de poder de compra, en porcentaje de la media "
        "de la UE-27 (NLPR_HW). Evolución: productividad real por hora trabajada (RLPR_HW, "
        "índice 2015 = 100 de Eurostat), reescalada a 1995 = 100 para comparar el crecimiento "
        "acumulado de cada país desde el inicio del periodo."
    ),
    sources=(Source("Eurostat, nama_10_lp_ulc", BROWSER_URL.format(dataset="nama_10_lp_ulc"), "nama_10_lp_ulc"),),
    caveats=(
        "Las comparaciones de nivel en PPS son válidas entre países en un mismo año; Eurostat "
        "desaconseja leerlas como serie temporal.",
        "La productividad por hora depende de la composición sectorial y de la tasa de empleo: "
        "destruir empleo poco productivo la sube sin que nadie trabaje mejor.",
        "Las horas trabajadas proceden de la contabilidad nacional y su calidad varía entre países.",
    ),
)

COLUMNS = ["geo", "geo_name", "year", "level_pc_eu27_pps", "real_index_2015", "real_index_1995", "obs_flags", "status"]


def compute(lp: pd.DataFrame) -> pd.DataFrame:
    level = lp[(lp["na_item"] == "NLPR_HW") & (lp["unit"] == "PC_EU27_2020_MPPS_CP")]
    real = lp[(lp["na_item"] == "RLPR_HW") & (lp["unit"] == "I15")]
    for sub in (level, real):
        if sub.duplicated(KEY).any():
            raise ValueError("duplicate productivity observations")

    lw = level.set_index(KEY)[["value"]].rename(columns={"value": "level_pc_eu27_pps"})
    rw = real.set_index(KEY)[["value"]].rename(columns={"value": "real_index_2015"})
    out = annual_grid(last_year(lw, rw)).join([lw, rw]).reset_index()

    base = out[out["year"] == START_YEAR].set_index("geo")["real_index_2015"]
    out["real_index_1995"] = out["real_index_2015"] / out["geo"].map(base) * 100
    out["status"] = status(out, ["level_pc_eu27_pps", "real_index_2015"])

    flags = [s.dropna(subset=["flag"]).assign(flag=lambda d: d["na_item"] + ":" + d["flag"])[[*KEY, "flag"]] for s in (level, real)]
    out = join_flags(out, *flags)
    out["geo_name"] = out["geo"].map(COUNTRIES)
    return out[COLUMNS].sort_values(KEY, ignore_index=True)
