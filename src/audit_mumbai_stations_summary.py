from pathlib import Path
import pandas as pd

INPUT = Path("data/raw/observations.csv")
OUTPUT = Path("data/processed/mumbai_station_audit.csv")

df = pd.read_csv(INPUT)

df["station_id"] = pd.to_numeric(df["station_id"], errors="coerce")
df["value"] = pd.to_numeric(df["value"], errors="coerce")
df["coverage_pct"] = pd.to_numeric(df["coverage_pct"], errors="coerce")

mumbai = df[
    df["city"].astype(str).str.lower().eq("mumbai")
].copy()

rows = []

for station_id, group in mumbai.groupby("station_id"):
    values = group["value"].dropna()
    counts = values.value_counts()

    rows.append({
        "station_id": int(station_id),
        "observations": len(group),
        "unique_values": values.nunique(),
        "median_pm25": values.median(),
        "mean_pm25": values.mean(),
        "max_pm25": values.max(),
        "readings_above_200": int((values > 200).sum()),
        "readings_above_500": int((values > 500).sum()),
        "most_repeated_value": counts.index[0] if not counts.empty else None,
        "most_repeated_count": int(counts.iloc[0]) if not counts.empty else 0,
        "mean_coverage_pct": group["coverage_pct"].mean(),
    })

report = pd.DataFrame(rows).sort_values("station_id")
OUTPUT.parent.mkdir(parents=True, exist_ok=True)
report.to_csv(OUTPUT, index=False)

print(report.round(2).to_string(index=False))
print(f"\nAudit report saved to: {OUTPUT}")