"""
Database Models for AI-Assisted Reliability & Error Budget Platform
PostgreSQL Schema Definitions using SQLAlchemy ORM
"""

from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, Float, DateTime, Boolean, 
    ForeignKey, Text, Enum, JSON, Index
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
import enum

Base = declarative_base()


class RiskLevel(enum.Enum):
    """Risk classification levels for SLO compliance"""
    SAFE = "safe"
    OBSERVE = "observe"
    DANGER = "danger"
    FREEZE = "freeze"


class AlertSeverity(enum.Enum):
    """Alert severity levels"""
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"
    EMERGENCY = "emergency"


class AlertChannel(enum.Enum):
    """Alert notification channels"""
    EMAIL = "email"
    SLACK = "slack"
    UI = "ui"
    PAGERDUTY = "pagerduty"


class Service(Base):
    """
    Services Table
    Represents monitored services in the platform
    """
    __tablename__ = "services"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), unique=True, nullable=False, index=True)
    description = Column(Text, nullable=True)
    team = Column(String(255), nullable=True)
    tier = Column(Integer, default=2)  # 1=Critical, 2=Standard, 3=Low
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_active = Column(Boolean, default=True)
    
    # Relationships
    metrics = relationship("Metric", back_populates="service", cascade="all, delete-orphan")
    slo_targets = relationship("SLOTarget", back_populates="service", cascade="all, delete-orphan")
    burn_history = relationship("BurnHistory", back_populates="service", cascade="all, delete-orphan")
    deployments = relationship("Deployment", back_populates="service", cascade="all, delete-orphan")
    alerts = relationship("Alert", back_populates="service", cascade="all, delete-orphan")


class Metric(Base):
    """
    Metrics Table
    Stores telemetry snapshots ingested from Prometheus or simulator
    """
    __tablename__ = "metrics"
    
    id = Column(Integer, primary_key=True, index=True)
    service_id = Column(Integer, ForeignKey("services.id"), nullable=False, index=True)
    timestamp = Column(DateTime, nullable=False, index=True)
    total_requests = Column(Integer, nullable=False, default=0)
    error_count = Column(Integer, nullable=False, default=0)
    latency_p50 = Column(Float, nullable=True)  # 50th percentile latency (ms)
    latency_p95 = Column(Float, nullable=True)  # 95th percentile latency (ms)
    latency_p99 = Column(Float, nullable=True)  # 99th percentile latency (ms)
    success_rate = Column(Float, nullable=True)  # Computed: (total - errors) / total
    
    # Relationships
    service = relationship("Service", back_populates="metrics")
    
    # Indexes for efficient querying
    __table_args__ = (
        Index("idx_metrics_service_timestamp", "service_id", "timestamp"),
        Index("idx_metrics_timestamp", "timestamp"),
    )


class SLOTarget(Base):
    """
    SLO Targets Table
    Defines Service Level Objectives for each service
    """
    __tablename__ = "slo_targets"
    
    id = Column(Integer, primary_key=True, index=True)
    service_id = Column(Integer, ForeignKey("services.id"), nullable=False, index=True)
    name = Column(String(255), nullable=False)  # e.g., "availability", "latency_p99"
    target_value = Column(Float, nullable=False)  # e.g., 99.9 for 99.9% availability
    window_days = Column(Integer, default=30)  # Rolling window in days
    error_budget_policy = Column(Float, default=100.0)  # Budget allocated (%)
    burn_rate_threshold = Column(Float, default=1.0)  # Normal burn rate
    critical_burn_rate = Column(Float, default=2.0)  # Critical threshold
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_active = Column(Boolean, default=True)
    
    # Relationships
    service = relationship("Service", back_populates="slo_targets")
    
    __table_args__ = (
        Index("idx_slo_service_name", "service_id", "name"),
    )


class BurnHistory(Base):
    """
    Burn History Table
    Tracks error budget burn rate over time
    """
    __tablename__ = "burn_history"
    
    id = Column(Integer, primary_key=True, index=True)
    service_id = Column(Integer, ForeignKey("services.id"), nullable=False, index=True)
    timestamp = Column(DateTime, nullable=False, index=True)
    window_minutes = Column(Integer, nullable=False)  # 5, 60, 1440 (24h)
    burn_rate = Column(Float, nullable=False)  # Current burn rate
    error_budget_consumed = Column(Float, nullable=False)  # Percentage consumed
    error_budget_remaining = Column(Float, nullable=False)  # Percentage remaining
    time_to_exhaustion_hours = Column(Float, nullable=True)  # Forecast
    risk_level = Column(Enum(RiskLevel), nullable=False, default=RiskLevel.SAFE)
    
    # Relationships
    service = relationship("Service", back_populates="burn_history")
    
    __table_args__ = (
        Index("idx_burn_service_timestamp", "service_id", "timestamp"),
        Index("idx_burn_risk_level", "risk_level"),
    )


class Deployment(Base):
    """
    Deployments Table
    Tracks deployment attempts and release gate decisions
    """
    __tablename__ = "deployments"
    
    id = Column(Integer, primary_key=True, index=True)
    service_id = Column(Integer, ForeignKey("services.id"), nullable=False, index=True)
    deployment_id = Column(String(255), unique=True, nullable=False)  # External ID
    version = Column(String(100), nullable=True)
    requested_at = Column(DateTime, default=datetime.utcnow)
    requested_by = Column(String(255), nullable=True)
    
    # Release gate decision
    allowed = Column(Boolean, nullable=False)
    blocked_reason = Column(Text, nullable=True)
    risk_level_at_request = Column(Enum(RiskLevel), nullable=True)
    burn_rate_at_request = Column(Float, nullable=True)
    
    # Deployment status
    status = Column(String(50), default="pending")  # pending, approved, rejected, completed
    completed_at = Column(DateTime, nullable=True)
    
    # Relationships
    service = relationship("Service", back_populates="deployments")
    
    __table_args__ = (
        Index("idx_deployment_service_time", "service_id", "requested_at"),
    )


class Alert(Base):
    """
    Alerts Table
    Stores generated alerts for notification and UI feed
    """
    __tablename__ = "alerts"
    
    id = Column(Integer, primary_key=True, index=True)
    service_id = Column(Integer, ForeignKey("services.id"), nullable=False, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    severity = Column(Enum(AlertSeverity), nullable=False)
    channel = Column(Enum(AlertChannel), nullable=False)
    title = Column(String(500), nullable=False)
    message = Column(Text, nullable=False)
    alert_metadata = Column(JSON, nullable=True)  # Additional context
    
    # Notification status
    sent = Column(Boolean, default=False)
    sent_at = Column(DateTime, nullable=True)
    acknowledged = Column(Boolean, default=False)
    acknowledged_by = Column(String(255), nullable=True)
    acknowledged_at = Column(DateTime, nullable=True)
    
    # Relationships
    service = relationship("Service", back_populates="alerts")
    
    __table_args__ = (
        Index("idx_alert_service_time", "service_id", "timestamp"),
        Index("idx_alert_severity", "severity"),
        Index("idx_alert_unack", "acknowledged"),
    )


class SystemConfig(Base):
    """
    System Configuration Table
    Global settings and thresholds
    """
    __tablename__ = "system_config"
    
    id = Column(Integer, primary_key=True, index=True)
    key = Column(String(255), unique=True, nullable=False, index=True)
    value = Column(Text, nullable=False)
    value_type = Column(String(50), default="string")  # string, int, float, json, bool
    description = Column(Text, nullable=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    updated_by = Column(String(255), nullable=True)
