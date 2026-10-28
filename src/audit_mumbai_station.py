
from pathlib import Path
import pandas as pd

path = Path("data/raw/observations.csv")
df = pd.read_csv(path)

df["date"] = pd.to_datetime(df["date"], errors="coerce")
df["value"] = pd.to_numeric(df["value"], errors="coerce")

# Examine the two Mumbai stations with suspicious readings.
mumbai = df[
    (df["city"] == "Mumbai")
    & (df["station_id"].astype(str).isin(["6927", "6956"]))
].copy()

for station_id, group in mumbai.groupby("station_id"):
    group = group.sort_values("date")

    print(f"\n{'=' * 55}")
    print(f"Station: {station_id}")
    print(f"Total observations: {len(group)}")
    print(f"Unique values: {group['value'].nunique()}")
    print(f"Median: {group['value'].median():.2f}")
    print(f"Maximum: {group['value'].max():.2f}")

    print("\nMost frequently repeated values:")
    print(group["value"].value_counts().head(10))

    print("\nReadings above 200 µg/m³:")
    print(
        group.loc[
            group["value"] > 200,
            ["date", "value", "coverage_pct"],
        ].to_string(index=False)
    )

# Check the effect of excluding station 6956.
clean_path = Path("data/processed/observations_clean.csv")
clean = pd.read_csv(clean_path)
clean["date"] = pd.to_datetime(clean["date"], errors="coerce")

print("\nCleaned dataset:")
print("Rows:", len(clean))
print("Mumbai rows by station:")
print(
    clean.loc[clean["city"] == "Mumbai"]
    .groupby("station_id")
    .size()
)
