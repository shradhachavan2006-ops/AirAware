
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.routers.meta import router as meta_router
from backend.routers.dashboard import router as dashboard_router
from backend.routers.observations import router as observations_router
from backend.routers.trends import router as trends_router
from backend.routers.statistics import router as statistics_router
from backend.routers.evaluation import router as evaluation_router
from backend.routers.forecast import router as forecast_router
from backend.routers.datasets import router as datasets_router
from backend.routers.quality import router as quality_router
from backend.routers.stat_analysis import router as stat_analysis_router
from backend.routers.regression import router as regression_router

app = FastAPI(
    title="AirAware API",
    description=(
        "Backend API for the AirAware V2 air-quality analytics and forecasting platform. "
        "Supports per-dataset analysis, hypothesis testing, regression and PM2.5 forecasting."
    ),
    version="2.0.0",
)

app.add_middleware(
    CORSMiddleware,
    # Allow any localhost/127.0.0.1 origin on any port (covers Vite on 5173/5174/etc.)
    allow_origin_regex=r"https?://(localhost|127\.0\.0\.1)(:\d+)?",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(meta_router)
app.include_router(dashboard_router)
app.include_router(observations_router)
app.include_router(trends_router)
app.include_router(statistics_router)
app.include_router(evaluation_router)
app.include_router(forecast_router)
app.include_router(datasets_router)
app.include_router(quality_router)
app.include_router(stat_analysis_router)
app.include_router(regression_router)


@app.get("/")
def root():
    return {
        "message": "Welcome to the AirAware V2 API",
        "status": "running",
        "version": "2.0.0",
    }


@app.get("/health")
def health_check():
    return {"status": "healthy"}
