
import pandas as pd

file_path = "data/processed/city_daily.csv"
df = pd.read_csv(file_path, parse_dates=["date"])

# 1. Check duplicate city-date records
duplicates = df.duplicated(["city", "date"]).sum()
print("Duplicate city-date rows:", duplicates)

# 2. Check missing dates for each city
print("\nMissing dates by city:")

for city, group in df.groupby("city"):
    all_dates = pd.date_range(
        start=group["date"].min(),
        end=group["date"].max(),
        freq="D",
    )

    existing_dates = pd.DatetimeIndex(group["date"].unique())
    missing_dates = all_dates.difference(existing_dates)

    print(f"{city}: {len(missing_dates)} missing dates")

# 3. Summarize PM2.5 values
print("\nPM2.5 summary by city:")
print(df.groupby("city")["pm25_mean"].describe().round(2))

# 4. Check invalid values
print("\nNegative PM2.5 values:", (df["pm25_mean"] < 0).sum())
print("Missing PM2.5 values:", df["pm25_mean"].isna().sum())

# 5. Check missing coverage information
print("Missing coverage_pct:", df["coverage_pct"].isna().sum())
