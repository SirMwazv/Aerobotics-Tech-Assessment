"""
Unit tests for external API client.

Tests cover:
- Successful API responses
- Retry logic on 5xx errors
- No retry on 4xx errors
- Async context manager
- Error handling
"""
import pytest
import httpx
import respx
from unittest.mock import AsyncMock, patch, MagicMock

from app.infrastructure.external_api_client import (
    ExternalAPIClient,
    ExternalAPIError,
    get_api_client,
)
from app.domain.models import TreeData, SurveyData, OrchardStatistics


# ============================================================
# API Client Initialization Tests
# ============================================================

class TestAPIClientInitialization:
    """Tests for API client initialization."""
    
    def test_client_initialization(self):
        """Client should initialize with correct configuration."""
        client = ExternalAPIClient()
        
        assert client.base_url is not None
        assert client.client is not None
    
    def test_singleton_pattern(self):
        """get_api_client should return the same instance."""
        # Reset the singleton for testing
        import app.infrastructure.external_api_client as module
        module._api_client = None
        
        client1 = get_api_client()
        client2 = get_api_client()
        
        assert client1 is client2


# ============================================================
# Async Context Manager Tests
# ============================================================

class TestAsyncContextManager:
    """Tests for async context manager functionality."""
    
    @pytest.mark.asyncio
    async def test_context_manager_enter(self):
        """__aenter__ should return the client instance."""
        client = ExternalAPIClient()
        
        async with client as ctx_client:
            assert ctx_client is client
    
    @pytest.mark.asyncio
    async def test_context_manager_exit_closes_client(self):
        """__aexit__ should close the HTTP client."""
        client = ExternalAPIClient()
        client.close = AsyncMock()
        
        async with client:
            pass
        
        client.close.assert_called_once()


# ============================================================
# API Response Tests
# ============================================================

class TestAPIResponses:
    """Tests for API response handling."""
    
    @pytest.mark.asyncio
    @respx.mock
    async def test_successful_get_request(self):
        """Successful GET request should return parsed JSON."""
        client = ExternalAPIClient()
        
        # Mock the response
        respx.get(f"{client.base_url}/test").mock(
            return_value=httpx.Response(200, json={"result": "success"})
        )
        
        result = await client._make_request("GET", "/test")
        
        assert result == {"result": "success"}
        await client.close()
    
    @pytest.mark.asyncio
    @respx.mock
    async def test_get_surveys_success(self):
        """get_survey_by_orchard should return SurveyData."""
        client = ExternalAPIClient()
        
        respx.get(f"{client.base_url}/farming/surveys/").mock(
            return_value=httpx.Response(200, json={
                "count": 1,
                "next": None,
                "previous": None,
                "results": [{
                    "id": 1,
                    "date": "2024-01-15",
                    "orchard_id": 216269,
                    "hectares": 2.5,
                    "polygon": "18.8,-32.3 18.9,-32.3"
                }]
            })
        )
        
        result = await client.get_survey_by_orchard(216269)
        
        assert isinstance(result, SurveyData)
        assert result.id == 1
        assert result.orchard_id == 216269
        await client.close()
    
    @pytest.mark.asyncio
    @respx.mock
    async def test_get_surveys_empty_results(self):
        """get_survey_by_orchard should raise error when no surveys found."""
        client = ExternalAPIClient()
        
        respx.get(f"{client.base_url}/farming/surveys/").mock(
            return_value=httpx.Response(200, json={
                "count": 0,
                "next": None,
                "previous": None,
                "results": []
            })
        )
        
        with pytest.raises(ExternalAPIError, match="No surveys found"):
            await client.get_survey_by_orchard(999999)
        
        await client.close()


# ============================================================
# Error Handling Tests
# ============================================================

class TestErrorHandling:
    """Tests for error handling."""
    
    @pytest.mark.asyncio
    @respx.mock
    async def test_4xx_error_no_retry(self):
        """4xx errors should not trigger retry."""
        client = ExternalAPIClient()
        
        respx.get(f"{client.base_url}/test").mock(
            return_value=httpx.Response(404, text="Not Found")
        )
        
        with pytest.raises(ExternalAPIError, match="404"):
            await client._make_request("GET", "/test")
        
        # Should only be called once (no retry)
        assert respx.calls.call_count == 1
        await client.close()
    
    @pytest.mark.asyncio
    @respx.mock
    async def test_5xx_error_triggers_retry(self):
        """5xx errors should trigger retry."""
        client = ExternalAPIClient()
        
        # First call fails with 500, second succeeds
        route = respx.get(f"{client.base_url}/test")
        route.side_effect = [
            httpx.Response(500, text="Internal Server Error"),
            httpx.Response(200, json={"result": "success"}),
        ]
        
        result = await client._make_request("GET", "/test")
        
        assert result == {"result": "success"}
        assert respx.calls.call_count == 2  # Retried once
        await client.close()


# ============================================================
# Polygon Parsing Tests
# ============================================================

class TestPolygonParsing:
    """Tests for polygon string parsing."""
    
    def test_parse_polygon_valid(self):
        """Valid polygon string should be parsed correctly."""
        client = ExternalAPIClient()
        polygon_str = "18.826,-32.328 18.827,-32.328 18.827,-32.327 18.826,-32.327"
        
        result = client.parse_polygon(polygon_str)
        
        assert len(result) == 4
        assert result[0] == [18.826, -32.328]
        assert result[1] == [18.827, -32.328]
    
    def test_parse_polygon_with_closing_point(self):
        """Polygon with closing point should be parsed correctly."""
        client = ExternalAPIClient()
        polygon_str = "18.826,-32.328 18.827,-32.328 18.827,-32.327 18.826,-32.327 18.826,-32.328"
        
        result = client.parse_polygon(polygon_str)
        
        assert len(result) == 5
        assert result[0] == result[-1]  # First and last point are the same


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
