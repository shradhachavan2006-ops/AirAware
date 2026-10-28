from fastapi import APIRouter

from backend.data_loader import load_daily_data

router = APIRouter(prefix="/meta", tags=["Metadata"])


@router.get("/cities")
def get_cities():
    df = load_daily_data()

    cities = sorted(df["city"].dropna().unique().tolist())

    return {"cities": cities}


@router.get("/date-range")
def get_date_range():
    df = load_daily_data()
    dates = df["date"].dropna()

    if dates.empty:
        return {"start": None, "end": None}

    return {
        "start": dates.min().strftime("%Y-%m-%d"),
        "end": dates.max().strftime("%Y-%m-%d"),
    }
