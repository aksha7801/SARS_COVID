"""Acquire, transform and validate the SARS-CoV-2 dashboard dataset.

One module holds the whole data pipeline so its lineage is inspectable:

* ``acquire()``       fetches the WHO weekly reported-deaths file (script) and prints
                      the one manual step (the WHO excess-mortality workbook).
* ``transform_raw()`` joins the two raw WHO sources into one country-month table.
* ``transform_sample()`` re-derives and re-checks the bundled sample (offline mode).
* ``validate()``      stops the pipeline when the table breaks a documented rule.
* ``main()``          runs the right path and writes ``data/processed.csv``.

Presentation lives in ``views.py`` and ``app.py``.

Units: every measure is a count of deaths in one calendar month (or a running total
from January 2020), so the unit is "deaths".
"""

from __future__ import annotations

import argparse
import os
import sys
import unicodedata
import warnings
from pathlib import Path
from urllib.error import URLError
from urllib.request import Request, urlopen

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
SAMPLE = ROOT / "data" / "sample.csv"
PROCESSED = ROOT / "data" / "processed.csv"
RAW_DIR = ROOT / "data" / "raw"
WEEKLY_RAW = RAW_DIR / "WHO-COVID-19-global-data.csv"
EXCESS_RAW = RAW_DIR / "WHO_COVID_Excess_Deaths_EstimatesByCountry.xlsx"

WEEKLY_URL = "https://srhdpeuwpubsa.blob.core.windows.net/whdh/COVID/WHO-COVID-19-global-data.csv"
EXCESS_PAGE = (
    "https://www.who.int/data/sets/"
    "global-excess-deaths-associated-with-covid-19-modelled-estimates"
)

MONTH_ENDS = pd.date_range("2020-01-31", "2021-12-31", freq="ME")
REGIONS = ["AFRO", "AMRO", "EMRO", "EURO", "SEARO", "WPRO"]
ESTIMATE_TYPES = ["reported", "predicted"]

# Sample = a documented subset of countries (all 24 months each), spanning every WHO region
# and including one country with negative estimated excess (China).
SAMPLE_COUNTRIES = [
    "AUS", "BRA", "CHN", "DEU", "EGY", "FRA", "IDN", "IND", "JPN",
    "MEX", "NGA", "PAK", "PER", "RUS", "USA", "ZAF",
]

# Workbook ISO3 -> WHO weekly ISO2 where the two files spell the country name differently.
NAME_OVERRIDES = {"GBR": "GB", "NLD": "NL", "CIV": "CI", "TUR": "TR"}

COLUMNS = [
    "date", "country_code", "country", "who_region", "estimate_type",
    "reported_deaths", "cumulative_reported_deaths",
    "expected_deaths", "all_cause_deaths", "excess_deaths",
    "cumulative_excess_deaths", "cumulative_excess_low", "cumulative_excess_high",
]
INTEGER_COLUMNS = ["reported_deaths", "cumulative_reported_deaths"]
FLOAT_COLUMNS = [
    "expected_deaths", "all_cause_deaths", "excess_deaths",
    "cumulative_excess_deaths", "cumulative_excess_low", "cumulative_excess_high",
]
STRING_COLUMNS = ["country_code", "country", "who_region", "estimate_type"]
# Plausible ranges (deaths). Excess can be negative; reported counts cannot.
RANGES = {
    "reported_deaths": (0, 5_000_000),
    "cumulative_reported_deaths": (0, 20_000_000),
    "expected_deaths": (0, 5_000_000),
    "all_cause_deaths": (0, 5_000_000),
    "excess_deaths": (-5_000_000, 10_000_000),
    "cumulative_excess_deaths": (-5_000_000, 20_000_000),
    "cumulative_excess_low": (-10_000_000, 20_000_000),
    "cumulative_excess_high": (-5_000_000, 30_000_000),
}


