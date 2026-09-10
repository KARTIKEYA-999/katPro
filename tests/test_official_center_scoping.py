import pytest
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.database import SessionLocal
from backend.app.models import User, Farmer, Token, ProcurementCenter, Official

client = TestClient(app)

def get_official_token(username: str, password: str = "official123") -> str:
    res = client.post("/api/auth/login", json={"username": username, "password": password})
    assert res.status_code == 200, f"Login failed for {username}: {res.text}"
    return res.json()["access_token"]

@pytest.fixture(autouse=True)
def reset_center_tokens():
    db = SessionLocal()
    tokens = db.query(Token).filter(Token.id.in_([26, 27, 28, 29, 30])).all()
    for t in tokens:
        t.status = "WAITING"
        t.called_at = None
        t.completed_at = None
    for cid in [2, 3, 4]:
        c = db.query(ProcurementCenter).filter(ProcurementCenter.id == cid).first()
        if c:
            c.current_token_seq = 0
            c.status = "OPEN"
    db.commit()
    db.close()
    yield

def test_official1_and_official2_farmer_registry_scoping():
    """
    Verify official1 (Center 1 - Suryapet) and official2 (Center 2 - Miryalaguda)
    see only their respective center's farmers in the registry.
    """
    token_off1 = get_official_token("official1")
    token_off2 = get_official_token("official2")

    # 1. Official 1 checks dashboard & farmers
    res1 = client.get("/api/official/dashboard", headers={"Authorization": f"Bearer {token_off1}"})
    assert res1.status_code == 200
    dash1 = res1.json()
    assert dash1["center_id"] == 1
    assert dash1["center_code"] == "CPC-001"

    res1_farmers = client.get("/api/official/farmers", headers={"Authorization": f"Bearer {token_off1}"})
    assert res1_farmers.status_code == 200
    farmers1 = res1_farmers.json()
    assert len(farmers1) > 0
    for f in farmers1:
        assert f["center_id"] == 1, f"Farmer {f['farmer_code']} has center_id {f['center_id']}, expected 1"
        assert f["center_code"] == "CPC-001"

    # 2. Official 2 checks dashboard & farmers
    res2 = client.get("/api/official/dashboard", headers={"Authorization": f"Bearer {token_off2}"})
    assert res2.status_code == 200
    dash2 = res2.json()
    assert dash2["center_id"] == 2
    assert dash2["center_code"] == "RPC-002"

    res2_farmers = client.get("/api/official/farmers", headers={"Authorization": f"Bearer {token_off2}"})
    assert res2_farmers.status_code == 200
    farmers2 = res2_farmers.json()
    assert len(farmers2) > 0
    for f in farmers2:
        assert f["center_id"] == 2, f"Farmer {f['farmer_code']} has center_id {f['center_id']}, expected 2"
        assert f["center_code"] == "RPC-002"

    # Verify no overlap between farmers of Center 1 and Center 2
    f1_codes = {f["farmer_code"] for f in farmers1}
    f2_codes = {f["farmer_code"] for f in farmers2}
    assert f1_codes.isdisjoint(f2_codes), f"Overlap found between Center 1 and Center 2: {f1_codes & f2_codes}"

def test_official_cross_center_modification_forbidden():
    """
    Ensure an official cannot edit or delete a farmer assigned to another procurement center.
    """
    token_off1 = get_official_token("official1") # Center 1
    token_off2 = get_official_token("official2") # Center 2

    # Get a farmer from Center 1
    res1 = client.get("/api/official/farmers", headers={"Authorization": f"Bearer {token_off1}"})
    c1_farmer = res1.json()[0]
    c1_farmer_id = c1_farmer["id"]

    # Official 2 attempts to update Center 1 farmer -> 403 Forbidden
    update_res = client.put(
        f"/api/official/farmers/{c1_farmer_id}",
        headers={"Authorization": f"Bearer {token_off2}"},
        json={"full_name": "Hacked Name", "phone": "9999988888", "village": "Hacked"}
    )
    assert update_res.status_code == 403, f"Expected 403, got {update_res.status_code}: {update_res.text}"

    # Official 2 attempts to delete Center 1 farmer -> 403 Forbidden
    del_res = client.delete(
        f"/api/official/farmers/{c1_farmer_id}",
        headers={"Authorization": f"Bearer {token_off2}"}
    )
    assert del_res.status_code == 403, f"Expected 403, got {del_res.status_code}: {del_res.text}"

    # Official 2 attempts to fetch registration certificate for Center 1 farmer -> 403 Forbidden
    cert_res = client.get(
        f"/api/official/farmers/{c1_farmer_id}/form-data",
        headers={"Authorization": f"Bearer {token_off2}"}
    )
    assert cert_res.status_code == 403, f"Expected 403, got {cert_res.status_code}: {cert_res.text}"

def test_official_enroll_farmer_auto_binds_to_assigned_center():
    """
    Ensure when an official registers a new farmer, it is automatically bound
    to the official's assigned procurement center.
    """
    token_off2 = get_official_token("official2") # Center 2 - Miryalaguda
    unique_suffix = "miryala_test"

    payload = {
        "username": f"farmer_{unique_suffix}",
        "password": "Password@123",
        "full_name": "Test Farmer Miryalaguda",
        "phone": "9848099881",
        "email": "miryala_farmer@test.com",
        "aadhaar_number": "984809988122",
        "village": "Ravulapenta",
        "mandal": "Miryalaguda",
        "district": "Nalgonda",
        "pincode": "508207",
        "land_area_acres": 4.5,
        "passbook_number": "TS-PB-MIRYALA-01",
        "primary_crop": "Paddy Common",
        "bank_account_number": "987654321012",
        "bank_ifsc_code": "SBIN0001234",
        "bank_name": "State Bank of India"
    }

    # Clean up user if already exists from prior test runs
    db = SessionLocal()
    existing_user = db.query(User).filter(User.username == payload["username"]).first()
    if existing_user:
        if existing_user.farmer_profile:
            db.delete(existing_user.farmer_profile)
        db.delete(existing_user)
        db.commit()
    db.close()

    res = client.post("/api/official/farmers", headers={"Authorization": f"Bearer {token_off2}"}, json=payload)
    assert res.status_code == 201, f"Failed to enroll farmer: {res.text}"
    data = res.json()
    assert data["center_id"] == 2
    assert data["center_code"] == "RPC-002"
    assert "Miryalaguda" in data["center_name"]

def test_call_next_farmer_picks_assigned_center_queue():
    """
    Verify call-next advances tokens strictly from the official's assigned procurement center.
    """
    token_off2 = get_official_token("official2") # Center 2 - Miryalaguda
    token_off3 = get_official_token("official3") # Center 3 - Warangal

    # Call next for Center 2
    call_res2 = client.post("/api/official/call-next", headers={"Authorization": f"Bearer {token_off2}"})
    assert call_res2.status_code == 200, f"Call next failed for official2: {call_res2.text}"
    data2 = call_res2.json()
    assert data2["current_token_number"].startswith("B"), f"Expected Center 2 token to start with B, got {data2['current_token_number']}"

    # Call next for Center 3
    call_res3 = client.post("/api/official/call-next", headers={"Authorization": f"Bearer {token_off3}"})
    assert call_res3.status_code == 200, f"Call next failed for official3: {call_res3.text}"
    data3 = call_res3.json()
    assert data3["current_token_number"].startswith("C"), f"Expected Center 3 token to start with C, got {data3['current_token_number']}"
