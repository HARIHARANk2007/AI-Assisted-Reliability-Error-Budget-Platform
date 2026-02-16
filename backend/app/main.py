"""
AI-Assisted Reliability & Error Budget Platform
Main FastAPI Application
"""

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import asyncio

from app.core.config import get_settings
from app.core.database import create_tables, get_db_context
from app.api.router import api_router

settings = get_settings()


# Background task for periodic computations
async def periodic_computation():
    """
    Background task that runs every minute to:
    - Compute burn rates
    - Store historical data
    - Evaluate and trigger alerts
    """
    from app.services.burn_rate_service import BurnRateEngine
    from app.services.alert_service import AlertManager
    from app.models.database import Service
    
    while True:
        try:
            with get_db_context() as db:
                services = db.query(Service).filter(Service.is_active == True).all()
                
                burn_engine = BurnRateEngine(db)
                alert_manager = AlertManager(db)
                
                for service in services:
                    try:
                        # Compute and store burn rate
                        for window in [5, 60, 1440]:
                            computation = burn_engine.compute_burn_rate(service.id, window)
                            burn_engine.store_burn_history(computation)
                        
                        # Evaluate alerts
                        alert_manager.evaluate_and_alert(service.id)
                        
                    except Exception as e:
                        print(f"Error processing service {service.name}: {e}")
                
                print(f"[Background] Processed {len(services)} services")
                
        except Exception as e:
            print(f"[Background] Error in periodic computation: {e}")
        
        await asyncio.sleep(settings.COMPUTATION_INTERVAL_SECONDS)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    # Startup
    print(f"Starting {settings.APP_NAME} v{settings.APP_VERSION}")
    
    # Create database tables
    create_tables()
    print("Database tables initialized")
    
    # Start background task if enabled
    task = None
    if settings.SCHEDULER_ENABLED:
        task = asyncio.create_task(periodic_computation())
        print("Background computation task started")
    
    yield
    
    # Shutdown
    if task:
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
    print("Application shutdown complete")


# Create FastAPI application
app = FastAPI(
    title=settings.APP_NAME,
    description="""
    ## AI-Assisted Reliability & Error Budget Platform
    
    A production-grade SRE platform for:
    - **SLO Monitoring**: Track service level objectives and compliance
    - **Error Budget Management**: Calculate and monitor error budget burn rates
    - **Predictive Analytics**: Forecast budget exhaustion using trend analysis
    - **Release Gating**: Automated deployment decisions based on reliability state
    - **AI Insights**: Human-readable reliability summaries and recommendations
    
    ### Key Features
    - Real-time burn rate computation with multi-window analysis (5m, 1h, 24h)
    - Risk classification (Safe → Observe → Danger → Freeze)
    - Linear regression-based exhaustion forecasting
    - Automated alert generation with cooldown
    - Deployment gate with override capabilities
    """,
    version=settings.APP_VERSION,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "detail": str(exc) if settings.DEBUG else "An unexpected error occurred"
        }
    )


# Include API router
app.include_router(api_router, prefix=settings.API_V1_PREFIX)


# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint for load balancers and monitoring"""
    return {
        "status": "healthy",
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "environment": settings.ENVIRONMENT
    }


# Root endpoint
@app.get("/")
async def root():
    """Root endpoint with API information"""
    return {
        "name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "docs": "/docs",
        "api_prefix": settings.API_V1_PREFIX,
        "endpoints": {
            "services": f"{settings.API_V1_PREFIX}/services",
            "slo": f"{settings.API_V1_PREFIX}/slo",
            "burn": f"{settings.API_V1_PREFIX}/burn",
            "forecast": f"{settings.API_V1_PREFIX}/forecast",
            "release": f"{settings.API_V1_PREFIX}/release",
            "summary": f"{settings.API_V1_PREFIX}/summary",
            "alerts": f"{settings.API_V1_PREFIX}/alerts",
            "metrics": f"{settings.API_V1_PREFIX}/metrics"
        }
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG
    )
