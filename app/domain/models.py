"""
Domain models for orchard and tree data.

These models represent the core domain entities and should be independent
of any infrastructure concerns (API clients, databases, etc.).
"""
from typing import List, Optional
from pydantic import BaseModel, Field


class TreeData(BaseModel):
    """Individual tree data."""
    id: int
    lat: float
    lng: float
    area: float = Field(description="Canopy area in m²")
    ndre: float = Field(description="Normalized Difference Red Edge index")
    ndvi: Optional[float] = None
    volume: Optional[float] = None
    row_index: Optional[int] = None
    tree_index: Optional[int] = None
    survey_id: int


class SurveyData(BaseModel):
    """Survey data."""
    id: int
    orchard_id: int
    date: str
    hectares: float
    polygon: str = Field(
        description="Polygon as space-separated 'lon,lat' pairs"
    )


class OrchardStatistics(BaseModel):
    """Orchard-level statistics."""
    survey_id: int
    tree_count: int
    missing_tree_count: int
    average_area_m2: float = Field(alias="average_area_m2")
    stddev_area_m2: float = Field(alias="stddev_area_m2")
    average_ndre: float
    stddev_ndre: float
    
    class Config:
        populate_by_name = True
