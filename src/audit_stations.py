
import pandas as pd

df = pd.read_csv("data/raw/observations.csv")
df["date"] = pd.to_datetime(df["date"])
df = df.sort_values(["city", "station_id", "date"])

print("STATION-LEVEL DATA QUALITY AUDIT")
print("=" * 65)

for (city, station), group in df.groupby(["city", "station_id"]):
    values = group["value"]
    frequent = values.value_counts().head(5)

    # Longest consecutive run of the same daily value
    same_as_previous = values.eq(values.shift())
    run_id = (~same_as_previous).cumsum()
    longest_run = same_as_previous.groupby(run_id).size().max()

    print(f"\nCity: {city} | Station ID: {station}")
    print(f"Observations: {len(group)}")
    print(f"Unique values: {values.nunique()}")
    print(f"Median: {values.median():.2f}")
    print(f"Maximum: {values.max():.2f}")
    print(f"Longest repeated-value run: {longest_run} days")
    print("Most frequent values:")
    print(frequent.to_string())

print("\nAudit complete. No records were changed.")
