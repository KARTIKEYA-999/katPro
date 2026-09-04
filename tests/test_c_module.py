import pytest
from backend.app.c_bridge import (
    compute_queue_metrics_fast,
    generate_token_fast,
    validate_token_string_fast,
    estimate_wait_time_historical_fast,
    _load_c_library
)

def test_c_library_loaded():
    """Verifies that the compiled C shared library is properly linked"""
    lib = _load_c_library()
    assert lib is not None, "C library libcqueue.dylib must be loaded"

def test_c_token_generation_and_validation():
    """Tests token generation and validation with C module"""
    token = generate_token_fast("A", 23, 1)
    assert token == "A023", f"Expected A023, got {token}"
    assert validate_token_string_fast(token) is True
    assert validate_token_string_fast("INVALID") is False

def test_c_queue_calculation_when_waiting():
    """
    Tests exact SIH example:
    Farmer Token: A023 (seq 23)
    Current Token: A018 (seq 18)
    Expected Ahead: 5
    Active Counters: 2
    Avg processing sec: 480 (8 minutes)
    Expected Wait: (5 * 480) / (2 * 60) = 20 minutes (or with 1 counter = 40 minutes)
    """
    metrics = compute_queue_metrics_fast(
        current_token_seq=18,
        farmer_token_seq=23,
        total_tokens_today=25,
        avg_proc_seconds=480,
        active_counters=2
    )

    assert metrics["farmers_ahead"] == 5, f"Expected 5 ahead, got {metrics['farmers_ahead']}"
    assert metrics["estimated_wait_minutes"] == 20
    assert metrics["is_farmer_turn"] is False
    assert metrics["is_approaching"] is False
    assert metrics["engine"].startswith("C"), "Must be calculated by compiled C engine"

def test_c_queue_calculation_when_turn_arrives():
    """Tests status when current token equals farmer token"""
    metrics = compute_queue_metrics_fast(
        current_token_seq=23,
        farmer_token_seq=23,
        total_tokens_today=25,
        avg_proc_seconds=480,
        active_counters=2
    )

    assert metrics["farmers_ahead"] == 0
    assert metrics["is_farmer_turn"] is True
    assert metrics["estimated_wait_minutes"] == 0

def test_c_queue_calculation_when_turn_approaching():
    """Tests approaching flag (ahead <= 2)"""
    metrics = compute_queue_metrics_fast(
        current_token_seq=21,
        farmer_token_seq=23,
        total_tokens_today=25,
        avg_proc_seconds=480,
        active_counters=2
    )

    assert metrics["farmers_ahead"] == 2
    assert metrics["is_approaching"] is True
    assert metrics["is_farmer_turn"] is False

def test_c_historical_ewma_estimation():
    """Tests EWMA waiting time calculation from recent samples"""
    recent_times = [420, 480, 510, 460, 490] # ~8 minutes each
    wait_min = estimate_wait_time_historical_fast(
        recent_processing_seconds=recent_times,
        farmers_ahead=5,
        active_counters=2,
        alpha=0.3,
        buffer_minutes=2
    )
    assert wait_min >= 20, f"Expected wait time >= 20 min, got {wait_min}"
