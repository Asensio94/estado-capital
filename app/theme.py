"""Colours and the shared Plotly layout.

Spain and France are the two highlighted series (orange / blue: validated pair, adjacent
CVD ΔE 24.7, both ≥ 3:1 on the surface). Every other country is a light grey line; the EU-27
reference is a dark grey dashed line, the US a dark grey dotted one. Identity is never colour
alone: highlighted lines are direct-labelled and every chart has a legend and hover.
"""

from __future__ import annotations

import plotly.graph_objects as go

SURFACE = "#fcfcfb"
PAGE = "#f9f9f7"
INK = "#0b0b0b"
INK_2 = "#52514e"
MUTED = "#898781"
GRID = "#e1e0d9"
AXIS = "#c3c2b7"

COUNTRY_COLOR = {"ES": "#eb6834", "FR": "#2a78d6"}
OTHER = "#c3c2b7"
REFERENCE = "#52514e"  # EU-27 / OECD average
US = "#0b0b0b"

# Diverging scale for the synthesis heatmap: red (net < 0) – neutral grey – blue (net > 0).
DIVERGING = [[0.0, "#e34948"], [0.5, "#f0efec"], [1.0, "#2a78d6"]]
# Two measures shown together (interest vs education).
MEASURE_COLOR = {"education": "#6250d6", "interest": "#e34948"}

FONT = "Inter, system-ui, -apple-system, Segoe UI, Roboto, sans-serif"


def style(geo: str) -> dict:
    """Line style per geography; order of drawing is handled by `draw_order`."""
    if geo in COUNTRY_COLOR:
        return {"color": COUNTRY_COLOR[geo], "width": 3, "dash": "solid"}
    if geo in ("EU27_2020", "OECD"):
        return {"color": REFERENCE, "width": 2, "dash": "dash"}
    if geo == "US":
        return {"color": US, "width": 2, "dash": "dot"}
    return {"color": OTHER, "width": 1.5, "dash": "solid"}


def draw_order(geos) -> list[str]:
    """Grey context first, reference next, highlighted countries last (on top)."""
    rank = {"ES": 4, "FR": 3, "EU27_2020": 2, "OECD": 2, "US": 2}
    return sorted(geos, key=lambda g: rank.get(g, 0))


def base_layout(fig: go.Figure, *, y_title: str, height: int = 420) -> go.Figure:
    fig.update_layout(
        template="none",
        height=height,
        paper_bgcolor=SURFACE,
        plot_bgcolor=SURFACE,
        font={"family": FONT, "size": 13, "color": INK_2},
        margin={"l": 56, "r": 96, "t": 16, "b": 40},
        hovermode="x unified",
        hoverlabel={"bgcolor": SURFACE, "bordercolor": AXIS, "font": {"color": INK}},
        legend={"orientation": "h", "y": -0.14, "x": 0, "font": {"size": 12}},
        separators=", ",
    )
    fig.update_xaxes(showgrid=False, linecolor=AXIS, ticks="outside", tickcolor=AXIS, tickfont={"color": MUTED})
    fig.update_yaxes(
        title={"text": y_title, "font": {"size": 12, "color": MUTED}},
        gridcolor=GRID, zeroline=False, tickfont={"color": MUTED}, linecolor=AXIS,
    )
    return fig
