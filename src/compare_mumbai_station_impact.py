from pathlib import Path

import pandas as pd

RAW_FILE = Path("data/processed/observations_clean.csv")

df = pd.read_csv(RAW_FILE)

df["date"] = pd.to_datetime(df["date"], errors="coerce")
df["value"] = pd.to_numeric(df["value"], errors="coerce")
df["station_id"] = pd.to_numeric(df["station_id"], errors="coerce")

# Keep valid Mumbai PM2.5 observations.
mumbai = df[
    df["city"].astype(str).str.lower().eq("mumbai")
    & df["date"].notna()
    & df["value"].notna()
].copy()

if mumbai.empty:
    raise ValueError("No valid Mumbai observations found.")

# Calculate each station's daily average first.
station_daily = (
    mumbai.groupby(["date", "station_id"], as_index=False)
    .agg(
        station_pm25=("value", "mean"),
        coverage_pct=("coverage_pct", "mean"),
    )
)

def city_daily(data):
    return (
        data.groupby("date", as_index=False)
        .agg(
            city_pm25=("station_pm25", "mean"),
            station_count=("station_id", "nunique"),
        )
    )

# Compare the city estimate with and without station 6956.
with_station = city_daily(station_daily).rename(
    columns={
        "city_pm25": "pm25_with_6956",
        "station_count": "stations_with_6956",
    }
)

without_station = city_daily(
    station_daily[station_daily["station_id"] != 6956]
).rename(
    columns={
        "city_pm25": "pm25_without_6956",
        "station_count": "stations_without_6956",
    }
)

comparison = with_station.merge(
    without_station,
    on="date",
    how="left",
)

comparison["difference"] = (
    comparison["pm25_with_6956"]
    - comparison["pm25_without_6956"]
)

print("\nMUMBAI: IMPACT OF STATION 6956")
print("=" * 60)
print(f"Dates with observations: {len(comparison)}")
print(
    "Dates with another station available:",
    comparison["pm25_without_6956"].notna().sum(),
)

valid = comparison.dropna(subset=["pm25_without_6956"])

if not valid.empty:
    print(
        "\nAverage PM2.5 with station 6956:",
        round(valid["pm25_with_6956"].mean(), 2),
    )
    print(
        "Average PM2.5 without station 6956:",
        round(valid["pm25_without_6956"].mean(), 2),
    )
    print(
        "Mean absolute daily difference:",
        round(valid["difference"].abs().mean(), 2),
    )

    print("\nDates with the largest impact:")
    print(
        valid.assign(
            absolute_difference=valid["difference"].abs()
        )
        .sort_values("absolute_difference", ascending=False)
        .head(15)[
            [
                "date",
                "pm25_with_6956",
                "pm25_without_6956",
                "difference",
                "stations_with_6956",
                "stations_without_6956",
            ]
        ]
        .round(2)
        .to_string(index=False)
    )
else:
    print(
        "\nNo dates have both station 6956 and another station. "
        "A direct comparison is not possible."
    )

print("\nAudit complete. No data was changed.")