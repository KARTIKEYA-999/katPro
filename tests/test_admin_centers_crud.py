import pytest
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.auth import create_access_token

client = TestClient(app)

@pytest.fixture
def admin_token():
    return create_access_token({"sub": "admin1", "role": "ADMIN", "user_id": 3})

def test_admin_centers_crud_and_coordinates(admin_token):
    headers = {"Authorization": f"Bearer {admin_token}"}
    
    # 1. Verify existing centers return coordinates in public endpoint
    pub_res = client.get("/api/public/centers")
    assert pub_res.status_code == 200
    pub_data = pub_res.json()
    assert len(pub_data) >= 4
    suryapet = next(c for c in pub_data if c["center_code"] == "CPC-001")
    assert suryapet["latitude"] is not None
    assert suryapet["longitude"] is not None
    assert abs(float(suryapet["latitude"]) - 17.1439) < 0.001
    assert abs(float(suryapet["longitude"]) - 79.6236) < 0.001

    # 2. Admin creates a new center with coordinates
    new_center = {
        "center_code": "TEST-HYD-99",
        "name": "Hyderabad Test Procurement Center",
        "district": "Hyderabad",
        "state": "Telangana",
        "address": "Agricultural Market, Gaddiannaram, Hyderabad - 500036",
        "contact_phone": "+91 40 24040101",
        "working_hours_start": "08:00:00",
        "working_hours_end": "17:00:00",
        "daily_capacity_mt": 180.0,
        "active_counters": 3,
        "avg_processing_seconds": 420,
        "status": "OPEN",
        "latitude": 17.3616,
        "longitude": 78.4747
    }
    create_res = client.post("/api/admin/centers", json=new_center, headers=headers)
    assert create_res.status_code == 200, create_res.text
    created = create_res.json()
    center_id = created["id"]
    assert created["center_code"] == "TEST-HYD-99"
    assert abs(float(created["latitude"]) - 17.3616) < 0.001
    assert abs(float(created["longitude"]) - 78.4747) < 0.001

    # 3. Admin updates the center
    update_data = {
        "name": "Hyderabad Central Mandi (Updated)",
        "daily_capacity_mt": 250.0,
        "active_counters": 4,
        "latitude": 17.3850,
        "longitude": 78.4867
    }
    update_res = client.put(f"/api/admin/centers/{center_id}", json=update_data, headers=headers)
    assert update_res.status_code == 200, update_res.text
    updated = update_res.json()
    assert updated["name"] == "Hyderabad Central Mandi (Updated)"
    assert updated["daily_capacity_mt"] == 250.0
    assert updated["active_counters"] == 4
    assert abs(float(updated["latitude"]) - 17.3850) < 0.001

    # 4. Admin deletes the newly created center
    delete_res = client.delete(f"/api/admin/centers/{center_id}", headers=headers)
    assert delete_res.status_code == 200, delete_res.text
    del_json = delete_res.json()
    assert del_json["action"] == "deleted"

    # Verify center is no longer found
    check_res = client.put(f"/api/admin/centers/{center_id}", json={"name": "test"}, headers=headers)
    assert check_res.status_code == 404
