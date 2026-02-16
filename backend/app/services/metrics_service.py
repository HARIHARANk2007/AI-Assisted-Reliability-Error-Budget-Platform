"""
Metrics Ingestion Service
Handles fetching and storing telemetry data from Prometheus or simulator
"""

import random
import math
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import and_

from app.models.database import Service, Metric
from app.schemas.schemas import MetricSnapshot
from app.core.config import get_settings

settings = get_settings()


class MetricsIngestionService:
    """
    Service for ingesting and managing telemetry metrics.
    Supports both real Prometheus metrics and simulated data for testing.
    """
    
    def __init__(self, db: Session):
        self.db = db
    
    def ingest_metrics(self, metrics: List[MetricSnapshot]) -> Dict[str, int]:
        """
        Ingest a batch of metric snapshots.
        
        Args:
            metrics: List of metric data points
            
        Returns:
            Dict with processed and error counts
        """
        processed = 0
        errors = 0
        
        for metric in metrics:
            try:
                # Find or create service
                service = self.db.query(Service).filter(
                    Service.name == metric.service
                ).first()
                
                if not service:
                    service = Service(name=metric.service, is_active=True)
                    self.db.add(service)
                    self.db.flush()
                
                # Calculate success rate
                success_rate = None
                if metric.total_requests > 0:
                    success_rate = (
                        (metric.total_requests - metric.error_count) 
                        / metric.total_requests * 100
                    )
                
                # Create metric record
                db_metric = Metric(
                    service_id=service.id,
                    timestamp=metric.timestamp,
                    total_requests=metric.total_requests,
                    error_count=metric.error_count,
                    latency_p50=metric.latency_p50,
                    latency_p95=metric.latency_p95,
                    latency_p99=metric.latency_p99,
                    success_rate=success_rate
                )
                self.db.add(db_metric)
                processed += 1
                
            except Exception as e:
                errors += 1
                print(f"Error ingesting metric: {e}")
        
        self.db.commit()
        return {"processed": processed, "errors": errors}
    
    def get_metrics(
        self,
        service_id: int,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 1000
    ) -> List[Metric]:
        """
        Retrieve metrics for a service within a time range.
        """
        query = self.db.query(Metric).filter(Metric.service_id == service_id)
        
        if start_time:
            query = query.filter(Metric.timestamp >= start_time)
        if end_time:
            query = query.filter(Metric.timestamp <= end_time)
        
        return query.order_by(Metric.timestamp.desc()).limit(limit).all()
    
    def get_latest_metrics(self, service_id: int) -> Optional[Metric]:
        """Get the most recent metric snapshot for a service."""
        return self.db.query(Metric).filter(
            Metric.service_id == service_id
        ).order_by(Metric.timestamp.desc()).first()
    
    def get_aggregated_metrics(
        self,
        service_id: int,
        window_minutes: int
    ) -> Dict[str, Any]:
        """
        Get aggregated metrics over a rolling window.
        
        Args:
            service_id: Service ID
            window_minutes: Rolling window in minutes
            
        Returns:
            Aggregated metrics dict
        """
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(minutes=window_minutes)
        
        metrics = self.db.query(Metric).filter(
            and_(
                Metric.service_id == service_id,
                Metric.timestamp >= start_time,
                Metric.timestamp <= end_time
            )
        ).all()
        
        if not metrics:
            return {
                "total_requests": 0,
                "error_count": 0,
                "availability": None,
                "avg_latency_p99": None,
                "window_minutes": window_minutes,
                "data_points": 0
            }
        
        total_requests = sum(m.total_requests for m in metrics)
        error_count = sum(m.error_count for m in metrics)
        
        availability = None
        if total_requests > 0:
            availability = (total_requests - error_count) / total_requests * 100
        
        latencies = [m.latency_p99 for m in metrics if m.latency_p99 is not None]
        avg_latency_p99 = sum(latencies) / len(latencies) if latencies else None
        
        return {
            "total_requests": total_requests,
            "error_count": error_count,
            "availability": availability,
            "avg_latency_p99": avg_latency_p99,
            "window_minutes": window_minutes,
            "data_points": len(metrics)
        }
    
    def cleanup_old_metrics(self, retention_days: int = None) -> int:
        """
        Remove metrics older than retention period.
        
        Returns:
            Number of records deleted
        """
        if retention_days is None:
            retention_days = settings.METRICS_RETENTION_DAYS
        
        cutoff = datetime.utcnow() - timedelta(days=retention_days)
        
        deleted = self.db.query(Metric).filter(
            Metric.timestamp < cutoff
        ).delete()
        
        self.db.commit()
        return deleted


