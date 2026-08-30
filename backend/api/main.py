from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .routes import router


app = FastAPI(
    title="NITK Smart Mobility API",
    description=(
        "Backend API for the NITK Dynamic Vehicle "
        "Routing and Ride Pooling System."
    ),
    version="1.0.0",
)


# --------------------------------------------------
# CORS
# --------------------------------------------------

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# --------------------------------------------------
# ROUTES
# --------------------------------------------------

app.include_router(router)


# --------------------------------------------------
# ROOT
# --------------------------------------------------

@app.get("/")
def root():
    return {
        "status": "online",
        "project": "NITK Smart Mobility",
        "version": "1.0.0",
    }


@app.get("/api/health")
def health_check():
    return {
        "status": "healthy",
        "service": "backend",
    }


@app.get("/api")
def api_info():
    return {
        "name": "NITK Smart Mobility API",
        "version": "1.0.0",
        "status": "running",
        "modules": [
            "locations",
            "routing",
            "demand_prediction",
            "ride_requests",
            "optimization",
            "simulation",
        ],
    }