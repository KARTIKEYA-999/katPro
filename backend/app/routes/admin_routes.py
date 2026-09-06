from datetime import date, datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func
from backend.app.database import get_db
from backend.app.models import (
    User, Farmer, Official, ProcurementCenter, Commodity,
    ProcurementSchedule, TimeSlot, Booking, Token, ProcurementTransaction, AuditLog,
    Notification
)
from backend.app.schemas import (
    CenterOut, CenterCreate, OptimizationRunRequest, OptimizationRunResponse,
    ScheduleCreate, ScheduleUpdate, ScheduleOut, TimeSlotOut, CommodityOut,
    OfficialCreate, OfficialUpdate, OfficialDetailOut, FarmerDetailOut, FarmerApprovalAction
)
from backend.app.auth import require_admin, get_password_hash
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

# --- CENTRAL OFFICE (OFFICIAL) USER MANAGEMENT ---

@router.get("/officials", response_model=List[OfficialDetailOut])
def get_admin_officials(
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Admin: Lists all Central Office officials with center details"""
    officials = db.query(Official).join(User).order_by(Official.id.asc()).all()
    res = []
    for off in officials:
        u = off.user
        res.append(OfficialDetailOut(
            id=off.id,
            user_id=u.id,
            username=u.username,
            full_name=u.full_name,
            phone=u.phone,
            email=u.email,
            center_id=off.center_id,
            center_name=off.center.name if off.center else None,
            center_code=off.center.center_code if off.center else None,
            employee_code=off.employee_code,
            designation=off.designation,
            is_active=u.is_active,
            created_at=u.created_at
        ))
    return res

@router.post("/officials", response_model=OfficialDetailOut, status_code=status.HTTP_201_CREATED)
def create_admin_official(
    req: OfficialCreate,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Admin: Creates a new Central Office user linked to a procurement center"""
    if db.query(User).filter(User.username == req.username).first():
        raise HTTPException(status_code=400, detail="Username already registered")
    if db.query(User).filter(User.phone == req.phone).first():
        raise HTTPException(status_code=400, detail="Phone number already registered")

    center = db.query(ProcurementCenter).filter(ProcurementCenter.id == req.center_id).first()
    if not center:
        raise HTTPException(status_code=404, detail="Selected procurement center not found")

    new_user = User(
        username=req.username,
        password_hash=get_password_hash(req.password),
        role="OFFICIAL",
        full_name=req.full_name,
        phone=req.phone,
        email=req.email,
        language_pref="en",
        is_active=True
    )
    db.add(new_user)
    db.flush()

    emp_code = req.employee_code or f"OFF-{center.center_code.split('-')[-1]}-{new_user.id:03d}"
    official = Official(
        user_id=new_user.id,
        center_id=center.id,
        employee_code=emp_code,
        designation=req.designation or "Procurement Officer"
    )
    db.add(official)
    db.commit()
    db.refresh(official)

    return OfficialDetailOut(
        id=official.id,
        user_id=new_user.id,
        username=new_user.username,
        full_name=new_user.full_name,
        phone=new_user.phone,
        email=new_user.email,
        center_id=center.id,
        center_name=center.name,
        center_code=center.center_code,
        employee_code=official.employee_code,
        designation=official.designation,
        is_active=new_user.is_active,
        created_at=new_user.created_at
    )

@router.put("/officials/{official_id}", response_model=OfficialDetailOut)
def update_admin_official(
    official_id: int,
    req: OfficialUpdate,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Admin: Updates an existing Central Office official's profile or center assignment"""
    official = db.query(Official).filter(Official.id == official_id).first()
    if not official:
        raise HTTPException(status_code=404, detail="Official not found")
    user = official.user

    if req.center_id is not None:
        center = db.query(ProcurementCenter).filter(ProcurementCenter.id == req.center_id).first()
        if not center:
            raise HTTPException(status_code=404, detail="Selected procurement center not found")
        official.center_id = center.id

    if req.designation is not None:
        official.designation = req.designation
    if req.employee_code is not None:
        official.employee_code = req.employee_code

    if req.full_name is not None:
        user.full_name = req.full_name
    if req.phone is not None:
        user.phone = req.phone
    if req.email is not None:
        user.email = req.email
    if req.is_active is not None:
        user.is_active = req.is_active
    if req.password and req.password.strip():
        user.password_hash = get_password_hash(req.password.strip())

    db.commit()
    db.refresh(official)

    return OfficialDetailOut(
        id=official.id,
        user_id=user.id,
        username=user.username,
        full_name=user.full_name,
        phone=user.phone,
        email=user.email,
        center_id=official.center_id,
        center_name=official.center.name if official.center else None,
        center_code=official.center.center_code if official.center else None,
        employee_code=official.employee_code,
        designation=official.designation,
        is_active=user.is_active,
        created_at=user.created_at
    )

@router.delete("/officials/{official_id}")
def delete_admin_official(
    official_id: int,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Admin: Deletes a Central Office official account"""
    official = db.query(Official).filter(Official.id == official_id).first()
    if not official:
        raise HTTPException(status_code=404, detail="Official not found")
    user = official.user
    username = user.username
    db.delete(official)
    db.delete(user)
    db.commit()
    return {"message": f"Central Office user {username} deleted successfully", "success": True}


# --- FARMER VERIFICATION & APPROVAL QUEUE ---

@router.get("/farmers", response_model=List[FarmerDetailOut])
def get_admin_farmers(
    approval_status: Optional[str] = None,
    search: Optional[str] = None,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Admin: Lists all registered farmers with verification and approval statuses"""
    query = db.query(Farmer).join(User)
    if approval_status and approval_status.upper() != "ALL":
        query = query.filter(Farmer.approval_status == approval_status.upper())
    if search and search.strip():
        term = f"%{search.strip()}%"
        query = query.filter(
            (User.full_name.ilike(term)) |
            (Farmer.farmer_code.ilike(term)) |
            (User.phone.ilike(term)) |
            (Farmer.village.ilike(term))
        )

    farmers = query.order_by(Farmer.created_at.desc()).all()
    return [
        FarmerDetailOut(
            id=f.id,
            user_id=f.user_id,
            username=f.user.username,
            farmer_code=f.farmer_code,
            full_name=f.user.full_name,
            phone=f.user.phone,
            email=f.user.email,
            village=f.village,
            mandal=f.mandal,
            district=f.district,
            state=f.state,
            land_size_acres=float(f.land_size_acres),
            primary_crop=f.primary_crop,
            bank_account_last4=f.bank_account_last4,
            profile_image_url=f.profile_image_url,
            approval_status=f.approval_status,
            approval_remarks=f.approval_remarks,
            approved_at=f.approved_at,
            created_at=f.created_at,
            is_active=f.user.is_active
        )
        for f in farmers
    ]

@router.put("/farmers/{farmer_id}/approve")
def approve_farmer_registration(
    farmer_id: int,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Admin: Approves a registered farmer and sends approval notification"""
    farmer = db.query(Farmer).filter(Farmer.id == farmer_id).first()
    if not farmer:
        raise HTTPException(status_code=404, detail="Farmer not found")

    farmer.approval_status = "APPROVED"
    farmer.approved_at = datetime.utcnow()
    farmer.approval_remarks = None

    # Dispatch notification to farmer
    notif = Notification(
        user_id=farmer.user_id,
        title="Farmer Registration Approved ✅",
        message="Congratulations! Your farmer account has been approved by the State Administrator. You are now authorized to book procurement slots and generate digital tokens.",
        notification_type="APPROVAL"
    )
    db.add(notif)
    db.commit()
    return {"message": f"Farmer {farmer.farmer_code} ({farmer.user.full_name}) approved successfully", "approval_status": "APPROVED"}

@router.put("/farmers/{farmer_id}/reject")
def reject_farmer_registration(
    farmer_id: int,
    req: FarmerApprovalAction,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Admin: Rejects a registered farmer with remarks and sends rejection notification"""
    farmer = db.query(Farmer).filter(Farmer.id == farmer_id).first()
    if not farmer:
        raise HTTPException(status_code=404, detail="Farmer not found")

    reason = req.remarks.strip() if req.remarks and req.remarks.strip() else "Land revenue or Aadhaar verification check did not match state records."
    farmer.approval_status = "REJECTED"
    farmer.approval_remarks = reason

    # Dispatch notification to farmer
    notif = Notification(
        user_id=farmer.user_id,
        title="Farmer Registration Rejected ❌",
        message=f"Your farmer account registration was rejected by the State Administrator. Reason: {reason}. Please contact your Mandi Central Office for verification.",
        notification_type="REJECTION"
    )
    db.add(notif)
    db.commit()
    return {"message": f"Farmer {farmer.farmer_code} rejected", "approval_status": "REJECTED", "remarks": reason}

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
