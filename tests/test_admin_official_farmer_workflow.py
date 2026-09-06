import uuid
import pytest
from fastapi.testclient import TestClient
from backend.app.main import app

client = TestClient(app)

def get_admin_headers():
    res = client.post("/api/auth/demo-login/admin").json()
    return {"Authorization": f"Bearer {res['access_token']}"}

def get_official_headers():
    res = client.post("/api/auth/demo-login/official").json()
    return {"Authorization": f"Bearer {res['access_token']}"}

def test_admin_official_crud():
    """
    Test Admin provision to Create, Edit, List, and Delete Central Office (OFFICIAL) users.
    """
    uid = uuid.uuid4().hex[:6]
    admin_headers = get_admin_headers()

    # 1. List existing officials
    res = client.get("/api/admin/officials", headers=admin_headers)
    assert res.status_code == 200
    initial_officials = res.json()
    assert isinstance(initial_officials, list)

    # 2. Create new Central Office Official
    new_official_payload = {
        "username": f"co_officer_{uid}",
        "password": "Password123!",
        "full_name": "Test Central Officer",
        "phone": f"987{uid[:7].zfill(7)}",
        "email": f"co_{uid}@procurement.gov.in",
        "center_id": 1,
        "designation": "Chief Procurement Inspector"
    }
    create_res = client.post("/api/admin/officials", json=new_official_payload, headers=admin_headers)
    assert create_res.status_code == 201, f"Failed to create official: {create_res.text}"
    created_official = create_res.json()
    official_id = created_official["id"]
    assert created_official["username"] == f"co_officer_{uid}"
    assert created_official["designation"] == "Chief Procurement Inspector"
    assert created_official["center_id"] == 1

    # Duplicate username check
    dup_res = client.post("/api/admin/officials", json=new_official_payload, headers=admin_headers)
    assert dup_res.status_code == 400

    # 3. Edit Central Office Official
    update_payload = {
        "full_name": "Senior Test Central Officer",
        "phone": f"988{uid[:7].zfill(7)}",
        "designation": "Director of Procurement",
        "center_id": 2,
        "is_active": True
    }
    update_res = client.put(f"/api/admin/officials/{official_id}", json=update_payload, headers=admin_headers)
    assert update_res.status_code == 200
    updated_data = update_res.json()
    assert updated_data["full_name"] == "Senior Test Central Officer"
    assert updated_data["designation"] == "Director of Procurement"
    assert updated_data["center_id"] == 2

    # 4. Verify in list
    list_res = client.get("/api/admin/officials", headers=admin_headers)
    assert any(o["id"] == official_id and o["full_name"] == "Senior Test Central Officer" for o in list_res.json())

    # 5. Delete Central Office Official
    del_res = client.delete(f"/api/admin/officials/{official_id}", headers=admin_headers)
    assert del_res.status_code == 200
    assert del_res.json()["success"] is True

    # Verify deleted
    verify_res = client.get("/api/admin/officials", headers=admin_headers)
    assert not any(o["id"] == official_id for o in verify_res.json())


