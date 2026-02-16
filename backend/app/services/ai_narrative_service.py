"""
AI Narrative Generator
Generates human-readable reliability insights and summaries
"""

from datetime import datetime
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import and_

from app.models.database import Service, Alert
from app.schemas.schemas import (
    AIInsight, AISummaryResponse, RiskLevel,
    AlertSeverity
)
from app.services.burn_rate_service import BurnRateEngine
from app.services.forecast_service import ForecastModule
from app.services.slo_service import SLOComputationEngine


class AINarrativeGenerator:
    """
    Generates AI-readable reliability summaries and insights.
    
    Uses template-based generation with dynamic data interpolation
    to create human-readable narratives about system reliability.
    """
    
    # Narrative templates
    TEMPLATES = {
        "burn_critical": (
            "{service} is burning error budget {burn_rate}× faster than allowed. "
            "SLA breach likely in ~{time_to_exhaustion}."
        ),
        "burn_elevated": (
            "{service} error budget consumption is elevated at {burn_rate}× normal rate. "
            "{budget_remaining}% budget remaining."
        ),
        "burn_healthy": (
            "{service} is operating within error budget parameters. "
            "Current burn rate: {burn_rate}×."
        ),
        "budget_exhausted": (
            "{service} has EXHAUSTED its error budget. "
            "All non-critical deployments should be halted."
        ),
        "budget_critical": (
            "{service} error budget is critically low at {budget_remaining}%. "
            "Immediate attention required."
        ),
        "slo_breach": (
            "{service} is currently BELOW SLO target. "
            "Availability: {availability}% (Target: {target}%)."
        ),
        "trend_worsening": (
            "{service} reliability is degrading. Burn rate has increased "
            "{trend_change}% over the last hour."
        ),
        "trend_improving": (
            "{service} reliability is improving. Burn rate has decreased "
            "{trend_change}% over the last hour."
        ),
        "incident_active": (
            "Active incident detected for {service}. "
            "Error rate spike of {error_rate_increase}%."
        ),
    }
    
    def __init__(self, db: Session):
        self.db = db
        self.burn_engine = BurnRateEngine(db)
        self.forecast_module = ForecastModule(db)
        self.slo_engine = SLOComputationEngine(db)
    
    def generate_summary(self) -> AISummaryResponse:
        """
        Generate comprehensive reliability summary for all services.
        
        Returns:
            AISummaryResponse with executive summary and per-service insights
        """
        services = self.db.query(Service).filter(Service.is_active == True).all()
        
        insights = []
        services_at_risk = []
        action_items = []
        total_health_score = 0
        critical_count = 0
        
        for service in services:
            service_insights, health_score = self._analyze_service(service)
            insights.extend(service_insights)
            total_health_score += health_score
            
            # Track at-risk services
            for insight in service_insights:
                if insight.severity in ["critical", "warning"]:
                    if service.name not in services_at_risk:
                        services_at_risk.append(service.name)
                if insight.severity == "critical":
                    critical_count += 1
        
        # Calculate overall metrics
        overall_score = total_health_score / len(services) if services else 100
        
        # Determine overall health
        if overall_score >= 90:
            overall_health = "healthy"
        elif overall_score >= 70:
            overall_health = "degraded"
        else:
            overall_health = "critical"
        
        # Generate action items
        action_items = self._generate_action_items(insights, services_at_risk)
        
        # Get nearest exhaustion
        nearest_exhaustion = self.forecast_module.get_nearest_exhaustion()
        
        # Generate executive summary
        executive_summary = self._generate_executive_summary(
            len(services),
            services_at_risk,
            overall_score,
            critical_count,
            nearest_exhaustion
        )
        
        return AISummaryResponse(
            generated_at=datetime.utcnow(),
            overall_health=overall_health,
            overall_score=round(overall_score, 1),
            executive_summary=executive_summary,
            insights=insights,
            action_items=action_items,
            services_at_risk=services_at_risk,
            nearest_budget_exhaustion=nearest_exhaustion
        )
    
    def _analyze_service(self, service: Service) -> tuple[List[AIInsight], float]:
        """
        Analyze a single service and generate insights.
        
        Returns:
            Tuple of (insights list, health score 0-100)
        """
        insights = []
        health_score = 100
        
        try:
            # Get burn rate
            burn = self.burn_engine.compute_burn_rate(service.id, 60)
            forecast = self.forecast_module.forecast_exhaustion(service.id)
            
            # Check budget exhaustion
            if burn.error_budget_remaining <= 0:
                insights.append(AIInsight(
                    service_name=service.name,
                    insight_type="warning",
                    message=self.TEMPLATES["budget_exhausted"].format(service=service.name),
                    severity="critical",
                    data={"budget_remaining": 0}
                ))
                health_score -= 50
            
            # Check burn rate
            elif burn.burn_rate >= 3.0:
                time_str = self._format_time(forecast.time_to_exhaustion_hours)
                insights.append(AIInsight(
                    service_name=service.name,
                    insight_type="warning",
                    message=self.TEMPLATES["burn_critical"].format(
                        service=service.name,
                        burn_rate=f"{burn.burn_rate:.1f}",
                        time_to_exhaustion=time_str
                    ),
                    severity="critical",
                    data={
                        "burn_rate": burn.burn_rate,
                        "time_to_exhaustion": forecast.time_to_exhaustion_hours
                    }
                ))
                health_score -= 40
            
            elif burn.burn_rate >= 1.5:
                insights.append(AIInsight(
                    service_name=service.name,
                    insight_type="warning",
                    message=self.TEMPLATES["burn_elevated"].format(
                        service=service.name,
                        burn_rate=f"{burn.burn_rate:.1f}",
                        budget_remaining=f"{burn.error_budget_remaining:.1f}"
                    ),
                    severity="warning",
                    data={"burn_rate": burn.burn_rate}
                ))
                health_score -= 20
            
            # Check budget remaining
            if burn.error_budget_remaining < 15 and burn.error_budget_remaining > 0:
                insights.append(AIInsight(
                    service_name=service.name,
                    insight_type="warning",
                    message=self.TEMPLATES["budget_critical"].format(
                        service=service.name,
                        budget_remaining=f"{burn.error_budget_remaining:.1f}"
                    ),
                    severity="warning",
                    data={"budget_remaining": burn.error_budget_remaining}
                ))
                health_score -= 15
            
            # Check trend
            if forecast.burn_rate_trend == "increasing":
                insights.append(AIInsight(
                    service_name=service.name,
                    insight_type="status",
                    message=self.TEMPLATES["trend_worsening"].format(
                        service=service.name,
                        trend_change=f"{abs(forecast.trend_slope * 100):.0f}"
                    ),
                    severity="info" if burn.risk_level == RiskLevel.SAFE else "warning",
                    data={"trend_slope": forecast.trend_slope}
                ))
                health_score -= 5
            
            # Add healthy status if no issues
            if not insights:
                insights.append(AIInsight(
                    service_name=service.name,
                    insight_type="status",
                    message=self.TEMPLATES["burn_healthy"].format(
                        service=service.name,
                        burn_rate=f"{burn.burn_rate:.2f}"
                    ),
                    severity="info",
                    data={"burn_rate": burn.burn_rate}
                ))
        
        except Exception as e:
            insights.append(AIInsight(
                service_name=service.name,
                insight_type="status",
                message=f"Unable to analyze {service.name}: insufficient data",
                severity="info",
                data={"error": str(e)}
            ))
        
        return insights, max(health_score, 0)
    
    def _format_time(self, hours: Optional[float]) -> str:
        """Format hours into human-readable time."""
        if hours is None:
            return "unknown"
        if hours < 1:
            return f"{int(hours * 60)} minutes"
        if hours < 24:
            return f"{hours:.1f} hours"
        return f"{hours / 24:.1f} days"
    
    def _generate_executive_summary(
        self,
        total_services: int,
        at_risk: List[str],
        score: float,
        critical_count: int,
        nearest_exhaustion: Optional[Dict]
    ) -> str:
        """Generate executive summary paragraph."""
        
        parts = []
        
        # Overall status
        if score >= 95:
            parts.append(f"Platform reliability is excellent with {total_services} services operating normally.")
        elif score >= 85:
            parts.append(f"Platform reliability is good. {total_services - len(at_risk)} of {total_services} services are healthy.")
        elif score >= 70:
            parts.append(f"Platform reliability requires attention. {len(at_risk)} services showing elevated error rates.")
        else:
            parts.append(f"Platform reliability is degraded. {len(at_risk)} services at risk, {critical_count} critical issues detected.")
        
        # At-risk services
        if at_risk:
            if len(at_risk) <= 3:
                parts.append(f"Services requiring attention: {', '.join(at_risk)}.")
            else:
                parts.append(f"{len(at_risk)} services require attention including {', '.join(at_risk[:3])}.")
        
        # Nearest exhaustion warning
        if nearest_exhaustion:
            time_str = self._format_time(nearest_exhaustion.get("time_to_exhaustion_hours"))
            parts.append(
                f"Nearest budget exhaustion: {nearest_exhaustion['service_name']} in ~{time_str}."
            )
        
        return " ".join(parts)
    
    def _generate_action_items(
        self,
        insights: List[AIInsight],
        at_risk: List[str]
    ) -> List[str]:
        """Generate prioritized action items."""
        
        actions = []
        
        # Critical items first
        critical_services = [i.service_name for i in insights if i.severity == "critical"]
        if critical_services:
            actions.append(f"URGENT: Investigate critical issues in {', '.join(set(critical_services))}")
        
        # Budget warnings
        budget_warnings = [i for i in insights if "budget" in i.message.lower() and "exhaust" in i.message.lower()]
        if budget_warnings:
            actions.append("Review error budget status and consider deployment freeze for affected services")
        
        # Trend issues
        trending_up = [i for i in insights if i.insight_type == "status" and "degrading" in i.message.lower()]
        if trending_up:
            actions.append("Monitor trending services and prepare incident response")
        
        # General recommendations
        if at_risk:
            actions.append("Review recent deployments to at-risk services for potential rollback")
        
        if not actions:
            actions.append("Continue monitoring - all systems operating normally")
        
        return actions
    
    def generate_service_narrative(self, service_id: int) -> str:
        """Generate detailed narrative for a specific service."""
        
        service = self.db.query(Service).filter(Service.id == service_id).first()
        if not service:
            return "Service not found."
        
        try:
            burn = self.burn_engine.compute_burn_rate(service_id, 60)
            forecast = self.forecast_module.forecast_exhaustion(service_id)
            
            parts = [f"## {service.name} Reliability Report\n"]
            
            # Current status
            parts.append(f"**Risk Level:** {burn.risk_level.value.upper()}")
            parts.append(f"**Burn Rate:** {burn.burn_rate:.2f}× (1.0 = normal)")
            parts.append(f"**Error Budget:** {burn.error_budget_remaining:.1f}% remaining")
            
            # Forecast
            if forecast.time_to_exhaustion_hours:
                parts.append(f"\n**Forecast:** Budget exhaustion in ~{self._format_time(forecast.time_to_exhaustion_hours)}")
            
            # Trend
            parts.append(f"**Trend:** {forecast.burn_rate_trend.capitalize()}")
            
            # Summary
            parts.append(f"\n{forecast.forecast_message}")
            
            return "\n".join(parts)
        
        except Exception as e:
            return f"Unable to generate report for {service.name}: {str(e)}"
