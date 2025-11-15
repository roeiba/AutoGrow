"""
Black box tests for project planting endpoints
"""

import pytest
import httpx
import time
from typing import Dict


class TestProjectsAPI:
    """Test suite for /api/v1/projects endpoints"""

    def test_create_project_returns_200(
        self, 
        api_client: httpx.Client, 
        sample_project_request: Dict
    ):
        """Test that creating a project returns 200 OK"""
        response = api_client.post("/api/v1/projects", json=sample_project_request)
        assert response.status_code == 200

    def test_create_project_returns_json(
        self, 
        api_client: httpx.Client, 
        sample_project_request: Dict
    ):
        """Test that response is valid JSON"""
        response = api_client.post("/api/v1/projects", json=sample_project_request)
        assert response.headers["content-type"] == "application/json"
        data = response.json()
        assert isinstance(data, dict)

    def test_create_project_has_required_fields(
        self, 
        api_client: httpx.Client, 
        sample_project_request: Dict
    ):
        """Test that response contains all required fields"""
        response = api_client.post("/api/v1/projects", json=sample_project_request)
        data = response.json()
        
        required_fields = [
            "project_id",
            "status",
            "created_at",
            "websocket_url",
            "estimated_completion_time"
        ]
        
        for field in required_fields:
            assert field in data, f"Missing required field: {field}"

    def test_create_project_id_is_uuid(
        self, 
        api_client: httpx.Client, 
        sample_project_request: Dict
    ):
        """Test that project_id is a valid UUID"""
        response = api_client.post("/api/v1/projects", json=sample_project_request)
        data = response.json()
        project_id = data["project_id"]
        
        # UUID format: 8-4-4-4-12 hex characters
        import re
        uuid_pattern = r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
        assert re.match(uuid_pattern, project_id), f"Invalid UUID format: {project_id}"

    def test_create_project_status_is_initializing(
        self, 
        api_client: httpx.Client, 
        sample_project_request: Dict
    ):
        """Test that initial status is 'initializing'"""
        response = api_client.post("/api/v1/projects", json=sample_project_request)
        data = response.json()
        assert data["status"] == "initializing"

    def test_create_project_websocket_url_format(
        self, 
        api_client: httpx.Client, 
        sample_project_request: Dict
    ):
        """Test that WebSocket URL is properly formatted"""
        response = api_client.post("/api/v1/projects", json=sample_project_request)
        data = response.json()
        ws_url = data["websocket_url"]
        
        assert ws_url.startswith("ws://") or ws_url.startswith("wss://")
        assert "/api/v1/projects/" in ws_url
        assert "/ws" in ws_url
        assert data["project_id"] in ws_url

    def test_create_project_estimated_time_is_positive(
        self, 
        api_client: httpx.Client, 
        sample_project_request: Dict
    ):
        """Test that estimated completion time is positive"""
        response = api_client.post("/api/v1/projects", json=sample_project_request)
        data = response.json()
        assert data["estimated_completion_time"] > 0

    def test_create_project_missing_name_returns_422(self, api_client: httpx.Client):
        """Test that missing project_name returns 422"""
        invalid_request = {
            "project_description": "Test description",
            "mode": "saas"
        }
        response = api_client.post("/api/v1/projects", json=invalid_request)
        assert response.status_code == 422

    def test_create_project_missing_description_returns_422(self, api_client: httpx.Client):
        """Test that missing project_description returns 422"""
        invalid_request = {
            "project_name": "test-project",
            "mode": "saas"
        }
        response = api_client.post("/api/v1/projects", json=invalid_request)
        assert response.status_code == 422

    def test_create_project_invalid_mode_returns_422(self, api_client: httpx.Client):
        """Test that invalid mode returns 422"""
        invalid_request = {
            "project_name": "test-project",
            "project_description": "Test description",
            "mode": "invalid_mode"
        }
        response = api_client.post("/api/v1/projects", json=invalid_request)
        assert response.status_code == 422

    def test_create_project_empty_name_returns_422(self, api_client: httpx.Client):
        """Test that empty project name returns 422"""
        invalid_request = {
            "project_name": "",
            "project_description": "Test description",
            "mode": "saas"
        }
        response = api_client.post("/api/v1/projects", json=invalid_request)
        assert response.status_code == 422

    def test_create_project_empty_description_returns_422(self, api_client: httpx.Client):
        """Test that empty description returns 422"""
        invalid_request = {
            "project_name": "test-project",
            "project_description": "",
            "mode": "saas"
        }
        response = api_client.post("/api/v1/projects", json=invalid_request)
        assert response.status_code == 422

    def test_create_project_with_minimal_data(
        self, 
        api_client: httpx.Client, 
        sample_project_request_minimal: Dict
    ):
        """Test creating project with minimal required data"""
        response = api_client.post("/api/v1/projects", json=sample_project_request_minimal)
        assert response.status_code == 200
        data = response.json()
        assert "project_id" in data

    def test_create_project_response_time(
        self, 
        api_client: httpx.Client, 
        sample_project_request: Dict
    ):
        """Test that project creation responds quickly (async)"""
        start = time.time()
        response = api_client.post("/api/v1/projects", json=sample_project_request)
        duration = time.time() - start
        
        assert response.status_code == 200
        # Should return immediately since it's async
        assert duration < 5.0, f"Project creation took too long: {duration}s"

    def test_create_multiple_projects_returns_unique_ids(
        self, 
        api_client: httpx.Client, 
        sample_project_request: Dict
    ):
        """Test that multiple projects get unique IDs"""
        response1 = api_client.post("/api/v1/projects", json=sample_project_request)
        response2 = api_client.post("/api/v1/projects", json=sample_project_request)
        
        assert response1.status_code == 200
        assert response2.status_code == 200
        
        id1 = response1.json()["project_id"]
        id2 = response2.json()["project_id"]
        
        assert id1 != id2, "Project IDs should be unique"

    def test_list_projects_endpoint_exists(self, api_client: httpx.Client):
        """Test that list projects endpoint exists"""
        response = api_client.get("/api/v1/projects")
        # Should return 200 or 404, not 405 (method not allowed)
        assert response.status_code in [200, 404, 501]

    def test_get_project_by_id_endpoint_exists(self, api_client: httpx.Client):
        """Test that get project by ID endpoint exists"""
        test_id = "00000000-0000-0000-0000-000000000000"
        response = api_client.get(f"/api/v1/projects/{test_id}")
        # Should return 404 or 501, not 405 (method not allowed)
        assert response.status_code in [404, 501]

    def test_invalid_json_returns_422(self, api_client: httpx.Client):
        """Test that invalid JSON returns 422"""
        response = api_client.post(
            "/api/v1/projects",
            content="invalid json",
            headers={"content-type": "application/json"}
        )
        assert response.status_code == 422

    def test_cors_headers_on_post(
        self, 
        api_client: httpx.Client, 
        sample_project_request: Dict
    ):
        """Test that CORS headers are present on POST requests"""
        response = api_client.post("/api/v1/projects", json=sample_project_request)
        assert "access-control-allow-origin" in response.headers
