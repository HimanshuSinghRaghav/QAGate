from fastapi import APIRouter

from app.api.v1 import checks, dashboard, ingestion, reviews, scoring

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(ingestion.router)
api_router.include_router(scoring.router)
api_router.include_router(checks.router)
api_router.include_router(reviews.router)
api_router.include_router(dashboard.router)
