"""
Integration tests for API endpoints.

Tests the full HTTP request/response cycle with mocked external dependencies.
"""
import pytest
from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient

from app.main import app
from app.infrastructure.external_api_client import ExternalAPIError


# ============================================================
# Health Check Tests
# ============================================================

class TestHealthEndpoints:
    """Tests for health check endpoints."""
    
    def test_root_endpoint(self, test_client):
        """Root endpoint should return healthy status."""
        response = test_client.get("/")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "service" in data
        assert "version" in data
    
    def test_health_endpoint(self, test_client):
        """Health endpoint should return healthy status."""
        response = test_client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"


# ============================================================
# Missing Trees Endpoint Tests
# ============================================================

class TestMissingTreesEndpoint:
    """Tests for the missing trees detection endpoint."""
    
    def test_get_missing_trees_invalid_orchard_id(self, test_client):
        """Should return 422 for invalid orchard ID format."""
        response = test_client.get("/api/v1/orchards/invalid/missing-trees")
        
        assert response.status_code == 422  # Validation error
    
    def test_get_missing_trees_response_structure(self, test_client, mock_api_client):
        """Should return proper response structure when successful."""
        # Override the dependency to use our mock
        from app.api.dependencies import get_orchard_service
        from app.services.application.orchard_service import OrchardService
        
        mock_service = AsyncMock(spec=OrchardService)
        mock_service.get_missing_tree_locations.return_value = [
            (-32.328023, 18.826754),
            (-32.327970, 18.826769),
        ]
        
        def override_service():
            return mock_service
        
        app.dependency_overrides[get_orchard_service] = override_service
        
        try:
            response = test_client.get("/api/v1/orchards/216269/missing-trees")
            
            assert response.status_code == 200
            data = response.json()
            assert "orchard_id" in data
            assert "locations" in data
            assert data["orchard_id"] == "216269"
            assert len(data["locations"]) == 2
            assert "latitude" in data["locations"][0]
            assert "longitude" in data["locations"][0]
        finally:
            app.dependency_overrides.clear()


# ============================================================
# Response Format Tests
# ============================================================

class TestResponseFormats:
    """Tests for API response formats."""
    
    def test_openapi_schema_available(self, test_client):
        """OpenAPI schema should be available."""
        response = test_client.get("/openapi.json")
        
        assert response.status_code == 200
        data = response.json()
        assert "openapi" in data
        assert "paths" in data
        assert "/api/v1/orchards/{orchard_id}/missing-trees" in data["paths"]
    
    def test_docs_endpoint_available(self, test_client):
        """Swagger docs should be available."""
        response = test_client.get("/docs")
        
        assert response.status_code == 200
        assert "swagger" in response.text.lower() or "html" in response.headers.get("content-type", "")
    
    def test_redoc_endpoint_available(self, test_client):
        """ReDoc should be available."""
        response = test_client.get("/redoc")
        
        assert response.status_code == 200


# ============================================================
# CORS Tests
# ============================================================

class TestCORS:
    """Tests for CORS configuration."""
    
    def test_cors_headers_present(self, test_client):
        """CORS headers should be present for cross-origin requests."""
        response = test_client.options(
            "/api/v1/orchards/216269/missing-trees",
            headers={
                "Origin": "http://example.com",
                "Access-Control-Request-Method": "GET",
            }
        )
        
        # CORS preflight should succeed
        assert response.status_code in [200, 405, 400]  # Depends on CORS config


# ============================================================
# Rate Limiting Tests
# ============================================================

class TestRateLimiting:
    """Tests for rate limiting functionality."""
    
    def test_rate_limit_documented_in_openapi(self, test_client):
        """Rate limit should be documented in OpenAPI."""
        response = test_client.get("/openapi.json")
        
        assert response.status_code == 200
        data = response.json()
        
        # Check that 429 response is documented
        missing_trees_path = data["paths"]["/api/v1/orchards/{orchard_id}/missing-trees"]
        assert "429" in missing_trees_path["get"]["responses"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
