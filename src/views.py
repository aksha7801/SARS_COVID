"""Streamlit views for the SARS-CoV-2 reported-vs-excess-deaths dashboard.

Each ``render_*`` function draws one principal view. ``app.py`` wraps every call in
``st.container(key=<view id>)`` so the manifest ids match the page.
"""

from __future__ import annotations

import altair as alt
import pandas as pd
import streamlit as st

WEEKLY_TITLE = "WHO COVID-19 dashboard: Weekly COVID-19 cases and deaths by date reported to WHO"
EXCESS_TITLE = (
    "WHO Estimates of Excess Mortality Associated with COVID-19 Pandemic "
    "(as of 5 April 2023): Estimates by country"
)
PUBLISHER = "World Health Organization"
DATE_LABEL = "Latest observation"
DOWNLOAD_LABEL = "Download filtered data"
EMPTY_MESSAGE = "No observations match the selected filters."

REGION_NAMES = {
    "AFRO": "Africa",
    "AMRO": "Americas",
    "EMRO": "Eastern Mediterranean",
    "EURO": "Europe",
    "SEARO": "South-East Asia",
    "WPRO": "Western Pacific",
}
MEASURES = {
    "Excess / reported (ratio)": "ratio",
    "Excess - reported (deaths)": "excess_minus_reported",
    "Reported - excess (deaths)": "reported_minus_excess",
}
TIMELINE_MEASURES = ["Monthly deaths", "Running total since Jan 2020 (with WHO 95% interval)"]
REGION_COLOURS = alt.Scale(
    domain=list(REGION_NAMES),
    range=["#0072B2", "#E69F00", "#009E73", "#CC79A7", "#D55E00", "#56B4E9"],
)


# ----------------------------------------------------------------------------- helpers
def _header(title: str, unit: str, data: pd.DataFrame, sources: bool = True) -> None:
    st.header(title)
    st.caption(f"Unit: {unit}")
    st.caption(f"{DATE_LABEL}: {data['date'].max().date().isoformat()}")
    if sources:
        st.caption(f"Source: {WEEKLY_TITLE}, {PUBLISHER}.")
        st.caption(f"Source: {EXCESS_TITLE}, {PUBLISHER}.")


def _csv_bytes(frame: pd.DataFrame) -> bytes:
    out = frame.copy()
    out["date"] = out["date"].dt.strftime("%Y-%m-%d")
    return out.to_csv(index=False).encode("utf-8")


def _download(frame: pd.DataFrame, key: str, file_name: str) -> None:
    st.download_button(
        DOWNLOAD_LABEL,
        data=_csv_bytes(frame),
        file_name=file_name,
        mime="text/csv",
        key=key,
    )


def _date_slider(data: pd.DataFrame, key: str) -> tuple:
    low, high = data["date"].min().date(), data["date"].max().date()
    return st.slider(
        "Months to include (month-end dates)",
        min_value=low,
        max_value=high,
        value=(low, high),
        format="YYYY-MM-DD",
        key=key,
    )


@st.cache_data(show_spinner=False)
def country_totals(frame: pd.DataFrame) -> pd.DataFrame:
    """Sum monthly reported and excess deaths per country over the rows supplied."""
    grouped = frame.groupby(["country_code", "country", "who_region"], as_index=False).agg(
        reported=("reported_deaths", "sum"),
        excess=("excess_deaths", "sum"),
    )
    return grouped


def _ratio(excess: pd.Series, reported: pd.Series, minimum: float) -> pd.Series:
    """Excess / reported, left empty where it would mislead (tiny or non-positive terms)."""
    usable = (reported >= max(minimum, 1)) & (excess > 0)
    return (excess / reported.where(usable)).where(usable)


