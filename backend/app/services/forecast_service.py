"""
Forecast Module
Predicts error budget exhaustion using linear projection and trend analysis
"""

from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import and_, func
import numpy as np

from app.models.database import Service, BurnHistory, SLOTarget
from app.schemas.schemas import ForecastResponse, RiskLevel
from app.services.burn_rate_service import BurnRateEngine


class ForecastModule:
    """
    Forecasting engine for error budget exhaustion prediction.
    
    Core Algorithm:
    Uses linear regression on historical burn rates to project when
    the error budget will reach zero.
    
    Time to Exhaustion Formula:
    If we have R% budget remaining and burning at rate B (normalized to 1.0/day):
    hours_to_exhaustion = (R / 100) * (window_hours) / B
    
    For a 30-day window burning at 2x rate:
    hours = (50 / 100) * (30 * 24) / 2.0 = 180 hours = 7.5 days
    """
    
    def __init__(self, db: Session):
        self.db = db
        self.burn_engine = BurnRateEngine(db)
    
    def forecast_exhaustion(
        self,
        service_id: int,
        use_historical_trend: bool = True
    ) -> ForecastResponse:
        """
        Predict when error budget will be exhausted.
        
        Args:
            service_id: Service to forecast for
            use_historical_trend: Whether to use trending or current burn rate
            
        Returns:
            ForecastResponse with predictions
        """
        service = self.db.query(Service).filter(Service.id == service_id).first()
        if not service:
            raise ValueError(f"Service {service_id} not found")
        
        # Get current burn rate
        current_burn = self.burn_engine.compute_burn_rate(service_id, 60)
        
        # Get SLO window for calculations
        slo_target = self.db.query(SLOTarget).filter(
            and_(
                SLOTarget.service_id == service_id,
                SLOTarget.name == "availability",
                SLOTarget.is_active == True
            )
        ).first()
        
        window_days = slo_target.window_days if slo_target else 30
        window_hours = window_days * 24
        
        # Calculate trend if using historical data
        burn_rate_for_forecast = current_burn.burn_rate
        trend_direction = "stable"
        trend_slope = 0.0
        confidence = "medium"
        
        if use_historical_trend:
            trend_data = self._calculate_trend(service_id)
            if trend_data:
                trend_slope = trend_data["slope"]
                trend_direction = trend_data["direction"]
                confidence = trend_data["confidence"]
                
                # Adjust burn rate based on trend
                # If trending up, project forward; if down, use current
                if trend_slope > 0:
                    # Project burn rate 1 hour forward
                    burn_rate_for_forecast = current_burn.burn_rate + trend_slope
        
        # Calculate time to exhaustion
        remaining_budget = current_burn.error_budget_remaining
        time_to_exhaustion = None
        exhaustion_time = None
        
        if burn_rate_for_forecast > 0 and remaining_budget > 0:
            # Hours until budget hits 0, given current consumption rate
            # If burning at rate 2.0 with 50% remaining, and window is 30 days:
            # At 2x rate, we consume 30 days of budget in 15 days
            # With 50% left, that's 7.5 days = 180 hours
            
            # Normalize: if burn_rate = 1.0, budget lasts exactly window_hours
            # if burn_rate = 2.0, budget lasts window_hours / 2
            time_to_exhaustion = (remaining_budget / 100) * window_hours / burn_rate_for_forecast
            time_to_exhaustion = round(time_to_exhaustion, 2)
            
            if time_to_exhaustion > 0:
                exhaustion_time = datetime.utcnow() + timedelta(hours=time_to_exhaustion)
        elif remaining_budget <= 0:
            time_to_exhaustion = 0.0
            exhaustion_time = datetime.utcnow()
        
        # Generate forecast message
        message = self._generate_forecast_message(
            service.name,
            current_burn.burn_rate,
            remaining_budget,
            time_to_exhaustion,
            trend_direction
        )
        
        return ForecastResponse(
            service_id=service_id,
            service_name=service.name,
            computed_at=datetime.utcnow(),
            current_burn_rate=current_burn.burn_rate,
            error_budget_remaining=remaining_budget,
            time_to_exhaustion_hours=time_to_exhaustion,
            projected_exhaustion_time=exhaustion_time,
            confidence_level=confidence,
            burn_rate_trend=trend_direction,
            trend_slope=round(trend_slope, 4),
            forecast_message=message
        )
    
    def _calculate_trend(self, service_id: int) -> Optional[Dict[str, Any]]:
        """
        Calculate burn rate trend using linear regression.
        
        Returns:
            Dict with slope, direction, and confidence
        """
        # Get last 6 hours of burn history (1h window)
        cutoff = datetime.utcnow() - timedelta(hours=6)
        
        history = self.db.query(BurnHistory).filter(
            and_(
                BurnHistory.service_id == service_id,
                BurnHistory.window_minutes == 60,
                BurnHistory.timestamp >= cutoff
            )
        ).order_by(BurnHistory.timestamp).all()
        
        if len(history) < 3:
            return None
        
        # Extract time series
        timestamps = []
        burn_rates = []
        base_time = history[0].timestamp
        
        for h in history:
            # Convert to hours from start
            hours = (h.timestamp - base_time).total_seconds() / 3600
            timestamps.append(hours)
            burn_rates.append(h.burn_rate)
        
        # Simple linear regression using numpy
        x = np.array(timestamps)
        y = np.array(burn_rates)
        
        # Calculate slope and intercept
        n = len(x)
        slope = (n * np.sum(x * y) - np.sum(x) * np.sum(y)) / (n * np.sum(x**2) - np.sum(x)**2)
        
        # Calculate R-squared for confidence
        y_mean = np.mean(y)
        y_pred = slope * x + (np.mean(y) - slope * np.mean(x))
        ss_res = np.sum((y - y_pred)**2)
        ss_tot = np.sum((y - y_mean)**2)
        r_squared = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0
        
        # Determine direction
        if slope > 0.1:
            direction = "increasing"
        elif slope < -0.1:
            direction = "decreasing"
        else:
            direction = "stable"
        
        # Confidence based on R-squared and data points
        if r_squared > 0.7 and n >= 5:
            confidence = "high"
        elif r_squared > 0.4 and n >= 3:
            confidence = "medium"
        else:
            confidence = "low"
        
        return {
            "slope": slope,  # Change per hour
            "direction": direction,
            "confidence": confidence,
            "r_squared": r_squared,
            "data_points": n
        }
    
    def _generate_forecast_message(
        self,
        service_name: str,
        burn_rate: float,
        remaining: float,
        hours_to_exhaustion: Optional[float],
        trend: str
    ) -> str:
        """Generate human-readable forecast message."""
        
        if remaining <= 0:
            return f"{service_name} has exhausted its error budget. Immediate action required."
        
        if hours_to_exhaustion is None:
            return f"{service_name} error budget status is healthy with {remaining:.1f}% remaining."
        
        # Format time nicely
        if hours_to_exhaustion < 1:
            time_str = f"{int(hours_to_exhaustion * 60)} minutes"
        elif hours_to_exhaustion < 24:
            time_str = f"{hours_to_exhaustion:.1f} hours"
        elif hours_to_exhaustion < 72:
            time_str = f"{hours_to_exhaustion / 24:.1f} days"
        else:
            time_str = f"{int(hours_to_exhaustion / 24)} days"
        
        # Build message based on severity
        if burn_rate >= 3.0:
            severity = "critically fast"
            urgency = "Immediate intervention required."
        elif burn_rate >= 2.0:
            severity = f"{burn_rate:.1f}× faster than allowed"
            urgency = "Action recommended within the hour."
        elif burn_rate >= 1.5:
            severity = f"{burn_rate:.1f}× normal rate"
            urgency = "Monitor closely."
        elif burn_rate >= 1.0:
            severity = "at the allowed rate"
            urgency = "Consider investigation."
        else:
            severity = "below normal"
            urgency = "Budget is healthy."
        
        trend_msg = ""
        if trend == "increasing":
            trend_msg = " Burn rate is trending upward."
        elif trend == "decreasing":
            trend_msg = " Burn rate is trending downward."
        
        return (
            f"{service_name} is burning error budget {severity}. "
            f"Budget exhaustion projected in ~{time_str}.{trend_msg} {urgency}"
        )
    
    def get_all_forecasts(self) -> List[ForecastResponse]:
        """Get forecasts for all active services."""
        
        services = self.db.query(Service).filter(Service.is_active == True).all()
        
        forecasts = []
        for service in services:
            try:
                forecast = self.forecast_exhaustion(service.id)
                forecasts.append(forecast)
            except Exception as e:
                print(f"Error forecasting for {service.name}: {e}")
        
        return forecasts
    
    def get_nearest_exhaustion(self) -> Optional[Dict[str, Any]]:
        """Find the service with the nearest budget exhaustion."""
        
        forecasts = self.get_all_forecasts()
        
        # Filter to services with actual exhaustion times
        at_risk = [
            f for f in forecasts 
            if f.time_to_exhaustion_hours is not None 
            and f.time_to_exhaustion_hours < 720  # Less than 30 days
        ]
        
        if not at_risk:
            return None
        
        # Sort by time to exhaustion
        nearest = min(at_risk, key=lambda f: f.time_to_exhaustion_hours)
        
        return {
            "service_name": nearest.service_name,
            "time_to_exhaustion_hours": nearest.time_to_exhaustion_hours,
            "projected_exhaustion_time": nearest.projected_exhaustion_time,
            "current_burn_rate": nearest.current_burn_rate,
            "budget_remaining": nearest.error_budget_remaining
        }
