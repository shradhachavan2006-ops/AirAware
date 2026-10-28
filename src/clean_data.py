"""Clean PM2.5 observations while preserving raw data and audit decisions."""

from pathlib import Path
import pandas as pd

RAW = Path("data/raw/observations.csv")
OUT = Path("data/processed/observations_clean.csv")
AUDIT = Path("data/processed/cleaning_audit.csv")

# Provisional exclusion from the primary analysis.
# This is a sensitivity decision, not proof that the sensor is faulty.
EXCLUDED_STATIONS = {
    ("Mumbai", 6927),
}

# Flag for further investigation; do not exclude automatically.
FLAGGED_STATIONS = {
    ("Mumbai", 6956),
}

MIN_COVERAGE = 75

PM25_ALIASES = {
    "pm25",
    "pm2.5",
    "pm2_5",
    "pm2 5",
}

UNIT_ALIASES = {
    "ug/m3",
    "µg/m3",
    "μg/m3",
    "ug/m³",
    "µg/m³",
    "μg/m³",
}


def normalize_text(series):
    return (
        series.astype("string")
        .str.strip()
        .str.lower()
        .str.replace(" ", "", regex=False)
    )


def main():
    if not RAW.exists():
        raise FileNotFoundError(f"Raw dataset not found: {RAW}")

    df = pd.read_csv(RAW)
    original_count = len(df)
    audit_rows = []

    required = {
        "city", "station_id", "date", "pollutant",
        "value", "unit", "coverage_pct",
    }
    missing = required - set(df.columns)

    if missing:
        raise ValueError(
            f"Missing required columns: {sorted(missing)}"
        )

    # Preserve the original raw file. All changes happen in memory.
    df["station_id"] = pd.to_numeric(
        df["station_id"], errors="coerce"
    )
    df["value"] = pd.to_numeric(df["value"], errors="coerce")
    df["coverage_pct"] = pd.to_numeric(
        df["coverage_pct"], errors="coerce"
    )
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df["city"] = df["city"].astype("string").str.strip()

    # Remove rows missing essential fields.
    before = len(df)
    df = df.dropna(
        subset=[
            "city", "station_id", "date", "pollutant",
            "value", "unit", "coverage_pct",
        ]
    ).copy()
    audit_rows.append({
        "step": "missing_required_fields",
        "rows_removed": before - len(df),
        "details": "Missing city, station, date, value, unit, pollutant or coverage",
    })

    # Keep PM2.5 observations only.
    pollutant_key = normalize_text(df["pollutant"])
    before = len(df)
    df = df[pollutant_key.isin(PM25_ALIASES)].copy()
    audit_rows.append({
        "step": "pollutant_filter",
        "rows_removed": before - len(df),
        "details": "Kept recognized PM2.5 pollutant labels only",
    })

    # Keep recognized micrograms-per-cubic-metre units only.
    unit_key = normalize_text(df["unit"])
    before = len(df)
    df = df[unit_key.isin(UNIT_ALIASES)].copy()
    audit_rows.append({
        "step": "unit_filter",
        "rows_removed": before - len(df),
        "details": "Kept recognized µg/m³ unit labels only",
    })

    # Remove physically invalid negative concentrations.
    before = len(df)
    df = df[df["value"] >= 0].copy()
    audit_rows.append({
        "step": "negative_values",
        "rows_removed": before - len(df),
        "details": "Removed negative PM2.5 values",
    })

    # Exclude provisionally flagged stations from primary analysis.
    excluded_mask = pd.Series(False, index=df.index)

    for city, station_id in EXCLUDED_STATIONS:
        excluded_mask |= (
            df["city"].str.casefold().eq(city.casefold())
            & df["station_id"].eq(station_id)
        )

    excluded_count = int(excluded_mask.sum())
    df = df.loc[~excluded_mask].copy()
    audit_rows.append({
        "step": "provisional_station_exclusion",
        "rows_removed": excluded_count,
        "details": "Mumbai station 6927 excluded provisionally after repeated-value audit",
    })

    # Keep observations with at least 75% coverage.
    before = len(df)
    df = df[df["coverage_pct"].between(MIN_COVERAGE, 100)].copy()
    audit_rows.append({
        "step": "coverage_filter",
        "rows_removed": before - len(df),
        "details": "Kept coverage from 75% through 100%",
    })

    # Resolve duplicate station-day-pollutant rows by retaining
    # the row with the highest coverage.
    duplicate_keys = ["city", "station_id", "date", "pollutant"]
    before = len(df)

    df = (
        df.sort_values("coverage_pct", ascending=False)
        .drop_duplicates(subset=duplicate_keys, keep="first")
        .copy()
    )

    audit_rows.append({
        "step": "duplicate_removal",
        "rows_removed": before - len(df),
        "details": "Kept the highest-coverage row per city/station/date/pollutant",
    })

    # Save cleaned data and the audit trail.
    OUT.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(OUT, index=False)

    pd.DataFrame(audit_rows).to_csv(AUDIT, index=False)

    print("\nAIR AWARE — CLEANING SUMMARY")
    print("=" * 55)
    print(f"Original raw rows: {original_count}")
    print(f"Cleaned rows: {len(df)}")
    print(f"Rows removed overall: {original_count - len(df)}")
    print(f"Cleaned dataset: {OUT}")
    print(f"Audit log: {AUDIT}")

    print("\nRows per city:")
    print(df.groupby("city").size().to_string())

    print("\nRows per Mumbai station:")
    mumbai = df[df["city"].str.casefold().eq("mumbai")]
    print(mumbai.groupby("station_id").size().to_string())

    print("\nCoverage summary:")
    print(df["coverage_pct"].describe().round(2).to_string())

    print("\nFlagged stations retained if they pass cleaning:")
    for city, station_id in FLAGGED_STATIONS:
        count = (
            df["city"].str.casefold().eq(city.casefold())
            & df["station_id"].eq(station_id)
        ).sum()
        print(f"{city} station {station_id}: {count} rows retained")

    print("\nCleaning complete. Raw observations were not modified.")


if __name__ == "__main__":
    main()