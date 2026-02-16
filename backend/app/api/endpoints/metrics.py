"""
Metrics Ingestion API Endpoints
"""

from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List

from app.core.database import get_db
from app.schemas.schemas import (
    MetricSnapshot, MetricsIngestRequest, MetricsIngestResponse, MetricResponse
)
from app.services.metrics_service import MetricsIngestionService, MetricsSimulator
from app.models.database import Service

router = APIRouter(prefix="/metrics", tags=["Metrics"])


@router.post("/ingest", response_model=MetricsIngestResponse)
async def ingest_metrics(
    request: MetricsIngestRequest,
    db: Session = Depends(get_db)
):
    """
    Ingest batch of telemetry metrics.
    
    Request:
    ```json
    {
        "metrics": [
            {
                "service": "api-gateway",
                "timestamp": "2024-01-15T10:30:00Z",
                "total_requests": 10000,
                "error_count": 15,
                "latency_p50": 25.5,
                "latency_p95": 95.2,
                "latency_p99": 245.8
            }
        ]
    }
    ```
    
    Response:
    ```json
    {
        "processed": 1,
        "errors": 0,
        "message": "Successfully ingested 1 metrics"
    }
    ```
    """
    ingestion_service = MetricsIngestionService(db)
    result = ingestion_service.ingest_metrics(request.metrics)
    
    return MetricsIngestResponse(
        processed=result["processed"],
        errors=result["errors"],
        message=f"Successfully ingested {result['processed']} metrics"
    )


@router.get("/{service_name}", response_model=List[MetricResponse])
async def get_service_metrics(
    service_name: str,
    hours: int = Query(24, description="Hours of history"),
    limit: int = Query(1000, ge=1, le=10000),
    db: Session = Depends(get_db)
):
    """
    Get metrics history for a service.
    """
    from datetime import datetime, timedelta
    
    service = db.query(Service).filter(Service.name == service_name).first()
    if not service:
        raise HTTPException(status_code=404, detail=f"Service '{service_name}' not found")
    
    ingestion_service = MetricsIngestionService(db)
    
    start_time = datetime.utcnow() - timedelta(hours=hours)
    metrics = ingestion_service.get_metrics(
        service_id=service.id,
        start_time=start_time,
        limit=limit
    )
    
    return [MetricResponse.model_validate(m) for m in metrics]


@router.get("/{service_name}/aggregated")
async def get_aggregated_metrics(
    service_name: str,
    window_minutes: int = Query(60, description="Aggregation window in minutes"),
    db: Session = Depends(get_db)
):
    """
    Get aggregated metrics over a rolling window.
    
    Example Response:
    ```json
    {
        "total_requests": 150000,
        "error_count": 225,
        "availability": 99.85,
        "avg_latency_p99": 185.5,
        "window_minutes": 60,
        "data_points": 60
    }
    ```
    """
    service = db.query(Service).filter(Service.name == service_name).first()
    if not service:
        raise HTTPException(status_code=404, detail=f"Service '{service_name}' not found")
    
    ingestion_service = MetricsIngestionService(db)
    return ingestion_service.get_aggregated_metrics(service.id, window_minutes)


@router.post("/simulate")
async def generate_simulated_metrics(
    hours: int = Query(24, description="Hours of history to generate"),
    chaos_level: float = Query(0.2, ge=0.0, le=1.0, description="Chaos level (0=stable, 1=chaotic)"),
    background_tasks: BackgroundTasks = None,
    db: Session = Depends(get_db)
):
    """
    Generate simulated metrics data for demo/testing.
    
    This creates realistic telemetry data with:
    - Daily traffic patterns
    - Random variance
    - Occasional incidents
    
    Use chaos_level to control how unstable the simulated environment is.
    """
    simulator = MetricsSimulator(chaos_level=chaos_level)
    historical_data = simulator.generate_historical_data(hours=hours, interval_seconds=60)
    
    ingestion_service = MetricsIngestionService(db)
    result = ingestion_service.ingest_metrics(historical_data)
    
    return {
        "message": f"Generated {hours} hours of simulated data",
        "metrics_generated": len(historical_data),
        "processed": result["processed"],
        "errors": result["errors"],
        "chaos_level": chaos_level
    }


@router.post("/simulate/snapshot")
async def generate_single_snapshot(
    chaos_level: float = Query(0.2, ge=0.0, le=1.0),
    db: Session = Depends(get_db)
):
    """
    Generate and ingest a single snapshot of metrics (current moment).
    Useful for real-time simulation.
    """
    simulator = MetricsSimulator(chaos_level=chaos_level)
    snapshot = simulator.generate_snapshot()
    
    ingestion_service = MetricsIngestionService(db)
    result = ingestion_service.ingest_metrics(snapshot)
    
    return {
        "message": "Snapshot generated",
        "services": len(snapshot),
        "processed": result["processed"],
        "timestamp": snapshot[0].timestamp if snapshot else None
    }


@router.post("/cleanup")
async def cleanup_old_metrics(
    retention_days: int = Query(30, ge=1, le=365),
    db: Session = Depends(get_db)
):
    """
    Clean up metrics older than retention period.
    """
    ingestion_service = MetricsIngestionService(db)
    deleted = ingestion_service.cleanup_old_metrics(retention_days)
    
    return {
        "message": f"Cleanup completed",
        "deleted_records": deleted,
        "retention_days": retention_days
    }