# --------------------------------------------------------------------------- acquire
def acquire() -> None:
    """Download the WHO weekly file; the excess workbook must be downloaded by hand."""
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    request = Request(WEEKLY_URL, headers={"User-Agent": "Mozilla/5.0 (dashboard-pipeline)"})
    try:
        with urlopen(request, timeout=60) as response:
            payload = response.read()
    except (URLError, TimeoutError, OSError) as error:
        sys.exit(
            f"Could not fetch {WEEKLY_URL}: {error}. Check your connection, or rerun "
            "with DASHBOARD_SAMPLE_MODE=1 to use the bundled sample."
        )
    WEEKLY_RAW.write_bytes(payload)
    print(f"Wrote {WEEKLY_RAW} ({len(payload):,} bytes)")
    print(
        "MANUAL STEP: the WHO excess-mortality workbook has no stable direct link. "
        f"Download 'WHO_COVID_Excess_Deaths_EstimatesByCountry.xlsx' from {EXCESS_PAGE} "
        f"and save it as {EXCESS_RAW}. The bundled copy is the 5 April 2023 release."
    )


# ------------------------------------------------------------------------- transform
def _fix_mojibake(text: str) -> str:
    """The WHO workbook stores a few names (Cote d'Ivoire, Turkiye) double-encoded."""
    try:
        return text.encode("latin-1").decode("utf-8")
    except (UnicodeEncodeError, UnicodeDecodeError):
        return text


def _ascii(text: str) -> str:
    """Fold accents (Cote d'Ivoire, Turkiye) so every file stays plain ASCII on any platform."""
    return unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")


def read_weekly(path: Path = WEEKLY_RAW) -> pd.DataFrame:
    # keep_default_na=False: Namibia's ISO2 code is the literal string "NA".
    frame = pd.read_csv(path, keep_default_na=False, na_values=[""], encoding_errors="replace")
    frame["date_reported"] = pd.to_datetime(frame["Date_reported"], errors="raise")
    return frame


def read_excess(path: Path = EXCESS_RAW) -> pd.DataFrame:
    # Imported here so the offline sample path needs no spreadsheet library.
    frame = pd.read_excel(
        path, sheet_name="Deaths by year and month", header=12,
        keep_default_na=False, na_values=[""],
    )
    frame = frame.dropna(subset=["iso3"]).copy()  # drops the footnote rows under the table
    frame["Country"] = frame["Country"].map(_fix_mojibake)  # repaired here, folded to ASCII on output
    return frame


def _month_end_cumulative(weekly: pd.DataFrame) -> tuple[pd.DataFrame, int]:
    """Cumulative reported deaths at each month end, by WHO ISO2 code.

    A week is assigned to the month in which its WHO week-ending date falls, so the
    week ending 2021-12-26 is the last one counted in December 2021. Downward
    revisions in WHO's cumulative counter are ignored (running maximum); the number of
    adjusted points is returned so the caller can warn about it.
    """
    pieces, adjusted = [], 0
    for code, group in weekly.sort_values("date_reported").groupby("Country_code"):
        series = group.set_index("date_reported")["Cumulative_deaths"].astype("int64")
        series = series[~series.index.duplicated(keep="last")]
        aligned = series.reindex(series.index.union(MONTH_ENDS)).ffill().reindex(MONTH_ENDS)
        aligned = aligned.fillna(0).astype("int64")
        monotone = aligned.cummax()
        adjusted += int((monotone != aligned).sum())
        pieces.append(pd.DataFrame({
            "Country_code": code, "date": MONTH_ENDS, "cumulative_reported_deaths": monotone.to_numpy(),
        }))
    return pd.concat(pieces, ignore_index=True), adjusted