def test_official_farmer_crud_and_form_data():
    """
    Test Central Office user provision to Create, Edit, Delete farmers,
    and download / retrieve the official Registration Form data.
    """
    uid = uuid.uuid4().hex[:6]
    official_headers = get_official_headers()

    # 1. Central Office creates new Farmer
    farmer_payload = {
        "username": f"farmer_co_{uid}",
        "password": "Password123!",
        "full_name": "Venkat Reddy Test",
        "phone": f"912{uid[:7].zfill(7)}",
        "email": f"venkat_{uid}@kisaan.in",
        "aadhaar_number": f"4455{uid[:8].zfill(8)}",
        "village": "Chivvemla",
        "mandal": "Suryapet",
        "district": "Suryapet",
        "pincode": "508213",
        "land_area_acres": 6.5,
        "passbook_number": f"TS-PB-{uid}",
        "primary_crop": "Paddy (Grade-A)",
        "bank_account_number": "987654321012",
        "bank_ifsc_code": "SBIN0004567",
        "bank_name": "State Bank of India"
    }

    create_res = client.post("/api/official/farmers", json=farmer_payload, headers=official_headers)
    assert create_res.status_code == 201, f"Failed to create farmer: {create_res.text}"
    created_farmer = create_res.json()
    farmer_id = created_farmer["id"]
    assert created_farmer["approval_status"] == "PENDING"
    assert created_farmer["land_area_acres"] == 6.5

    # 2. Central Office retrieves printable registration certificate / form data
    form_res = client.get(f"/api/official/farmers/{farmer_id}/form-data", headers=official_headers)
    assert form_res.status_code == 200
    form_data = form_res.json()
    assert form_data["full_name"] == "Venkat Reddy Test"
    assert form_data["village"] == "Chivvemla"
    assert form_data["district"] == "Suryapet"
    assert form_data["state"] == "Telangana"
    assert form_data["approval_status"] == "PENDING"
    assert form_data["center_name"] is not None

    # 3. Central Office edits Farmer profile
    update_payload = {
        "full_name": "Venkat Reddy Test Jr.",
        "phone": f"913{uid[:7].zfill(7)}",
        "village": "Chivvemla Rural",
        "land_area_acres": 7.0,
        "passbook_number": f"TS-PB-{uid}-B",
        "primary_crop": "Paddy (Grade-A)"
    }
    update_res = client.put(f"/api/official/farmers/{farmer_id}", json=update_payload, headers=official_headers)
    assert update_res.status_code == 200
    updated_farmer = update_res.json()
    assert updated_farmer["full_name"] == "Venkat Reddy Test Jr."
    assert updated_farmer["land_area_acres"] == 7.0

    # 4. Central Office deletes Farmer
    del_res = client.delete(f"/api/official/farmers/{farmer_id}", headers=official_headers)
    assert del_res.status_code == 200
    assert del_res.json()["success"] is True

    # Verify not in center list
    list_res = client.get("/api/official/farmers", headers=official_headers)
    assert not any(f["id"] == farmer_id for f in list_res.json())


def test_farmer_approval_workflow_and_booking_gate():
    """
    Verify:
    1. Unapproved/PENDING farmer is blocked from booking tokens (HTTP 403).
    2. State Admin approves the farmer -> approval_status becomes 'APPROVED', notification sent.
    3. Approved farmer can now book tokens.
    """
    uid = uuid.uuid4().hex[:6]
    official_headers = get_official_headers()
    admin_headers = get_admin_headers()

    # Create farmer via Central Office
    farmer_payload = {
        "username": f"gate_farmer_{uid}",
        "password": "Password123!",
        "full_name": "Gate Farmer Test",
        "phone": f"990{uid[:7].zfill(7)}",
        "email": f"gate_{uid}@kisaan.in",
        "aadhaar_number": f"1122{uid[:8].zfill(8)}",
        "village": "Miryalaguda",
        "mandal": "Miryalaguda",
        "district": "Nalgonda",
        "pincode": "508207",
        "land_area_acres": 10.0,
        "passbook_number": f"PB-GATE-{uid}",
        "primary_crop": "Paddy (Common)",
        "bank_account_number": "123456789012",
        "bank_ifsc_code": "SBIN0001122",
        "bank_name": "State Bank of India"
    }
    create_res = client.post("/api/official/farmers", json=farmer_payload, headers=official_headers)
    assert create_res.status_code == 201
    farmer_id = create_res.json()["id"]

    # Farmer logs in
    login_res = client.post("/api/auth/login", json={
        "username": f"gate_farmer_{uid}",
        "password": "Password123!"
    })
    assert login_res.status_code == 200
    farmer_token = login_res.json()["access_token"]
    farmer_headers = {"Authorization": f"Bearer {farmer_token}"}

    # Verify farmer profile shows PENDING
    profile_res = client.get("/api/farmer/profile", headers=farmer_headers)
    assert profile_res.status_code == 200
    assert profile_res.json()["approval_status"] == "PENDING"

    # Farmer attempts to book a token -> MUST BE BLOCKED WITH 403
    scheds_res = client.get("/api/farmer/schedules?center_id=1&commodity_id=1")
    sched = scheds_res.json()[0]
    avail_slot = next((s for s in sched["slots"] if not s["is_full"]), None)
    if not avail_slot:
        avail_slot = sched["slots"][2]

    book_payload = {
        "schedule_id": sched["id"],
        "slot_id": avail_slot["id"],
        "commodity_id": 1,
        "estimated_quantity_quintals": 40.0
    }
    book_res = client.post("/api/farmer/book", json=book_payload, headers=farmer_headers)
    assert book_res.status_code == 403, f"Expected 403 Forbidden for unapproved farmer, got {book_res.status_code}"
    assert "PENDING" in book_res.json()["detail"]

    # Admin approves farmer
    approve_res = client.put(f"/api/admin/farmers/{farmer_id}/approve", headers=admin_headers)
    assert approve_res.status_code == 200
    assert approve_res.json()["approval_status"] == "APPROVED"

    # Verify notification was sent to farmer
    notif_res = client.get("/api/farmer/notifications", headers=farmer_headers)
    assert notif_res.status_code == 200
    notifs = notif_res.json()
    assert len(notifs) > 0
    approval_notif = next((n for n in notifs if n["notification_type"] == "APPROVAL"), None)
    assert approval_notif is not None, "Notification of type 'APPROVAL' should have been created"
    assert "approved" in approval_notif["title"].lower()

    # Now the approved farmer attempts to book a token -> MUST SUCCEED
    approved_book_res = client.post("/api/farmer/book", json=book_payload, headers=farmer_headers)
    assert approved_book_res.status_code == 200, f"Approved farmer should be allowed to book: {approved_book_res.text}"
    token_data = approved_book_res.json()
    assert "token_number" in token_data
    assert token_data["token_number"].startswith("A")

    # Clean up
    client.delete(f"/api/official/farmers/{farmer_id}", headers=official_headers)


