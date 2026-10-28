"""Create auditable city-day PM2.5 averages from cleaned observations."""

from pathlib import Path
import pandas as pd

RAW = Path("data/processed/observations_clean.csv")
OUT = Path("data/processed/city_daily.csv")

VALID_POLLUTANTS = {"PM2.5", "PM25", "PM₂.₅"}
VALID_UNITS = {
    "ug/m3", "µg/m3", "μg/m3",
    "ug/m³", "µg/m³", "μg/m³",
}


def normalize_unit(value):
    """Normalize common microgram-per-cubic-metre spellings."""
    return (
        str(value).strip().lower()
        .replace(" ", "")
    )


def aggregate_city_daily(
    df: pd.DataFrame,
    min_stations: int = 1,
) -> pd.DataFrame:
    """Calculate equal-weighted station-day means for each city-day."""

    required = {
        "city", "station_id", "date", "pollutant",
        "value", "unit", "coverage_pct",
    }

    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Missing required columns: {sorted(missing)}")

    if min_stations < 1:
        raise ValueError("min_stations must be at least 1.")

    data = df.copy()

    data["city"] = data["city"].astype("string").str.strip()
    data["station_id"] = pd.to_numeric(
        data["station_id"], errors="coerce"
    )
    data["date"] = pd.to_datetime(
        data["date"], errors="coerce"
    ).dt.floor("D")
    data["value"] = pd.to_numeric(
        data["value"], errors="coerce"
    )
    data["coverage_pct"] = pd.to_numeric(
        data["coverage_pct"], errors="coerce"
    )

    # Keep recognized PM2.5 measurements and units.
    pollutant = (
        data["pollutant"].astype("string")
        .str.strip().str.upper()
        .str.replace(" ", "", regex=False)
    )
    unit = data["unit"].map(normalize_unit)

    data = data[
        pollutant.isin(VALID_POLLUTANTS)
        & unit.isin(VALID_UNITS)
    ].copy()

    # Reject missing, negative, or invalid observations.
    data = data.dropna(
        subset=[
            "city", "station_id", "date",
            "value", "coverage_pct",
        ]
    )
    data = data[
        data["city"].ne("")
        & data["value"].ge(0)
        & data["coverage_pct"].between(0, 100)
    ].copy()

    if data.empty:
        raise ValueError(
            "No valid PM2.5 observations remain after filtering."
        )

    # The cleaning stage should already remove duplicates.
    # Fail visibly rather than silently counting duplicate records.
    keys = ["city", "station_id", "date", "pollutant"]
    duplicate_count = int(data.duplicated(keys, keep=False).sum())

    if duplicate_count:
        raise ValueError(
            f"Found {duplicate_count} rows belonging to duplicate "
            "city/station/date/pollutant keys. Run src.clean_data "
            "and inspect its duplicate-removal audit first."
        )

    # First: one mean per station per day.
    station_day = (
        data.groupby(
            ["city", "station_id", "date"],
            as_index=False,
        )
        .agg(
            pm25_station_mean=("value", "mean"),
            station_coverage=("coverage_pct", "mean"),
        )
    )

    # Second: equal-weighted average across stations.
    city_day = (
        station_day.groupby(
            ["city", "date"],
            as_index=False,
        )
        .agg(
            pm25_mean=("pm25_station_mean", "mean"),
            station_count=("station_id", "nunique"),
            coverage_pct=("station_coverage", "mean"),
        )
    )

    city_day = city_day[
        city_day["station_count"] >= min_stations
    ].copy()

    city_day = city_day.sort_values(
        ["city", "date"]
    ).reset_index(drop=True)

    return city_day


def main():
    if not RAW.exists():
        raise FileNotFoundError(
            f"{RAW} not found. Run python -m src.clean_data first."
        )

    df = pd.read_csv(RAW)
    result = aggregate_city_daily(df, min_stations=1)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    result.to_csv(OUT, index=False)

    print(f"Saved {len(result)} city-day rows to {OUT}")

    print("\nRecords by city:")
    print(result.groupby("city").size().to_string())

    print("\nStation count per city-day:")
    print(
        result.groupby("city")["station_count"]
        .value_counts()
        .sort_index()
        .to_string()
    )

    print("\nMissing values:")
    print(result.isna().sum().to_string())

    print("\nPM2.5 summary by city:")
    print(
        result.groupby("city")["pm25_mean"]
        .agg(["count", "mean", "median", "min", "max"])
        .round(2)
        .to_string()
    )

    print("\nAggregation complete.")


if __name__ == "__main__":
    main()