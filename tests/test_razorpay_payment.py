import pytest
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.database import SessionLocal
from backend.app.models import Token, ProcurementCenter, ProcurementTransaction, Notification

client = TestClient(app)

@pytest.fixture(autouse=True)
def setup_test_token():
    db = SessionLocal()
    # Ensure token 18 (A018) is set to PROCESSING and ready for testing
    t18 = db.query(Token).filter(Token.id == 18).first()
    if t18:
        t18.status = "PROCESSING"
        t18.completed_at = None

    # Clean any prior transaction for token 18
    db.query(ProcurementTransaction).filter(ProcurementTransaction.token_id == 18).delete()
    db.commit()
    db.close()
    yield

def test_token_payment_details_endpoint():
    """Verify endpoint provides full beneficiary & payment details for a token"""
    official_resp = client.post("/api/auth/demo-login/official")
    assert official_resp.status_code == 200
    headers = {"Authorization": f"Bearer {official_resp.json()['access_token']}"}

    resp = client.get("/api/official/token-payment-details/18", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["token_id"] == 18
    assert data["token_number"] == "A018"
    assert data["farmer_name"] is not None
    assert data["bank_name"] is not None
    assert data["bank_account_number"] is not None
    assert data["bank_ifsc_code"] is not None
    assert data["msp_rate"] > 0

def test_complete_token_razorpay_payment_failed():
    """Verify official can record payment failure and token transitions to PAYMENT_FAILED"""
    official_resp = client.post("/api/auth/demo-login/official")
    assert official_resp.status_code == 200
    headers = {"Authorization": f"Bearer {official_resp.json()['access_token']}"}

    fail_payload = {
        "token_id": 18,
        "gross_weight_qtl": 42.50,
        "tare_weight_qtl": 2.50,
        "moisture_content_pct": 14.2,
        "quality_grade": "Grade-A",
        "payment_status": "PAYMENT_FAILED",
        "payment_method": "RAZORPAY_DBT",
        "failure_reason": "Bank network authorization timeout",
        "bank_account_number": "382910484821",
        "bank_ifsc": "SBIN0020112"
    }

    res = client.post("/api/official/complete-token", headers=headers, json=fail_payload)
    assert res.status_code == 200
    res_data = res.json()
    assert res_data["success"] is False
    assert res_data["token_status"] == "PAYMENT_FAILED"
    assert res_data["payment_status"] == "PAYMENT_FAILED"
    assert "timeout" in res_data["reason"]

    # Check DB state
    db = SessionLocal()
    token = db.query(Token).filter(Token.id == 18).first()
    assert token.status == "PAYMENT_FAILED"

    txn = db.query(ProcurementTransaction).filter(ProcurementTransaction.token_id == 18).first()
    assert txn is not None
    assert txn.payment_status == "PAYMENT_FAILED"
    assert txn.failure_reason == "Bank network authorization timeout"
    db.close()

def test_retry_and_complete_token_razorpay_success():
    """Verify official can retry payment after failure and complete transaction with Razorpay ID"""
    official_resp = client.post("/api/auth/demo-login/official")
    assert official_resp.status_code == 200
    headers = {"Authorization": f"Bearer {official_resp.json()['access_token']}"}

    success_payload = {
        "token_id": 18,
        "gross_weight_qtl": 42.50,
        "tare_weight_qtl": 2.50,
        "moisture_content_pct": 14.0,
        "quality_grade": "Grade-A",
        "payment_status": "SUCCESS",
        "payment_method": "RAZORPAY_DBT",
        "razorpay_payment_id": "pay_test_sih_dbt_9848123",
        "razorpay_order_id": "order_dbt_test_18",
        "bank_account_number": "382910484821",
        "bank_ifsc": "SBIN0020112"
    }

    res = client.post("/api/official/complete-token", headers=headers, json=success_payload)
    assert res.status_code == 200
    res_data = res.json()
    assert res_data["success"] is True
    assert res_data["token_status"] == "COMPLETED"
    assert res_data["payment_status"] == "DIRECT_BENEFIT_TRANSFER"
    assert res_data["razorpay_payment_id"] == "pay_test_sih_dbt_9848123"

    # Check DB state
    db = SessionLocal()
    token = db.query(Token).filter(Token.id == 18).first()
    assert token.status == "COMPLETED"
    assert token.completed_at is not None

    txn = db.query(ProcurementTransaction).filter(ProcurementTransaction.token_id == 18).first()
    assert txn is not None
    assert txn.payment_status == "DIRECT_BENEFIT_TRANSFER"
    assert txn.razorpay_payment_id == "pay_test_sih_dbt_9848123"
    assert txn.net_weight_qtl == 40.00
    db.close()
