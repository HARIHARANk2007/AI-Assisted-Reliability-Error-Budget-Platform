"""
Burn Rate Engine
Calculates error budget burn rates and maintains historical records
"""

from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import and_, func, desc

from app.models.database import Service, Metric, SLOTarget, BurnHistory, RiskLevel as DBRiskLevel
from app.schemas.schemas import BurnRateComputation, RiskLevel
from app.core.config import get_settings, RISK_THRESHOLDS

settings = get_settings()


class BurnRateEngine:
    """
    Engine for computing and tracking error budget burn rates.
    
    Core Formula:
    burn_rate = current_error_rate / allowed_error_rate
    
    Where:
    - current_error_rate = errors_in_window / requests_in_window
    - allowed_error_rate = 1 - (slo_target / 100)
    
    Interpretation:
    - burn_rate = 1.0: Consuming budget at exactly the allowed rate
    - burn_rate = 2.0: Consuming budget 2x faster than allowed
    - burn_rate = 0.5: Consuming budget at half the allowed rate (healthy)
    
    Time to Exhaustion:
    If burning at rate B with R% budget remaining:
    time_to_exhaustion = (R / 100) * window_hours / B
    """
    
    WINDOW_CONFIGS = [
        {"minutes": 5, "name": "5m", "weight": 0.3},
        {"minutes": 60, "name": "1h", "weight": 0.4},
        {"minutes": 1440, "name": "24h", "weight": 0.3},
    ]
    
    def __init__(self, db: Session):
        self.db = db
    
    def compute_burn_rate(
        self,
        service_id: int,
        window_minutes: int = 60
    ) -> BurnRateComputation:
        """
        Compute current burn rate for a service.
        
        Args:
            service_id: Service to compute for
            window_minutes: Rolling window size
            
        Returns:
            BurnRateComputation with all metrics
        """
        service = self.db.query(Service).filter(Service.id == service_id).first()
        if not service:
            raise ValueError(f"Service {service_id} not found")
        
        # Get SLO target (use availability as primary)
        slo_target = self.db.query(SLOTarget).filter(
            and_(
                SLOTarget.service_id == service_id,
                SLOTarget.name == "availability",
                SLOTarget.is_active == True
            )
        ).first()
        
        if not slo_target:
            # Use default 99.9% if no target configured
            target_value = 99.9
            critical_burn_rate = 2.0
        else:
            target_value = slo_target.target_value
            critical_burn_rate = slo_target.critical_burn_rate
        
        # Calculate allowed error rate from SLO
        allowed_error_rate = (100 - target_value) / 100  # e.g., 0.001 for 99.9%
        
        # Get metrics for the window
        now = datetime.utcnow()
        window_start = now - timedelta(minutes=window_minutes)
        
        metrics = self.db.query(
            func.sum(Metric.total_requests).label('total'),
            func.sum(Metric.error_count).label('errors')
        ).filter(
            and_(
                Metric.service_id == service_id,
                Metric.timestamp >= window_start,
                Metric.timestamp <= now
            )
        ).first()
        
        total_requests = metrics.total or 0
        error_count = metrics.errors or 0
        
        # Current error rate
        current_error_rate = 0.0
        if total_requests > 0:
            current_error_rate = error_count / total_requests
        
        # Burn rate calculation
        burn_rate = 0.0
        if allowed_error_rate > 0:
            burn_rate = current_error_rate / allowed_error_rate
        
        # Error budget calculation
        # Total budget for the window
        total_budget = total_requests * allowed_error_rate
        consumed = error_count
        
        consumed_percentage = 0.0
        remaining_percentage = 100.0
        if total_budget > 0:
            consumed_percentage = min((consumed / total_budget) * 100, 100)
            remaining_percentage = max(100 - consumed_percentage, 0)
        
        # Determine risk level
        risk_level = self._classify_risk(burn_rate, consumed_percentage)
        risk_info = RISK_THRESHOLDS[risk_level.value]
        
        return BurnRateComputation(
            service_id=service_id,
            service_name=service.name,
            timestamp=now,
            window_minutes=window_minutes,
            current_error_rate=round(current_error_rate, 6),
            allowed_error_rate=round(allowed_error_rate, 6),
            burn_rate=round(burn_rate, 3),
            error_budget_consumed=round(consumed_percentage, 2),
            error_budget_remaining=round(remaining_percentage, 2),
            risk_level=risk_level,
            risk_color=risk_info["color"],
            risk_action=risk_info["action"]
        )
    
    def _classify_risk(
        self,
        burn_rate: float,
        budget_consumed: float
    ) -> RiskLevel:
        """
        Classify risk level based on burn rate and budget consumption.
        
        Thresholds (configurable):
        - SAFE: burn_rate < 1.0 AND budget_consumed < 50%
        - OBSERVE: burn_rate < 1.5 AND budget_consumed < 70%
        - DANGER: burn_rate < 2.0 AND budget_consumed < 85%
        - FREEZE: burn_rate >= 2.0 OR budget_consumed >= 85%
        """
        if burn_rate >= settings.BURN_RATE_FREEZE_THRESHOLD or budget_consumed >= settings.ERROR_BUDGET_FREEZE_THRESHOLD:
            return RiskLevel.FREEZE
        elif burn_rate >= settings.BURN_RATE_DANGER_THRESHOLD or budget_consumed >= settings.ERROR_BUDGET_DANGER_THRESHOLD:
            return RiskLevel.DANGER
        elif burn_rate >= settings.BURN_RATE_OBSERVE_THRESHOLD or budget_consumed >= settings.ERROR_BUDGET_OBSERVE_THRESHOLD:
            return RiskLevel.OBSERVE
        else:
            return RiskLevel.SAFE
    
    def compute_all_windows(self, service_id: int) -> List[BurnRateComputation]:
        """Compute burn rates for all standard windows."""
        results = []
        for window in self.WINDOW_CONFIGS:
            computation = self.compute_burn_rate(service_id, window["minutes"])
            results.append(computation)
        return results
    
    def store_burn_history(self, computation: BurnRateComputation) -> BurnHistory:
        """Store a burn rate computation in history."""
        
        # Map schema RiskLevel to DB RiskLevel
        db_risk_level = DBRiskLevel(computation.risk_level.value)
        
        history = BurnHistory(
            service_id=computation.service_id,
            timestamp=computation.timestamp,
            window_minutes=computation.window_minutes,
            burn_rate=computation.burn_rate,
            error_budget_consumed=computation.error_budget_consumed,
            error_budget_remaining=computation.error_budget_remaining,
            time_to_exhaustion_hours=None,  # Computed by forecast module
            risk_level=db_risk_level
        )
        self.db.add(history)
        self.db.commit()
        return history
    
    def get_burn_history(
        self,
        service_id: int,
        hours: int = 24,
        window_minutes: int = 60
    ) -> List[BurnHistory]:
        """Get historical burn rates for a service."""
        
        cutoff = datetime.utcnow() - timedelta(hours=hours)
        
        return self.db.query(BurnHistory).filter(
            and_(
                BurnHistory.service_id == service_id,
                BurnHistory.window_minutes == window_minutes,
                BurnHistory.timestamp >= cutoff
            )
        ).order_by(BurnHistory.timestamp.desc()).all()
    
    def get_burn_statistics(
        self,
        service_id: int,
        hours: int = 24
    ) -> Dict[str, Any]:
        """Get burn rate statistics over a period."""
        
        cutoff = datetime.utcnow() - timedelta(hours=hours)
        
        stats = self.db.query(
            func.avg(BurnHistory.burn_rate).label('avg_burn'),
            func.max(BurnHistory.burn_rate).label('max_burn'),
            func.min(BurnHistory.burn_rate).label('min_burn'),
            func.avg(BurnHistory.error_budget_consumed).label('avg_consumed')
        ).filter(
            and_(
                BurnHistory.service_id == service_id,
                BurnHistory.timestamp >= cutoff
            )
        ).first()
        
        return {
            "average_burn_rate": round(stats.avg_burn or 0, 3),
            "peak_burn_rate": round(stats.max_burn or 0, 3),
            "min_burn_rate": round(stats.min_burn or 0, 3),
            "average_budget_consumed": round(stats.avg_consumed or 0, 2),
            "hours": hours
        }
    
    def get_weighted_burn_rate(self, service_id: int) -> Tuple[float, RiskLevel]:
        """
        Calculate weighted burn rate across all windows.
        
        Weights give more importance to longer windows for stability,
        but also considers short windows for recent issues.
        """
        computations = self.compute_all_windows(service_id)
        
        if not computations:
            return 0.0, RiskLevel.SAFE
        
        weighted_burn = 0.0
        total_weight = 0.0
        worst_risk = RiskLevel.SAFE
        
        for computation, config in zip(computations, self.WINDOW_CONFIGS):
            weight = config["weight"]
            weighted_burn += computation.burn_rate * weight
            total_weight += weight
            
            # Track worst risk level
            if self._risk_severity(computation.risk_level) > self._risk_severity(worst_risk):
                worst_risk = computation.risk_level
        
        final_burn = weighted_burn / total_weight if total_weight > 0 else 0.0
        return round(final_burn, 3), worst_risk
    
    def _risk_severity(self, risk: RiskLevel) -> int:
        """Convert risk level to numeric severity for comparison."""
        severity_map = {
            RiskLevel.SAFE: 0,
            RiskLevel.OBSERVE: 1,
            RiskLevel.DANGER: 2,
            RiskLevel.FREEZE: 3
        }
        return severity_map.get(risk, 0)
