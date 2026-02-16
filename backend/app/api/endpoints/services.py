"""
Services API Endpoints
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional

from app.core.database import get_db
from app.models.database import Service
from app.schemas.schemas import (
    ServiceResponse, ServiceCreate, ServiceUpdate, ServiceListResponse
)
from app.services.slo_service import create_default_slo_targets

router = APIRouter(prefix="/services", tags=["Services"])


@router.get("", response_model=ServiceListResponse)
async def list_services(
    active_only: bool = Query(True, description="Filter to active services only"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db)
):
    """
    List all services with optional filtering.
    
    Returns:
        List of services with total count
    """
    query = db.query(Service)
    
    if active_only:
        query = query.filter(Service.is_active == True)
    
    total = query.count()
    services = query.offset(skip).limit(limit).all()
    
    return ServiceListResponse(
        services=[ServiceResponse.model_validate(s) for s in services],
        total=total
    )


@router.get("/{service_id}", response_model=ServiceResponse)
async def get_service(
    service_id: int,
    db: Session = Depends(get_db)
):
    """
    Get a specific service by ID.
    """
    service = db.query(Service).filter(Service.id == service_id).first()
    if not service:
        raise HTTPException(status_code=404, detail="Service not found")
    return ServiceResponse.model_validate(service)


@router.post("", response_model=ServiceResponse, status_code=201)
async def create_service(
    service: ServiceCreate,
    db: Session = Depends(get_db)
):
    """
    Create a new service and default SLO targets.
    """
    # Check if name already exists
    existing = db.query(Service).filter(Service.name == service.name).first()
    if existing:
        raise HTTPException(
            status_code=400, 
            detail=f"Service with name '{service.name}' already exists"
        )
    
    db_service = Service(**service.model_dump())
    db.add(db_service)
    db.commit()
    db.refresh(db_service)
    
    # Create default SLO targets
    create_default_slo_targets(db, db_service.id)
    
    return ServiceResponse.model_validate(db_service)


@router.patch("/{service_id}", response_model=ServiceResponse)
async def update_service(
    service_id: int,
    update: ServiceUpdate,
    db: Session = Depends(get_db)
):
    """
    Update a service.
    """
    service = db.query(Service).filter(Service.id == service_id).first()
    if not service:
        raise HTTPException(status_code=404, detail="Service not found")
    
    update_data = update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(service, field, value)
    
    db.commit()
    db.refresh(service)
    return ServiceResponse.model_validate(service)


@router.delete("/{service_id}", status_code=204)
async def delete_service(
    service_id: int,
    db: Session = Depends(get_db)
):
    """
    Delete a service (soft delete - marks as inactive).
    """
    service = db.query(Service).filter(Service.id == service_id).first()
    if not service:
        raise HTTPException(status_code=404, detail="Service not found")
    
    service.is_active = False
    db.commit()
