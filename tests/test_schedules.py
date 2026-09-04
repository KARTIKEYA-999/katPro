import pytest
from fastapi.testclient import TestClient
from backend.app.main import app

client = TestClient(app)

def test_official_schedule_write_forbidden():
    """
    Validates role separation: Officials CANNOT create, update, or delete schedules.
    Procurement Schedules & Capacity Management is restricted exclusively to Admins.
    """
    # 1. Login as official
    login_resp = client.post("/api/auth/demo-login/official")
    assert login_resp.status_code == 200
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 2. Official reading schedules is permitted (read-only for daily operations)
    list_resp = client.get("/api/official/schedules", headers=headers)
    assert list_resp.status_code == 200

    # 3. Official attempting to CREATE a schedule is blocked with 403
    create_payload = {
        "commodity_id": 1,
        "schedule_date": "2026-09-25",
        "start_time": "08:30:00",
        "end_time": "17:30:00",
        "total_capacity_quintals": 450.0,
        "tokens_per_slot": 12
    }
    create_resp = client.post("/api/official/schedules", json=create_payload, headers=headers)
    assert create_resp.status_code == 403
    assert "restricted to State Administrators" in create_resp.json()["detail"]

    # 4. Official attempting to UPDATE a schedule is blocked with 403
    put_resp = client.put("/api/official/schedules/1", json={"status": "PAUSED"}, headers=headers)
    assert put_resp.status_code == 403
    assert "restricted to State Administrators" in put_resp.json()["detail"]

    # 5. Official attempting to DELETE a schedule is blocked with 403
    del_resp = client.delete("/api/official/schedules/1", headers=headers)
    assert del_resp.status_code == 403
    assert "restricted to State Administrators" in del_resp.json()["detail"]


def test_admin_schedule_crud_full_lifecycle():
    """
    Tests statewide schedule administration exclusively managed by State Administrators:
    1. Admin fetches notified commodities
    2. Admin lists schedules across all centers
    3. Admin creates schedule for Center 1 with flexible time formats
    4. Admin updates capacity and status
    5. Admin removes schedule and cleans up
    """
    # 1. Login as Admin
    login_resp = client.post("/api/auth/demo-login/admin")
    assert login_resp.status_code == 200
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 2. Commodities
    comm_resp = client.get("/api/admin/commodities", headers=headers)
    assert comm_resp.status_code == 200
    commodities = comm_resp.json()
    assert len(commodities) > 0
    commodity_id = commodities[0]["id"]

    # 3. Create schedule for Center 1
    new_sched = {
        "center_id": 1,
        "commodity_id": commodity_id,
        "schedule_date": "2026-09-29",
        "start_time": "09:00",
        "end_time": "17:00",
        "total_capacity_quintals": 600.0,
        "tokens_per_slot": 15,
        "slot_names": [
            "Morning Slot 1 (09:00 - 11:00)",
            "Morning Slot 2 (11:00 - 13:00)",
            "Afternoon Slot (14:00 - 17:00)"
        ]
    }
    create_resp = client.post("/api/admin/schedules", json=new_sched, headers=headers)
    assert create_resp.status_code == 200
    sched_id = create_resp.json()["schedule_id"]
    assert sched_id is not None

    # 4. Verify in admin schedules list
    list_resp = client.get("/api/admin/schedules?center_id=1", headers=headers)
    assert list_resp.status_code == 200
    schedules = list_resp.json()
    target_sched = next((s for s in schedules if s["id"] == sched_id), None)
    assert target_sched is not None
    assert target_sched["total_capacity_quintals"] == 600.0
    assert len(target_sched["slots"]) == 3

    # 5. Admin updates schedule
    update_payload = {
        "total_capacity_quintals": 750.0,
        "status": "PAUSED"
    }
    put_resp = client.put(f"/api/admin/schedules/{sched_id}", json=update_payload, headers=headers)
    assert put_resp.status_code == 200
    assert put_resp.json()["status"] == "PAUSED"

    # 6. Admin deletes schedule
    del_resp = client.delete(f"/api/admin/schedules/{sched_id}", headers=headers)
    assert del_resp.status_code == 200
    assert del_resp.json()["action"] in ("DELETED", "CANCELLED")


def test_unauthenticated_access_blocked():
    """
    Verifies that unauthenticated calls to protected routes are rejected with 401.
    """
    assert client.get("/api/admin/schedules").status_code == 401
    assert client.post("/api/admin/schedules", json={}).status_code == 401
    assert client.get("/api/official/schedules").status_code == 401
    assert client.get("/api/farmer/active-token").status_code == 401
