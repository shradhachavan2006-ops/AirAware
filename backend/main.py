
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.routers.meta import router as meta_router
from backend.routers.dashboard import router as dashboard_router
from backend.routers.observations import router as observations_router
from backend.routers.trends import router as trends_router
from backend.routers.statistics import router as statistics_router
from backend.routers.evaluation import router as evaluation_router

app = FastAPI(
    title="AirAware API",
    description="Backend API for the AirAware air-quality analytics dashboard.",
    version="1.0.0",
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


@app.get("/")
def root():
    return {
        "message": "Welcome to the AirAware API",
        "status": "running",
    }


@app.get("/health")
def health_check():
    return {"status": "healthy"}
