"""
Dependency injection for FastAPI.
"""
from typing import Annotated
from fastapi import Depends

from app.infrastructure.external_api_client import (
    ExternalAPIClient,
    get_api_client,
)
from app.services.domain.missing_tree_detector import MissingTreeDetector
from app.services.application.orchard_service import OrchardService


def get_missing_tree_detector() -> MissingTreeDetector:
    """
    Dependency factory for MissingTreeDetector.
    
    Returns:
        MissingTreeDetector instance
    """
    return MissingTreeDetector()


def get_orchard_service(
    api_client: Annotated[ExternalAPIClient, Depends(get_api_client)],
    detector: Annotated[MissingTreeDetector, Depends(get_missing_tree_detector)],
) -> OrchardService:
    """
    Dependency factory for OrchardService.
    
    Args:
        api_client: External API client (injected)
        detector: Missing tree detector (injected)
        
    Returns:
        OrchardService instance
    """
    return OrchardService(api_client=api_client, detector=detector)


# Type aliases for cleaner route signatures
OrchardServiceDep = Annotated[OrchardService, Depends(get_orchard_service)]
