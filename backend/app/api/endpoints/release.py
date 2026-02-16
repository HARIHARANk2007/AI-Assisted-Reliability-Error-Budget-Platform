"""
Release Gate API Endpoints
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from app.core.database import get_db
from app.schemas.schemas import ReleaseCheckRequest, ReleaseCheckResponse
from app.services.release_gate_service import ReleaseGateController

router = APIRouter(prefix="/release", tags=["Release Gate"])


@router.post("/check", response_model=ReleaseCheckResponse)
async def check_release(
    request: ReleaseCheckRequest,
    db: Session = Depends(get_db)
):
    """
    Check if a deployment should be allowed.
    
    This is the main release gate endpoint that evaluates system reliability
    and determines whether deployment should proceed.
    
    Request:
    ```json
    {
        "service_name": "api-gateway",
        "deployment_id": "deploy-123",
        "version": "v2.1.0",
        "requested_by": "john.doe@company.com",
        "override": false,
        "override_reason": null
    }
    ```
    
    Response (Allowed):
    ```json
    {
        "allowed": true,
        "reason": "Deployment allowed: System reliability is healthy",
        "service_name": "api-gateway",
        "deployment_id": "deploy-123",
        "current_risk_level": "safe",
        "current_burn_rate": 0.8,
        "error_budget_remaining": 75.5,
        "time_to_exhaustion_hours": 720.0,
        "recommendations": ["System is operating normally"],
        "checked_at": "2024-01-15T10:30:00Z",
        "checked_by": "john.doe@company.com"
    }
    ```
    
    Response (Blocked):
    ```json
    {
        "allowed": false,
        "reason": "Deployment blocked: System is in DANGER state with elevated error rates",
        "service_name": "api-gateway",
        "deployment_id": "deploy-123",
        "current_risk_level": "danger",
        "current_burn_rate": 2.5,
        "error_budget_remaining": 15.2,
        "time_to_exhaustion_hours": 8.5,
        "recommendations": [
            "System is in DANGER state - consider waiting",
            "Error budget is running low",
            "Wait for system to stabilize or provide override with justification"
        ],
        "checked_at": "2024-01-15T10:30:00Z",
        "checked_by": "john.doe@company.com"
    }
    ```
    """
    gate_controller = ReleaseGateController(db)
    return gate_controller.check_release(request)


@router.get("/history")
async def get_deployment_history(
    service_name: str = None,
    limit: int = 50,
    db: Session = Depends(get_db)
):
    """
    Get deployment decision history.
    """
    from app.models.database import Service
    
    service_id = None
    if service_name:
        service = db.query(Service).filter(Service.name == service_name).first()
        if not service:
            raise HTTPException(status_code=404, detail=f"Service '{service_name}' not found")
        service_id = service.id
    
    gate_controller = ReleaseGateController(db)
    deployments = gate_controller.get_deployment_history(service_id, limit)
    
    return [
        {
            "deployment_id": d.deployment_id,
            "service_id": d.service_id,
            "version": d.version,
            "allowed": d.allowed,
            "blocked_reason": d.blocked_reason,
            "risk_level_at_request": d.risk_level_at_request.value if d.risk_level_at_request else None,
            "burn_rate_at_request": d.burn_rate_at_request,
            "status": d.status,
            "requested_at": d.requested_at,
            "requested_by": d.requested_by
        }
        for d in deployments
    ]


@router.get("/statistics")
async def get_gate_statistics(
    days: int = 7,
    db: Session = Depends(get_db)
):
    """
    Get release gate statistics.
    
    Example Response:
    ```json
    {
        "period_days": 7,
        "total_deployments": 45,
        "blocked_deployments": 8,
        "allowed_deployments": 37,
        "block_rate": 17.78,
        "risk_distribution": {
            "safe": 30,
            "observe": 7,
            "danger": 5,
            "freeze": 3
        }
    }
    ```
    """
    gate_controller = ReleaseGateController(db)
    return gate_controller.get_gate_statistics(days)
