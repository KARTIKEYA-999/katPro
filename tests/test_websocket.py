import pytest
from starlette.testclient import TestClient
from backend.app.main import app

def test_websocket_handshake_scenarios():
    """
    Validates that WebSocket connections succeed across all query parameter permutations,
    including missing user_id, empty strings, invalid strings, and valid parameters,
    preventing 403 Forbidden handshake rejections.
    """
    client = TestClient(app)

    scenarios = [
        "/ws/live?center_id=1&user_id=",
        "/ws/live?center_id=&user_id=",
        "/ws/live?center_id=1",
        "/ws/live",
        "/ws/live?center_id=1&user_id=10",
        "/ws/live?center_id=invalid&user_id=invalid",
    ]

    for url in scenarios:
        with client.websocket_connect(url) as websocket:
            data = websocket.receive_json()
            assert data.get("event") == "CONNECTED"
            assert "center_id" in data
