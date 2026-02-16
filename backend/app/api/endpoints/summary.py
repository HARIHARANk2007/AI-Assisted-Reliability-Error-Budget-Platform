"""
Summary & Dashboard API Endpoints
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime, timedelta

from app.core.database import get_db
from app.models.database import Service, BurnHistory
from app.schemas.schemas import (
    AISummaryResponse, DashboardOverview, HeatmapData, RiskLevel
)
from app.services.ai_narrative_service import AINarrativeGenerator
from app.services.slo_service import SLOComputationEngine
from app.services.burn_rate_service import BurnRateEngine
from app.services.forecast_service import ForecastModule
from app.services.alert_service import AlertManager
from app.core.config import RISK_THRESHOLDS

router = APIRouter(prefix="/summary", tags=["Summary & Dashboard"])


@router.get("", response_model=AISummaryResponse)
async def get_ai_summary(
    db: Session = Depends(get_db)
):
    """
    Get AI-generated reliability summary.
    
    Example Response:
    ```json
    {
        "generated_at": "2024-01-15T10:30:00Z",
        "overall_health": "degraded",
        "overall_score": 82.5,
        "executive_summary": "Platform reliability requires attention. 2 services showing elevated error rates. Services requiring attention: api-gateway, payment-service. Nearest budget exhaustion: api-gateway in ~4.2 hours.",
        "insights": [
            {
                "service_name": "api-gateway",
                "insight_type": "warning",
                "message": "api-gateway is burning error budget 3.2× faster than allowed. SLA breach likely in ~4.2 hours.",
                "severity": "critical"
            }
        ],
        "action_items": [
            "URGENT: Investigate critical issues in api-gateway",
            "Review error budget status and consider deployment freeze for affected services"
        ],
        "services_at_risk": ["api-gateway", "payment-service"],
        "nearest_budget_exhaustion": {
            "service_name": "api-gateway",
            "time_to_exhaustion_hours": 4.2
        }
    }
    ```
    """
    ai_generator = AINarrativeGenerator(db)
    return ai_generator.generate_summary()


@router.get("/executive", response_model=DashboardOverview)
async def get_executive_overview(
    db: Session = Depends(get_db)
):
    """
    Get executive dashboard overview.
    
    Example Response:
    ```json
    {
        "total_services": 8,
        "services_meeting_slo": 6,
        "services_at_risk": 2,
        "global_compliance_score": 96.5,
        "risk_distribution": {
            "safe": 5,
            "observe": 1,
            "danger": 1,
            "freeze": 1
        },
        "average_budget_remaining": 65.5,
        "lowest_budget_service": "api-gateway",
        "lowest_budget_percentage": 15.2,
        "nearest_exhaustion": {
            "service_name": "api-gateway",
            "time_to_exhaustion_hours": 4.2
        },
        "active_alerts": 5,
        "critical_alerts": 2,
        "compliance_trend_24h": "degrading"
    }
    ```
    """
    # Get SLO compliance
    slo_engine = SLOComputationEngine(db)
    global_compliance = slo_engine.compute_global_compliance()
    
    # Get risk distribution
    burn_engine = BurnRateEngine(db)
    services = db.query(Service).filter(Service.is_active == True).all()
    
    risk_distribution = {"safe": 0, "observe": 0, "danger": 0, "freeze": 0}
    lowest_budget = None
    lowest_budget_service = None
    budget_totals = []
    
    for service in services:
        try:
            burn = burn_engine.compute_burn_rate(service.id, 60)
            risk_distribution[burn.risk_level.value] += 1
            
            budget_totals.append(burn.error_budget_remaining)
            if lowest_budget is None or burn.error_budget_remaining < lowest_budget:
                lowest_budget = burn.error_budget_remaining
                lowest_budget_service = service.name
        except:
            pass
    
    # Get forecast info
    forecast_module = ForecastModule(db)
    nearest = forecast_module.get_nearest_exhaustion()
    
    # Get alerts
    alert_manager = AlertManager(db)
    alert_feed = alert_manager.get_alert_feed(hours=24)
    critical_alerts = sum(1 for a in alert_feed.alerts if a.severity.value in ["critical", "emergency"])
    
    # Calculate trend (simplified)
    compliance_trend = "stable"
    
    avg_budget = sum(budget_totals) / len(budget_totals) if budget_totals else 100.0
    
    return DashboardOverview(
        total_services=global_compliance["total_services"],
        services_meeting_slo=global_compliance["services_meeting_slo"],
        services_at_risk=len(global_compliance["services_at_risk"]),
        global_compliance_score=global_compliance["global_compliance"],
        risk_distribution=risk_distribution,
        average_budget_remaining=round(avg_budget, 2),
        lowest_budget_service=lowest_budget_service,
        lowest_budget_percentage=lowest_budget,
        nearest_exhaustion=nearest,
        active_alerts=alert_feed.total,
        critical_alerts=critical_alerts,
        compliance_trend_24h=compliance_trend
    )


@router.get("/heatmap", response_model=HeatmapData)
async def get_risk_heatmap(
    hours: int = Query(24, description="Hours of history for heatmap"),
    interval_hours: int = Query(1, description="Interval between data points"),
    db: Session = Depends(get_db)
):
    """
    Get risk heatmap data (Service × Time matrix).
    
    Example Response:
    ```json
    {
        "services": ["api-gateway", "user-service", "payment-service"],
        "timestamps": ["2024-01-15T00:00:00Z", "2024-01-15T01:00:00Z", ...],
        "risk_matrix": [
            ["safe", "safe", "observe", "danger", ...],
            ["safe", "safe", "safe", "safe", ...],
            ["observe", "danger", "freeze", "danger", ...]
        ]
    }
    ```
    """
    services = db.query(Service).filter(Service.is_active == True).order_by(Service.name).all()
    
    if not services:
        return HeatmapData(services=[], timestamps=[], risk_matrix=[])
    
    # Generate timestamp points
    now = datetime.utcnow()
    timestamps = []
    current = now - timedelta(hours=hours)
    while current <= now:
        timestamps.append(current)
        current += timedelta(hours=interval_hours)
    
    # Build matrix
    risk_matrix = []
    
    for service in services:
        service_risks = []
        for ts in timestamps:
            # Get historical risk level closest to this timestamp
            history = db.query(BurnHistory).filter(
                BurnHistory.service_id == service.id,
                BurnHistory.window_minutes == 60,
                BurnHistory.timestamp >= ts - timedelta(minutes=30),
                BurnHistory.timestamp <= ts + timedelta(minutes=30)
            ).first()
            
            if history:
                service_risks.append(history.risk_level.value)
            else:
                service_risks.append("safe")  # Default if no data
        
        risk_matrix.append(service_risks)
    
    return HeatmapData(
        services=[s.name for s in services],
        timestamps=timestamps,
        risk_matrix=risk_matrix
    )


@router.get("/narrative/{service_name}")
async def get_service_narrative(
    service_name: str,
    db: Session = Depends(get_db)
):
    """
    Get detailed AI narrative for a specific service.
    """
    service = db.query(Service).filter(Service.name == service_name).first()
    if not service:
        raise HTTPException(status_code=404, detail=f"Service '{service_name}' not found")
    
    ai_generator = AINarrativeGenerator(db)
    narrative = ai_generator.generate_service_narrative(service.id)
    
    return {"service_name": service_name, "narrative": narrative}
