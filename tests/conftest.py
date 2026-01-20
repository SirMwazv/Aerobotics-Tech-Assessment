"""
Shared pytest fixtures for all tests.

This module provides common fixtures including:
- Sample tree data
- Sample statistics
- Sample polygons
- Mock API client
- FastAPI test client
"""
import pytest
import numpy as np
from typing import AsyncGenerator
from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient
from httpx import AsyncClient

from app.main import app
from app.domain.models import TreeData, SurveyData, OrchardStatistics
from app.infrastructure.external_api_client import ExternalAPIClient


# ============================================================
# Sample Data Fixtures
# ============================================================

@pytest.fixture
def sample_trees() -> list[TreeData]:
    """Create a sample grid of trees with one missing."""
    trees = []
    tree_id = 1
    
    # Create a 5x5 grid with regular spacing
    # Missing tree at position (2, 2)
    for row in range(5):
        for col in range(5):
            if row == 2 and col == 2:
                continue  # Skip to simulate missing tree
            
            trees.append(TreeData(
                id=tree_id,
                lat=-32.328 + row * 0.0001,  # ~11m spacing
                lng=18.826 + col * 0.0001,
                area=20.0 + np.random.normal(0, 2),
                ndre=0.55 + np.random.normal(0, 0.02),
                survey_id=1
            ))
            tree_id += 1
    
    return trees


@pytest.fixture
def sample_statistics() -> OrchardStatistics:
    """Create sample orchard statistics."""
    return OrchardStatistics(
        survey_id=1,
        tree_count=24,
        missing_tree_count=1,
        average_area_m2=20.0,
        stddev_area_m2=2.0,
        average_ndre=0.55,
        stddev_ndre=0.02,
    )


@pytest.fixture
def sample_polygon() -> list[list[float]]:
    """Create a sample orchard polygon."""
    # Square polygon around the grid
    return [
        [18.8255, -32.3285],  # lon, lat format
        [18.8270, -32.3285],
        [18.8270, -32.3275],
        [18.8255, -32.3275],
        [18.8255, -32.3285],  # Close the polygon
    ]


@pytest.fixture
def sample_survey() -> SurveyData:
    """Create a sample survey."""
    return SurveyData(
        id=1,
        date="2024-01-15",
        orchard_id=216269,
        hectares=2.5,
        polygon="18.8255,-32.3285 18.8270,-32.3285 18.8270,-32.3275 18.8255,-32.3275 18.8255,-32.3285"
    )


@pytest.fixture
def regular_grid_coords() -> list[tuple[float, float]]:
    """Create regular grid coordinates in meters."""
    coords = []
    spacing = 10.0  # 10 meters
    
    for row in range(10):
        for col in range(10):
            coords.append((col * spacing, row * spacing))
    
    return coords


# ============================================================
# Mock API Client Fixtures
# ============================================================

@pytest.fixture
def mock_api_client(sample_trees, sample_statistics, sample_survey):
    """Create a mock external API client."""
    mock_client = AsyncMock(spec=ExternalAPIClient)
    mock_client.get_survey_by_orchard.return_value = sample_survey
    mock_client.get_survey_statistics.return_value = sample_statistics
    mock_client.get_trees.return_value = sample_trees
    mock_client.parse_polygon.return_value = [
        [18.8255, -32.3285],
        [18.8270, -32.3285],
        [18.8270, -32.3275],
        [18.8255, -32.3275],
        [18.8255, -32.3285],
    ]
    return mock_client


# ============================================================
# FastAPI Test Client Fixtures
# ============================================================

@pytest.fixture
def test_client() -> TestClient:
    """Create a synchronous test client for FastAPI."""
    return TestClient(app)


@pytest.fixture
async def async_test_client() -> AsyncGenerator[AsyncClient, None]:
    """Create an async test client for FastAPI."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client
