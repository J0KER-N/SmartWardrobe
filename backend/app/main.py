import logging
import sys
from contextlib import asynccontextmanager

from fastapi import FastAPI, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text

from .config import get_settings
from .database import engine
from .models import Base
from .routers import auth, wardrobe, tryon, recommendations, records, profile

settings = get_settings()

# Configure logging
def setup_logging():
    """Configure application logging."""
    log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    log_level = getattr(logging, settings.log_level.upper(), logging.INFO)

    handlers = [logging.StreamHandler(sys.stdout)]
    if settings.log_file:
        from logging.handlers import RotatingFileHandler
        file_handler = RotatingFileHandler(
            settings.log_file,
            maxBytes=10 * 1024 * 1024,  # 10MB
            backupCount=5,
        )
        handlers.append(file_handler)

    logging.basicConfig(
        level=log_level,
        format=log_format,
        handlers=handlers,
    )

    # Set third-party loggers to WARNING
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING if not settings.database_echo else logging.INFO)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events."""
    # Startup
    logger = logging.getLogger(__name__)
    logger.info(f"Starting {settings.app_name} in {settings.environment} mode")
    
    # Create database tables
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables initialized")
    
    yield
    
    # Shutdown
    logger.info("Shutting down application")


setup_logging()
logger = logging.getLogger(__name__)

app = FastAPI(
    title=settings.app_name,
    description="Smart Wardrobe System Backend API",
    version="1.0.0",
    lifespan=lifespan,
    debug=settings.debug,
)

# CORS configuration
cors_origins = settings.get_cors_origins()
if cors_origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        allow_headers=["*"],
        expose_headers=["*"],
    )
    logger.info(f"CORS enabled for origins: {cors_origins}")
else:
    logger.warning("CORS not configured - no allowed origins set")

# Include routers
app.include_router(auth.router)
app.include_router(wardrobe.router)
app.include_router(tryon.router)
app.include_router(recommendations.router)
app.include_router(records.router)
app.include_router(profile.router)


@app.get("/health", tags=["health"])
def health_check():
    """Basic health check endpoint."""
    return {"status": "ok", "environment": settings.environment}


@app.get("/health/detailed", tags=["health"])
def detailed_health_check():
    """Detailed health check including database connectivity."""
    health_status = {
        "status": "ok",
        "environment": settings.environment,
        "checks": {
            "database": "unknown",
            "ai_services": {},
        },
    }

    # Check database
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        health_status["checks"]["database"] = "healthy"
    except Exception as e:
        health_status["checks"]["database"] = f"unhealthy: {str(e)}"
        health_status["status"] = "degraded"

    # Check AI services
    if settings.leffa_endpoint:
        health_status["checks"]["ai_services"]["leffa"] = "configured"
    if settings.fashionclip_endpoint:
        health_status["checks"]["ai_services"]["fashionclip"] = "configured"
    if settings.baichuan_api_url:
        health_status["checks"]["ai_services"]["baichuan"] = "configured"

    return health_status


@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler."""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Internal server error" if settings.is_production else str(exc)},
    )

