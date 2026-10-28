"""Recent-observations endpoint.

GET /observations/recent?city=&start=&end=&limit=12

Returns up to `limit` rows from the processed city-level daily dataset,
ordered newest first.  All query parameters are optional:

- city  – if supplied, only rows for that city are returned (exact match,
           case-sensitive, consistent with the original Streamlit app).
           Unknown city names raise HTTP 404.
- start – inclusive lower bound on date (YYYY-MM-DD).  Default: no lower bound.
- end   – inclusive upper bound on date (YYYY-MM-DD).  Default: no upper bound.
- limit – number of rows to return (1–100, default 12).

Original-app semantics preserved
---------------------------------
* Date filtering uses pandas `Series.between(start, end)` — inclusive on both ends,
  matching every Streamlit page that does `df[df["date"].between(start, end)]`.
* Rows where `pm25_mean` is NaN are *included* in the result set (the source
  data may have missing readings; suppressing them would hide coverage gaps).
  This mirrors the 'recent observations' table in `app.py`, which uses the
  full `city_df` — not the `valid` subset — for display.
* Dates are serialised as YYYY-MM-DD ISO strings.
* PM2.5 values are in µg/m³, not AQI.
"""

from __future__ import annotations

from typing import Optional

import numpy as np
import pandas as pd
from fastapi import APIRouter, HTTPException, Query

from backend.data_loader import load_daily_data

router = APIRouter(prefix="/observations", tags=["Observations"])

_LIMIT_MAX = 100
_LIMIT_DEFAULT = 12


# ---------------------------------------------------------------------------
# Private helpers (intentionally self-contained; no cross-router imports)
# ---------------------------------------------------------------------------

def _parse_date(value: str, field: str) -> pd.Timestamp:
    """Parse a YYYY-MM-DD string into a Timestamp; raise HTTP 400 on failure."""
    try:
        return pd.Timestamp(value)
    except Exception:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid {field} date: '{value}'. Expected YYYY-MM-DD.",
        )


def _safe_float(value) -> Optional[float]:
    """Return a Python float, or None if the value is NaN / None."""
    if value is None:
        return None
    try:
        f = float(value)
        return None if np.isnan(f) else round(f, 4)
    except (TypeError, ValueError):
        return None


def _serialize_row(row: pd.Series) -> dict:
    """Convert one observation row into a JSON-serialisable dict."""
    date_val = row.get("date")
    return {
        "date": date_val.strftime("%Y-%m-%d") if pd.notna(date_val) else None,
        "city": str(row.get("city", "")),
        "pm25_mean": _safe_float(row.get("pm25_mean")),
        "station_count": (
            int(row["station_count"])
            if pd.notna(row.get("station_count"))
            else None
        ),
        "coverage_pct": _safe_float(row.get("coverage_pct")),
    }


# ---------------------------------------------------------------------------
# Endpoint
# ---------------------------------------------------------------------------

@router.get("/recent")
def get_recent_observations(
    city: Optional[str] = Query(
        default=None,
        description=(
            "City name (e.g. Pune). "
            "If omitted, observations for all cities are returned."
        ),
    ),
    start: Optional[str] = Query(
        default=None,
        description="Inclusive start date in YYYY-MM-DD format.",
    ),
    end: Optional[str] = Query(
        default=None,
        description="Inclusive end date in YYYY-MM-DD format.",
    ),
    limit: int = Query(
        default=_LIMIT_DEFAULT,
        ge=1,
        le=_LIMIT_MAX,
        description=f"Maximum rows to return (1–{_LIMIT_MAX}, default {_LIMIT_DEFAULT}).",
    ),
):
    """Return up to *limit* observations, newest first.

    Filtering logic:
    1. Load the full processed dataset.
    2. If *city* is given, validate it against known cities, then keep only
       rows for that city.
    3. If *start* is given, drop rows whose date is before *start* (inclusive).
    4. If *end*   is given, drop rows whose date is after  *end*  (inclusive).
    5. Sort descending by date.
    6. Return the first *limit* rows serialised as JSON objects.
    """

    # --- Parse date params (only if provided) --------------------------------
    start_ts: Optional[pd.Timestamp] = None
    end_ts: Optional[pd.Timestamp] = None

    if start is not None:
        start_ts = _parse_date(start, "start")
    if end is not None:
        end_ts = _parse_date(end, "end")

    if start_ts is not None and end_ts is not None and start_ts > end_ts:
        raise HTTPException(
            status_code=400,
            detail=f"start ({start}) must not be after end ({end}).",
        )

    # --- Load data -----------------------------------------------------------
    df = load_daily_data()

    # --- City filter ---------------------------------------------------------
    if city is not None:
        known_cities = sorted(df["city"].dropna().unique().tolist())
        if city not in known_cities:
            raise HTTPException(
                status_code=404,
                detail=(
                    f"City '{city}' not found. "
                    f"Known cities: {known_cities}."
                ),
            )
        df = df[df["city"] == city]

    # --- Date filter (inclusive on both ends) --------------------------------
    if start_ts is not None and end_ts is not None:
        df = df[df["date"].between(start_ts, end_ts)]
    elif start_ts is not None:
        df = df[df["date"] >= start_ts]
    elif end_ts is not None:
        df = df[df["date"] <= end_ts]

    # --- Sort and truncate ---------------------------------------------------
    df = df.sort_values("date", ascending=False).head(limit)

    # --- Serialise -----------------------------------------------------------
    observations = [_serialize_row(row) for _, row in df.iterrows()]

    return {
        "filters": {
            "city": city,
            "start": start_ts.strftime("%Y-%m-%d") if start_ts is not None else None,
            "end": end_ts.strftime("%Y-%m-%d") if end_ts is not None else None,
            "limit": limit,
        },
        "count": len(observations),
        "observations": observations,
    }
