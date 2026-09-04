import ctypes
import os
import logging
from typing import Dict, Any, List, Optional
from backend.app.config import C_LIB_PATH

logger = logging.getLogger("sih_procurement.c_bridge")

# Define C FastQueueMetrics structure matching c_modules/queue_fast.h
class FastQueueMetrics(ctypes.Structure):
    _fields_ = [
        ("farmers_ahead", ctypes.c_int32),
        ("estimated_wait_minutes", ctypes.c_int32),
        ("completion_percent", ctypes.c_int32),
        ("is_farmer_turn", ctypes.c_int32),
        ("is_approaching", ctypes.c_int32),
        ("status_code", ctypes.c_int32),
    ]

_c_lib = None

def _load_c_library():
    global _c_lib
    if _c_lib is not None:
        return _c_lib

    if os.path.exists(C_LIB_PATH):
        try:
            _c_lib = ctypes.CDLL(C_LIB_PATH)
            
            # Setup calc_queue_metrics
            _c_lib.calc_queue_metrics.argtypes = [
                ctypes.c_int32,  # current_token_seq
                ctypes.c_int32,  # farmer_token_seq
                ctypes.c_int32,  # total_tokens_today
                ctypes.c_int32,  # avg_proc_seconds
                ctypes.c_int32,  # active_counters
                ctypes.POINTER(FastQueueMetrics) # out_metrics
            ]
            _c_lib.calc_queue_metrics.restype = ctypes.c_int

            # Setup estimate_wait_time_ewma
            _c_lib.estimate_wait_time_ewma.argtypes = [
                ctypes.POINTER(ctypes.c_int32), # historical_times_sec
                ctypes.c_int32,                 # sample_count
                ctypes.c_int32,                 # farmers_ahead
                ctypes.c_int32,                 # active_counters
                ctypes.c_float,                 # alpha
                ctypes.c_int32                  # buffer_minutes
            ]
            _c_lib.estimate_wait_time_ewma.restype = ctypes.c_int

            # Setup generate_secure_token
            _c_lib.generate_secure_token.argtypes = [
                ctypes.c_char,                  # prefix
                ctypes.c_int32,                 # sequence_num
                ctypes.c_int32,                 # center_id
                ctypes.c_char_p,                # out_buf
                ctypes.c_int32                  # max_len
            ]
            _c_lib.generate_secure_token.restype = ctypes.c_int

            # Setup validate_token_string
            _c_lib.validate_token_string.argtypes = [ctypes.c_char_p]
            _c_lib.validate_token_string.restype = ctypes.c_int

            logger.info(f"Successfully loaded C queue acceleration library from {C_LIB_PATH}")
            return _c_lib
        except Exception as e:
            logger.error(f"Failed to bind C library {C_LIB_PATH}: {e}")
            _c_lib = None
            return None
    else:
        logger.warning(f"C library not found at {C_LIB_PATH}. Running Python fallback logic.")
        return None

def compute_queue_metrics_fast(
    current_token_seq: int,
    farmer_token_seq: int,
    total_tokens_today: int = 50,
    avg_proc_seconds: int = 480,
    active_counters: int = 2
) -> Dict[str, Any]:
    """
    Invokes compiled C module to calculate queue position, ahead count, and ETA in sub-microsecond time.
    """
    lib = _load_c_library()
    if lib:
        metrics = FastQueueMetrics()
        res = lib.calc_queue_metrics(
            ctypes.c_int32(current_token_seq),
            ctypes.c_int32(farmer_token_seq),
            ctypes.c_int32(total_tokens_today),
            ctypes.c_int32(avg_proc_seconds),
            ctypes.c_int32(active_counters),
            ctypes.byref(metrics)
        )
        if res == 0:
            return {
                "farmers_ahead": metrics.farmers_ahead,
                "estimated_wait_minutes": metrics.estimated_wait_minutes,
                "completion_percent": metrics.completion_percent,
                "is_farmer_turn": bool(metrics.is_farmer_turn),
                "is_approaching": bool(metrics.is_approaching),
                "status_code": metrics.status_code,
                "engine": "C (libcqueue.dylib)"
            }

    # Python fallback calculation if C library unavailable
    active_counters = max(1, active_counters)
    avg_proc_seconds = max(60, avg_proc_seconds)
    ahead = max(0, farmer_token_seq - max(0, current_token_seq)) if farmer_token_seq > current_token_seq else 0
    is_turn = (farmer_token_seq == current_token_seq)
    is_approaching = (0 < ahead <= 2)
    wait_minutes = round((ahead * avg_proc_seconds) / (active_counters * 60.0))
    if ahead > 0 and wait_minutes < 1:
        wait_minutes = 1

    return {
        "farmers_ahead": ahead,
        "estimated_wait_minutes": wait_minutes,
        "completion_percent": min(100, (current_token_seq * 100) // max(1, total_tokens_today)),
        "is_farmer_turn": is_turn,
        "is_approaching": is_approaching,
        "status_code": 1 if is_turn else (2 if farmer_token_seq < current_token_seq else 0),
        "engine": "Python fallback"
    }

def generate_token_fast(prefix: str, sequence_num: int, center_id: int) -> str:
    """
    Invokes C module to generate standard token string (e.g. 'A023') with CRC8 validation integrity.
    """
    lib = _load_c_library()
    if lib:
        buf = ctypes.create_string_buffer(32)
        res = lib.generate_secure_token(
            ctypes.c_char(prefix.encode('utf-8')[0]),
            ctypes.c_int32(sequence_num),
            ctypes.c_int32(center_id),
            buf,
            ctypes.c_int32(32)
        )
        if res == 0:
            return buf.value.decode('utf-8')
    return f"{prefix}{sequence_num:03d}"

def validate_token_string_fast(token_str: str) -> bool:
    """
    Invokes C module to validate token string format and integrity.
    """
    lib = _load_c_library()
    if lib:
        return bool(lib.validate_token_string(ctypes.c_char_p(token_str.encode('utf-8'))))
    return len(token_str) >= 4 and token_str[0].isalpha() and token_str[1:4].isdigit()

def estimate_wait_time_historical_fast(
    recent_processing_seconds: List[int],
    farmers_ahead: int,
    active_counters: int = 2,
    alpha: float = 0.25,
    buffer_minutes: int = 2
) -> int:
    """
    Applies EWMA historical service rate formula via C module.
    """
    if farmers_ahead <= 0:
        return 0

    lib = _load_c_library()
    if lib and recent_processing_seconds:
        arr_type = ctypes.c_int32 * len(recent_processing_seconds)
        c_arr = arr_type(*recent_processing_seconds)
        return int(lib.estimate_wait_time_ewma(
            c_arr,
            ctypes.c_int32(len(recent_processing_seconds)),
            ctypes.c_int32(farmers_ahead),
            ctypes.c_int32(active_counters),
            ctypes.c_float(alpha),
            ctypes.c_int32(buffer_minutes)
        ))
    
    # Fallback
    avg_sec = sum(recent_processing_seconds) / len(recent_processing_seconds) if recent_processing_seconds else 480.0
    return max(1, round((farmers_ahead * avg_sec) / (max(1, active_counters) * 60.0)) + buffer_minutes)
