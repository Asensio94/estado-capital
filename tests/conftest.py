import pandas as pd
import pytest

from core.config import COUNTRIES, START_YEAR


def make_inputs(years=range(START_YEAR, START_YEAR + 3)) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Synthetic tidy gov_10a_main / nama_10_gdp frames: GDP 1000, GFCF 30 + i, CFC 28 for every geo."""
    gov, gdp = [], []
    for i, year in enumerate(years):
        for geo in COUNTRIES:
            gfcf, cfc, y = 30.0 + i, 28.0, 1000.0
            for item, val in (("P51G", gfcf), ("P51C", cfc)):
                gov.append(dict(sector="S13", na_item=item, unit="MIO_EUR", geo=geo, year=year, value=val, flag=None))
                gov.append(dict(sector="S13", na_item=item, unit="PC_GDP", geo=geo, year=year,
                                value=round(val / y * 100, 1), flag=None))
            gdp.append(dict(na_item="B1GQ", unit="CP_MEUR", geo=geo, year=year, value=y, flag=None))
    return pd.DataFrame(gov), pd.DataFrame(gdp)


@pytest.fixture
def inputs():
    return make_inputs()
