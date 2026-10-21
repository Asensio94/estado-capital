"""Figure builders. Absent observations are NaN and are drawn as gaps (connectgaps=False)."""

from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from app import theme

NAMES = {"EU27_2020": "UE-27", "OECD": "Media OCDE", "US": "EE. UU."}


def _fmt(v: float, decimals: int) -> str:
    return f"{v:,.{decimals}f}".replace(",", "X").replace(".", ",").replace("X", ".")


def country_lines(
    df: pd.DataFrame,
    *,
    x: str,
    y: str,
    y_title: str,
    decimals: int = 2,
    zero_line: bool = False,
    ref_line: float | None = None,
    band: tuple[float, float] | None = None,
    name_col: str = "geo_name",
    dash_col: str | None = None,
    dashed: tuple = (),
    labels: dict | None = None,
    height: int = 420,
) -> go.Figure:
    """One line per geography; ES/FR highlighted and direct-labelled at their last value.

    With `dash_col`, each geography is split into segments by that column (e.g. two methodologies)
    and the values listed in `dashed` are drawn dotted; `labels` names them in the hover.
    """
    labels = labels or {}
    fig = go.Figure()
    tags = []
    if band:
        fig.add_hrect(y0=band[0], y1=band[1], fillcolor=theme.GRID, opacity=0.5, line_width=0, layer="below")
    if zero_line:
        fig.add_hline(y=0, line={"color": theme.INK_2, "width": 1})
    if ref_line is not None:
        fig.add_hline(y=ref_line, line={"color": theme.AXIS, "width": 1})

    for geo in theme.draw_order(df["geo"].unique()):
        rows = df[df["geo"] == geo]
        parts = rows.groupby(dash_col, sort=False) if dash_col else [(None, rows)]
        for key, sub in parts:
            sub = sub.sort_values(x)
            st = theme.style(geo)
            if dash_col and key in dashed:
                st = st | {"dash": "dot", "width": max(st["width"] - 1, 1.5)}
            name = sub[name_col].iloc[0]
            fig.add_trace(
                go.Scatter(
                    x=sub[x], y=sub[y], name=name, mode="lines",
                    line=st, connectgaps=False,
                    legendgroup=geo, showlegend=_first(fig, geo),
                    hovertemplate=f"{name}{'' if key is None else ' · ' + str(labels.get(key, key))}: "
                                  f"%{{y:.{decimals}f}}<extra></extra>",
                )
            )
            last = sub.dropna(subset=[y]).tail(1)
            if geo in theme.COUNTRY_COLOR and len(last) and key not in dashed:
                tags.append((last[x].iloc[0], last[y].iloc[0], f"<b>{name}</b> {_fmt(last[y].iloc[0], decimals)}"))
    _direct_labels(fig, tags, df[y])
    return theme.base_layout(fig, y_title=y_title, height=height)


def _direct_labels(fig: go.Figure, tags: list, values: pd.Series, gap: float = 0.06) -> None:
    """End-of-line labels; when two land within `gap` of the y-range they are pushed apart vertically."""
    span = float(values.max() - values.min()) or 1.0
    tags = sorted(tags, key=lambda t: t[1])
    for i, (tx, ty, text) in enumerate(tags):
        shift = 0
        if len(tags) == 2 and abs(tags[1][1] - tags[0][1]) < gap * span:
            shift = -9 if i == 0 else 9
        fig.add_annotation(x=tx, y=ty, text=text, xanchor="left", xshift=6, yshift=shift,
                           showarrow=False, font={"color": theme.INK, "size": 12})


def _first(fig: go.Figure, geo: str) -> bool:
    return sum(t.legendgroup == geo for t in fig.data) == 0


def net_heatmap(df: pd.DataFrame) -> go.Figure:
    """Country × year grid of net investment, diverging around zero; missing cells stay blank."""
    order = ["ES", "FR", "DE", "IT", "PT", "PL", "EU27_2020"]
    grid = df.pivot(index="geo", columns="year", values="net_pc_gdp").reindex(order)
    names = [df.loc[df["geo"] == g, "geo_name"].iloc[0] for g in order]
    zmax = float(grid.abs().max().max())
    text = grid.map(lambda v: "sin dato" if pd.isna(v) else _fmt(v, 2))
    fig = go.Figure(
        go.Heatmap(
            z=grid.values, x=grid.columns, y=names, zmin=-zmax, zmax=zmax, zmid=0,
            colorscale=theme.DIVERGING, xgap=2, ygap=2, text=text.values,
            hovertemplate="%{y}, %{x}: %{text} % del PIB<extra></extra>",
            colorbar={"title": {"text": "% PIB", "side": "right"}, "thickness": 10, "outlinewidth": 0,
                      "tickfont": {"color": theme.MUTED}},
        )
    )
    fig = theme.base_layout(fig, y_title="", height=320)
    fig.update_layout(hovermode="closest", margin={"l": 80, "r": 16, "t": 8, "b": 32})
    fig.update_yaxes(autorange="reversed", gridcolor=theme.SURFACE, tickfont={"color": theme.INK_2})
    return fig


