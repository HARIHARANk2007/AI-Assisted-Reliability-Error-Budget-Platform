"""
Pydantic Schemas for API Request/Response Validation
"""

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


# ============ Enums ============

class RiskLevel(str, Enum):
    SAFE = "safe"
    OBSERVE = "observe"
    DANGER = "danger"
    FREEZE = "freeze"


class AlertSeverity(str, Enum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"
    EMERGENCY = "emergency"


class AlertChannel(str, Enum):
    EMAIL = "email"
    SLACK = "slack"
    UI = "ui"
    PAGERDUTY = "pagerduty"


# ============ Service Schemas ============

class ServiceBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    team: Optional[str] = None
    tier: int = Field(default=2, ge=1, le=3)


class ServiceCreate(ServiceBase):
    pass


class ServiceUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    team: Optional[str] = None
    tier: Optional[int] = None
    is_active: Optional[bool] = None


class ServiceResponse(ServiceBase):
    id: int
    created_at: datetime
    updated_at: datetime
    is_active: bool
    
    class Config:
        from_attributes = True


class ServiceListResponse(BaseModel):
    services: List[ServiceResponse]
    total: int


# ============ Metrics Schemas ============

class MetricSnapshot(BaseModel):
    """Raw metric data point"""
    service: str
    timestamp: datetime
    total_requests: int = Field(ge=0)
    error_count: int = Field(ge=0)
    latency_p50: Optional[float] = None
    latency_p95: Optional[float] = None
    latency_p99: Optional[float] = None


class MetricResponse(BaseModel):
    id: int
    service_id: int
    timestamp: datetime
    total_requests: int
    error_count: int
    latency_p50: Optional[float]
    latency_p95: Optional[float]
    latency_p99: Optional[float]
    success_rate: Optional[float]
    
    class Config:
        from_attributes = True


class MetricsIngestRequest(BaseModel):
    """Batch metrics ingestion request"""
    metrics: List[MetricSnapshot]


class MetricsIngestResponse(BaseModel):
    processed: int
    errors: int
    message: str


# ============ SLO Schemas ============

class SLOTargetBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    target_value: float = Field(..., ge=0, le=100)
    window_days: int = Field(default=30, ge=1, le=365)
    error_budget_policy: float = Field(default=100.0, ge=0, le=100)
    burn_rate_threshold: float = Field(default=1.0, ge=0)
    critical_burn_rate: float = Field(default=2.0, ge=0)


class SLOTargetCreate(SLOTargetBase):
    service_id: int


class SLOTargetUpdate(BaseModel):
    target_value: Optional[float] = None
    window_days: Optional[int] = None
    error_budget_policy: Optional[float] = None
    burn_rate_threshold: Optional[float] = None
    critical_burn_rate: Optional[float] = None
    is_active: Optional[bool] = None


class SLOTargetResponse(SLOTargetBase):
    id: int
    service_id: int
    created_at: datetime
    updated_at: datetime
    is_active: bool
    
    class Config:
        from_attributes = True


class SLOComputation(BaseModel):
    """Computed SLO metrics for a service"""
    service_id: int
    service_name: str
    slo_name: str
    target_value: float
    current_value: float
    is_meeting_slo: bool
    
    # Error budget
    total_budget: float  # Total allowed errors
    consumed_budget: float  # Errors that occurred
    consumed_percentage: float
    remaining_percentage: float
    
    # Rolling windows
    availability_5m: Optional[float] = None
    availability_1h: Optional[float] = None
    availability_24h: Optional[float] = None
    
    # Timestamps
    window_start: datetime
    window_end: datetime
    computed_at: datetime


class SLOResponse(BaseModel):
    """Full SLO status for a service"""
    service: ServiceResponse
    targets: List[SLOTargetResponse]
    computations: List[SLOComputation]
    overall_compliance: float
    risk_level: RiskLevel


# ============ Burn Rate Schemas ============

class BurnRateComputation(BaseModel):
    """Burn rate calculation result"""
    service_id: int
    service_name: str
    timestamp: datetime
    window_minutes: int
    
    # Rates
    current_error_rate: float
    allowed_error_rate: float
    burn_rate: float
    
    # Budget status
    error_budget_consumed: float
    error_budget_remaining: float
    
    # Risk
    risk_level: RiskLevel
    risk_color: str
    risk_action: str


class BurnHistoryResponse(BaseModel):
    service_id: int
    service_name: str
    history: List[BurnRateComputation]
    current_burn_rate: float
    average_burn_rate_24h: float
    peak_burn_rate_24h: float


# ============ Forecast Schemas ============

class ForecastResponse(BaseModel):
    """Budget exhaustion forecast"""
    service_id: int
    service_name: str
    computed_at: datetime
    
    # Current state
    current_burn_rate: float
    error_budget_remaining: float
    
    # Forecast
    time_to_exhaustion_hours: Optional[float]
    projected_exhaustion_time: Optional[datetime]
    confidence_level: str  # "high", "medium", "low"
    
    # Trend
    burn_rate_trend: str  # "increasing", "stable", "decreasing"
    trend_slope: float
    
    # Message
    forecast_message: str


# ============ Release Gate Schemas ============

class ReleaseCheckRequest(BaseModel):
    """Release gate check request"""
    service_name: str
    deployment_id: str
    version: Optional[str] = None
    requested_by: Optional[str] = None
    override: bool = False  # Force deployment (requires auth)
    override_reason: Optional[str] = None


class ReleaseCheckResponse(BaseModel):
    """Release gate decision"""
    allowed: bool
    reason: str
    service_name: str
    deployment_id: str
    
    # Context
    current_risk_level: RiskLevel
    current_burn_rate: float
    error_budget_remaining: float
    time_to_exhaustion_hours: Optional[float]
    
    # Recommendations
    recommendations: List[str]
    
    # Audit
    checked_at: datetime
    checked_by: str = "system"


# ============ Alert Schemas ============

class AlertCreate(BaseModel):
    service_id: int
    severity: AlertSeverity
    channel: AlertChannel
    title: str
    message: str
    metadata: Optional[Dict[str, Any]] = None


class AlertResponse(BaseModel):
    id: int
    service_id: int
    service_name: Optional[str] = None
    timestamp: datetime
    severity: AlertSeverity
    channel: AlertChannel
    title: str
    message: str
    metadata: Optional[Dict[str, Any]]
    sent: bool
    acknowledged: bool
    acknowledged_by: Optional[str]
    
    class Config:
        from_attributes = True


class AlertFeedResponse(BaseModel):
    alerts: List[AlertResponse]
    total: int
    unacknowledged: int


# ============ AI Summary Schemas ============

class AIInsight(BaseModel):
    """Individual AI-generated insight"""
    service_name: str
    insight_type: str  # "warning", "recommendation", "status"
    message: str
    severity: str
    data: Optional[Dict[str, Any]] = None


class AISummaryResponse(BaseModel):
    """AI-generated reliability summary"""
    generated_at: datetime
    overall_health: str  # "healthy", "degraded", "critical"
    overall_score: float  # 0-100
    
    # Executive summary
    executive_summary: str
    
    # Per-service insights
    insights: List[AIInsight]
    
    # Action items
    action_items: List[str]
    
    # Services at risk
    services_at_risk: List[str]
    
    # Forecasts
    nearest_budget_exhaustion: Optional[Dict[str, Any]]


# ============ Dashboard Schemas ============

class DashboardOverview(BaseModel):
    """Executive dashboard data"""
    total_services: int
    services_meeting_slo: int
    services_at_risk: int
    global_compliance_score: float
    
    # Risk distribution
    risk_distribution: Dict[str, int]
    
    # Budget status
    average_budget_remaining: float
    lowest_budget_service: Optional[str]
    lowest_budget_percentage: Optional[float]
    
    # Forecasts
    nearest_exhaustion: Optional[Dict[str, Any]]
    
    # Recent alerts
    active_alerts: int
    critical_alerts: int
    
    # Trends
    compliance_trend_24h: str  # "improving", "stable", "degrading"


class HeatmapData(BaseModel):
    """Service vs Time risk heatmap"""
    services: List[str]
    timestamps: List[datetime]
    risk_matrix: List[List[str]]  # risk levels


# ============ Config Schemas ============

class ConfigUpdate(BaseModel):
    """Configuration update request"""
    key: str
    value: Any
    description: Optional[str] = None


class ConfigResponse(BaseModel):
    key: str
    value: Any
    value_type: str
    description: Optional[str]
    updated_at: datetime