# --------------------------------------------------------------------------- view 1
def render_tracking_view(data: pd.DataFrame) -> None:
    _header("How closely do reported deaths track estimated excess deaths?", "deaths (count of people)", data)

    regions = sorted(data["who_region"].unique())
    selected = st.multiselect(
        "WHO regions",
        regions,
        default=regions,
        format_func=lambda code: f"{code} ({REGION_NAMES.get(code, code)})",
        key="tracking_regions",
    )
    start, end = _date_slider(data, "tracking_period")
    st.write(f"Selected regions: {', '.join(selected) if selected else 'none'}")

    mask = data["who_region"].isin(selected) & data["date"].between(pd.Timestamp(start), pd.Timestamp(end))
    filtered = data.loc[mask].copy()

    if filtered.empty:
        st.info(EMPTY_MESSAGE)
    else:
        totals = country_totals(filtered)
        reported, excess = int(totals["reported"].sum()), float(totals["excess"].sum())
        columns = st.columns(4)
        columns[0].metric("Reported COVID-19 deaths", f"{reported:,.0f} deaths")
        columns[1].metric("WHO estimated excess deaths", f"{excess:,.0f} deaths")
        columns[2].metric(
            "Excess / reported",
            f"{excess / reported:.1f}x" if reported > 0 and excess > 0 else "not defined",
        )
        at_or_above = int((totals["reported"] >= totals["excess"]).sum())
        columns[3].metric("Countries reporting >= excess", f"{at_or_above} of {len(totals)}")

        plotted = totals[(totals["reported"] > 0) & (totals["excess"] > 0)]
        omitted = totals.loc[~totals.index.isin(plotted.index), "country"].tolist()
        if plotted.empty:
            st.info("No selected country has both reported and excess deaths above zero for this period, so nothing can be drawn on a log scale.")
        else:
            low, high = float(plotted[["reported", "excess"]].min().min()), float(plotted[["reported", "excess"]].max().max())
            diagonal = pd.DataFrame({"reported": [low, high], "excess": [low, high]})
            points = (
                alt.Chart(plotted)
                .mark_circle(size=70, opacity=0.8)
                .encode(
                    x=alt.X("reported:Q", scale=alt.Scale(type="log"), title="Reported COVID-19 deaths (deaths, log scale)"),
                    y=alt.Y("excess:Q", scale=alt.Scale(type="log"), title="WHO estimated excess deaths (deaths, log scale)"),
                    color=alt.Color("who_region:N", scale=REGION_COLOURS, title="WHO region"),
                    tooltip=[
                        alt.Tooltip("country:N", title="Country"),
                        alt.Tooltip("who_region:N", title="WHO region"),
                        alt.Tooltip("reported:Q", title="Reported deaths", format=",.0f"),
                        alt.Tooltip("excess:Q", title="Excess deaths", format=",.0f"),
                    ],
                )
            )
            line = (
                alt.Chart(diagonal)
                .mark_line(strokeDash=[5, 4], color="#555555")
                .encode(x="reported:Q", y="excess:Q")
            )
            st.altair_chart((line + points).properties(height=420), width="stretch")
            st.caption(
                "Each dot is one country. The dashed line is where reported deaths equal estimated excess "
                "deaths; dots above it have more estimated excess than reported deaths. Totals are summed "
                "over the selected months."
            )
        if omitted:
            st.caption(
                f"Not drawn on the log scale (reported = 0 or estimated excess <= 0): {', '.join(sorted(omitted))}. "
                "They are still counted in the totals above."
            )
    _download(filtered, "tracking_download", "filtered_country_months.csv")


