"""Building blocks: every chart ships with its definition, source, dates, caveats and gaps."""

from __future__ import annotations

import pandas as pd
from dash import dash_table, dcc, html

from app import data
from indicators.common import Meta


def sources_block(meta: Meta) -> html.Div:
    sources = data.manifest().get("sources", {})
    items = []
    for s in meta.sources:
        info = sources.get(s.dataset or "", {})
        if info:
            when = f"extraído el {data.fmt_date(info.get('extracted_at'))}"
            if info.get("source_updated"):
                when += f"; última actualización de la fuente: {data.fmt_date(info['source_updated'])}"
        else:
            when = "sin datos cargados"
        items.append(html.Li([html.A(s.label, href=s.url, target="_blank", rel="noopener"), f" — {when}"]))
    return html.Div([html.H4("Fuente"), html.Ul(items)], className="meta-block")


def chart_card(
    title: str,
    figure,
    meta: Meta,
    *,
    note: str | None = None,
    missing: list[str] | None = None,
    table: pd.DataFrame | None = None,
) -> html.Section:
    gaps = (
        html.Div([html.H4("Datos ausentes"), html.Ul([html.Li(m) for m in missing])], className="meta-block gaps")
        if missing
        else html.Div([html.H4("Datos ausentes"), html.P("Ninguno en el periodo mostrado.")], className="meta-block gaps")
    )
    children = [
        html.H3(title),
        html.P(note, className="chart-note") if note else None,
        dcc.Graph(figure=figure, config={"displaylogo": False, "responsive": True}),
        html.Div(
            [
                html.Div([html.H4("Definición"), html.P(meta.definition)], className="meta-block"),
                sources_block(meta),
                html.Div([html.H4("Advertencias metodológicas"), html.Ul([html.Li(c) for c in meta.caveats])], className="meta-block"),
                gaps,
            ],
            className="meta-grid",
        ),
    ]
    if table is not None:
        children.append(
            html.Details(
                [
                    html.Summary("Ver los datos en tabla"),
                    dash_table.DataTable(
                        data=table.to_dict("records"),
                        columns=[{"name": c, "id": c} for c in table.columns],
                        page_size=15, sort_action="native", filter_action="native",
                        style_cell={"fontFamily": "inherit", "fontSize": 13, "padding": "4px 8px"},
                        style_header={"fontWeight": 600},
                    ),
                ],
                className="table-view",
            )
        )
    return html.Section([c for c in children if c is not None], className="card")


def empty_card(title: str, meta: Meta, message: str) -> html.Section:
    return html.Section(
        [
            html.H3(title),
            html.Div(message, className="empty"),
            html.Div(
                [
                    html.Div([html.H4("Definición"), html.P(meta.definition)], className="meta-block"),
                    sources_block(meta),
                    html.Div([html.H4("Advertencias metodológicas"), html.Ul([html.Li(c) for c in meta.caveats])], className="meta-block"),
                ],
                className="meta-grid",
            ),
        ],
        className="card",
    )


def stat_tile(label: str, value: str, sub: str, highlight: bool = False) -> html.Div:
    return html.Div(
        [html.Div(label, className="tile-label"), html.Div(value, className="tile-value"), html.Div(sub, className="tile-sub")],
        className="tile highlight" if highlight else "tile",
    )
