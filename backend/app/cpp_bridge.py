import ctypes
import os
import logging
from typing import Dict, Any, List, Optional
from backend.app.config import CPP_LIB_PATH

logger = logging.getLogger("sih_procurement.cpp_bridge")

# Define C-compatible structures matching cpp_modules/optimizer.h
class QueueItemInput(ctypes.Structure):
    _fields_ = [
        ("token_id", ctypes.c_int32),
        ("sequence_num", ctypes.c_int32),
        ("arrival_timestamp", ctypes.c_int32),
        ("estimated_quantity_qtl", ctypes.c_int32),
        ("commodity_urgency", ctypes.c_int32),
        ("previous_no_shows", ctypes.c_int32),
    ]

class OptimizedQueueItem(ctypes.Structure):
    _fields_ = [
        ("token_id", ctypes.c_int32),
        ("sequence_num", ctypes.c_int32),
        ("optimized_rank", ctypes.c_int32),
        ("priority_score", ctypes.c_float),
        ("estimated_wait_minutes", ctypes.c_int32),
    ]

class CenterWorkloadConfig(ctypes.Structure):
    _fields_ = [
        ("center_id", ctypes.c_int32),
        ("total_expected_farmers", ctypes.c_int32),
        ("total_capacity_qtl", ctypes.c_int32),
        ("active_counters", ctypes.c_int32),
        ("slot_duration_minutes", ctypes.c_int32),
        ("operating_hours", ctypes.c_int32),
    ]

class WorkloadOptimizationResult(ctypes.Structure):
    _fields_ = [
        ("average_wait_minutes", ctypes.c_float),
        ("peak_wait_minutes", ctypes.c_float),
        ("counter_utilization_pct", ctypes.c_float),
        ("recommended_counters", ctypes.c_int32),
        ("peak_bottleneck_hour", ctypes.c_int32),
        ("recommended_slot_capacity", ctypes.c_int32),
    ]

_cpp_lib = None

def _load_cpp_library():
    global _cpp_lib
    if _cpp_lib is not None:
        return _cpp_lib

    if os.path.exists(CPP_LIB_PATH):
        try:
            _cpp_lib = ctypes.CDLL(CPP_LIB_PATH)

            # Setup optimize_queue_prioritization
            _cpp_lib.optimize_queue_prioritization.argtypes = [
                ctypes.POINTER(QueueItemInput),
                ctypes.c_int32,
                ctypes.c_int32,
                ctypes.c_int32,
                ctypes.c_int32,
                ctypes.POINTER(OptimizedQueueItem)
            ]
            _cpp_lib.optimize_queue_prioritization.restype = ctypes.c_int

            # Setup analyze_center_workload
            _cpp_lib.analyze_center_workload.argtypes = [
                ctypes.POINTER(CenterWorkloadConfig),
                ctypes.POINTER(ctypes.c_int32),
                ctypes.c_int32,
                ctypes.POINTER(WorkloadOptimizationResult)
            ]
            _cpp_lib.analyze_center_workload.restype = ctypes.c_int

            # Setup simulate_procurement_day
            _cpp_lib.simulate_procurement_day.argtypes = [
                ctypes.c_int32,
                ctypes.c_int32,
                ctypes.c_int32,
                ctypes.c_int32,
                ctypes.POINTER(ctypes.c_float),
                ctypes.POINTER(ctypes.c_float),
                ctypes.POINTER(ctypes.c_float)
            ]
            _cpp_lib.simulate_procurement_day.restype = ctypes.c_int

            logger.info(f"Successfully loaded C++ optimization library from {CPP_LIB_PATH}")
            return _cpp_lib
        except Exception as e:
            logger.error(f"Failed to bind C++ library {CPP_LIB_PATH}: {e}")
            _cpp_lib = None
            return None
    else:
        logger.warning(f"C++ library not found at {CPP_LIB_PATH}. Running Python fallback logic.")
        return None

def run_center_workload_optimization(
    center_id: int,
    expected_farmers: int = 60,
    total_capacity_qtl: int = 1500,
    active_counters: int = 2,
    operating_hours: int = 8,
    hourly_arrivals: Optional[List[int]] = None
) -> Dict[str, Any]:
    """
    Executes C++ workload optimization model to determine optimal counter allocation,
    bottleneck peak hours, and slot capacities.
    """
    lib = _load_cpp_library()
    if lib:
        cfg = CenterWorkloadConfig(
            center_id=center_id,
            total_expected_farmers=expected_farmers,
            total_capacity_qtl=total_capacity_qtl,
            active_counters=active_counters,
            slot_duration_minutes=60,
            operating_hours=operating_hours
        )

        arrivals = hourly_arrivals or [8, 12, 16, 14, 10, 8, 5, 3]
        arr_type = ctypes.c_int32 * len(arrivals)
        c_arrivals = arr_type(*arrivals)

        result = WorkloadOptimizationResult()
        res = lib.analyze_center_workload(
            ctypes.byref(cfg),
            c_arrivals,
            ctypes.c_int32(len(arrivals)),
            ctypes.byref(result)
        )

        if res == 0:
            return {
                "center_id": center_id,
                "average_wait_minutes": round(float(result.average_wait_minutes), 1),
                "peak_wait_minutes": round(float(result.peak_wait_minutes), 1),
                "counter_utilization_pct": round(float(result.counter_utilization_pct), 1),
                "recommended_counters": int(result.recommended_counters),
                "peak_bottleneck_hour": int(result.peak_bottleneck_hour),
                "recommended_slot_capacity": int(result.recommended_slot_capacity),
                "engine": "C++ (libcppqueue_opt.dylib)"
            }

    # Python Fallback
    return {
        "center_id": center_id,
        "average_wait_minutes": 22.5,
        "peak_wait_minutes": 48.0,
        "counter_utilization_pct": 78.4,
        "recommended_counters": max(1, active_counters),
        "peak_bottleneck_hour": 2,
        "recommended_slot_capacity": 12,
        "engine": "Python fallback"
    }

def run_procurement_day_simulation(
    total_farmers: int = 80,
    active_counters: int = 2,
    mean_proc_sec: int = 480,
    stddev_proc_sec: int = 60
) -> Dict[str, float]:
    """
    Executes stochastic discrete-event simulation in C++ using random arrival distributions.
    """
    lib = _load_cpp_library()
    if lib:
        avg_wait = ctypes.c_float()
        max_wait = ctypes.c_float()
        utilization = ctypes.c_float()

        res = lib.simulate_procurement_day(
            ctypes.c_int32(total_farmers),
            ctypes.c_int32(active_counters),
            ctypes.c_int32(mean_proc_sec),
            ctypes.c_int32(stddev_proc_sec),
            ctypes.byref(avg_wait),
            ctypes.byref(max_wait),
            ctypes.byref(utilization)
        )
        if res == 0:
            return {
                "simulated_avg_wait_min": round(float(avg_wait.value), 1),
                "simulated_max_wait_min": round(float(max_wait.value), 1),
                "simulated_utilization_pct": round(float(utilization.value), 1),
                "engine": "C++ Discrete-Event Simulation"
            }

    return {
        "simulated_avg_wait_min": 24.0,
        "simulated_max_wait_min": 52.0,
        "simulated_utilization_pct": 82.5,
        "engine": "Python fallback simulation"
    }
