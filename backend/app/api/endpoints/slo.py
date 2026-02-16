"""
SLO API Endpoints
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional

from app.core.database import get_db
from app.models.database import Service, SLOTarget
from app.schemas.schemas import (
    SLOTargetResponse, SLOTargetCreate, SLOTargetUpdate,
    SLOComputation, SLOResponse, RiskLevel
)
from app.services.slo_service import SLOComputationEngine
from app.services.burn_rate_service import BurnRateEngine

router = APIRouter(prefix="/slo", tags=["SLO"])


@router.get("/{service_name}", response_model=SLOResponse)
async def get_service_slo(
    service_name: str,
    db: Session = Depends(get_db)
):
    """
    Get full SLO status for a service.
    
    Returns:
        - Service info
        - SLO targets
        - Current computations
        - Overall compliance and risk level
    
    Example Response:
    ```json
    {
        "service": {
            "id": 1,
            "name": "api-gateway",
            "tier": 1
        },
        "targets": [
            {
                "name": "availability",
                "target_value": 99.9,
                "window_days": 30
            }
        ],
        "computations": [
            {
                "slo_name": "availability",
                "target_value": 99.9,
                "current_value": 99.82,
                "is_meeting_slo": false,
                "consumed_percentage": 180.0,
                "remaining_percentage": -80.0,
                "availability_5m": 99.5,
                "availability_1h": 99.7,
                "availability_24h": 99.82
            }
        ],
        "overall_compliance": 99.82,
        "risk_level": "danger"
    }
    ```
    """
    service = db.query(Service).filter(Service.name == service_name).first()
    if not service:
        raise HTTPException(status_code=404, detail=f"Service '{service_name}' not found")
    
    # Get SLO targets
    targets = db.query(SLOTarget).filter(
        SLOTarget.service_id == service.id,
        SLOTarget.is_active == True
    ).all()
    
    # Compute SLOs
    slo_engine = SLOComputationEngine(db)
    computations = slo_engine.compute_slo(service.id)
    
    # Get risk level
    burn_engine = BurnRateEngine(db)
    _, risk_level = burn_engine.get_weighted_burn_rate(service.id)
    
    # Calculate overall compliance
    overall_compliance = 100.0
    if computations:
        compliances = [
            min(c.current_value / c.target_value * 100, 100) 
            for c in computations
        ]
        overall_compliance = sum(compliances) / len(compliances)
    
    from app.schemas.schemas import ServiceResponse
    return SLOResponse(
        service=ServiceResponse.model_validate(service),
        targets=[SLOTargetResponse.model_validate(t) for t in targets],
        computations=computations,
        overall_compliance=round(overall_compliance, 2),
        risk_level=risk_level
    )


@router.get("", response_model=List[dict])
async def get_all_slo_status(
    db: Session = Depends(get_db)
):
    """
    Get SLO status summary for all services.
    """
    slo_engine = SLOComputationEngine(db)
    return slo_engine.get_all_services_slo_status()


@router.post("/targets", response_model=SLOTargetResponse, status_code=201)
async def create_slo_target(
    target: SLOTargetCreate,
    db: Session = Depends(get_db)
):
    """
    Create a new SLO target for a service.
    """
    # Verify service exists
    service = db.query(Service).filter(Service.id == target.service_id).first()
    if not service:
        raise HTTPException(status_code=404, detail="Service not found")
    
    db_target = SLOTarget(**target.model_dump())
    db.add(db_target)
    db.commit()
    db.refresh(db_target)
    
    return SLOTargetResponse.model_validate(db_target)


@router.patch("/targets/{target_id}", response_model=SLOTargetResponse)
async def update_slo_target(
    target_id: int,
    update: SLOTargetUpdate,
    db: Session = Depends(get_db)
):
    """
    Update an SLO target.
    """
    target = db.query(SLOTarget).filter(SLOTarget.id == target_id).first()
    if not target:
        raise HTTPException(status_code=404, detail="SLO target not found")
    
    update_data = update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(target, field, value)
    
    db.commit()
    db.refresh(target)
    return SLOTargetResponse.model_validate(target)


@router.get("/compliance/global")
async def get_global_compliance(
    db: Session = Depends(get_db)
):
    """
    Get global platform compliance metrics.
    
    Example Response:
    ```json
    {
        "total_services": 8,
        "services_meeting_slo": 6,
        "global_compliance": 96.5,
        "services_at_risk": ["payment-service", "api-gateway"]
    }
    ```
    """
    slo_engine = SLOComputationEngine(db)
    return slo_engine.compute_global_compliance()