def gross_vs_cfc(df: pd.DataFrame, geos=("ES", "FR")) -> go.Figure:
    """Small multiples: gross fixed capital formation (solid) vs consumption of fixed capital (dashed)."""
    names = [df.loc[df["geo"] == g, "geo_name"].iloc[0] for g in geos]
    fig = make_subplots(rows=1, cols=len(geos), shared_yaxes=True, subplot_titles=names, horizontal_spacing=0.06)
    for i, geo in enumerate(geos, start=1):
        sub = df[df["geo"] == geo].sort_values("year")
        color = theme.COUNTRY_COLOR.get(geo, theme.REFERENCE)
        for col, label, dash in (("gfcf_pc_gdp", "Inversión bruta (P51G)", "solid"), ("cfc_pc_gdp", "Consumo de capital fijo (P51C)", "dash")):
            fig.add_trace(
                go.Scatter(
                    x=sub["year"], y=sub[col], name=label, legendgroup=label, showlegend=i == 1,
                    line={"color": color if dash == "solid" else theme.INK_2, "width": 2.5 if dash == "solid" else 2, "dash": dash},
                    connectgaps=False, hovertemplate=f"{label}: %{{y:.2f}}<extra></extra>",
                ),
                row=1, col=i,
            )
    fig = theme.base_layout(fig, y_title="% del PIB", height=340)
    fig.update_layout(margin={"r": 16, "t": 32})
    fig.update_annotations(font={"color": theme.INK, "size": 13})
    return fig


def two_measures(df: pd.DataFrame, geos=("ES", "FR", "EU27_2020")) -> go.Figure:
    """Small multiples per country: interest (red) vs education (violet), both % of GDP."""
    names = [df.loc[df["geo"] == g, "geo_name"].iloc[0] for g in geos]
    fig = make_subplots(rows=1, cols=len(geos), shared_yaxes=True, subplot_titles=names, horizontal_spacing=0.05)
    measures = (("education_pc_gdp", "Educación (COFOG GF09)", "education"), ("interest_pc_gdp", "Intereses (D41PAY)", "interest"))
    for i, geo in enumerate(geos, start=1):
        sub = df[df["geo"] == geo].sort_values("year")
        for col, label, key in measures:
            fig.add_trace(
                go.Scatter(
                    x=sub["year"], y=sub[col], name=label, legendgroup=label, showlegend=i == 1,
                    line={"color": theme.MEASURE_COLOR[key], "width": 2.5}, connectgaps=False,
                    hovertemplate=f"{label}: %{{y:.2f}}<extra></extra>",
                ),
                row=1, col=i,
            )
    fig = theme.base_layout(fig, y_title="% del PIB", height=340)
    fig.update_layout(margin={"r": 16, "t": 32})
    fig.update_annotations(font={"color": theme.INK, "size": 13})
    return fig


def pisa_lines(df: pd.DataFrame) -> go.Figure:
    """Small multiples by subject; x = edition, with the birth cohort in the hover."""
    fig = make_subplots(rows=1, cols=2, shared_yaxes=True, subplot_titles=["Matemáticas", "Lectura"], horizontal_spacing=0.06)
    for i, subject in enumerate(("math", "reading"), start=1):
        for geo in theme.draw_order(df["geo"].unique()):
            sub = df[(df["geo"] == geo) & (df["subject"] == subject)].sort_values("edition")
            # The 2000 maths point is not trend-comparable: plotted as a lone marker, not joined.
            joined = sub.where(sub["trend_comparable"])
            name = sub["geo_name"].iloc[0]
            st = theme.style(geo)
            fig.add_trace(
                go.Scatter(
                    x=sub["edition"], y=joined["mean"], name=name, legendgroup=geo, showlegend=i == 1,
                    mode="lines+markers", line=st, marker={"size": 8 if geo in theme.COUNTRY_COLOR else 5},
                    customdata=sub["cohort"], connectgaps=False,
                    hovertemplate=f"{name}: %{{y:.0f}} (nacidos en %{{customdata}})<extra></extra>",
                ),
                row=1, col=i,
            )
            lone = sub[~sub["trend_comparable"]].dropna(subset=["mean"])
            if len(lone):
                fig.add_trace(
                    go.Scatter(x=lone["edition"], y=lone["mean"], mode="markers", showlegend=False, legendgroup=geo,
                               marker={"size": 8, "symbol": "circle-open", "color": st["color"]},
                               hovertemplate=f"{name} (no comparable): %{{y:.0f}}<extra></extra>"),
                    row=1, col=i,
                )
    fig = theme.base_layout(fig, y_title="puntos", height=380)
    fig.update_layout(margin={"r": 16, "t": 32})
    fig.update_annotations(font={"color": theme.INK, "size": 13})
    return fig
