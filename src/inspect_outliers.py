
import pandas as pd

raw = pd.read_csv("data/raw/observations.csv")
daily = pd.read_csv("data/processed/city_daily.csv")

# Inspect the highest city-day values
print("Top 10 city-day PM2.5 values:")
print(
    daily.nlargest(10, "pm25_mean")[
        ["city", "date", "pm25_mean", "station_count"]
    ].to_string(index=False)
)

# Find the individual station readings for Mumbai's highest day
mumbai = daily[daily["city"] == "Mumbai"]
highest = mumbai.loc[mumbai["pm25_mean"].idxmax()]

print("\nRaw station readings on Mumbai's highest day:")
readings = raw[
    (raw["city"] == "Mumbai")
    & (raw["date"] == highest["date"])
]

print(
    readings[
        ["station_id", "date", "value", "unit", "coverage_pct"]
    ].to_string(index=False)
)

print("\nRaw station values above 200 µg/m³:")
print(
    raw[raw["value"] > 200][
        ["city", "station_id", "date", "value", "unit", "coverage_pct"]
    ].to_string(index=False)
)

