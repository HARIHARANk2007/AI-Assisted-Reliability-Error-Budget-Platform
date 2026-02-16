"""
Forecast API Endpoints
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional

from app.core.database import get_db
from app.models.database import Service
from app.schemas.schemas import ForecastResponse
from app.services.forecast_service import ForecastModule

router = APIRouter(prefix="/forecast", tags=["Forecast"])


@router.get("/{service_name}", response_model=ForecastResponse)
async def get_service_forecast(
    service_name: str,
    use_trend: bool = True,
    db: Session = Depends(get_db)
):
    """
    Get budget exhaustion forecast for a service.
    
    Example Response:
    ```json
    {
        "service_id": 1,
        "service_name": "api-gateway",
        "computed_at": "2024-01-15T10:30:00Z",
        "current_burn_rate": 3.2,
        "error_budget_remaining": 25.5,
        "time_to_exhaustion_hours": 4.2,
        "projected_exhaustion_time": "2024-01-15T14:42:00Z",
        "confidence_level": "high",
        "burn_rate_trend": "increasing",
        "trend_slope": 0.15,
        "forecast_message": "api-gateway is burning error budget 3.2× faster than allowed. Budget exhaustion projected in ~4.2 hours. Burn rate is trending upward. Immediate intervention required."
    }
    ```
    """
    service = db.query(Service).filter(Service.name == service_name).first()
    if not service:
        raise HTTPException(status_code=404, detail=f"Service '{service_name}' not found")
    
    forecast_module = ForecastModule(db)
    return forecast_module.forecast_exhaustion(service.id, use_historical_trend=use_trend)


@router.get("", response_model=List[ForecastResponse])
async def get_all_forecasts(
    db: Session = Depends(get_db)
):
    """
    Get budget exhaustion forecasts for all services.
    Sorted by time to exhaustion (most critical first).
    """
    forecast_module = ForecastModule(db)
    forecasts = forecast_module.get_all_forecasts()
    
    # Sort by time to exhaustion
    def sort_key(f):
        if f.time_to_exhaustion_hours is None:
            return float('inf')
        return f.time_to_exhaustion_hours
    
    return sorted(forecasts, key=sort_key)


@router.get("/critical/nearest")
async def get_nearest_exhaustion(
    db: Session = Depends(get_db)
):
    """
    Get the service with nearest budget exhaustion.
    
    Example Response:
    ```json
    {
        "service_name": "api-gateway",
        "time_to_exhaustion_hours": 4.2,
        "projected_exhaustion_time": "2024-01-15T14:42:00Z",
        "current_burn_rate": 3.2,
        "budget_remaining": 25.5
    }
    ```
    """
    forecast_module = ForecastModule(db)
    nearest = forecast_module.get_nearest_exhaustion()
    
    if not nearest:
        return {
            "message": "No services with imminent budget exhaustion",
            "service_name": None,
            "time_to_exhaustion_hours": None
        }
    
    return nearest
