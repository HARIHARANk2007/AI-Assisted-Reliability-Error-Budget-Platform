"""
API Router - Aggregates all endpoint routers
"""

from fastapi import APIRouter

from app.api.endpoints import (
    services,
    slo,
    burn,
    forecast,
    release,
    summary,
    alerts,
    metrics
)

# Main API router
api_router = APIRouter()

# Include all endpoint routers
api_router.include_router(services.router)
api_router.include_router(slo.router)
api_router.include_router(burn.router)
api_router.include_router(forecast.router)
api_router.include_router(release.router)
api_router.include_router(summary.router)
api_router.include_router(alerts.router)
api_router.include_router(metrics.router)
