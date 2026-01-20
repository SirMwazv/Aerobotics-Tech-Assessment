"""
Infrastructure layer: External API client with retry logic.

This module handles communication with the external Aerobotics API.
It uses DTOs (Data Transfer Objects) for API responses and maps them
to domain models.
"""
from typing import List, Dict, Any, Optional
from pydantic import BaseModel
import httpx
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
)

from app.config import settings
from app.domain.models import TreeData, SurveyData, OrchardStatistics
from app.infrastructure.api_constants import AeroboticsAPIEndpoints, APIConstants


# DTOs for API responses (infrastructure concern)
class TreeSurveysResponse(BaseModel):
    """Response DTO from tree_surveys endpoint."""
    count: int
    next: Optional[str] = None
    previous: Optional[str] = None
    results: List[TreeData]


class SurveysResponse(BaseModel):
    """Response DTO from surveys endpoint."""
    count: int
    next: Optional[str] = None
    previous: Optional[str] = None
    results: List[SurveyData]


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
                "accept": APIConstants.CONTENT_TYPE_JSON,
            },
            timeout=APIConstants.DEFAULT_TIMEOUT,
        )
    
    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()
    
    async def __aenter__(self) -> "ExternalAPIClient":
        """Async context manager entry."""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Async context manager exit - ensures client is closed."""
        await self.close()
    
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
            AeroboticsAPIEndpoints.SURVEYS,
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
            AeroboticsAPIEndpoints.get_survey_summaries(survey_id)
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
            AeroboticsAPIEndpoints.get_tree_surveys(survey_id)
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
