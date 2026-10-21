"""Smoke test: every dashboard page renders from the processed data."""

import pytest

from core.config import PROCESSED_DIR

pytestmark = [
    pytest.mark.data,
    pytest.mark.skipif(not (PROCESSED_DIR / "manifest.json").exists(), reason="run `make etl` first"),
]


@pytest.mark.parametrize("path", ["/", "/inversion-neta", "/intereses-educacion", "/electricidad", "/productividad", "/pisa", "/metodologia"])
def test_page_renders(path):
    from app.main import route

    body, nav = route(path)
    assert "Sin datos procesados" not in str(body)
