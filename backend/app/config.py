import os
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent

# PostgreSQL connection configuration
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://localhost:5432/sih_procurement"
)

# JWT Authentication Config
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "sih2026-digital-procurement-secret-key-super-secure")
JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 24 Hours

# Compiled C and C++ library paths
PLATFORM_EXT = "dylib" if sys.platform == "darwin" else "so"

C_LIB_PATH = os.getenv(
    "C_LIB_PATH",
    str(BASE_DIR / "c_modules" / f"libcqueue.{PLATFORM_EXT}")
)

CPP_LIB_PATH = os.getenv(
    "CPP_LIB_PATH",
    str(BASE_DIR / "cpp_modules" / f"libcppqueue_opt.{PLATFORM_EXT}")
)