def transform_raw(weekly: pd.DataFrame, excess: pd.DataFrame) -> pd.DataFrame:
    """Join WHO reported deaths to WHO modelled excess deaths at country-month level."""
    cumulative, adjusted = _month_end_cumulative(weekly)
    if adjusted:
        warnings.warn(
            f"{adjusted} month-end cumulative reported-death values were lower than an "
            "earlier month (WHO revision); the earlier value was carried forward.",
            stacklevel=2,
        )
    names = weekly.drop_duplicates("Country_code")[["Country_code", "Country", "WHO_region"]]
    names = names.rename(columns={"Country": "who_name"})

    excess = excess.copy()
    excess["date"] = (
        pd.to_datetime(dict(year=excess["year"].astype(int), month=excess["month"].astype(int), day=1))
        + pd.offsets.MonthEnd(0)
    )
    # Link the files by ISO2 code: by WHO country name, with four documented overrides.
    by_name = names.assign(Country=names["who_name"].map(_fix_mojibake)).set_index("Country")["Country_code"]
    excess["Country_code"] = excess["Country"].map(by_name)
    for iso3, iso2 in NAME_OVERRIDES.items():
        excess.loc[excess["iso3"] == iso3, "Country_code"] = iso2
    unmatched = sorted(excess.loc[excess["Country_code"].isna(), "Country"].unique())
    if unmatched:
        raise ValueError(f"Countries in the excess workbook with no WHO weekly match: {unmatched}")

    merged = (
        excess.merge(names[["Country_code", "WHO_region"]], on="Country_code", how="left")
        .merge(cumulative, on=["Country_code", "date"], how="left", validate="one_to_one")
        .sort_values(["iso3", "date"])
    )
    merged["reported_deaths"] = (
        merged.groupby("iso3")["cumulative_reported_deaths"].diff()
        .fillna(merged["cumulative_reported_deaths"]).astype("int64")
    )
    frame = pd.DataFrame({
        "date": merged["date"],
        "country_code": merged["iso3"].astype(str),
        "country": merged["Country"].map(_ascii).astype(str),
        "who_region": merged["WHO_region"].astype(str),
        "estimate_type": merged["type"].astype(str),
        "reported_deaths": merged["reported_deaths"],
        "cumulative_reported_deaths": merged["cumulative_reported_deaths"],
        "expected_deaths": merged["expected.mean"],
        "all_cause_deaths": merged["acm.mean"],
        "excess_deaths": merged["excess.mean*"],
        "cumulative_excess_deaths": merged["cumul.excess.mean*"],
        "cumulative_excess_low": merged["cumul.excess.low*"],
        "cumulative_excess_high": merged["cumul.excess.high*"],
    })
    return _finalise(frame)


def transform_sample(sample: pd.DataFrame) -> pd.DataFrame:
    """Offline path: re-derive the running total from monthly counts and compare it."""
    frame = sample.copy()
    frame["date"] = pd.to_datetime(frame["date"], errors="raise")
    frame = frame.sort_values(["country_code", "date"])
    derived = frame.groupby("country_code")["reported_deaths"].cumsum()
    if not (derived == frame["cumulative_reported_deaths"]).all():
        raise ValueError("cumulative_reported_deaths does not equal the running sum of reported_deaths")
    return _finalise(frame)


def _finalise(frame: pd.DataFrame) -> pd.DataFrame:
    frame = frame.copy()
    frame["date"] = pd.to_datetime(frame["date"], errors="raise").dt.strftime("%Y-%m-%d")
    for column in INTEGER_COLUMNS:
        frame[column] = frame[column].astype("int64")
    for column in FLOAT_COLUMNS:
        frame[column] = frame[column].astype("float64").round(3)
    return frame.sort_values(["country", "date"]).reset_index(drop=True)[COLUMNS]


