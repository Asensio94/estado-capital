"""Dash app: a header with navigation and one page per indicator, routed by URL path."""

from __future__ import annotations

from dash import Dash, Input, Output, dcc, html

from app import data, pages
from etl.phase2 import PENDING

app = Dash(__name__, title="Estado del capital", suppress_callback_exceptions=True)
server = app.server  # for gunicorn


def methodology_page():
    built = data.manifest().get("built_at")
    return html.Div(
        [
            html.Section(
                [
                    html.H3("Cómo se calcula"),
                    html.Ol(
                        [
                            html.Li("El ETL descarga las series de la API de Eurostat (y de la EIA) y guarda la respuesta íntegra con su fecha de extracción."),
                            html.Li("Antes de cada descarga comprueba que todos los códigos (dataset, partidas, unidades, países) existen en los metadatos de la API."),
                            html.Li("Los porcentajes del PIB se calculan desde niveles en millones de euros; los porcentajes redondeados de Eurostat se usan solo como control."),
                            html.Li("Cada país y año del periodo aparece siempre: si falta un dato, se muestra como ausente. No se interpola nada."),
                        ]
                    ),
                    html.P(f"Última construcción de los datos: {data.fmt_date(built)}." if built else "Aún no se han construido los datos."),
                    html.P("La discusión completa está en METHODOLOGY.md, en el repositorio."),
                ],
                className="card",
            ),
            html.Section(
                [
                    html.H3("Fase 2 (pendiente)"),
                    html.Ul([html.Li([html.B(p.name), f" — {p.feeds}. Acceso: {p.access}."]) for p in PENDING]),
                ],
                className="card",
            ),
        ]
    )


def nav(path: str):
    return html.Nav(
        [dcc.Link(label, href=href, className="active" if href == path else "") for href, (label, _) in pages.PAGES.items()],
        className="nav",
    )


app.layout = html.Div(
    [
        dcc.Location(id="url"),
        html.Header(
            [
                html.H1("Estado del capital"),
                html.P("¿Mantienen España y Francia su capital público y humano, o lo consumen? "
                       "Comparación con Alemania, Italia, Portugal, Polonia y la UE-27 desde 1995, con fuentes oficiales."),
                html.Div(id="nav"),
            ],
            className="site-header",
        ),
        html.Main(id="page"),
        html.Footer(
            html.P(["Datos: Eurostat, EIA, OCDE. Código y metodología en el repositorio del proyecto. ",
                    "Las cifras recientes son provisionales."]),
            className="site-footer",
        ),
    ]
)


@app.callback(Output("page", "children"), Output("nav", "children"), Input("url", "pathname"))
def route(path: str | None):
    path = path if path in pages.PAGES else "/"
    _, render = pages.PAGES[path]
    try:
        body = methodology_page() if render is None else render()
    except data.NoData as exc:
        body = html.Section([html.H3("Sin datos procesados"), html.P(str(exc))], className="card")
    return body, nav(path)
