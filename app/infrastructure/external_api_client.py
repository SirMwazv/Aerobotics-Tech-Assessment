"""
Infrastructure layer: External API client with retry logic.
"""
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
import httpx
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
)

from app.config import settings


# Pydantic models for API responses
class TreeData(BaseModel):
    """Individual tree data from the external API."""
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


class TreeSurveysResponse(BaseModel):
    """Response from tree_surveys endpoint."""
    count: int
    next: Optional[str] = None
    previous: Optional[str] = None
    results: List[TreeData]


class SurveyData(BaseModel):
    """Survey data from the external API."""
    id: int
    orchard_id: int
    date: str
    hectares: float
    polygon: str = Field(
        description="Polygon as space-separated 'lon,lat' pairs"
    )


class SurveysResponse(BaseModel):
    """Response from surveys endpoint."""
    count: int
    next: Optional[str] = None
    previous: Optional[str] = None
    results: List[SurveyData]


class OrchardStatistics(BaseModel):
    """Orchard-level statistics from tree_survey_summaries."""
    survey_id: int
    tree_count: int
    missing_tree_count: int
    average_area_m2: float = Field(alias="average_area_m2")
    stddev_area_m2: float = Field(alias="stddev_area_m2")
    average_ndre: float
    stddev_ndre: float
    
    class Config:
        populate_by_name = True


class ExternalAPIError(Exception):
    """Custom exception for external API errors."""
    pass


class ExternalAPIClient:
    """
    Client for interacting with the Aerobotics API.
    Implements retry logic with exponential backoff.
    """
    
    def __init__(self):
        """Initialize the API client with configuration."""
        self.base_url = settings.external_api_base_url
        self.api_key = settings.external_api_key
        self.client = httpx.AsyncClient(
            base_url=self.base_url,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "accept": "application/json",
            },
            timeout=30.0,
        )
    
    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()
    
    @retry(
        stop=stop_after_attempt(settings.max_retry_attempts),
        wait=wait_exponential(
            multiplier=settings.retry_backoff_multiplier,
            min=settings.retry_min_wait,
            max=settings.retry_max_wait,
        ),
        retry=retry_if_exception_type((httpx.HTTPStatusError, httpx.RequestError)),
        reraise=True,
    )
    async def _make_request(
        self, 
        method: str, 
        endpoint: str, 
        **kwargs
    ) -> Dict[str, Any]:
        """
        Make an HTTP request with retry logic.
        
        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint path
            **kwargs: Additional arguments for the request
            
        Returns:
            Response data as dictionary
            
        Raises:
            ExternalAPIError: If the request fails after retries
        """
        try:
            response = await self.client.request(method, endpoint, **kwargs)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            # Retry on server errors (5xx)
            if e.response.status_code >= 500:
                raise
            # Don't retry on client errors (4xx)
            raise ExternalAPIError(
                f"API request failed: {e.response.status_code} - {e.response.text}"
            )
        except httpx.RequestError as e:
            raise ExternalAPIError(f"API request error: {str(e)}")
    
    async def get_survey_by_orchard(self, orchard_id: int) -> SurveyData:
        """
        Fetch the latest survey for an orchard.
        
        Args:
            orchard_id: Unique identifier for the orchard
            
        Returns:
            SurveyData instance
            
        Raises:
            ExternalAPIError: If the request fails or no surveys found
        """
        data = await self._make_request(
            "GET", 
            f"/farming/surveys/",
            params={"orchard_id": orchard_id}
        )
        response = SurveysResponse(**data)
        
        if not response.results:
            raise ExternalAPIError(f"No surveys found for orchard {orchard_id}")
        
        # Return the first (most recent) survey
        return response.results[0]
    
    async def get_survey_statistics(self, survey_id: int) -> OrchardStatistics:
        """
        Fetch statistics for a survey.
        
        Args:
            survey_id: Unique identifier for the survey
            
        Returns:
            OrchardStatistics instance
            
        Raises:
            ExternalAPIError: If the request fails
        """
        data = await self._make_request(
            "GET", 
            f"/farming/surveys/{survey_id}/tree_survey_summaries/"
        )
        return OrchardStatistics(**data)
    
    async def get_trees(self, survey_id: int) -> List[TreeData]:
        """
        Fetch tree-level data for a survey.
        
        Args:
            survey_id: Unique identifier for the survey
            
        Returns:
            List of TreeData instances
            
        Raises:
            ExternalAPIError: If the request fails
        """
        data = await self._make_request(
            "GET", 
            f"/farming/surveys/{survey_id}/tree_surveys/"
        )
        response = TreeSurveysResponse(**data)
        return response.results
    
    def parse_polygon(self, polygon_str: str) -> List[List[float]]:
        """
        Parse polygon string to list of [lon, lat] coordinates.
        
        Args:
            polygon_str: Space-separated 'lon,lat' pairs
            
        Returns:
            List of [longitude, latitude] pairs
        """
        coords = []
        for pair in polygon_str.strip().split():
            lon, lat = pair.split(',')
            coords.append([float(lon), float(lat)])
        return coords


# Singleton instance
_api_client: Optional[ExternalAPIClient] = None


def get_api_client() -> ExternalAPIClient:
    """
    Get or create the singleton API client instance.
    
    Returns:
        ExternalAPIClient instance
    """
    global _api_client
    if _api_client is None:
        _api_client = ExternalAPIClient()
    return _api_client
