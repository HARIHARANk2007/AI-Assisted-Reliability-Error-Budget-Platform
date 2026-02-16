"""
Application Configuration
Environment-based settings using Pydantic
"""

from pydantic_settings import BaseSettings
from typing import Optional, List
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings with environment variable support"""
    
    # Application
    APP_NAME: str = "SRE Reliability Platform"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    ENVIRONMENT: str = "development"
    
    # Database - SQLite for local dev, PostgreSQL for production
    DATABASE_URL: str = "sqlite:///./sre_platform.db"
    DATABASE_POOL_SIZE: int = 10
    DATABASE_MAX_OVERFLOW: int = 20
    
    # Redis (for caching/pubsub)
    REDIS_URL: str = "redis://localhost:6379/0"
    
    # API Settings
    API_V1_PREFIX: str = "/api/v1"
    CORS_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:8080"]
    
    # Metrics Ingestion
    PROMETHEUS_URL: Optional[str] = None
    METRICS_FETCH_INTERVAL_SECONDS: int = 60
    METRICS_RETENTION_DAYS: int = 30
    
    # SLO Computation
    DEFAULT_SLO_WINDOW_DAYS: int = 30
    ROLLING_WINDOWS_MINUTES: List[int] = [5, 60, 1440]  # 5m, 1h, 24h
    
    # Burn Rate Thresholds
    BURN_RATE_SAFE_THRESHOLD: float = 1.0
    BURN_RATE_OBSERVE_THRESHOLD: float = 1.5
    BURN_RATE_DANGER_THRESHOLD: float = 2.0
    BURN_RATE_FREEZE_THRESHOLD: float = 3.0
    
    # Risk Classification
    ERROR_BUDGET_OBSERVE_THRESHOLD: float = 70.0  # % consumed
    ERROR_BUDGET_DANGER_THRESHOLD: float = 85.0
    ERROR_BUDGET_FREEZE_THRESHOLD: float = 95.0
    
    # Release Gate
    RELEASE_GATE_BURN_RATE_THRESHOLD: float = 2.0
    RELEASE_GATE_BUDGET_THRESHOLD: float = 90.0  # Block if >90% consumed
    
    # Alerts
    ALERT_COOLDOWN_MINUTES: int = 15
    SLACK_WEBHOOK_URL: Optional[str] = None
    EMAIL_SMTP_HOST: Optional[str] = None
    EMAIL_SMTP_PORT: int = 587
    EMAIL_FROM_ADDRESS: Optional[str] = None
    
    # Background Tasks
    SCHEDULER_ENABLED: bool = True
    COMPUTATION_INTERVAL_SECONDS: int = 60
    
    class Config:
        env_file = ".env"
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance"""
    return Settings()


# Risk level thresholds configuration
RISK_THRESHOLDS = {
    "safe": {
        "burn_rate_max": 1.0,
        "budget_consumed_max": 50.0,
        "color": "#22c55e",
        "action": "Normal operations"
    },
    "observe": {
        "burn_rate_max": 1.5,
        "budget_consumed_max": 70.0,
        "color": "#eab308",
        "action": "Increased monitoring"
    },
    "danger": {
        "burn_rate_max": 2.0,
        "budget_consumed_max": 85.0,
        "color": "#f97316",
        "action": "Limit non-critical changes"
    },
    "freeze": {
        "burn_rate_max": float('inf'),
        "budget_consumed_max": 100.0,
        "color": "#ef4444",
        "action": "Block all deployments"
    }
}

# SLO Formulas Documentation
SLO_FORMULAS = {
    "availability": {
        "formula": "(total_requests - error_count) / total_requests * 100",
        "description": "Percentage of successful requests"
    },
    "error_budget_total": {
        "formula": "(1 - slo_target/100) * total_requests",
        "description": "Total allowed errors based on SLO"
    },
    "error_budget_consumed": {
        "formula": "(actual_errors / allowed_errors) * 100",
        "description": "Percentage of error budget used"
    },
    "burn_rate": {
        "formula": "current_error_rate / allowed_error_rate",
        "description": "Rate at which error budget is being consumed (1.0 = normal)"
    },
    "time_to_exhaustion": {
        "formula": "remaining_budget / (burn_rate * normal_consumption_rate)",
        "description": "Hours until budget reaches zero at current burn rate"
    }
}
