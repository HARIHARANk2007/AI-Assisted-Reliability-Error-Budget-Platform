"""
Release Gate Controller
Implements deployment gating based on reliability state
"""

from datetime import datetime
from typing import Optional, List, Dict, Any
import uuid
from sqlalchemy.orm import Session
from sqlalchemy import and_

from app.models.database import Service, Deployment, RiskLevel as DBRiskLevel
from app.schemas.schemas import ReleaseCheckRequest, ReleaseCheckResponse, RiskLevel
from app.services.burn_rate_service import BurnRateEngine
from app.services.forecast_service import ForecastModule
from app.core.config import get_settings

settings = get_settings()


class ReleaseGateController:
    """
    Release gate for deployment decisions based on system reliability.
    
    Decision Logic:
    1. If risk_level == FREEZE → BLOCK
    2. If risk_level == DANGER → BLOCK (unless override)
    3. If burn_rate > threshold → BLOCK
    4. If budget_consumed > threshold → BLOCK
    5. Otherwise → ALLOW
    
    Overrides:
    - Requires explicit override flag and reason
    - Recorded for audit purposes
    """
    
    def __init__(self, db: Session):
        self.db = db
        self.burn_engine = BurnRateEngine(db)
        self.forecast_module = ForecastModule(db)
    
    def check_release(self, request: ReleaseCheckRequest) -> ReleaseCheckResponse:
        """
        Evaluate whether a deployment should proceed.
        
        Args:
            request: Release check request with service and deployment info
            
        Returns:
            ReleaseCheckResponse with decision and context
        """
        # Find service
        service = self.db.query(Service).filter(
            Service.name == request.service_name
        ).first()
        
        if not service:
            return ReleaseCheckResponse(
                allowed=False,
                reason=f"Service '{request.service_name}' not found",
                service_name=request.service_name,
                deployment_id=request.deployment_id,
                current_risk_level=RiskLevel.FREEZE,
                current_burn_rate=0.0,
                error_budget_remaining=0.0,
                time_to_exhaustion_hours=None,
                recommendations=["Register the service before deploying"],
                checked_at=datetime.utcnow(),
                checked_by="system"
            )
        
        # Get current reliability state
        burn_computation = self.burn_engine.compute_burn_rate(service.id, 60)
        weighted_burn, worst_risk = self.burn_engine.get_weighted_burn_rate(service.id)
        
        # Get forecast
        forecast = self.forecast_module.forecast_exhaustion(service.id)
        
        # Make decision
        allowed, reason, recommendations = self._evaluate_gate(
            burn_rate=weighted_burn,
            risk_level=worst_risk,
            budget_remaining=burn_computation.error_budget_remaining,
            time_to_exhaustion=forecast.time_to_exhaustion_hours,
            override=request.override,
            override_reason=request.override_reason
        )
        
        # Record deployment attempt
        self._record_deployment(
            service_id=service.id,
            deployment_id=request.deployment_id,
            version=request.version,
            requested_by=request.requested_by,
            allowed=allowed,
            reason=reason,
            risk_level=worst_risk,
            burn_rate=weighted_burn
        )
        
        return ReleaseCheckResponse(
            allowed=allowed,
            reason=reason,
            service_name=service.name,
            deployment_id=request.deployment_id,
            current_risk_level=worst_risk,
            current_burn_rate=weighted_burn,
            error_budget_remaining=burn_computation.error_budget_remaining,
            time_to_exhaustion_hours=forecast.time_to_exhaustion_hours,
            recommendations=recommendations,
            checked_at=datetime.utcnow(),
            checked_by=request.requested_by or "system"
        )
    
    def _evaluate_gate(
        self,
        burn_rate: float,
        risk_level: RiskLevel,
        budget_remaining: float,
        time_to_exhaustion: Optional[float],
        override: bool,
        override_reason: Optional[str]
    ) -> tuple[bool, str, List[str]]:
        """
        Evaluate gate conditions and return decision.
        
        Returns:
            Tuple of (allowed, reason, recommendations)
        """
        recommendations = []
        
        # FREEZE - Always block unless override
        if risk_level == RiskLevel.FREEZE:
            if override and override_reason:
                return (
                    True,
                    f"OVERRIDE: Deployment allowed despite FREEZE state. Reason: {override_reason}",
                    ["Deployment approved via override - monitor closely"]
                )
            return (
                False,
                "Deployment blocked: System is in FREEZE state due to critical reliability issues",
                [
                    "Investigate and resolve active incidents before deploying",
                    "Error budget is critically low or exhausted",
                    "Consider rolling back recent changes"
                ]
            )
        
        # DANGER - Block unless override
        if risk_level == RiskLevel.DANGER:
            recommendations.append("System is in DANGER state - consider waiting")
            if override and override_reason:
                return (
                    True,
                    f"OVERRIDE: Deployment allowed despite DANGER state. Reason: {override_reason}",
                    recommendations + ["Monitor deployment closely and be ready to rollback"]
                )
            return (
                False,
                "Deployment blocked: System is in DANGER state with elevated error rates",
                recommendations + [
                    "Error budget is running low",
                    "Wait for system to stabilize or provide override with justification"
                ]
            )
        
        # Check burn rate threshold
        if burn_rate > settings.RELEASE_GATE_BURN_RATE_THRESHOLD:
            return (
                False,
                f"Deployment blocked: Burn rate ({burn_rate:.2f}x) exceeds threshold ({settings.RELEASE_GATE_BURN_RATE_THRESHOLD}x)",
                [
                    "Current error rate is too high for safe deployment",
                    "Investigate recent changes that may have caused elevated errors"
                ]
            )
        
        # Check budget threshold
        budget_consumed = 100 - budget_remaining
        if budget_consumed > settings.RELEASE_GATE_BUDGET_THRESHOLD:
            return (
                False,
                f"Deployment blocked: Error budget {budget_consumed:.1f}% consumed exceeds threshold ({settings.RELEASE_GATE_BUDGET_THRESHOLD}%)",
                [
                    "Error budget is nearly exhausted",
                    "Prioritize reliability improvements before new deployments"
                ]
            )
        
        # Check if exhaustion is imminent
        if time_to_exhaustion is not None and time_to_exhaustion < 4:
            recommendations.append(
                f"Warning: Error budget will be exhausted in ~{time_to_exhaustion:.1f} hours"
            )
        
        # OBSERVE - Allow with warnings
        if risk_level == RiskLevel.OBSERVE:
            recommendations.extend([
                "System is in OBSERVE state - increased monitoring recommended",
                "Consider smaller deployment batches"
            ])
            return (
                True,
                "Deployment allowed with caution: System reliability is being observed",
                recommendations
            )
        
        # SAFE - Allow
        return (
            True,
            "Deployment allowed: System reliability is healthy",
            recommendations if recommendations else ["System is operating normally"]
        )
    
    def _record_deployment(
        self,
        service_id: int,
        deployment_id: str,
        version: Optional[str],
        requested_by: Optional[str],
        allowed: bool,
        reason: str,
        risk_level: RiskLevel,
        burn_rate: float
    ):
        """Record deployment attempt for audit."""
        
        # Generate unique ID if not provided
        if not deployment_id:
            deployment_id = str(uuid.uuid4())
        
        db_risk = DBRiskLevel(risk_level.value)
        
        deployment = Deployment(
            service_id=service_id,
            deployment_id=deployment_id,
            version=version,
            requested_by=requested_by,
            allowed=allowed,
            blocked_reason=reason if not allowed else None,
            risk_level_at_request=db_risk,
            burn_rate_at_request=burn_rate,
            status="approved" if allowed else "rejected"
        )
        self.db.add(deployment)
        self.db.commit()
    
    def get_deployment_history(
        self,
        service_id: Optional[int] = None,
        limit: int = 50
    ) -> List[Deployment]:
        """Get deployment history, optionally filtered by service."""
        
        query = self.db.query(Deployment)
        if service_id:
            query = query.filter(Deployment.service_id == service_id)
        
        return query.order_by(Deployment.requested_at.desc()).limit(limit).all()
    
    def get_gate_statistics(self, days: int = 7) -> Dict[str, Any]:
        """Get deployment gate statistics over a period."""
        from datetime import timedelta
        from sqlalchemy import func
        
        cutoff = datetime.utcnow() - timedelta(days=days)
        
        # Total deployments
        total = self.db.query(func.count(Deployment.id)).filter(
            Deployment.requested_at >= cutoff
        ).scalar()
        
        # Blocked deployments
        blocked = self.db.query(func.count(Deployment.id)).filter(
            and_(
                Deployment.requested_at >= cutoff,
                Deployment.allowed == False
            )
        ).scalar()
        
        # By risk level at request
        risk_counts = self.db.query(
            Deployment.risk_level_at_request,
            func.count(Deployment.id)
        ).filter(
            Deployment.requested_at >= cutoff
        ).group_by(Deployment.risk_level_at_request).all()
        
        risk_distribution = {r[0].value: r[1] for r in risk_counts if r[0]}
        
        return {
            "period_days": days,
            "total_deployments": total or 0,
            "blocked_deployments": blocked or 0,
            "allowed_deployments": (total or 0) - (blocked or 0),
            "block_rate": round((blocked or 0) / total * 100, 2) if total else 0,
            "risk_distribution": risk_distribution
        }
