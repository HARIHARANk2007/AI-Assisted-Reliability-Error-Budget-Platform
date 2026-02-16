"""
Alert Manager Service
Manages alert generation, storage, and simulated notifications
"""

from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import and_, func, desc

from app.models.database import (
    Service, Alert, 
    AlertSeverity as DBAlertSeverity,
    AlertChannel as DBAlertChannel
)
from app.schemas.schemas import (
    AlertCreate, AlertResponse, AlertFeedResponse,
    AlertSeverity, AlertChannel, RiskLevel
)
from app.services.burn_rate_service import BurnRateEngine
from app.core.config import get_settings

settings = get_settings()


class AlertManager:
    """
    Manages reliability alerts and notifications.
    
    Features:
    - Alert generation based on thresholds
    - Cooldown to prevent alert fatigue
    - Simulated email/Slack/UI notifications
    - Alert acknowledgment tracking
    """
    
    # Alert templates
    ALERT_TEMPLATES = {
        "budget_exhausted": {
            "title": "[CRITICAL] Error Budget Exhausted: {service}",
            "message": "Error budget for {service} has been completely exhausted. Deployment freeze recommended.",
            "severity": AlertSeverity.EMERGENCY
        },
        "budget_critical": {
            "title": "[WARNING] Error Budget Critical: {service}",
            "message": "Error budget for {service} is critically low ({remaining}% remaining). Budget will be exhausted in ~{time}.",
            "severity": AlertSeverity.CRITICAL
        },
        "burn_rate_high": {
            "title": "[ALERT] High Burn Rate: {service}",
            "message": "{service} is burning error budget at {rate}× the allowed rate. Current risk level: {risk}.",
            "severity": AlertSeverity.WARNING
        },
        "risk_escalation": {
            "title": "[NOTICE] Risk Level Changed: {service}",
            "message": "{service} risk level has escalated from {from_risk} to {to_risk}.",
            "severity": AlertSeverity.WARNING
        },
        "deployment_blocked": {
            "title": "[INFO] Deployment Blocked: {service}",
            "message": "Deployment {deployment_id} was blocked due to {reason}.",
            "severity": AlertSeverity.INFO
        },
        "recovery": {
            "title": "[RESOLVED] Service Recovered: {service}",
            "message": "{service} has recovered. Risk level is now {risk}.",
            "severity": AlertSeverity.INFO
        }
    }
    
    def __init__(self, db: Session):
        self.db = db
        self.burn_engine = BurnRateEngine(db)
    
    def create_alert(
        self,
        service_id: int,
        alert_type: str,
        channel: AlertChannel,
        template_vars: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None
    ) -> Optional[Alert]:
        """
        Create an alert from a template.
        
        Args:
            service_id: Service this alert relates to
            alert_type: Template key
            channel: Notification channel
            template_vars: Variables for template interpolation
            metadata: Additional context data
            
        Returns:
            Created Alert or None if in cooldown
        """
        template = self.ALERT_TEMPLATES.get(alert_type)
        if not template:
            raise ValueError(f"Unknown alert type: {alert_type}")
        
        # Check cooldown
        if self._is_in_cooldown(service_id, alert_type):
            return None
        
        # Format message
        title = template["title"].format(**template_vars)
        message = template["message"].format(**template_vars)
        severity = template["severity"]
        
        # Map to DB enums
        db_severity = DBAlertSeverity(severity.value)
        db_channel = DBAlertChannel(channel.value)
        
        alert = Alert(
            service_id=service_id,
            severity=db_severity,
            channel=db_channel,
            title=title,
            message=message,
            metadata=metadata or {}
        )
        
        self.db.add(alert)
        self.db.commit()
        self.db.refresh(alert)
        
        # Simulate sending notification
        self._send_notification(alert)
        
        return alert
    
    def _is_in_cooldown(self, service_id: int, alert_type: str) -> bool:
        """Check if similar alert was sent recently."""
        cooldown_start = datetime.utcnow() - timedelta(minutes=settings.ALERT_COOLDOWN_MINUTES)
        
        recent = self.db.query(Alert).filter(
            and_(
                Alert.service_id == service_id,
                Alert.timestamp >= cooldown_start,
                Alert.metadata.contains({"alert_type": alert_type})
            )
        ).first()
        
        return recent is not None
    
    def _send_notification(self, alert: Alert):
        """Simulate sending notification (would integrate with real services)."""
        now = datetime.utcnow()
        
        # Mark as sent
        alert.sent = True
        alert.sent_at = now
        self.db.commit()
        
        # Log simulation
        channel = alert.channel.value
        print(f"[ALERT SIMULATION] {channel.upper()}: {alert.title}")
        print(f"  Message: {alert.message}")
        print(f"  Severity: {alert.severity.value}")
        
        # In production, this would:
        # - EMAIL: Send via SMTP
        # - SLACK: Post to webhook
        # - PAGERDUTY: Create incident
        # - UI: Push via WebSocket
    
    def evaluate_and_alert(self, service_id: int) -> List[Alert]:
        """
        Evaluate service state and generate appropriate alerts.
        
        Returns:
            List of generated alerts
        """
        service = self.db.query(Service).filter(Service.id == service_id).first()
        if not service:
            return []
        
        alerts = []
        
        try:
            burn = self.burn_engine.compute_burn_rate(service_id, 60)
            
            # Budget exhausted
            if burn.error_budget_remaining <= 0:
                alert = self.create_alert(
                    service_id=service_id,
                    alert_type="budget_exhausted",
                    channel=AlertChannel.SLACK,
                    template_vars={"service": service.name},
                    metadata={"alert_type": "budget_exhausted"}
                )
                if alert:
                    alerts.append(alert)
            
            # Budget critical (< 15%)
            elif burn.error_budget_remaining < 15:
                from app.services.forecast_service import ForecastModule
                forecast = ForecastModule(self.db).forecast_exhaustion(service_id)
                
                time_str = self._format_time(forecast.time_to_exhaustion_hours)
                alert = self.create_alert(
                    service_id=service_id,
                    alert_type="budget_critical",
                    channel=AlertChannel.SLACK,
                    template_vars={
                        "service": service.name,
                        "remaining": f"{burn.error_budget_remaining:.1f}",
                        "time": time_str
                    },
                    metadata={"alert_type": "budget_critical"}
                )
                if alert:
                    alerts.append(alert)
            
            # High burn rate
            if burn.burn_rate >= 2.0:
                alert = self.create_alert(
                    service_id=service_id,
                    alert_type="burn_rate_high",
                    channel=AlertChannel.UI,
                    template_vars={
                        "service": service.name,
                        "rate": f"{burn.burn_rate:.1f}",
                        "risk": burn.risk_level.value.upper()
                    },
                    metadata={"alert_type": "burn_rate_high"}
                )
                if alert:
                    alerts.append(alert)
        
        except Exception as e:
            print(f"Error evaluating alerts for service {service_id}: {e}")
        
        return alerts
    
    def _format_time(self, hours: Optional[float]) -> str:
        """Format hours into readable string."""
        if hours is None:
            return "unknown"
        if hours < 1:
            return f"{int(hours * 60)} minutes"
        if hours < 24:
            return f"{hours:.1f} hours"
        return f"{hours / 24:.1f} days"
    
    def get_alerts(
        self,
        service_id: Optional[int] = None,
        severity: Optional[AlertSeverity] = None,
        acknowledged: Optional[bool] = None,
        hours: int = 24,
        limit: int = 100
    ) -> List[AlertResponse]:
        """
        Retrieve alerts with optional filters.
        """
        cutoff = datetime.utcnow() - timedelta(hours=hours)
        
        query = self.db.query(Alert, Service.name).join(
            Service, Alert.service_id == Service.id
        ).filter(Alert.timestamp >= cutoff)
        
        if service_id:
            query = query.filter(Alert.service_id == service_id)
        if severity:
            query = query.filter(Alert.severity == DBAlertSeverity(severity.value))
        if acknowledged is not None:
            query = query.filter(Alert.acknowledged == acknowledged)
        
        results = query.order_by(desc(Alert.timestamp)).limit(limit).all()
        
        alerts = []
        for alert, service_name in results:
            alerts.append(AlertResponse(
                id=alert.id,
                service_id=alert.service_id,
                service_name=service_name,
                timestamp=alert.timestamp,
                severity=AlertSeverity(alert.severity.value),
                channel=AlertChannel(alert.channel.value),
                title=alert.title,
                message=alert.message,
                metadata=alert.metadata,
                sent=alert.sent,
                acknowledged=alert.acknowledged,
                acknowledged_by=alert.acknowledged_by
            ))
        
        return alerts
    
    def get_alert_feed(
        self,
        hours: int = 24,
        limit: int = 50
    ) -> AlertFeedResponse:
        """Get alert feed for UI display."""
        
        alerts = self.get_alerts(hours=hours, limit=limit)
        
        unack = self.db.query(func.count(Alert.id)).filter(
            and_(
                Alert.timestamp >= datetime.utcnow() - timedelta(hours=hours),
                Alert.acknowledged == False
            )
        ).scalar()
        
        total = self.db.query(func.count(Alert.id)).filter(
            Alert.timestamp >= datetime.utcnow() - timedelta(hours=hours)
        ).scalar()
        
        return AlertFeedResponse(
            alerts=alerts,
            total=total or 0,
            unacknowledged=unack or 0
        )
    
    def acknowledge_alert(
        self,
        alert_id: int,
        acknowledged_by: str
    ) -> Optional[Alert]:
        """Mark an alert as acknowledged."""
        
        alert = self.db.query(Alert).filter(Alert.id == alert_id).first()
        if not alert:
            return None
        
        alert.acknowledged = True
        alert.acknowledged_by = acknowledged_by
        alert.acknowledged_at = datetime.utcnow()
        self.db.commit()
        
        return alert
    
    def bulk_acknowledge(
        self,
        alert_ids: List[int],
        acknowledged_by: str
    ) -> int:
        """Acknowledge multiple alerts at once."""
        
        updated = self.db.query(Alert).filter(
            Alert.id.in_(alert_ids)
        ).update(
            {
                Alert.acknowledged: True,
                Alert.acknowledged_by: acknowledged_by,
                Alert.acknowledged_at: datetime.utcnow()
            },
            synchronize_session=False
        )
        self.db.commit()
        
        return updated
    
    def get_alert_statistics(self, days: int = 7) -> Dict[str, Any]:
        """Get alert statistics over a period."""
        
        cutoff = datetime.utcnow() - timedelta(days=days)
        
        # Total by severity
        severity_counts = self.db.query(
            Alert.severity,
            func.count(Alert.id)
        ).filter(
            Alert.timestamp >= cutoff
        ).group_by(Alert.severity).all()
        
        # Unacknowledged
        unack = self.db.query(func.count(Alert.id)).filter(
            and_(
                Alert.timestamp >= cutoff,
                Alert.acknowledged == False
            )
        ).scalar()
        
        return {
            "period_days": days,
            "by_severity": {s[0].value: s[1] for s in severity_counts},
            "total": sum(s[1] for s in severity_counts),
            "unacknowledged": unack or 0
        }
