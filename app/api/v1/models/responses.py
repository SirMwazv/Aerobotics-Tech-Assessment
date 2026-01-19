"""
API response models using Pydantic.
"""
from typing import List
from pydantic import BaseModel, Field


class MissingTreeLocation(BaseModel):
    """Single missing tree location."""
    latitude: float = Field(
        description="Latitude coordinate in degrees",
        examples=[34.0522]
    )
    longitude: float = Field(
        description="Longitude coordinate in degrees",
        examples=[-118.2437]
    )


class MissingTreesResponse(BaseModel):
    """Response model for missing trees endpoint."""
    orchard_id: str = Field(
        description="Unique identifier for the orchard"
    )
    missing_tree_count: int = Field(
        description="Number of missing trees detected"
    )
    locations: List[MissingTreeLocation] = Field(
        description="Coordinates of detected missing tree locations"
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "orchard_id": "orchard_123",
                "missing_tree_count": 3,
                "locations": [
                    {"latitude": 34.0522, "longitude": -118.2437},
                    {"latitude": 34.0523, "longitude": -118.2438},
                    {"latitude": 34.0524, "longitude": -118.2439},
                ]
            }
        }
