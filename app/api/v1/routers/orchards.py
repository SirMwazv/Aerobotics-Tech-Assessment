"""
API router for orchard endpoints.
"""
from fastapi import APIRouter, HTTPException, Path
from typing import Annotated

from app.api.dependencies import OrchardServiceDep
from app.api.v1.models.responses import MissingTreesResponse, MissingTreeLocation
from app.infrastructure.external_api_client import ExternalAPIError


router = APIRouter(
    prefix="/orchards",
    tags=["orchards"],
)


@router.get(
    "/{orchard_id}/missing-trees",
    response_model=MissingTreesResponse,
    summary="Get missing tree locations",
    description="""
    Detect and return the locations of missing trees in an orchard.
    
    This endpoint:
    1. Fetches orchard and survey data from the external API
    2. Filters unhealthy trees using statistical analysis
    3. Performs spatial analysis to detect gaps in tree coverage
    4. Returns latitude/longitude coordinates of likely missing tree locations
    
    The detection algorithm uses:
    - 2-sigma statistical filtering for tree health
    - KD-Tree spatial indexing for efficient queries
    - Median nearest-neighbor distance for spacing estimation
    - Polygon containment validation
    """,
    responses={
        200: {
            "description": "Successfully detected missing tree locations",
            "content": {
                "application/json": {
                    "example": {
                        "orchard_id": "216269",
                        "locations": [
                            {"latitude": -32.328023, "longitude": 18.826754},
                            {"latitude": -32.327970, "longitude": 18.826769},
                        ]
                    }
                }
            }
        },
        404: {
            "description": "Orchard not found",
        },
        500: {
            "description": "Internal server error or external API failure",
        }
    }
)
async def get_missing_trees(
    orchard_id: Annotated[int, Path(description="Unique identifier for the orchard")],
    orchard_service: OrchardServiceDep,
) -> MissingTreesResponse:
    """
    Get missing tree locations for an orchard.
    
    Args:
        orchard_id: Unique identifier for the orchard
        orchard_service: Orchard service (injected dependency)
        
    Returns:
        MissingTreesResponse with detected locations
        
    Raises:
        HTTPException: If orchard is not found or API call fails
    """
    try:
        # Delegate to service layer (no business logic here)
        locations = await orchard_service.get_missing_tree_locations(orchard_id)
        
        # Transform to response model
        return MissingTreesResponse(
            orchard_id=str(orchard_id),
            locations=[
                MissingTreeLocation(latitude=lat, longitude=lon)
                for lat, lon in locations
            ]
        )
    
    except ExternalAPIError as e:
        # Handle external API errors
        error_msg = str(e)
        if "404" in error_msg or "not found" in error_msg.lower() or "No surveys" in error_msg:
            raise HTTPException(
                status_code=404,
                detail=f"Orchard with ID '{orchard_id}' not found or has no surveys"
            )
        else:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to fetch orchard data: {error_msg}"
            )
    
    except Exception as e:
        # Handle unexpected errors
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )
