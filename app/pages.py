"""One function per page. Each returns the page body for the router in app.main."""

from __future__ import annotations

from dash import dcc, html

from app import charts, data
from app.charts import _fmt
from app.components import chart_card, empty_card, stat_tile
from indicators import electricity_prices, interest_education, net_investment, pisa, productivity


def synthesis():
    df = data.table("net_investment")
    last = int(df.loc[df["status"] == "ok", "year"].max())
    tiles = []
    for geo in ["ES", "FR", "DE", "IT", "PT", "PL", "EU27_2020"]:
        sub = df[df["geo"] == geo]
        latest = sub[sub["year"] == last]["net_pc_gdp"].iloc[0]
        n_neg = int(sub["consumes_stock"].fillna(False).sum())
        years = f"{int(sub['year'].min())}–{last}"
        tiles.append(
            stat_tile(
                sub["geo_name"].iloc[0],
                "sin dato" if latest != latest else f"{_fmt(latest, 2)} %",
                f"{n_neg} años ≤ 0 en {years}",
                highlight=geo in ("ES", "FR"),
            )
        )
    m = net_investment.META
    return html.Div(
        [
            html.P(
                "Inversión pública neta: lo que las administraciones invierten en capital fijo menos lo que "
                "se estima que ese capital se deprecia en el año. Por debajo de cero, el stock público "
                "se reduce.",
                className="lede",
            ),
            html.H3(f"Inversión pública neta en {last} (% del PIB)", className="section-title"),
            html.Div(tiles, className="tiles"),
            chart_card(
                "Inversión pública neta por país y año (% del PIB)",
                charts.net_heatmap(df),
                m,
                note="Rojo: la inversión no cubre el consumo de capital fijo estimado. Azul: el stock crece.",
                missing=data.missing_ranges(df, "net_pc_gdp"),
            ),
            chart_card(
                "Evolución (% del PIB)",
                charts.country_lines(df, x="year", y="net_pc_gdp", y_title="% del PIB", zero_line=True, band=(-0.1, 0.1)),
                m,
                note="La franja gris (±0,1 pp) marca valores cuyo signo no es concluyente.",
                missing=data.missing_ranges(df, "net_pc_gdp"),
            ),
            dcc.Link("Detalle: inversión bruta y consumo de capital fijo →", href="/inversion-neta", className="more"),
        ]
    )


def net_investment_page():
    df = data.table("net_investment")
    m = net_investment.META
    cols = ["geo_name", "year", "gfcf_pc_gdp", "cfc_pc_gdp", "net_pc_gdp", "net_meur", "obs_flags", "status"]
    return html.Div(
        [
            chart_card(
                "Inversión pública neta (% del PIB)",
                charts.country_lines(df, x="year", y="net_pc_gdp", y_title="% del PIB", zero_line=True, band=(-0.1, 0.1)),
                m,
                missing=data.missing_ranges(df, "net_pc_gdp"),
                table=df[cols].round(3),
            ),
            chart_card(
                "España y Francia: inversión bruta frente a consumo de capital fijo",
                charts.gross_vs_cfc(df),
                m,
                note="Cuando la línea discontinua (depreciación estimada) supera a la continua, la inversión neta es negativa.",
                missing=data.missing_ranges(df[df["geo"].isin(["ES", "FR"])], "net_pc_gdp"),
            ),
        ]
    )


def interest_education_page():
    df = data.table("interest_education")
    m = interest_education.META
    cols = ["geo_name", "year", "interest_pc_gdp", "education_pc_gdp", "interest_to_education", "obs_flags", "status"]
    return html.Div(
        [
            chart_card(
                "Euros de intereses por cada euro de gasto en educación",
                charts.country_lines(df, x="year", y="interest_to_education", y_title="intereses / educación", ref_line=1),
                m,
                note="Por encima de 1, el Estado paga más en intereses que lo que gasta en educación.",
                missing=data.missing_ranges(df, "interest_to_education"),
                table=df[cols].round(3),
            ),
            chart_card(
                "Intereses y educación (% del PIB)",
                charts.two_measures(df),
                m,
                missing=data.missing_ranges(df[df["geo"].isin(["ES", "FR", "EU27_2020"])], "education_pc_gdp")
                + data.missing_ranges(df[df["geo"].isin(["ES", "FR", "EU27_2020"])], "interest_pc_gdp"),
            ),
        ]
    )


