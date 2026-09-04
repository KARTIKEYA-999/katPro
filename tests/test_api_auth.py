import pytest
from fastapi.testclient import TestClient
from backend.app.main import app

client = TestClient(app)

def test_health_endpoint():
    """Verifies public health endpoint reports PostgreSQL, C, and C++ status"""
    response = client.get("/api/public/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "HEALTHY"
    assert data["database_postgresql"] == "CONNECTED"
    assert "LOADED" in data["c_acceleration_module"]
    assert "LOADED" in data["cpp_optimization_module"]

def test_demo_login_farmer():
    """Tests demo login for farmer role"""
    response = client.post("/api/auth/demo-login/farmer")
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["user"]["role"] == "FARMER"
    assert data["user"]["username"] == "farmer1"

def test_demo_login_official():
    """Tests demo login for official role"""
    response = client.post("/api/auth/demo-login/official")
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["user"]["role"] == "OFFICIAL"
    assert data["user"]["username"] == "official1"

def test_demo_login_admin():
    """Tests demo login for administrator role"""
    response = client.post("/api/auth/demo-login/admin")
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["user"]["role"] == "ADMIN"
    assert data["user"]["username"] == "admin1"

def test_role_access_control():
    """
    Verifies that a Farmer token CANNOT access Official or Admin endpoints (RBAC).
    """
    farmer_login = client.post("/api/auth/demo-login/farmer").json()
    farmer_token = farmer_login["access_token"]
    headers = {"Authorization": f"Bearer {farmer_token}"}

    # Farmer trying to access official dashboard -> Must return 403 Forbidden
    resp = client.get("/api/official/dashboard", headers=headers)
    assert resp.status_code == 403, "Farmer should not have access to Official dashboard"

    # Farmer trying to access admin dashboard -> Must return 403 Forbidden
    resp = client.get("/api/admin/dashboard", headers=headers)
    assert resp.status_code == 403, "Farmer should not have access to Admin dashboard"


def test_login_role_synchronization_validation():
    """
    Verifies that selecting an incorrect role causes login rejection with 403.
    """
    # 1. Matching role succeeds
    resp_match = client.post("/api/auth/login", json={
        "username": "official1",
        "password": "official123",
        "role": "OFFICIAL"
    })
    assert resp_match.status_code == 200
    assert resp_match.json()["user"]["role"] == "OFFICIAL"

    # 2. Mismatched role fails with 403
    resp_mismatch = client.post("/api/auth/login", json={
        "username": "official1",
        "password": "official123",
        "role": "ADMIN"
    })
    assert resp_mismatch.status_code == 403
    assert "Role mismatch" in resp_mismatch.json()["detail"]


def test_farmer_registration_with_profile_image():
    """
    Verifies that a farmer can register with a profile photo (base64 data URI).
    Checks that the image is saved to disk, assigned to user and farmer, and returned in profile.
    """
    import uuid
    from pathlib import Path
    from backend.app.config import BASE_DIR

    # Valid 1x1 PNG base64 data URI
    sample_b64_png = (
        "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAA"
        "DUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
    )

    uid = uuid.uuid4().hex[:6]
    reg_payload = {
        "username": f"farmer_img_{uid}",
        "password": "Password123!",
        "role": "FARMER",
        "full_name": f"Farmer With Photo {uid}",
        "phone": f"+9198{uid[:8]}",
        "village": "Kodad, Suryapet",
        "profile_image": sample_b64_png
    }

    resp = client.post("/api/auth/register", json=reg_payload)
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert "access_token" in data
    assert "user" in data
    avatar_url = data["user"].get("profile_image_url")
    assert avatar_url is not None
    assert avatar_url.startswith("/static/uploads/avatars/farmer_")
    assert avatar_url.endswith(".png")

    # Verify physical file existence
    relative_path = avatar_url.replace("/static/", "")
    full_disk_path = BASE_DIR / "frontend" / relative_path
    assert full_disk_path.exists(), f"Image file not found at {full_disk_path}"

    # Verify GET /api/farmer/profile returns profile_image_url
    token = data["access_token"]
    profile_resp = client.get("/api/farmer/profile", headers={"Authorization": f"Bearer {token}"})
    assert profile_resp.status_code == 200
    profile_data = profile_resp.json()
    assert profile_data["profile_image_url"] == avatar_url
    assert profile_data["full_name"] == reg_payload["full_name"]


def test_farmer_registration_without_profile_image():
    """
    Verifies that farmer registration without profile photo functions seamlessly with None.
    """
    import uuid
    uid = uuid.uuid4().hex[:6]
    reg_payload = {
        "username": f"farmer_noimg_{uid}",
        "password": "Password123!",
        "role": "FARMER",
        "full_name": f"Farmer No Photo {uid}",
        "phone": f"+9197{uid[:8]}",
        "village": "Huzurnagar, Suryapet"
    }

    resp = client.post("/api/auth/register", json=reg_payload)
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["user"].get("profile_image_url") is None

