from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text
from backend.app.database import get_db
from backend.app.models import ProcurementCenter, Announcement
from backend.app.schemas import CenterOut, AnnouncementOut
from backend.app.c_bridge import _load_c_library
from backend.app.cpp_bridge import _load_cpp_library

router = APIRouter(prefix="/api/public", tags=["Public Feeds"])

@router.get("/centers", response_model=list[CenterOut])
def get_public_centers(db: Session = Depends(get_db)):
    """Public display board of all procurement centers and current serving tokens"""
    return db.query(ProcurementCenter).order_by(ProcurementCenter.id.asc()).all()

@router.get("/announcements", response_model=list[AnnouncementOut])
def get_public_announcements(db: Session = Depends(get_db)):
    """Public notices, weather warnings, and schedule updates"""
    return db.query(Announcement).filter(Announcement.is_active == True).order_by(Announcement.id.desc()).limit(10).all()

@router.get("/health")
def system_health_check(db: Session = Depends(get_db)):
    """
    Verifies operational status of PostgreSQL, compiled C module, and compiled C++ module.
    """
    db_ok = False
    try:
        db.execute(text("SELECT 1;"))
        db_ok = True
    except Exception:
        db_ok = False

    c_ok = _load_c_library() is not None
    cpp_ok = _load_cpp_library() is not None

    return {
        "status": "HEALTHY" if (db_ok and c_ok and cpp_ok) else "DEGRADED",
        "database_postgresql": "CONNECTED" if db_ok else "ERROR",
        "c_acceleration_module": "LOADED (libcqueue.dylib)" if c_ok else "FALLBACK",
        "cpp_optimization_module": "LOADED (libcppqueue_opt.dylib)" if cpp_ok else "FALLBACK",
        "websockets_realtime": "ACTIVE"
    }
