"""
Integration tests for end-to-end workflows
"""

import pytest
import httpx
import time


class TestIntegration:
    """Integration tests for complete workflows"""

    @pytest.mark.integration
    def test_complete_project_creation_flow(
        self,
        api_client: httpx.Client,
        sample_project_request: dict
    ):
        """Test complete project creation flow"""
        # Step 1: Create project
        response = api_client.post("/api/v1/projects", json=sample_project_request)
        assert response.status_code == 200
        
        data = response.json()
        project_id = data["project_id"]
        
        # Step 2: Verify response structure
        assert "project_id" in data
        assert "status" in data
        assert "websocket_url" in data
        assert data["status"] == "initializing"
        
        # Step 3: Verify project ID format
        import re
        uuid_pattern = r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
        assert re.match(uuid_pattern, project_id)
        
        # Step 4: Verify WebSocket URL is accessible
        ws_url = data["websocket_url"]
        assert project_id in ws_url

    @pytest.mark.integration
    @pytest.mark.slow
    def test_api_handles_concurrent_requests(
        self,
        api_client: httpx.Client,
        sample_project_request: dict
    ):
        """Test that API handles concurrent project creation requests"""
        import concurrent.futures
        
        def create_project():
            response = api_client.post("/api/v1/projects", json=sample_project_request)
            return response.status_code, response.json()
        
        # Create 5 projects concurrently
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(create_project) for _ in range(5)]
            results = [f.result() for f in concurrent.futures.as_completed(futures)]
        
        # All should succeed
        for status_code, data in results:
            assert status_code == 200
            assert "project_id" in data
        
        # All IDs should be unique
        project_ids = [data["project_id"] for _, data in results]
        assert len(project_ids) == len(set(project_ids)), "Duplicate project IDs found"

    @pytest.mark.integration
    def test_api_error_handling(self, api_client: httpx.Client):
        """Test that API properly handles various error scenarios"""
        # Test 1: Invalid JSON
        response = api_client.post(
            "/api/v1/projects",
            content="not json",
            headers={"content-type": "application/json"}
        )
        assert response.status_code == 422
        
        # Test 2: Missing required fields
        response = api_client.post("/api/v1/projects", json={})
        assert response.status_code == 422
        
        # Test 3: Invalid field types
        response = api_client.post("/api/v1/projects", json={
            "project_name": 123,  # Should be string
            "project_description": "test",
            "mode": "saas"
        })
        assert response.status_code == 422

    @pytest.mark.integration
    def test_api_response_consistency(
        self,
        api_client: httpx.Client,
        sample_project_request: dict
    ):
        """Test that API responses are consistent across multiple calls"""
        responses = []
        
        for _ in range(3):
            response = api_client.post("/api/v1/projects", json=sample_project_request)
            assert response.status_code == 200
            responses.append(response.json())
            time.sleep(0.5)  # Small delay between requests
        
        # Check that all responses have the same structure
        keys_set = [set(r.keys()) for r in responses]
        assert all(k == keys_set[0] for k in keys_set), "Response structure is inconsistent"
        
        # Check that all statuses are 'initializing'
        assert all(r["status"] == "initializing" for r in responses)

    @pytest.mark.integration
    def test_api_handles_special_characters(self, api_client: httpx.Client):
        """Test that API handles special characters in input"""
        special_chars_request = {
            "project_name": "test-project-with-émojis-🚀",
            "project_description": "A project with special chars: @#$%^&*()",
            "mode": "saas"
        }
        
        response = api_client.post("/api/v1/projects", json=special_chars_request)
        # Should either accept (200) or reject gracefully (422)
        assert response.status_code in [200, 422]
        
        if response.status_code == 200:
            data = response.json()
            assert "project_id" in data

    @pytest.mark.integration
    def test_api_handles_long_descriptions(self, api_client: httpx.Client):
        """Test that API handles long project descriptions"""
        long_description = "A" * 1000  # 1000 character description
        
        long_request = {
            "project_name": "long-desc-test",
            "project_description": long_description,
            "mode": "saas"
        }
        
        response = api_client.post("/api/v1/projects", json=long_request)
        # Should either accept (200) or reject gracefully (422)
        assert response.status_code in [200, 422]

    @pytest.mark.integration
    def test_health_check_during_load(
        self,
        api_client: httpx.Client,
        sample_project_request: dict
    ):
        """Test that health check remains responsive during project creation"""
        # Create a project (async operation)
        api_client.post("/api/v1/projects", json=sample_project_request)
        
        # Immediately check health
        response = api_client.get("/")
        assert response.status_code == 200
        
        data = response.json()
        assert data["status"] == "healthy"