# --------------------------------------------------------------------------- view 2
def render_divergence_view(data: pd.DataFrame) -> None:
    _header("Where do reported deaths and estimated excess deaths diverge most?", "deaths (count of people) or ratio", data)
    st.caption("Totals cover the whole period, January 2020 to December 2021, the span of WHO's excess estimates.")

    regions = sorted(data["who_region"].unique())
    selected = st.multiselect(
        "WHO regions to rank",
        regions,
        default=regions,
        format_func=lambda code: f"{code} ({REGION_NAMES.get(code, code)})",
        key="ranking_regions",
    )
    measure_label = st.selectbox("Rank countries by", list(MEASURES), key="rank_measure")
    minimum = st.number_input(
        "Minimum reported deaths for a ratio",
        min_value=0,
        value=1000,
        step=500,
        key="min_reported",
        help="Ratios are unstable when few deaths were reported, so countries below this are not ranked by ratio.",
    )
    top_n = st.slider("Countries to show", min_value=3, max_value=30, value=10, key="top_n")

    filtered = data.loc[data["who_region"].isin(selected)].copy()
    if filtered.empty:
        st.info(EMPTY_MESSAGE)
    else:
        final = filtered[filtered["date"] == filtered["date"].max()].copy()
        final["reported"] = final["cumulative_reported_deaths"].astype(float)
        final["excess"] = final["cumulative_excess_deaths"]
        final["low"], final["high"] = final["cumulative_excess_low"], final["cumulative_excess_high"]
        measure = MEASURES[measure_label]
        if measure == "ratio":
            final["value"] = _ratio(final["excess"], final["reported"], minimum)
            final["value_low"] = final["low"].clip(lower=0) / final["reported"].where(final["value"].notna())
            final["value_high"] = final["high"] / final["reported"].where(final["value"].notna())
            reference, axis_title = 1.0, "Excess / reported deaths (ratio; 1 = equal)"
            unit_note = "A ratio of 3 means WHO's central estimate of excess deaths is three times the reported count."
        elif measure == "excess_minus_reported":
            final["value"] = final["excess"] - final["reported"]
            final["value_low"], final["value_high"] = final["low"] - final["reported"], final["high"] - final["reported"]
            reference, axis_title = 0.0, "Estimated excess - reported deaths (deaths)"
            unit_note = "Positive values: more estimated excess deaths than reported COVID-19 deaths."
        else:
            final["value"] = final["reported"] - final["excess"]
            final["value_low"], final["value_high"] = final["reported"] - final["high"], final["reported"] - final["low"]
            reference, axis_title = 0.0, "Reported - estimated excess deaths (deaths)"
            unit_note = "Positive values: more reported COVID-19 deaths than estimated excess deaths."

        ranked = final.dropna(subset=["value"]).sort_values("value", ascending=False)
        excluded = len(final) - len(ranked)
        top = ranked.head(top_n)
        if top.empty:
            st.info("No country meets the minimum reported deaths for a ratio. Lower the minimum to rank countries.")
        else:
            order = top["country"].tolist()
            base = alt.Chart(top)
            bars = base.mark_bar().encode(
                y=alt.Y("country:N", sort=order, title=None, axis=alt.Axis(labelLimit=260)),
                x=alt.X("value:Q", title=axis_title),
                color=alt.Color("who_region:N", scale=REGION_COLOURS, title="WHO region"),
                tooltip=[
                    alt.Tooltip("country:N", title="Country"),
                    alt.Tooltip("reported:Q", title="Reported deaths", format=",.0f"),
                    alt.Tooltip("excess:Q", title="Excess deaths (central)", format=",.0f"),
                    alt.Tooltip("value:Q", title="Ranking value", format=",.2f"),
                ],
            )
            whiskers = base.mark_rule(color="#222222").encode(
                y=alt.Y("country:N", sort=order), x="value_low:Q", x2="value_high:Q"
            )
            zero = alt.Chart(pd.DataFrame({"x": [reference]})).mark_rule(strokeDash=[4, 4], color="#555555").encode(x="x:Q")
            st.altair_chart((bars + whiskers + zero).properties(height=max(180, 28 * len(top))), width="stretch")
            st.caption(
                f"{unit_note} Whiskers span WHO's 95% interval for cumulative excess deaths; "
                "the reported count itself is treated as exact. Rankings favour large countries when "
                "measured in deaths and countries with little reported mortality when measured as a ratio; "
                "neither adjusts for population size."
            )
            table = top[["country", "who_region", "reported", "excess", "low", "high", "value"]].copy()
            table["within_interval"] = (table["reported"] >= table["low"]) & (table["reported"] <= table["high"])
            table.columns = [
                "Country", "WHO region", "Reported deaths", "Excess deaths (central)",
                "Excess 95% low", "Excess 95% high", "Ranking value", "Reported inside 95% interval",
            ]
            st.dataframe(
                table.round(2),
                hide_index=True,
                width="stretch",
                column_config={
                    "Reported deaths": st.column_config.NumberColumn(format="%d"),
                    "Excess deaths (central)": st.column_config.NumberColumn(format="%d"),
                    "Excess 95% low": st.column_config.NumberColumn(format="%d"),
                    "Excess 95% high": st.column_config.NumberColumn(format="%d"),
                },
            )
        if excluded:
            st.caption(
                f"{excluded} of {len(final)} countries cannot be ranked by this measure "
                "(for the ratio: fewer reported deaths than the minimum, or estimated excess <= 0)."
            )
    _download(filtered, "ranking_download", "filtered_country_months_ranking.csv")