def test_farmer_rejection_workflow():
    """
    Verify:
    1. Admin rejects registered farmer with remarks.
    2. Farmer status is REJECTED.
    3. Rejection notification is sent to farmer with reason.
    4. Rejected farmer is blocked from booking tokens.
    """
    uid = uuid.uuid4().hex[:6]
    official_headers = get_official_headers()
    admin_headers = get_admin_headers()

    # Create farmer via Central Office
    farmer_payload = {
        "username": f"reject_farmer_{uid}",
        "password": "Password123!",
        "full_name": "Reject Farmer Test",
        "phone": f"998{uid[:7].zfill(7)}",
        "email": f"reject_{uid}@kisaan.in",
        "aadhaar_number": f"9988{uid[:8].zfill(8)}",
        "village": "Warangal Rural",
        "mandal": "Warangal",
        "district": "Warangal",
        "pincode": "506002",
        "land_area_acres": 4.0,
        "passbook_number": f"PB-REJ-{uid}",
        "primary_crop": "Cotton (Medium Staple)",
        "bank_account_number": "654321098765",
        "bank_ifsc_code": "SBIN0003344",
        "bank_name": "State Bank of India"
    }
    create_res = client.post("/api/official/farmers", json=farmer_payload, headers=official_headers)
    assert create_res.status_code == 201
    farmer_id = create_res.json()["id"]

    # Admin rejects the farmer
    rejection_remarks = "Land revenue survey number does not match Dharani records."
    reject_res = client.put(
        f"/api/admin/farmers/{farmer_id}/reject",
        json={"remarks": rejection_remarks},
        headers=admin_headers
    )
    assert reject_res.status_code == 200
    assert reject_res.json()["approval_status"] == "REJECTED"
    assert reject_res.json()["remarks"] == rejection_remarks

    # Farmer logs in
    login_res = client.post("/api/auth/login", json={
        "username": f"reject_farmer_{uid}",
        "password": "Password123!"
    })
    assert login_res.status_code == 200
    farmer_token = login_res.json()["access_token"]
    farmer_headers = {"Authorization": f"Bearer {farmer_token}"}

    # Verify farmer profile
    profile_res = client.get("/api/farmer/profile", headers=farmer_headers)
    assert profile_res.status_code == 200
    profile_data = profile_res.json()
    assert profile_data["approval_status"] == "REJECTED"
    assert profile_data["approval_remarks"] == rejection_remarks

    # Verify notification with rejection reason
    notif_res = client.get("/api/farmer/notifications", headers=farmer_headers)
    assert notif_res.status_code == 200
    notifs = notif_res.json()
    rejection_notif = next((n for n in notifs if n["notification_type"] == "REJECTION"), None)
    assert rejection_notif is not None, "Notification of type 'REJECTION' should have been created"
    assert rejection_remarks in rejection_notif["message"]

    # Booking attempt is rejected
    book_payload = {
        "schedule_id": 1,
        "slot_id": 1,
        "commodity_id": 1,
        "estimated_quantity_quintals": 20.0
    }
    book_res = client.post("/api/farmer/book", json=book_payload, headers=farmer_headers)
    assert book_res.status_code == 403
    assert "REJECTED" in book_res.json()["detail"]

    # Clean up
    client.delete(f"/api/official/farmers/{farmer_id}", headers=official_headers)
