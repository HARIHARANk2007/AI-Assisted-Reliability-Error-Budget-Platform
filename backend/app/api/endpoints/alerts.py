"""
Alerts API Endpoints
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional

from app.core.database import get_db
from app.schemas.schemas import (
    AlertResponse, AlertFeedResponse, AlertSeverity
)
from app.services.alert_service import AlertManager

router = APIRouter(prefix="/alerts", tags=["Alerts"])


@router.get("", response_model=AlertFeedResponse)
async def get_alerts(
    service_name: Optional[str] = None,
    severity: Optional[AlertSeverity] = None,
    acknowledged: Optional[bool] = None,
    hours: int = Query(24, description="Hours of history"),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db)
):
    """
    Get alert feed with optional filtering.
    
    Example Response:
    ```json
    {
        "alerts": [
            {
                "id": 1,
                "service_id": 1,
                "service_name": "api-gateway",
                "timestamp": "2024-01-15T10:25:00Z",
                "severity": "critical",
                "channel": "slack",
                "title": "[WARNING] Error Budget Critical: api-gateway",
                "message": "Error budget for api-gateway is critically low (15.2% remaining). Budget will be exhausted in ~4.2 hours.",
                "sent": true,
                "acknowledged": false,
                "acknowledged_by": null
            }
        ],
        "total": 15,
        "unacknowledged": 8
    }
    ```
    """
    from app.models.database import Service
    
    service_id = None
    if service_name:
        service = db.query(Service).filter(Service.name == service_name).first()
        if not service:
            raise HTTPException(status_code=404, detail=f"Service '{service_name}' not found")
        service_id = service.id
    
    alert_manager = AlertManager(db)
    alerts = alert_manager.get_alerts(
        service_id=service_id,
        severity=severity,
        acknowledged=acknowledged,
        hours=hours,
        limit=limit
    )
    
    # Get totals
    from sqlalchemy import func, and_
    from app.models.database import Alert
    from datetime import datetime, timedelta
    
    cutoff = datetime.utcnow() - timedelta(hours=hours)
    
    query = db.query(Alert).filter(Alert.timestamp >= cutoff)
    if service_id:
        query = query.filter(Alert.service_id == service_id)
    
    total = query.count()
    unack = query.filter(Alert.acknowledged == False).count()
    
    return AlertFeedResponse(
        alerts=alerts,
        total=total,
        unacknowledged=unack
    )


@router.get("/feed", response_model=AlertFeedResponse)
async def get_alert_feed(
    hours: int = Query(24, description="Hours of history"),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db)
):
    """
    Get simplified alert feed for UI display.
    """
    alert_manager = AlertManager(db)
    return alert_manager.get_alert_feed(hours=hours, limit=limit)


@router.post("/{alert_id}/acknowledge")
async def acknowledge_alert(
    alert_id: int,
    acknowledged_by: str = Query(..., description="User acknowledging the alert"),
    db: Session = Depends(get_db)
):
    """
    Acknowledge an alert.
    """
    alert_manager = AlertManager(db)
    alert = alert_manager.acknowledge_alert(alert_id, acknowledged_by)
    
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    
    return {
        "success": True,
        "alert_id": alert_id,
        "acknowledged_by": acknowledged_by,
        "acknowledged_at": alert.acknowledged_at
    }


@router.post("/acknowledge-bulk")
async def bulk_acknowledge(
    alert_ids: List[int],
    acknowledged_by: str = Query(..., description="User acknowledging the alerts"),
    db: Session = Depends(get_db)
):
    """
    Acknowledge multiple alerts at once.
    """
    alert_manager = AlertManager(db)
    updated = alert_manager.bulk_acknowledge(alert_ids, acknowledged_by)
    
    return {
        "success": True,
        "updated_count": updated,
        "acknowledged_by": acknowledged_by
    }


@router.get("/statistics")
async def get_alert_statistics(
    days: int = Query(7, description="Period in days"),
    db: Session = Depends(get_db)
):
    """
    Get alert statistics.
    
    Example Response:
    ```json
    {
        "period_days": 7,
        "by_severity": {
            "info": 25,
            "warning": 15,
            "critical": 8,
            "emergency": 2
        },
        "total": 50,
        "unacknowledged": 12
    }
    ```
    """
    alert_manager = AlertManager(db)
    return alert_manager.get_alert_statistics(days)
