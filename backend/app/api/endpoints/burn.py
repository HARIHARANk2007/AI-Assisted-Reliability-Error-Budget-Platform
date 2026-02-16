"""
Burn Rate API Endpoints
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List

from app.core.database import get_db
from app.models.database import Service
from app.schemas.schemas import BurnRateComputation, BurnHistoryResponse
from app.services.burn_rate_service import BurnRateEngine

router = APIRouter(prefix="/burn", tags=["Burn Rate"])


@router.get("/{service_name}", response_model=BurnHistoryResponse)
async def get_service_burn_rate(
    service_name: str,
    window_minutes: int = Query(60, description="Rolling window in minutes"),
    history_hours: int = Query(24, description="Hours of history to retrieve"),
    db: Session = Depends(get_db)
):
    """
    Get burn rate for a service with historical data.
    
    Example Response:
    ```json
    {
        "service_id": 1,
        "service_name": "api-gateway",
        "history": [
            {
                "timestamp": "2024-01-15T10:00:00Z",
                "window_minutes": 60,
                "burn_rate": 1.2,
                "error_budget_consumed": 45.5,
                "error_budget_remaining": 54.5,
                "risk_level": "observe",
                "risk_color": "#eab308",
                "risk_action": "Increased monitoring"
            }
        ],
        "current_burn_rate": 1.2,
        "average_burn_rate_24h": 1.1,
        "peak_burn_rate_24h": 2.5
    }
    ```
    """
    service = db.query(Service).filter(Service.name == service_name).first()
    if not service:
        raise HTTPException(status_code=404, detail=f"Service '{service_name}' not found")
    
    burn_engine = BurnRateEngine(db)
    
    # Get current computation
    current = burn_engine.compute_burn_rate(service.id, window_minutes)
    
    # Get history
    history_records = burn_engine.get_burn_history(service.id, history_hours, window_minutes)
    
    # Get statistics
    stats = burn_engine.get_burn_statistics(service.id, history_hours)
    
    # Convert history to response format
    history = []
    for record in history_records:
        history.append(BurnRateComputation(
            service_id=record.service_id,
            service_name=service.name,
            timestamp=record.timestamp,
            window_minutes=record.window_minutes,
            current_error_rate=0.0,  # Not stored in history
            allowed_error_rate=0.0,  # Not stored in history
            burn_rate=record.burn_rate,
            error_budget_consumed=record.error_budget_consumed,
            error_budget_remaining=record.error_budget_remaining,
            risk_level=record.risk_level.value,
            risk_color="#22c55e",  # Would need to look up
            risk_action=""
        ))
    
    return BurnHistoryResponse(
        service_id=service.id,
        service_name=service.name,
        history=history,
        current_burn_rate=current.burn_rate,
        average_burn_rate_24h=stats["average_burn_rate"],
        peak_burn_rate_24h=stats["peak_burn_rate"]
    )


@router.get("/{service_name}/current", response_model=BurnRateComputation)
async def get_current_burn_rate(
    service_name: str,
    window_minutes: int = Query(60, description="Rolling window in minutes"),
    db: Session = Depends(get_db)
):
    """
    Get current burn rate for a service (single computation).
    """
    service = db.query(Service).filter(Service.name == service_name).first()
    if not service:
        raise HTTPException(status_code=404, detail=f"Service '{service_name}' not found")
    
    burn_engine = BurnRateEngine(db)
    return burn_engine.compute_burn_rate(service.id, window_minutes)


@router.get("/{service_name}/windows", response_model=List[BurnRateComputation])
async def get_all_window_burn_rates(
    service_name: str,
    db: Session = Depends(get_db)
):
    """
    Get burn rates for all standard windows (5m, 1h, 24h).
    """
    service = db.query(Service).filter(Service.name == service_name).first()
    if not service:
        raise HTTPException(status_code=404, detail=f"Service '{service_name}' not found")
    
    burn_engine = BurnRateEngine(db)
    return burn_engine.compute_all_windows(service.id)


@router.get("", response_model=List[BurnRateComputation])
async def get_all_services_burn_rate(
    window_minutes: int = Query(60, description="Rolling window in minutes"),
    db: Session = Depends(get_db)
):
    """
    Get current burn rates for all active services.
    """
    services = db.query(Service).filter(Service.is_active == True).all()
    burn_engine = BurnRateEngine(db)
    
    results = []
    for service in services:
        try:
            computation = burn_engine.compute_burn_rate(service.id, window_minutes)
            results.append(computation)
        except Exception as e:
            print(f"Error computing burn rate for {service.name}: {e}")
    
    return results
