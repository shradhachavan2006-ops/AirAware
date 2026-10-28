
"""Download daily PM2.5 observations from OpenAQ."""
import os
import pandas as pd
from openaq import OpenAQ
from pathlib import Path

OUT = Path("data/raw/observations.csv")
START_DATE = "2025-02-19"
END_DATE = "2026-10-13"
LIMIT = 1000

# City, location ID, PM2.5 sensor ID
SENSORS = [
    ("Pune",   60658,   12236449),
    ("Mumbai", 6927,    12235926),
    ("Mumbai", 6956,    12235896),
    ("Mumbai", 6959,    12236435),
    ("Nashik", 5592,    12235635),
    ("Nashik", 3409451, 12238112),
    ("Nashik", 3409453, 12238130),
    ("Nagpur", 5621,    12235626),
    ("Nagpur", 3409464, 12238213),
    ("Nagpur", 3409465, 12238222),
]

def main():
    api_key = os.environ.get("OPENAQ_API_KEY")
    if not api_key:
        raise RuntimeError(
            "OPENAQ_API_KEY is missing. Configure it in this terminal first."
        )

    rows = []

    with OpenAQ(api_key=api_key) as client:
        for city, location_id, sensor_id in SENSORS:
            print(f"\nDownloading {city}, location {location_id}...")
            page = 1

            while True:
                try:
                    response = client.measurements.list(
                        sensors_id=sensor_id,
                        data="days",
                        date_from=START_DATE,
                        date_to=END_DATE,
                        limit=LIMIT,
                        page=page,
                    )
                except Exception as exc:
                    print(
                        f"Request failed for sensor {sensor_id}, "
                        f"page {page}: {type(exc).__name__}: {exc}"
                    )
                    break

                records = response.results
                if not records:
                    break

                for record in records:
                    parameter = getattr(record, "parameter", None)
                    coverage = getattr(record, "coverage", None)
                    period = getattr(record, "period", None)
                    date_info = getattr(period, "datetime_from", None)
                    local_datetime = getattr(date_info, "local", None)

                    if local_datetime is None or record.value is None:
                        continue

                    coverage_pct = (
                        getattr(coverage, "percent_complete", None)
                        if coverage else None
                    )

                    rows.append({
                        "city": city,
                        "station_id": location_id,
                        "date": str(local_datetime)[:10],
                        "pollutant": "PM2.5",
                        "value": record.value,
                        "unit": getattr(parameter, "units", "µg/m³"),
                        "coverage_pct": coverage_pct,
                        "source": "OpenAQ",
                    })

                print(f"  Page {page}: {len(records)} records")

                if len(records) < LIMIT:
                    break

                page += 1

    columns = [
        "city", "station_id", "date", "pollutant",
        "value", "unit", "coverage_pct", "source"
    ]

    if not rows:
        raise RuntimeError(
            "No measurements downloaded. The existing CSV was not changed."
        )

    df = pd.DataFrame(rows, columns=columns)
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df["value"] = pd.to_numeric(df["value"], errors="coerce")
    df = df.dropna(subset=["date", "value"])
    df = df[df["value"] >= 0]
    df["date"] = df["date"].dt.strftime("%Y-%m-%d")

    df = df.drop_duplicates(
        subset=["city", "station_id", "date", "pollutant"]
    )
    df = df.sort_values(["city", "date", "station_id"])

    OUT.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(OUT, index=False)

    print(f"\nSaved {len(df)} observations to {OUT}")
    print("\nRows per city:")
    print(df.groupby("city").size().to_string())
    print("\nDate range per city:")
    print(df.groupby("city")["date"].agg(["min", "max"]).to_string())

if __name__ == "__main__":
    main()
