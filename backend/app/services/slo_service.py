"""
SLO Computation Engine
Calculates Service Level Objective compliance, error budgets, and rolling window metrics
"""

from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import and_, func

from app.models.database import Service, Metric, SLOTarget
from app.schemas.schemas import SLOComputation, RiskLevel
from app.core.config import get_settings, RISK_THRESHOLDS

settings = get_settings()


class SLOComputationEngine:
    """
    Engine for computing SLO compliance and error budgets.
    
    Core Formulas:
    
    1. Availability:
       availability = (total_requests - error_count) / total_requests * 100
    
    2. Error Budget Total (allowed errors):
       error_budget_total = (1 - slo_target/100) * total_requests
       Example: For 99.9% SLO with 1M requests = 0.001 * 1M = 1000 allowed errors
    
    3. Error Budget Consumed:
       consumed_percentage = (actual_errors / allowed_errors) * 100
    
    4. Error Budget Remaining:
       remaining_percentage = 100 - consumed_percentage
    """
    
    def __init__(self, db: Session):
        self.db = db
    
    def compute_slo(
        self,
        service_id: int,
        slo_target_id: Optional[int] = None
    ) -> List[SLOComputation]:
        """
        Compute SLO metrics for a service.
        
        Args:
            service_id: Service to compute SLOs for
            slo_target_id: Optional specific SLO target (computes all if None)
            
        Returns:
            List of SLO computations
        """
        service = self.db.query(Service).filter(Service.id == service_id).first()
        if not service:
            raise ValueError(f"Service {service_id} not found")
        
        # Get SLO targets
        query = self.db.query(SLOTarget).filter(
            and_(
                SLOTarget.service_id == service_id,
                SLOTarget.is_active == True
            )
        )
        if slo_target_id:
            query = query.filter(SLOTarget.id == slo_target_id)
        
        slo_targets = query.all()
        
        computations = []
        for target in slo_targets:
            computation = self._compute_single_slo(service, target)
            computations.append(computation)
        
        return computations
    
    def _compute_single_slo(
        self,
        service: Service,
        slo_target: SLOTarget
    ) -> SLOComputation:
        """Compute a single SLO target."""
        
        now = datetime.utcnow()
        window_start = now - timedelta(days=slo_target.window_days)
        
        # Aggregate metrics over the SLO window
        metrics = self.db.query(
            func.sum(Metric.total_requests).label('total_requests'),
            func.sum(Metric.error_count).label('error_count')
        ).filter(
            and_(
                Metric.service_id == service.id,
                Metric.timestamp >= window_start,
                Metric.timestamp <= now
            )
        ).first()
        
        total_requests = metrics.total_requests or 0
        error_count = metrics.error_count or 0
        
        # Calculate current availability
        current_value = 100.0
        if total_requests > 0:
            current_value = (total_requests - error_count) / total_requests * 100
        
        # Calculate error budget
        slo_target_fraction = slo_target.target_value / 100
        allowed_error_rate = 1 - slo_target_fraction
        
        # Total budget = allowed errors based on traffic
        total_budget = total_requests * allowed_error_rate if total_requests > 0 else 0
        consumed_budget = error_count
        
        # Budget percentages
        consumed_percentage = 0.0
        remaining_percentage = 100.0
        if total_budget > 0:
            consumed_percentage = min((consumed_budget / total_budget) * 100, 100)
            remaining_percentage = max(100 - consumed_percentage, 0)
        
        # Rolling window availability
        availability_5m = self._compute_window_availability(service.id, 5)
        availability_1h = self._compute_window_availability(service.id, 60)
        availability_24h = self._compute_window_availability(service.id, 1440)
        
        return SLOComputation(
            service_id=service.id,
            service_name=service.name,
            slo_name=slo_target.name,
            target_value=slo_target.target_value,
            current_value=round(current_value, 4),
            is_meeting_slo=current_value >= slo_target.target_value,
            total_budget=round(total_budget, 2),
            consumed_budget=consumed_budget,
            consumed_percentage=round(consumed_percentage, 2),
            remaining_percentage=round(remaining_percentage, 2),
            availability_5m=availability_5m,
            availability_1h=availability_1h,
            availability_24h=availability_24h,
            window_start=window_start,
            window_end=now,
            computed_at=now
        )
    
    def _compute_window_availability(
        self,
        service_id: int,
        window_minutes: int
    ) -> Optional[float]:
        """Compute availability over a rolling window."""
        
        now = datetime.utcnow()
        start = now - timedelta(minutes=window_minutes)
        
        metrics = self.db.query(
            func.sum(Metric.total_requests).label('total'),
            func.sum(Metric.error_count).label('errors')
        ).filter(
            and_(
                Metric.service_id == service_id,
                Metric.timestamp >= start,
                Metric.timestamp <= now
            )
        ).first()
        
        total = metrics.total or 0
        errors = metrics.errors or 0
        
        if total == 0:
            return None
        
        return round((total - errors) / total * 100, 4)
    
    def get_all_services_slo_status(self) -> List[Dict[str, Any]]:
        """Get SLO status summary for all active services."""
        
        services = self.db.query(Service).filter(Service.is_active == True).all()
        
        results = []
        for service in services:
            try:
                computations = self.compute_slo(service.id)
                
                overall_compliance = 100.0
                if computations:
                    # Weighted by how much below target
                    compliances = [
                        min(c.current_value / c.target_value * 100, 100) 
                        for c in computations
                    ]
                    overall_compliance = sum(compliances) / len(compliances)
                
                results.append({
                    "service_id": service.id,
                    "service_name": service.name,
                    "computations": computations,
                    "overall_compliance": round(overall_compliance, 2),
                    "is_healthy": overall_compliance >= 100,
                })
            except Exception as e:
                print(f"Error computing SLO for {service.name}: {e}")
        
        return results
    
    def compute_global_compliance(self) -> Dict[str, Any]:
        """Compute global platform compliance metrics."""
        
        services_status = self.get_all_services_slo_status()
        
        total_services = len(services_status)
        if total_services == 0:
            return {
                "total_services": 0,
                "services_meeting_slo": 0,
                "global_compliance": 100.0,
                "services_at_risk": []
            }
        
        services_meeting_slo = sum(1 for s in services_status if s["is_healthy"])
        global_compliance = sum(s["overall_compliance"] for s in services_status) / total_services
        
        # Services below 100% compliance
        at_risk = [
            s["service_name"] for s in services_status 
            if not s["is_healthy"]
        ]
        
        return {
            "total_services": total_services,
            "services_meeting_slo": services_meeting_slo,
            "global_compliance": round(global_compliance, 2),
            "services_at_risk": at_risk
        }


def create_default_slo_targets(db: Session, service_id: int) -> List[SLOTarget]:
    """
    Create default SLO targets for a new service.
    """
    defaults = [
        {
            "name": "availability",
            "target_value": 99.9,
            "window_days": 30,
            "burn_rate_threshold": 1.0,
            "critical_burn_rate": 2.0
        },
        {
            "name": "latency_p99",
            "target_value": 99.0,  # 99% of requests under threshold
            "window_days": 30,
            "burn_rate_threshold": 1.0,
            "critical_burn_rate": 2.0
        }
    ]
    
    targets = []
    for default in defaults:
        target = SLOTarget(service_id=service_id, **default)
        db.add(target)
        targets.append(target)
    
    db.commit()
    return targets
