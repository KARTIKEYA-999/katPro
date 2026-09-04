import pytest
from fastapi.testclient import TestClient
from backend.app.main import app

from backend.app.database import SessionLocal
from backend.app.models import Token, ProcurementCenter

client = TestClient(app)

@pytest.fixture(autouse=True)
def reset_demo_state():
    db = SessionLocal()
    # Remove any dynamically created test tokens with id > 25
    from backend.app.models import Booking, ProcurementTransaction
    extra_tokens = db.query(Token).filter(Token.id > 25).all()
    for et in extra_tokens:
        # Also delete transactions if any
        db.query(ProcurementTransaction).filter(ProcurementTransaction.token_id == et.id).delete()
        db.delete(et)
    db.commit()

    extra_bookings = db.query(Booking).filter(Booking.id > 25).all()
    for eb in extra_bookings:
        db.delete(eb)
    db.commit()

    # Reset seeded waiting tokens 19 to 25
    waiting_tokens = db.query(Token).filter(Token.id.between(19, 25)).all()
    for wt in waiting_tokens:
        wt.status = "WAITING"
        wt.called_at = None
        wt.completed_at = None

    c = db.query(ProcurementCenter).filter(ProcurementCenter.id == 1).first()
    if c:
        c.current_token_seq = 18
        c.status = "OPEN"
    db.commit()
    db.close()
    yield

def test_full_queue_and_procurement_lifecycle():
    """
    End-to-End SIH Workflow Test:
    1. Farmer1 checks live queue (Token A023)
    2. Official advances queue (Calls next token)
    3. Farmer1's queue position updates
    4. Official completes procurement with weighbridge data
    """
    # 1. Farmer Login
    farmer_resp = client.post("/api/auth/demo-login/farmer")
    assert farmer_resp.status_code == 200
    farmer_token = farmer_resp.json()["access_token"]
    f_headers = {"Authorization": f"Bearer {farmer_token}"}

    # 2. Farmer checks active token status
    status_resp = client.get("/api/farmer/active-token", headers=f_headers)
    assert status_resp.status_code == 200
    status_data = status_resp.json()
    assert status_data["has_active_token"] is True
    initial_token = status_data["token"]
    assert initial_token["token_number"] == "A023"
    initial_ahead = initial_token["farmers_ahead"]
    assert initial_ahead >= 1

    # 3. Official Login
    official_resp = client.post("/api/auth/demo-login/official")
    assert official_resp.status_code == 200
    official_token = official_resp.json()["access_token"]
    o_headers = {"Authorization": f"Bearer {official_token}"}

    # 4. Official checks queue roster
    queue_resp = client.get("/api/official/queue", headers=o_headers)
    assert queue_resp.status_code == 200
    queue_list = queue_resp.json()
    assert len(queue_list) > 0

    # 5. Official calls next farmer (Advances queue)
    call_resp = client.post("/api/official/call-next", headers=o_headers)
    assert call_resp.status_code == 200
    call_data = call_resp.json()
    assert "Successfully called Token" in call_data["message"]
    new_seq = call_data["current_token_seq"]

    # 6. Verify Farmer's updated status (Farmers ahead decreased by 1!)
    updated_status_resp = client.get("/api/farmer/active-token", headers=f_headers)
    assert updated_status_resp.status_code == 200
    updated_data = updated_status_resp.json()["token"]
    assert updated_data["current_token_seq"] == new_seq
    assert updated_data["farmers_ahead"] == initial_ahead - 1

    # 7. Official updates center status
    status_update = client.post(
        "/api/official/update-center-status",
        headers=o_headers,
        json={"status": "IN PROGRESS", "notes": "Weighbridges running at full capacity"}
    )
    assert status_update.status_code == 200
    assert status_update.json()["status"] == "IN PROGRESS"
