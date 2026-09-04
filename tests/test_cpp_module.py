import pytest
from backend.app.cpp_bridge import (
    run_center_workload_optimization,
    run_procurement_day_simulation,
    _load_cpp_library
)

def test_cpp_library_loaded():
    """Verifies that the compiled C++ shared library is properly linked"""
    lib = _load_cpp_library()
    assert lib is not None, "C++ library libcppqueue_opt.dylib must be loaded"

def test_cpp_center_workload_optimization():
    """Tests C++ center workload optimizer and counter recommendation"""
    res = run_center_workload_optimization(
        center_id=1,
        expected_farmers=75,
        total_capacity_qtl=1500,
        active_counters=2,
        operating_hours=8,
        hourly_arrivals=[6, 14, 18, 15, 10, 8, 4, 2]
    )

    assert res["center_id"] == 1
    assert res["average_wait_minutes"] >= 0.0
    assert res["peak_wait_minutes"] >= 0.0
    assert res["counter_utilization_pct"] > 0.0
    assert res["recommended_counters"] >= 1
    assert 0 <= res["peak_bottleneck_hour"] <= 7
    assert res["engine"].startswith("C++"), "Must be calculated by compiled C++ module"

def test_cpp_procurement_day_simulation():
    """Tests C++ discrete-event queue simulation"""
    sim = run_procurement_day_simulation(
        total_farmers=60,
        active_counters=2,
        mean_proc_sec=480,
        stddev_proc_sec=60
    )

    assert sim["simulated_avg_wait_min"] > 0.0
    assert sim["simulated_max_wait_min"] >= sim["simulated_avg_wait_min"]
    assert 0.0 < sim["simulated_utilization_pct"] <= 100.0
    assert "C++" in sim["engine"]
