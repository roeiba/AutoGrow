"""
Black box tests for WebSocket functionality
"""

import pytest
import httpx
from websockets.sync.client import connect
from websockets.exceptions import WebSocketException
import json
import time


class TestWebSocket:
    """Test suite for WebSocket connections"""

    def test_websocket_endpoint_exists(self, api_base_url: str):
        """Test that WebSocket endpoint is accessible"""
        # Convert http to ws
        ws_url = api_base_url.replace("http://", "ws://").replace("https://", "wss://")
        test_id = "00000000-0000-0000-0000-000000000000"
        ws_endpoint = f"{ws_url}/api/v1/projects/{test_id}/ws"
        
        try:
            # Try to connect (will fail but shouldn't give connection refused)
            with connect(ws_endpoint, open_timeout=5) as websocket:
                websocket.close()
        except WebSocketException:
            # Expected - project doesn't exist, but endpoint is reachable
            pass
        except Exception as e:
            # Connection refused or timeout means service is down
            pytest.fail(f"WebSocket endpoint not accessible: {e}")

    @pytest.mark.skip(reason="Requires actual project creation")
    def test_websocket_connection_with_valid_project(
        self, 
        api_client: httpx.Client,
        api_base_url: str,
        sample_project_request: dict
    ):
        """Test WebSocket connection with a valid project ID"""
        # Create a project first
        response = api_client.post("/api/v1/projects", json=sample_project_request)
        assert response.status_code == 200
        
        data = response.json()
        project_id = data["project_id"]
        ws_url = data["websocket_url"]
        
        try:
            with connect(ws_url, open_timeout=10) as websocket:
                # Send ping
                websocket.send("ping")
                
                # Wait for pong or progress update
                message = websocket.recv(timeout=5)
                assert message is not None
                
        except WebSocketException as e:
            pytest.fail(f"WebSocket connection failed: {e}")

    @pytest.mark.skip(reason="Requires actual project creation")
    def test_websocket_receives_progress_updates(
        self, 
        api_client: httpx.Client,
        api_base_url: str,
        sample_project_request: dict
    ):
        """Test that WebSocket receives progress updates"""
        # Create a project
        response = api_client.post("/api/v1/projects", json=sample_project_request)
        data = response.json()
        ws_url = data["websocket_url"]
        
        try:
            with connect(ws_url, open_timeout=10) as websocket:
                # Wait for progress updates (timeout after 30 seconds)
                start_time = time.time()
                received_update = False
                
                while time.time() - start_time < 30:
                    try:
                        message = websocket.recv(timeout=5)
                        data = json.loads(message)
                        
                        # Check if it's a progress update
                        if "status" in data and "progress_percent" in data:
                            received_update = True
                            assert isinstance(data["progress_percent"], (int, float))
                            assert 0 <= data["progress_percent"] <= 100
                            break
                            
                    except TimeoutError:
                        continue
                
                assert received_update, "No progress updates received within 30 seconds"
                
        except WebSocketException as e:
            pytest.fail(f"WebSocket connection failed: {e}")

    def test_websocket_url_format_in_response(
        self,
        api_client: httpx.Client,
        sample_project_request: dict
    ):
        """Test that WebSocket URL in response is properly formatted"""
        response = api_client.post("/api/v1/projects", json=sample_project_request)
        data = response.json()
        ws_url = data["websocket_url"]
        
        # Check protocol
        assert ws_url.startswith("ws://") or ws_url.startswith("wss://"), \
            f"Invalid WebSocket protocol in URL: {ws_url}"
        
        # Check path structure
        assert "/api/v1/projects/" in ws_url, "Missing API path in WebSocket URL"
        assert "/ws" in ws_url, "Missing /ws endpoint in WebSocket URL"
        
        # Check project ID is in URL
        project_id = data["project_id"]
        assert project_id in ws_url, "Project ID not in WebSocket URL"