def electricity_page():
    df = data.table("electricity_prices")
    m = electricity_prices.META
    eu = df[df["geo"] != "US"]
    has_us = df.loc[df["geo"] == "US", "price_eur_kwh"].notna().any()
    fig = charts.country_lines(
        df, x="date", y="price_eur_kwh", y_title="EUR/kWh, sin IVA", decimals=3,
        dash_col="series", dashed=("consumer_Ie", "us_eia"), labels=electricity_prices.SERIES,
    )
    fig.add_vline(x="2007-07-01", line={"color": "#c3c2b7", "width": 1, "dash": "dot"})
    fig.add_annotation(x="2007-07-01", y=1, yref="paper", text="cambio de metodología", showarrow=False,
                       xanchor="left", xshift=4, font={"size": 11, "color": "#898781"})
    missing = [f"{electricity_prices.SERIES[s]} · {line}" for s, sub in df.groupby("series")
               for line in data.missing_ranges(sub, "price_eur_kwh", period="period")]
    note = "Semestral; hasta 2007, línea punteada (consumidor tipo Ie, no comparable con la banda ID)."
    if not has_us:
        note += " La serie de EE. UU. no está disponible en esta extracción."
    cols = ["geo_name", "series_label", "period", "price_eur_kwh", "obs_flags", "status"]
    return html.Div([chart_card("Precio de la electricidad para la industria", fig, m, note=note,
                                missing=missing, table=df[cols].round(4))])


def productivity_page():
    df = data.table("productivity")
    m = productivity.META
    cols = ["geo_name", "year", "level_pc_eu27_pps", "real_index_2015", "real_index_1995", "obs_flags", "status"]
    return html.Div(
        [
            chart_card(
                "Nivel: PIB por hora trabajada (UE-27 = 100, en PPS)",
                charts.country_lines(df, x="year", y="level_pc_eu27_pps", y_title="UE-27 = 100", decimals=1, ref_line=100),
                m,
                note="Compara países dentro de un mismo año; no debe leerse como serie temporal.",
                missing=data.missing_ranges(df, "level_pc_eu27_pps"),
                table=df[cols].round(2),
            ),
            chart_card(
                "Evolución: productividad real por hora (1995 = 100)",
                charts.country_lines(df, x="year", y="real_index_1995", y_title="índice, 1995 = 100", decimals=1, ref_line=100),
                m,
                missing=data.missing_ranges(df, "real_index_1995"),
            ),
        ]
    )


def pisa_page():
    df = data.table("pisa")
    m = pisa.META
    if df["mean"].notna().sum() == 0:
        return html.Div([empty_card(
            "Rendimiento PISA por cohortes", m,
            "Sin datos: PISA no se publica en una API y aún no se ha importado el CSV manual "
            "(data/manual/pisa/README.md explica el formato y cómo documentar la fecha de descarga).",
        )])
    df = df.assign(series=df["subject"])
    cols = ["geo_name", "edition", "cohort", "subject", "mean", "se", "trend_comparable", "status"]
    missing = [f"{s}: {line}" for s, sub in df.groupby("subject") for line in data.missing_ranges(sub, "mean", period="edition")]
    return html.Div([chart_card(
        "Rendimiento PISA por edición (y cohorte de nacimiento)", charts.pisa_lines(df), m,
        note="Círculo hueco: matemáticas 2000, no comparable con la tendencia.", missing=missing, table=df[cols],
    )])


PAGES = {
    "/": ("Síntesis", synthesis),
    "/inversion-neta": ("1 · Inversión neta", net_investment_page),
    "/intereses-educacion": ("2 · Intereses y educación", interest_education_page),
    "/electricidad": ("3 · Electricidad", electricity_page),
    "/productividad": ("4 · Productividad", productivity_page),
    "/pisa": ("5 · PISA", pisa_page),
    "/metodologia": ("Metodología", None),
}
