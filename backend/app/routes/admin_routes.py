from datetime import date, datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func
from backend.app.database import get_db
from backend.app.models import (
    User, Farmer, Official, ProcurementCenter, Commodity,
    ProcurementSchedule, TimeSlot, Booking, Token, ProcurementTransaction, AuditLog
)
from backend.app.schemas import (
    CenterOut, CenterCreate, OptimizationRunRequest, OptimizationRunResponse,
    ScheduleCreate, ScheduleUpdate, ScheduleOut, TimeSlotOut, CommodityOut
)
from backend.app.auth import require_admin
from backend.app.cpp_bridge import run_center_workload_optimization, run_procurement_day_simulation

router = APIRouter(prefix="/api/admin", tags=["Admin Module"])

@router.get("/dashboard")
def get_admin_dashboard(
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    Comprehensive State-Level Administration KPIs:
    Total registered farmers, centers, total weight procured, financial disbursements,
    and system operational status.
    """
    total_farmers = db.query(Farmer).count()
    total_centers = db.query(ProcurementCenter).count()
    total_officials = db.query(Official).count()

    txns = db.query(ProcurementTransaction).all()
    total_txns = len(txns)
    total_weight_qtl = sum(float(t.net_weight_qtl) for t in txns)
    total_payout = sum(float(t.final_amount) for t in txns)

    # Today's metrics
    today_txns = db.query(ProcurementTransaction).filter(
        func.date(ProcurementTransaction.processed_at) == date.today()
    ).all()
    today_count = len(today_txns)
    today_weight_qtl = sum(float(t.net_weight_qtl) for t in today_txns)

    # Active tokens currently in queue
    active_tokens = db.query(Token).filter(Token.status.in_(["WAITING", "PROCESSING"])).count()

    return {
        "total_registered_farmers": total_farmers,
        "total_procurement_centers": total_centers,
        "total_officials": total_officials,
        "total_procured_quintals": round(total_weight_qtl, 2),
        "total_procured_metric_tonnes": round(total_weight_qtl / 10.0, 2),
        "total_disbursed_inr": round(total_payout, 2),
        "today_transactions_count": today_count,
        "today_procured_quintals": round(today_weight_qtl, 2),
        "active_queue_tokens": active_tokens,
        "system_status": "ONLINE - ALL SERVICES OPERATIONAL"
    }

@router.get("/centers", response_model=List[CenterOut])
def get_all_centers(
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Lists all centers with operational parameters"""
    return db.query(ProcurementCenter).order_by(ProcurementCenter.id.asc()).all()

@router.post("/centers", response_model=CenterOut)
def create_center(
    req: CenterCreate,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Creates a new procurement center"""
    if db.query(ProcurementCenter).filter(ProcurementCenter.center_code == req.center_code).first():
        raise HTTPException(status_code=400, detail="Center code already exists")

    center = ProcurementCenter(
        center_code=req.center_code,
        name=req.name,
        district=req.district,
        state=req.state,
        address=req.address,
        contact_phone=req.contact_phone,
        working_hours_start=datetime.strptime(req.working_hours_start, "%H:%M:%S").time(),
        working_hours_end=datetime.strptime(req.working_hours_end, "%H:%M:%S").time(),
        daily_capacity_mt=req.daily_capacity_mt,
        active_counters=req.active_counters,
        avg_processing_seconds=req.avg_processing_seconds,
        status="OPEN"
    )
    db.add(center)
    db.commit()
    db.refresh(center)
    return center

@router.put("/centers/{center_id}")
def update_center(
    center_id: int,
    req: CenterCreate,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Updates center configuration (counters, capacity, hours)"""
    center = db.query(ProcurementCenter).filter(ProcurementCenter.id == center_id).first()
    if not center:
        raise HTTPException(status_code=404, detail="Center not found")

    center.name = req.name
    center.district = req.district
    center.state = req.state
    center.address = req.address
    center.contact_phone = req.contact_phone
    center.daily_capacity_mt = req.daily_capacity_mt
    center.active_counters = req.active_counters
    center.avg_processing_seconds = req.avg_processing_seconds
    db.commit()
    return {"message": "Center updated successfully"}

@router.get("/users")
def list_users(
    role: Optional[str] = None,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Retrieves list of users filtered by role"""
    query = db.query(User)
    if role:
        query = query.filter(User.role == role.upper())
    users = query.order_by(User.id.asc()).all()

    return [
        {
            "id": u.id,
            "username": u.username,
            "role": u.role,
            "full_name": u.full_name,
            "phone": u.phone,
            "email": u.email,
            "language_pref": u.language_pref,
            "is_active": u.is_active,
            "created_at": u.created_at.strftime("%Y-%m-%d %H:%M") if u.created_at else None
        }
        for u in users
    ]

@router.put("/users/{user_id}/status")
def toggle_user_status(
    user_id: int,
    is_active: bool,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Activates or suspends a user account"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user.is_active = is_active
    db.commit()
    return {"message": f"User {user.username} active status set to {is_active}"}

@router.get("/reports")
def get_analytics_reports(
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    Analytics & Reporting Data:
    Provides center-wise, commodity-wise, and daily aggregated performance.
    """
    # 1. Commodity Breakdown
    commodities = db.query(Commodity).all()
    commodity_data = []
    for c in commodities:
        txns = db.query(ProcurementTransaction).join(Booking).filter(Booking.commodity_id == c.id).all()
        weight = sum(float(t.net_weight_qtl) for t in txns)
        payout = sum(float(t.final_amount) for t in txns)
        commodity_data.append({
            "name": c.name,
            "category": c.category,
            "msp_rate": float(c.msp_per_quintal),
            "transactions_count": len(txns),
            "total_weight_qtl": round(weight, 2),
            "total_payout_inr": round(payout, 2)
        })

    # 2. Center Breakdown
    centers = db.query(ProcurementCenter).all()
    center_data = []
    for pc in centers:
        txns = db.query(ProcurementTransaction).filter(ProcurementTransaction.center_id == pc.id).all()
        weight = sum(float(t.net_weight_qtl) for t in txns)
        payout = sum(float(t.final_amount) for t in txns)
        center_data.append({
            "id": pc.id,
            "name": pc.name,
            "district": pc.district,
            "active_counters": pc.active_counters,
            "current_token": f"A{pc.current_token_seq:03d}" if pc.current_token_seq > 0 else "None",
            "status": pc.status,
            "transactions_count": len(txns),
            "total_weight_qtl": round(weight, 2),
            "total_payout_inr": round(payout, 2)
        })

    return {
        "commodities": commodity_data,
        "centers": center_data
    }

@router.post("/run-cpp-optimization", response_model=OptimizationRunResponse)
def trigger_cpp_optimization(
    req: OptimizationRunRequest,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    SIH Technology Showcase: Invokes compiled C++ module (libcppqueue_opt)
    to perform dynamic queue workload optimization and counter allocation.
    """
    center = db.query(ProcurementCenter).filter(ProcurementCenter.id == req.center_id).first()
    if not center:
        raise HTTPException(status_code=404, detail="Center not found")

    opt_res = run_center_workload_optimization(
        center_id=center.id,
        expected_farmers=75,
        total_capacity_qtl=int(center.daily_capacity_mt * 10),
        active_counters=center.active_counters,
        operating_hours=req.operating_hours
    )

    summary = (
        f"C++ Workload Optimizer calculated average wait of {opt_res['average_wait_minutes']} min "
        f"with peak backlog at Hour {opt_res['peak_bottleneck_hour']}. "
        f"Recommended active counters: {opt_res['recommended_counters']} (Current: {center.active_counters})."
    )

    return OptimizationRunResponse(
        center_id=center.id,
        center_name=center.name,
        average_wait_minutes=opt_res["average_wait_minutes"],
        peak_wait_minutes=opt_res["peak_wait_minutes"],
        counter_utilization_pct=opt_res["counter_utilization_pct"],
        recommended_counters=opt_res["recommended_counters"],
        peak_bottleneck_hour=opt_res["peak_bottleneck_hour"],
        recommended_slot_capacity=opt_res["recommended_slot_capacity"],
        status_summary=summary
    )

@router.post("/run-cpp-simulation")
def trigger_cpp_simulation(
    total_farmers: int = 80,
    active_counters: int = 2,
    current_user: User = Depends(require_admin)
):
    """
    SIH Technology Showcase: Runs stochastic discrete-event simulation in C++
    using exponential arrivals and normal service times.
    """
    sim_res = run_procurement_day_simulation(
        total_farmers=total_farmers,
        active_counters=active_counters
    )
    return sim_res

# --- STATEWIDE PROCUREMENT SCHEDULE ADMINISTRATION ---
def _parse_time(val: str):
    for fmt in ("%H:%M:%S", "%H:%M"):
        try:
            return datetime.strptime(val.strip(), fmt).time()
        except ValueError:
            pass
    raise HTTPException(status_code=400, detail=f"Invalid time format '{val}'. Expected HH:MM or HH:MM:SS")

@router.get("/commodities", response_model=List[CommodityOut])
def admin_get_commodities(
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Admin endpoint: lists active commodities with MSP rates for schedule creation"""
    return db.query(Commodity).filter(Commodity.is_active == True).order_by(Commodity.name.asc()).all()

@router.get("/schedules", response_model=List[ScheduleOut])
def get_all_schedules(
    center_id: Optional[int] = None,
    schedule_date: Optional[date] = None,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Admin endpoint: lists procurement schedules across all or specific centers"""
    query = db.query(ProcurementSchedule)
    if center_id:
        query = query.filter(ProcurementSchedule.center_id == center_id)
    if schedule_date:
        query = query.filter(ProcurementSchedule.schedule_date == schedule_date)
    schedules = query.order_by(ProcurementSchedule.schedule_date.desc(), ProcurementSchedule.center_id.asc()).all()

    results = []
    for s in schedules:
        slots_out = [
            TimeSlotOut(
                id=sl.id,
                schedule_id=sl.schedule_id,
                slot_name=sl.slot_name,
                start_time=sl.start_time,
                end_time=sl.end_time,
                max_tokens=sl.max_tokens,
                booked_tokens=sl.booked_tokens,
                is_active=sl.is_active
            ) for sl in s.slots
        ]
        results.append(ScheduleOut(
            id=s.id,
            center_id=s.center_id,
            commodity_id=s.commodity_id,
            commodity_name=s.commodity.name if s.commodity else "General",
            center_name=s.center.name if s.center else "Center",
            schedule_date=s.schedule_date,
            start_time=s.start_time,
            end_time=s.end_time,
            total_capacity_quintals=float(s.total_capacity_quintals),
            booked_capacity_quintals=float(s.booked_capacity_quintals),
            status=s.status,
            slots=slots_out
        ))
    return results

@router.post("/schedules")
def admin_create_schedule(
    req: ScheduleCreate,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Admin endpoint: creates a procurement schedule for any center"""
    if not req.center_id:
        raise HTTPException(status_code=400, detail="center_id is required for admin schedule creation")

    center = db.query(ProcurementCenter).filter(ProcurementCenter.id == req.center_id).first()
    if not center:
        raise HTTPException(status_code=404, detail="Procurement center not found")

    commodity = db.query(Commodity).filter(Commodity.id == req.commodity_id).first()
    if not commodity:
        raise HTTPException(status_code=404, detail="Commodity not found")

    sched = ProcurementSchedule(
        center_id=req.center_id,
        commodity_id=req.commodity_id,
        schedule_date=req.schedule_date,
        start_time=_parse_time(req.start_time),
        end_time=_parse_time(req.end_time),
        total_capacity_quintals=req.total_capacity_quintals,
        status="ACTIVE"
    )
    db.add(sched)
    db.flush()

    slot_names = req.slot_names or [
        "Morning Slot 1 (08:30 - 10:30)",
        "Morning Slot 2 (10:30 - 12:30)",
        "Afternoon Slot (13:00 - 15:30)"
    ]
    for name in slot_names:
        slot = TimeSlot(
            schedule_id=sched.id,
            slot_name=name,
            start_time=sched.start_time,
            end_time=sched.end_time,
            max_tokens=req.tokens_per_slot,
            booked_tokens=0,
            is_active=True
        )
        db.add(slot)

    db.commit()
    db.refresh(sched)
    return {
        "message": f"Schedule #{sched.id} created for {center.name} ({commodity.name})",
        "schedule_id": sched.id
    }

@router.put("/schedules/{schedule_id}")
def admin_update_schedule(
    schedule_id: int,
    req: ScheduleUpdate,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Admin endpoint: updates any schedule statewide"""
    sched = db.query(ProcurementSchedule).filter(ProcurementSchedule.id == schedule_id).first()
    if not sched:
        raise HTTPException(status_code=404, detail="Schedule not found")

    if req.commodity_id is not None:
        sched.commodity_id = req.commodity_id
    if req.schedule_date is not None:
        sched.schedule_date = req.schedule_date
    if req.start_time is not None:
        sched.start_time = _parse_time(req.start_time)
    if req.end_time is not None:
        sched.end_time = _parse_time(req.end_time)
    if req.total_capacity_quintals is not None:
        sched.total_capacity_quintals = req.total_capacity_quintals
    if req.status is not None:
        valid_statuses = ["ACTIVE", "PAUSED", "FULL", "COMPLETED", "CANCELLED"]
        new_status = req.status.upper()
        if new_status not in valid_statuses:
            raise HTTPException(status_code=400, detail=f"Status must be one of {valid_statuses}")
        sched.status = new_status
        if new_status == "CANCELLED":
            for slot in sched.slots:
                slot.is_active = False

    db.commit()
    db.refresh(sched)
    return {"message": f"Schedule #{schedule_id} updated successfully", "status": sched.status}

@router.delete("/schedules/{schedule_id}")
def admin_delete_schedule(
    schedule_id: int,
    force: bool = False,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Admin endpoint: permanently deletes or cancels schedule"""
    sched = db.query(ProcurementSchedule).filter(ProcurementSchedule.id == schedule_id).first()
    if not sched:
        raise HTTPException(status_code=404, detail="Schedule not found")

    bookings_count = db.query(Booking).filter(Booking.schedule_id == sched.id).count()
    if bookings_count == 0 or force:
        db.delete(sched)
        db.commit()
        return {"message": f"Schedule #{schedule_id} deleted", "action": "DELETED"}
    else:
        sched.status = "CANCELLED"
        for slot in sched.slots:
            slot.is_active = False
        db.commit()
        return {
            "message": f"Schedule #{schedule_id} cancelled (active bookings: {bookings_count})",
            "action": "CANCELLED"
        }