# --------------------------------------------------------------------------- view 3
def render_timeline_view(data: pd.DataFrame) -> None:
    _header("When did reported deaths and estimated excess deaths diverge?", "deaths per month, or running total of deaths", data)

    countries = sorted(data["country"].unique())
    default = ["India"] if "India" in countries else countries[:1]
    selected = st.multiselect(
        "Countries (up to 6)", countries, default=default, max_selections=6, key="timeline_countries"
    )
    measure = st.radio("Show", TIMELINE_MEASURES, key="timeline_measure")
    start, end = _date_slider(data, "timeline_period")

    mask = data["country"].isin(selected) & data["date"].between(pd.Timestamp(start), pd.Timestamp(end))
    filtered = data.loc[mask].copy()
    if filtered.empty:
        st.info(EMPTY_MESSAGE)
    else:
        predicted_share = (filtered["estimate_type"] == "predicted").mean()
        st.metric(
            "Selected months where WHO's all-cause deaths are modelled, not reported",
            f"{predicted_share:.0%} of country-months",
        )
        if measure == TIMELINE_MEASURES[0]:
            long = pd.concat(
                [
                    filtered.assign(series="Reported COVID-19 deaths", deaths=filtered["reported_deaths"].astype(float)),
                    filtered.assign(series="WHO estimated excess deaths", deaths=filtered["excess_deaths"]),
                ]
            )
            lines = alt.Chart(long).mark_line().encode(
                x=alt.X("date:T", title="Month"),
                y=alt.Y("deaths:Q", title="Deaths per month (deaths)"),
                color=alt.Color("series:N", title=None, scale=alt.Scale(range=["#0072B2", "#D55E00"])),
            )
            dots = alt.Chart(long).mark_point(filled=True, size=45).encode(
                x="date:T",
                y="deaths:Q",
                color=alt.Color("series:N", title=None, scale=alt.Scale(range=["#0072B2", "#D55E00"])),
                shape=alt.Shape("estimate_type:N", title="WHO all-cause deaths", scale=alt.Scale(domain=["reported", "predicted"], range=["circle", "diamond"])),
                tooltip=[
                    alt.Tooltip("country:N", title="Country"),
                    alt.Tooltip("date:T", title="Month", format="%b %Y"),
                    alt.Tooltip("series:N", title="Series"),
                    alt.Tooltip("deaths:Q", title="Deaths", format=",.0f"),
                    alt.Tooltip("estimate_type:N", title="WHO all-cause deaths"),
                ],
            )
            chart = alt.layer(lines, dots).properties(width=330, height=240).facet(
                facet=alt.Facet("country:N", title=None), columns=2
            )
            caption = (
                "Monthly reported deaths use WHO's weekly counts, assigned to the month of the week-ending "
                "date. Diamonds mark months where WHO's all-cause deaths were modelled rather than taken from "
                "national records, so the excess estimate for those months is more uncertain."
            )
        else:
            long = pd.concat(
                [
                    filtered.assign(series="Reported COVID-19 deaths", deaths=filtered["cumulative_reported_deaths"].astype(float)),
                    filtered.assign(series="WHO estimated excess deaths", deaths=filtered["cumulative_excess_deaths"]),
                ]
            )
            # Both layers must share one data frame so the layered chart can be faceted.
            band = (
                alt.Chart(long)
                .transform_filter(alt.datum.series == "WHO estimated excess deaths")
                .mark_area(opacity=0.2, color="#D55E00")
                .encode(
                    x=alt.X("date:T", title="Month"),
                    y=alt.Y("cumulative_excess_low:Q", title="Running total of deaths since Jan 2020 (deaths)"),
                    y2="cumulative_excess_high:Q",
                )
            )
            lines = alt.Chart(long).mark_line().encode(
                x="date:T",
                y="deaths:Q",
                color=alt.Color("series:N", title=None, scale=alt.Scale(range=["#0072B2", "#D55E00"])),
                tooltip=[
                    alt.Tooltip("country:N", title="Country"),
                    alt.Tooltip("date:T", title="Month", format="%b %Y"),
                    alt.Tooltip("series:N", title="Series"),
                    alt.Tooltip("deaths:Q", title="Running total (deaths)", format=",.0f"),
                ],
            )
            chart = alt.layer(band, lines).properties(width=330, height=240).facet(
                facet=alt.Facet("country:N", title=None), columns=2
            )
            caption = (
                "Running totals start in January 2020 whatever months are selected. The shaded band is WHO's "
                "95% interval for cumulative excess deaths; the reported series has no interval."
            )
        st.altair_chart(chart, width="stretch")
        st.caption(caption)
    _download(filtered, "timeline_download", "filtered_country_timeline.csv")