class MetricsSimulator:
    """
    Simulates Prometheus-style metrics for testing and demo purposes.
    Generates realistic telemetry patterns with configurable chaos.
    """
    
    SERVICES = [
        {"name": "api-gateway", "base_rps": 10000, "base_error_rate": 0.001},
        {"name": "user-service", "base_rps": 5000, "base_error_rate": 0.002},
        {"name": "payment-service", "base_rps": 2000, "base_error_rate": 0.0005},
        {"name": "inventory-service", "base_rps": 3000, "base_error_rate": 0.001},
        {"name": "notification-service", "base_rps": 8000, "base_error_rate": 0.003},
        {"name": "search-service", "base_rps": 6000, "base_error_rate": 0.002},
        {"name": "recommendation-engine", "base_rps": 4000, "base_error_rate": 0.001},
        {"name": "auth-service", "base_rps": 7000, "base_error_rate": 0.0008},
    ]
    
    def __init__(self, chaos_level: float = 0.1):
        """
        Initialize simulator.
        
        Args:
            chaos_level: 0.0 (stable) to 1.0 (chaotic) - affects variance and incidents
        """
        self.chaos_level = chaos_level
        self._incident_services = set()
        self._incident_start_times = {}
    
    def generate_snapshot(
        self,
        timestamp: datetime = None
    ) -> List[MetricSnapshot]:
        """
        Generate a snapshot of metrics for all services.
        
        Args:
            timestamp: Timestamp for metrics (defaults to now)
            
        Returns:
            List of MetricSnapshot objects
        """
        if timestamp is None:
            timestamp = datetime.utcnow()
        
        snapshots = []
        
        for service_config in self.SERVICES:
            snapshot = self._generate_service_snapshot(service_config, timestamp)
            snapshots.append(snapshot)
        
        return snapshots
    
    def _generate_service_snapshot(
        self,
        service_config: Dict[str, Any],
        timestamp: datetime
    ) -> MetricSnapshot:
        """Generate metrics for a single service."""
        
        name = service_config["name"]
        base_rps = service_config["base_rps"]
        base_error_rate = service_config["base_error_rate"]
        
        # Time-based patterns (simulate daily/hourly variations)
        hour = timestamp.hour
        day_factor = 1.0 + 0.3 * math.sin(hour / 24 * 2 * math.pi - math.pi/2)
        
        # Random variance
        variance = random.gauss(1.0, 0.1 * self.chaos_level)
        
        # Check for ongoing or new incidents
        is_incident = name in self._incident_services
        if not is_incident and random.random() < 0.01 * self.chaos_level:
            self._incident_services.add(name)
            self._incident_start_times[name] = timestamp
            is_incident = True
        
        # End incidents after some time
        if is_incident and name in self._incident_start_times:
            incident_duration = (timestamp - self._incident_start_times[name]).total_seconds()
            if incident_duration > random.randint(300, 1800):  # 5-30 minutes
                self._incident_services.discard(name)
                del self._incident_start_times[name]
                is_incident = False
        
        # Calculate requests
        rps = int(base_rps * day_factor * variance)
        total_requests = max(rps, 0)
        
        # Calculate error rate
        if is_incident:
            # During incident: elevated error rate
            error_rate = base_error_rate * random.uniform(5, 50)
        else:
            error_rate = base_error_rate * random.gauss(1.0, 0.2 * self.chaos_level)
        
        error_rate = max(0, min(1, error_rate))  # Clamp to [0, 1]
        error_count = int(total_requests * error_rate)
        
        # Calculate latencies
        base_latency = random.uniform(10, 50)  # ms
        latency_multiplier = random.uniform(1.5, 3.0) if is_incident else 1.0
        
        latency_p50 = base_latency * latency_multiplier * random.gauss(1.0, 0.1)
        latency_p95 = latency_p50 * random.uniform(2, 4)
        latency_p99 = latency_p95 * random.uniform(1.5, 2.5)
        
        return MetricSnapshot(
            service=name,
            timestamp=timestamp,
            total_requests=total_requests,
            error_count=error_count,
            latency_p50=round(latency_p50, 2),
            latency_p95=round(latency_p95, 2),
            latency_p99=round(latency_p99, 2)
        )
    
    def generate_historical_data(
        self,
        hours: int = 24,
        interval_seconds: int = 60
    ) -> List[MetricSnapshot]:
        """
        Generate historical metrics data.
        
        Args:
            hours: Number of hours of history to generate
            interval_seconds: Time between data points
            
        Returns:
            List of historical metric snapshots
        """
        snapshots = []
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(hours=hours)
        
        current_time = start_time
        while current_time <= end_time:
            snapshots.extend(self.generate_snapshot(current_time))
            current_time += timedelta(seconds=interval_seconds)
        
        return snapshots
    
    def inject_incident(self, service_name: str):
        """Manually inject an incident for a service."""
        self._incident_services.add(service_name)
        self._incident_start_times[service_name] = datetime.utcnow()
    
    def resolve_incident(self, service_name: str):
        """Manually resolve an incident for a service."""
        self._incident_services.discard(service_name)
        if service_name in self._incident_start_times:
            del self._incident_start_times[service_name]
