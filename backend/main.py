
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.routers.meta import router as meta_router
from backend.routers.dashboard import router as dashboard_router
from backend.routers.observations import router as observations_router

app = FastAPI(
    title="AirAware API",
    description="Backend API for the AirAware air-quality analytics dashboard.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(meta_router)
app.include_router(dashboard_router)
app.include_router(observations_router)


@app.get("/")
def root():
    return {
        "message": "Welcome to the AirAware API",
        "status": "running",
    }


@app.get("/health")
def health_check():
    return {"status": "healthy"}