# ------------------------------------------------------------------------- validate
def validate(frame: pd.DataFrame) -> None:
    """Stop the pipeline if the dataset breaks a documented expectation."""
    missing_columns = set(COLUMNS).difference(frame.columns)
    if missing_columns:
        raise ValueError(f"Missing columns: {sorted(missing_columns)}")
    if len(frame) < 100:
        raise ValueError("The dataset must contain at least 100 country-month rows")
    if frame[COLUMNS].isna().any().any():
        raise ValueError("Unexpected missing values found")
    if frame.duplicated(["date", "country_code"]).any():
        raise ValueError("Duplicate date and country_code keys found")

    dates = pd.to_datetime(frame["date"], errors="raise")
    if dates.min() < pd.Timestamp("2020-01-31") or dates.max() > pd.Timestamp("2021-12-31"):
        raise ValueError("Date outside the documented period 2020-01-31 to 2021-12-31")
    if not (dates + pd.offsets.MonthEnd(0) == dates).all():
        raise ValueError("Dates must be month-end dates")
    counts = frame.groupby("country_code")["date"].nunique()
    if (counts != len(MONTH_ENDS)).any():
        raise ValueError(f"Every country needs {len(MONTH_ENDS)} months; incomplete: {sorted(counts[counts != len(MONTH_ENDS)].index)}")
    if frame.groupby("country_code")["country"].nunique().max() != 1:
        raise ValueError("A country code maps to more than one country name")
    if not set(frame["who_region"]).issubset(REGIONS):
        raise ValueError(f"Unexpected WHO region: {sorted(set(frame['who_region']) - set(REGIONS))}")
    if not set(frame["estimate_type"]).issubset(ESTIMATE_TYPES):
        raise ValueError("Unexpected estimate_type")
    if not frame["country_code"].str.fullmatch(r"[A-Z]{3}").all():
        raise ValueError("country_code must be an ISO 3166-1 alpha-3 code")

    for column, (low, high) in RANGES.items():
        values = pd.to_numeric(frame[column], errors="raise")
        if not values.between(low, high).all():
            raise ValueError(f"{column} outside the plausible range {low} to {high} deaths")
    for column in INTEGER_COLUMNS:
        if (frame[column] % 1 != 0).any():
            raise ValueError(f"{column} must be whole numbers of deaths")

    ordered = frame.assign(date=dates).sort_values(["country_code", "date"])
    grouped = ordered.groupby("country_code")
    if not (ordered["cumulative_reported_deaths"] == grouped["reported_deaths"].cumsum()).all():
        raise ValueError("cumulative_reported_deaths is not the running sum of reported_deaths")
    drift = (ordered["cumulative_excess_deaths"] - grouped["excess_deaths"].cumsum()).abs()
    if (drift > 0.5).any():
        raise ValueError("cumulative_excess_deaths is not the running sum of excess_deaths (tolerance 0.5 deaths)")
    # WHO's workbook footnote says deaths from other shocks (conflict, disasters) were
    # removed from published excess, so excess_deaths need not equal all-cause minus
    # expected. Small differences are warned about; a large one stops the pipeline.
    gap = (ordered["all_cause_deaths"] - ordered["expected_deaths"] - ordered["excess_deaths"]).abs()
    if (gap > 0.25 * ordered["expected_deaths"].clip(lower=1)).any():
        raise ValueError("excess_deaths differs from all_cause_deaths minus expected_deaths by over 25% of expected deaths")
    if (gap > 0.5).any():
        warnings.warn(
            f"{int((gap > 0.5).sum())} country-months in {ordered.loc[gap > 0.5, 'country_code'].nunique()} "
            f"countries have excess_deaths different from all_cause_deaths minus expected_deaths "
            f"(largest difference {gap.max():,.0f} deaths); published WHO excess is kept as supplied.",
            stacklevel=2,
        )
    bounds_ok = (
        (ordered["cumulative_excess_low"] <= ordered["cumulative_excess_deaths"] + 0.5)
        & (ordered["cumulative_excess_deaths"] <= ordered["cumulative_excess_high"] + 0.5)
    )
    if not bounds_ok.all():
        raise ValueError("The cumulative excess interval does not bracket its mean")


# ------------------------------------------------------------------------------ main
def read_table(path: Path) -> pd.DataFrame:
    return pd.read_csv(
        path,
        dtype={column: "string" for column in STRING_COLUMNS} | {"date": "string"},
        keep_default_na=False,
        na_values=[""],
    )


def build_sample_from_processed() -> None:
    """Re-cut data/sample.csv from the full processed table (run after a live build)."""
    full = read_table(PROCESSED)
    subset = full[full["country_code"].isin(SAMPLE_COUNTRIES)]
    validate(subset)
    subset.to_csv(SAMPLE, index=False)
    print(f"Wrote {len(subset)} rows ({subset['country_code'].nunique()} countries) to {SAMPLE}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--acquire", action="store_true", help="Download the WHO weekly file and stop")
    parser.add_argument("--validate", action="store_true", help="Validate data/processed.csv and stop")
    parser.add_argument("--make-sample", action="store_true", help="Re-cut data/sample.csv from data/processed.csv")
    args = parser.parse_args()
    sample_mode = os.getenv("DASHBOARD_SAMPLE_MODE", "0") == "1"
    if args.acquire:
        if sample_mode:
            parser.error("Unset DASHBOARD_SAMPLE_MODE before acquiring live data")
        acquire()
        return
    if args.validate:
        validate(read_table(PROCESSED))
        print("Processed data valid")
        return
    if args.make_sample:
        build_sample_from_processed()
        return
    if sample_mode:
        frame = transform_sample(read_table(SAMPLE))
    else:
        missing = [path for path in (WEEKLY_RAW, EXCESS_RAW) if not path.exists()]
        if missing:
            sys.exit(f"Missing raw files: {[str(p) for p in missing]}. Run `python -m src.data --acquire` first.")
        frame = transform_raw(read_weekly(), read_excess())
    validate(frame)
    PROCESSED.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(PROCESSED, index=False)
    print(f"Validated and wrote {len(frame)} rows ({frame['country_code'].nunique()} countries) to {PROCESSED}")


if __name__ == "__main__":
    main()
