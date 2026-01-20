"""
FastAPI application entry point.
"""
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from app.config import settings
from app.middleware.error_handler import ErrorHandlerMiddleware
from app.api.v1.routers import orchards

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.log_level.upper(), logging.INFO),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

# Rate limiter
limiter = Limiter(key_func=get_remote_address)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan context manager.
    
    Handles startup and shutdown events using the modern FastAPI pattern.
    """
    # Startup
    logger.info(f"Starting {settings.app_name} v{settings.app_version}")
    logger.info(f"Log level: {settings.log_level}")
    logger.info(f"Detection config: threshold_multiplier={settings.missing_tree_threshold_multiplier}, "
                f"use_row_detection={settings.missing_tree_use_row_detection}")
    logger.info(f"Rate limit: {settings.rate_limit_requests} requests/minute")
    
    yield
    
    # Shutdown
    from app.infrastructure.external_api_client import get_api_client
    logger.info("Shutting down application...")
    client = get_api_client()
    await client.close()
    logger.info("Shutdown complete")


# Create FastAPI application
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="""
    Geospatial Analytics API for Agrotech Platform
    
    This API provides endpoints for analyzing orchard data and detecting missing trees
    using advanced spatial analysis and agronomic signals.
    
    ## Features
    
    - **Missing Tree Detection**: Identify locations of missing trees using statistical
      filtering and spatial gap analysis
    - **Geospatial Analysis**: Project coordinates, build spatial indices, and perform
      geometric operations
    - **Robust Error Handling**: Automatic retries with exponential backoff for external
      API calls
    - **Rate Limiting**: Protects the API from abuse
    - **SOLID Architecture**: Clean separation of concerns with dependency injection
    
    ## Detection Algorithm
    
    The missing tree detection algorithm:
    1. Filters unhealthy trees using 2-sigma statistical analysis
    2. Projects coordinates to a planar system (UTM)
    3. Builds a KD-Tree for efficient spatial queries
    4. Estimates expected tree spacing using median nearest-neighbor distance
    5. Detects spatial gaps larger than expected spacing
    6. Validates candidates are inside orchard boundary
    7. Returns latitude/longitude coordinates of missing tree locations
    """,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
)

# Add rate limiter to app state
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Add CORS middleware with configurable origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add global error handling middleware
app.add_middleware(ErrorHandlerMiddleware)

# Include routers
app.include_router(orchards.router, prefix="/api/v1")


@app.get("/", tags=["health"])
async def root():
    """
    Root endpoint for health check.
    
    Returns:
        Status message
    """
    return {
        "status": "healthy",
        "service": settings.app_name,
        "version": settings.app_version,
    }


@app.get("/health", tags=["health"])
async def health_check():
    """
    Health check endpoint.
    
    Returns:
        Health status
    """
    return {
        "status": "healthy",
        "service": settings.app_name,
    }
