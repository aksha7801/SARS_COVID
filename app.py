from __future__ import annotations

import os
from pathlib import Path

import pandas as pd
import streamlit as st

from src.views import (
    EXCESS_TITLE,
    PUBLISHER,
    WEEKLY_TITLE,
    render_divergence_view,
    render_timeline_view,
    render_tracking_view,
)


ROOT = Path(__file__).resolve().parent
SAMPLE = ROOT / "data" / "sample.csv"
PROCESSED = ROOT / "data" / "processed.csv"
STRING_COLUMNS = {"country_code": "string", "country": "string", "who_region": "string", "estimate_type": "string"}


@st.cache_data
def load_data(path: str) -> pd.DataFrame:
    # Explicit string dtypes and keep_default_na=False keep identifiers such as "NA" intact.
    frame = pd.read_csv(path, dtype=STRING_COLUMNS, keep_default_na=False, na_values=[""], parse_dates=["date"])
    for column in ("country_code", "country", "who_region", "estimate_type"):
        frame[column] = frame[column].astype(object)
    return frame.sort_values(["country", "date"]).reset_index(drop=True)


def data_path() -> Path:
    sample_mode = os.getenv("DASHBOARD_SAMPLE_MODE", "0") == "1"
    if sample_mode or not PROCESSED.exists():
        return SAMPLE
    return PROCESSED


st.set_page_config(page_title="Reported vs excess COVID-19 deaths", layout="wide")
st.title("Reported COVID-19 deaths versus estimated excess deaths, 2020-2021")
st.write(
    "**Question:** How closely do the COVID-19 deaths that countries reported to the World Health "
    "Organization track WHO's modelled estimate of excess deaths, and where do the two diverge most?"
)
st.caption(
    "Audience: public-health analysts and policy advisers who need to judge where official COVID-19 "
    "death counts understate, or roughly match, the pandemic's total mortality impact."
)

data = load_data(str(data_path()))
countries = data["country_code"].nunique()
st.caption(
    f"Coverage: {countries} countries, 24 months (January 2020 to December 2021), one row per country-month. "
    "Excess deaths are WHO modelled estimates, not counts."
)

last = data[data["date"] == data["date"].max()]
reported_total, excess_total = float(last["cumulative_reported_deaths"].sum()), float(last["cumulative_excess_deaths"].sum())
if reported_total > 0 and excess_total > 0:
    st.info(
        f"**In the {countries} countries loaded,** {reported_total:,.0f} COVID-19 deaths were reported "
        f"to WHO by the end of 2021, against about {excess_total:,.0f} estimated excess deaths "
        f"({excess_total / reported_total:.1f}x as many). Excess deaths are all-cause deaths above what "
        "was expected, so they include deaths caused indirectly by the pandemic and carry model uncertainty; "
        "they are not a count of COVID-19 deaths."
    )

with st.container(key="tracking_overview"):
    render_tracking_view(data)

with st.container(key="divergence_ranking"):
    render_divergence_view(data)

with st.container(key="country_timeline"):
    render_timeline_view(data)

with st.expander("Data, definitions and limitations"):
    st.markdown(
        f"**Sources:** (1) {WEEKLY_TITLE}, published by the {PUBLISHER}. "
        f"(2) {EXCESS_TITLE}, published by the {PUBLISHER}."
    )
    st.markdown(
        "**Reported deaths** are COVID-19 deaths that national authorities reported to WHO, summed by "
        "the WHO week-ending date and allocated to the month in which that week ends. The week ending 26 "
        "December 2021 is the last one counted, so a few days at the end of 2021 fall outside the totals. "
        "WHO revises earlier weeks, and countries differ in testing, in how a COVID-19 death is defined "
        "and in reporting completeness."
    )
    st.markdown(
        "**Excess deaths** are WHO's modelled estimate of all-cause deaths above the number expected "
        "without the pandemic (central estimate with a 95% interval for the running total). The estimate "
        "covers deaths associated with the pandemic directly or indirectly, and WHO removed deaths from "
        "other shocks such as conflict and natural disasters. In months marked *predicted*, WHO's all-cause "
        "deaths were themselves modelled because national records were unavailable."
    )
    st.markdown(
        "**What this cannot show:** the gap between the two series is not an error rate in any country's "
        "reporting. It mixes under-reporting, indirect deaths, differences in definitions and modelling "
        "uncertainty. Counts are not adjusted for population size or age structure, so comparing countries "
        "of very different size should be done with care. WHO's estimates stop at December 2021; "
        "later years are not covered."
    )
    st.markdown(
        "WHO's disclaimer applies: these estimates may differ from, and should not be regarded as, "
        "official national statistics, and this dashboard is not endorsed by or affiliated with WHO."
    )
