"""
FastAPI application entry point.
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.middleware.error_handler import ErrorHandlerMiddleware
from app.api.v1.routers import orchards


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
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
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


# Application lifecycle events
@app.on_event("startup")
async def startup_event():
    """Run on application startup."""
    pass


@app.on_event("shutdown")
async def shutdown_event():
    """Run on application shutdown."""
    from app.infrastructure.external_api_client import get_api_client
    
    # Close the API client
    client = get_api_client()
    await client.close()
