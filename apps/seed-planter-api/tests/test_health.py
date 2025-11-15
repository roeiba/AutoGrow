"""
Black box tests for health and basic endpoints
"""

import pytest
import httpx
from datetime import datetime


class TestHealthEndpoints:
    """Test suite for health check and basic API endpoints"""

    def test_root_endpoint_returns_200(self, api_client: httpx.Client):
        """Test that root endpoint returns 200 OK"""
        response = api_client.get("/")
        assert response.status_code == 200

    def test_root_endpoint_returns_json(self, api_client: httpx.Client):
        """Test that root endpoint returns valid JSON"""
        response = api_client.get("/")
        assert response.headers["content-type"] == "application/json"
        data = response.json()
        assert isinstance(data, dict)

    def test_root_endpoint_has_required_fields(self, api_client: httpx.Client):
        """Test that root endpoint contains required fields"""
        response = api_client.get("/")
        data = response.json()
        
        required_fields = ["service", "status", "version", "mode", "timestamp"]
        for field in required_fields:
            assert field in data, f"Missing required field: {field}"

    def test_root_endpoint_service_name(self, api_client: httpx.Client):
        """Test that service name is correct"""
        response = api_client.get("/")
        data = response.json()
        assert data["service"] == "SeedGPT Seed Planter API"

    def test_root_endpoint_status_healthy(self, api_client: httpx.Client):
        """Test that status is healthy"""
        response = api_client.get("/")
        data = response.json()
        assert data["status"] == "healthy"

    def test_root_endpoint_version_format(self, api_client: httpx.Client):
        """Test that version follows semantic versioning"""
        response = api_client.get("/")
        data = response.json()
        version = data["version"]
        assert isinstance(version, str)
        # Check format: X.Y.Z
        parts = version.split(".")
        assert len(parts) == 3
        assert all(part.isdigit() for part in parts)

    def test_root_endpoint_timestamp_format(self, api_client: httpx.Client):
        """Test that timestamp is in ISO format"""
        response = api_client.get("/")
        data = response.json()
        timestamp = data["timestamp"]
        
        # Verify it's a valid ISO timestamp
        try:
            datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
        except ValueError:
            pytest.fail(f"Invalid timestamp format: {timestamp}")

    def test_root_endpoint_mode(self, api_client: httpx.Client):
        """Test that mode is set"""
        response = api_client.get("/")
        data = response.json()
        assert data["mode"] in ["SaaS", "User"], f"Invalid mode: {data['mode']}"

    def test_cors_headers_present(self, api_client: httpx.Client):
        """Test that CORS headers are present"""
        response = api_client.options("/")
        assert "access-control-allow-origin" in response.headers

    def test_api_responds_within_timeout(self, api_client: httpx.Client):
        """Test that API responds within acceptable time"""
        import time
        start = time.time()
        response = api_client.get("/")
        duration = time.time() - start
        
        assert response.status_code == 200
        assert duration < 2.0, f"API took too long to respond: {duration}s"
