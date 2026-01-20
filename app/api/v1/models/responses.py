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
    locations: List[MissingTreeLocation] = Field(
        description="Coordinates of detected missing tree locations"
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "orchard_id": "216269",
                "locations": [
                    {"latitude": -32.328023, "longitude": 18.826754},
                    {"latitude": -32.327970, "longitude": 18.826769},
                    {"latitude": -32.328037, "longitude": 18.826818},
                ]
            }
        }

