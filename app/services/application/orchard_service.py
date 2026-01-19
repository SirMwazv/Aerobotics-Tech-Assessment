"""
Application service: Orchestration layer for orchard operations.
"""
from typing import List, Tuple

from app.infrastructure.external_api_client import (
    ExternalAPIClient,
    ExternalAPIError,
)
from app.services.domain.missing_tree_detector import MissingTreeDetector


class OrchardService:
    """
    Application service for orchard-related operations.
    
    Orchestrates data fetching and business logic execution.
    Follows the application layer pattern - no business logic here,
    only coordination between infrastructure and domain layers.
    """
    
    def __init__(
        self,
        api_client: ExternalAPIClient,
        detector: MissingTreeDetector,
    ):
        """
        Initialize the service with dependencies.
        
        Args:
            api_client: External API client for data fetching
            detector: Missing tree detector for spatial analysis
        """
        self.api_client = api_client
        self.detector = detector
    
    async def get_missing_tree_locations(
        self,
        orchard_id: int,
    ) -> List[Tuple[float, float]]:
        """
        Get missing tree locations for an orchard.
        
        This method orchestrates:
        1. Fetching survey data for the orchard
        2. Fetching survey statistics
        3. Fetching tree data
        4. Running missing tree detection
        
        Args:
            orchard_id: Unique identifier for the orchard
            
        Returns:
            List of (latitude, longitude) tuples for missing trees
            
        Raises:
            ExternalAPIError: If data fetching fails
            ValueError: If orchard data is invalid
        """
        # Fetch survey for orchard
        survey = await self.api_client.get_survey_by_orchard(orchard_id)
        
        # Fetch survey statistics
        statistics = await self.api_client.get_survey_statistics(survey.id)
        
        # Fetch tree data
        trees = await self.api_client.get_trees(survey.id)
        
        # Validate that we have trees
        if not trees:
            return []
        
        # Parse polygon coordinates
        polygon_coords = self.api_client.parse_polygon(survey.polygon)
        
        # Run missing tree detection
        missing_locations = self.detector.detect_missing_trees(
            trees=trees,
            statistics=statistics,
            polygon_coords=polygon_coords,
        )
        
        return missing_locations
