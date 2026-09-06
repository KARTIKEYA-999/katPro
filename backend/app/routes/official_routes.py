from datetime import datetime, date
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func
from backend.app.database import get_db
from backend.app.models import (
    User, Farmer, Official, ProcurementCenter, Commodity, ProcurementSchedule,
    TimeSlot, Booking, Token, QueueEntry, ProcurementTransaction, Announcement, Notification
)
from backend.app.schemas import (
    CallNextRequest, CompleteTransactionRequest, SkipTokenRequest,
    CenterStatusUpdate, AnnouncementCreate, ScheduleCreate, ScheduleUpdate,
    ScheduleOut, TimeSlotOut, CommodityOut,
    FarmerCreateByOfficial, FarmerUpdateByOfficial, FarmerDetailOut
)
from backend.app.auth import require_official, get_password_hash
from backend.app.c_bridge import compute_queue_metrics_fast
from backend.app.websocket_manager import manager

router = APIRouter(prefix="/api/official", tags=["Official Module"])

def get_official_center(current_user: User, db: Session) -> ProcurementCenter:
    official = db.query(Official).filter(Official.user_id == current_user.id).first()
    if not official:
        raise HTTPException(status_code=404, detail="Official profile not found")
    center = db.query(ProcurementCenter).filter(ProcurementCenter.id == official.center_id).first()
    if not center:
        raise HTTPException(status_code=404, detail="Assigned procurement center not found")
    return center

@router.get("/dashboard")
def get_official_dashboard(
    current_user: User = Depends(require_official),
    db: Session = Depends(get_db)
):
    """
    Official Dashboard Statistics:
    Displays today's total farmers, waiting count, completed count, active token,
    estimated backlog, and center operational status.
    """
    center = get_official_center(current_user, db)

    tokens = db.query(Token).filter(
        Token.center_id == center.id,
        func.date(Token.issued_at) == date.today()
    ).all()

    total_today = len(tokens)
    waiting_count = sum(1 for t in tokens if t.status == "WAITING")
    processing_count = sum(1 for t in tokens if t.status == "PROCESSING")
    completed_count = sum(1 for t in tokens if t.status == "COMPLETED")
    skipped_count = sum(1 for t in tokens if t.status == "SKIPPED")

    current_token_str = f"A{center.current_token_seq:03d}" if center.current_token_seq > 0 else "None"

    # Average wait time estimation for queue using C module parameters
    est_wait_min = 0
    if waiting_count > 0:
        est_wait_min = round((waiting_count * center.avg_processing_seconds) / (max(1, center.active_counters) * 60.0))

    return {
        "center_id": center.id,
        "center_code": center.center_code,
        "center_name": center.name,
        "district": center.district,
        "status": center.status,
        "active_counters": center.active_counters,
        "current_token_seq": center.current_token_seq,
        "current_token": current_token_str,
        "total_farmers_today": total_today,
        "waiting_farmers": waiting_count,
        "processing_farmers": processing_count,
        "completed_farmers": completed_count,
        "skipped_farmers": skipped_count,
        "estimated_avg_wait_minutes": est_wait_min,
        "working_hours": f"{center.working_hours_start.strftime('%H:%M')} - {center.working_hours_end.strftime('%H:%M')}"
    }

@router.get("/queue")
def get_official_queue(
    current_user: User = Depends(require_official),
    db: Session = Depends(get_db)
):
    """
    Retrieves full roster of today's tokens in ordered sequence with real-time status.
    """
    center = get_official_center(current_user, db)

    tokens = db.query(Token).filter(
        Token.center_id == center.id,
        func.date(Token.issued_at) == date.today()
    ).order_by(Token.sequence_number.asc()).all()

    queue_list = []
    for t in tokens:
        booking = t.booking
        farmer_user = booking.farmer.user
        queue_list.append({
            "token_id": t.id,
            "token_number": t.token_number,
            "sequence_number": t.sequence_number,
            "farmer_name": farmer_user.full_name,
            "farmer_phone": farmer_user.phone,
            "village": booking.farmer.village,
            "commodity": booking.commodity.name,
            "estimated_quantity_qtl": float(booking.estimated_quantity_quintals),
            "vehicle_number": booking.vehicle_number or "N/A",
            "status": t.status,
            "slot_name": booking.slot.slot_name,
            "issued_at": t.issued_at.strftime("%H:%M:%S") if t.issued_at else None,
            "called_at": t.called_at.strftime("%H:%M:%S") if t.called_at else None
        })
    return queue_list

@router.post("/call-next")
async def call_next_token(
    current_user: User = Depends(require_official),
    db: Session = Depends(get_db)
):
    """
    Official Calls Next Farmer:
    1. Finds the next WAITING token in sequence
    2. Updates center.current_token_seq
    3. Sets token status to PROCESSING
    4. Notifies the specific farmer via DB alert
    5. Broadcasts real-time WebSocket event so Farmer Dashboard updates instantly!
    """
    center = get_official_center(current_user, db)

    if center.status == "PAUSED":
        raise HTTPException(status_code=400, detail="Center queue is currently PAUSED. Please resume operations first.")

    # Find next waiting token
    next_token = db.query(Token).filter(
        Token.center_id == center.id,
        func.date(Token.issued_at) == date.today(),
        Token.status == "WAITING"
    ).order_by(Token.sequence_number.asc()).first()

    if not next_token:
        raise HTTPException(status_code=400, detail="No more farmers waiting in queue today.")

    # Update previous processing token if any
    prev_processing = db.query(Token).filter(
        Token.center_id == center.id,
        func.date(Token.issued_at) == date.today(),
        Token.status == "PROCESSING"
    ).all()
    for pt in prev_processing:
        pt.status = "COMPLETED"
        pt.completed_at = datetime.utcnow()

    # Advance center current token sequence
    center.current_token_seq = next_token.sequence_number
    next_token.status = "PROCESSING"
    next_token.called_at = datetime.utcnow()
    next_token.booking.status = "IN_PROGRESS"

    # Send high-priority alert to the called farmer
    farmer_user_id = next_token.booking.farmer.user_id
    notif = Notification(
        user_id=farmer_user_id,
        title=f"YOUR TURN HAS ARRIVED: Token {next_token.token_number}",
        message=f"Please proceed immediately to Weighbridge / Inspection Counter at {center.name}.",
        notification_type="TURN_ALERT"
    )
    db.add(notif)
    db.commit()

    token_str = next_token.token_number

    # Broadcast real-time WebSocket update to all farmers & officials
    await manager.broadcast_to_center(center.id, {
        "event": "TOKEN_ADVANCED",
        "center_id": center.id,
        "current_token_seq": center.current_token_seq,
        "current_token_number": token_str,
        "called_at": datetime.utcnow().isoformat(),
        "timestamp": datetime.utcnow().isoformat()
    })

    return {
        "message": f"Successfully called Token {token_str}",
        "current_token_seq": center.current_token_seq,
        "current_token_number": token_str,
        "farmer_name": next_token.booking.farmer.user.full_name
    }

@router.post("/complete-token")
async def complete_procurement_transaction(
    req: CompleteTransactionRequest,
    current_user: User = Depends(require_official),
    db: Session = Depends(get_db)
):
    """
    Completes weighing, quality inspection, and records official procurement transaction.
    """
    center = get_official_center(current_user, db)
    token = db.query(Token).filter(Token.id == req.token_id, Token.center_id == center.id).first()
    if not token:
        raise HTTPException(status_code=404, detail="Token not found")

    booking = token.booking
    commodity = booking.commodity

    net_weight = req.gross_weight_qtl - req.tare_weight_qtl
    if net_weight <= 0:
        raise HTTPException(status_code=400, detail="Net weight must be strictly positive")

    msp_rate = float(commodity.msp_per_quintal)
    final_amount = round(net_weight * msp_rate, 2)

    txn_ref = f"TXN-{date.today().strftime('%Y%m%d')}-{token.id:04d}"

    txn = ProcurementTransaction(
        transaction_ref=txn_ref,
        booking_id=booking.id,
        token_id=token.id,
        center_id=center.id,
        gross_weight_qtl=req.gross_weight_qtl,
        tare_weight_qtl=req.tare_weight_qtl,
        net_weight_qtl=net_weight,
        moisture_content_pct=req.moisture_content_pct,
        quality_grade=req.quality_grade,
        msp_rate=msp_rate,
        final_amount=final_amount,
        payment_status="DIRECT_BENEFIT_TRANSFER"
    )
    db.add(txn)

    token.status = "COMPLETED"
    token.completed_at = datetime.utcnow()
    booking.status = "COMPLETED"

    # Farmer DBT notification
    farmer_user_id = booking.farmer.user_id
    notif = Notification(
        user_id=farmer_user_id,
        title=f"Procurement Receipt: {txn_ref}",
        message=f"Net Weight: {net_weight} Qtl ({commodity.name}). Total Amount: Rs {final_amount:,.2f}. Dispatched for DBT transfer.",
        notification_type="SUCCESS"
    )
    db.add(notif)
    db.commit()

    # Broadcast completion update
    await manager.broadcast_to_center(center.id, {
        "event": "TRANSACTION_COMPLETED",
        "center_id": center.id,
        "token_number": token.token_number,
        "txn_ref": txn_ref,
        "net_weight_qtl": net_weight,
        "final_amount": final_amount
    })

    return {
        "message": f"Procurement completed for {token.token_number}",
        "transaction_ref": txn_ref,
        "net_weight_qtl": net_weight,
        "final_amount": final_amount,
        "payment_status": "DIRECT_BENEFIT_TRANSFER"
    }

@router.post("/skip-token")
async def skip_token(
    req: SkipTokenRequest,
    current_user: User = Depends(require_official),
    db: Session = Depends(get_db)
):
    """Marks farmer as No-Show / Skipped and advances queue"""
    center = get_official_center(current_user, db)
    token = db.query(Token).filter(Token.id == req.token_id, Token.center_id == center.id).first()
    if not token:
        raise HTTPException(status_code=404, detail="Token not found")

    token.status = "SKIPPED"
    token.booking.status = "NO_SHOW"
    db.commit()

    await manager.broadcast_to_center(center.id, {
        "event": "TOKEN_SKIPPED",
        "center_id": center.id,
        "token_number": token.token_number,
        "reason": req.reason
    })

    return {"message": f"Token {token.token_number} marked as skipped", "reason": req.reason}

@router.post("/update-center-status")
async def update_center_status(
    req: CenterStatusUpdate,
    current_user: User = Depends(require_official),
    db: Session = Depends(get_db)
):
    """
    Updates center procurement status (OPEN, PAUSED, DELAYED, COMPLETED, CLOSED).
    Broadcasts real-time notice to all farmers connected to this center.
    """
    center = get_official_center(current_user, db)
    center.status = req.status
    db.commit()

    # Broadcast real-time status change event
    await manager.broadcast_to_center(center.id, {
        "event": "CENTER_STATUS_CHANGED",
        "center_id": center.id,
        "center_name": center.name,
        "status": center.status,
        "notes": req.notes,
        "timestamp": datetime.utcnow().isoformat()
    })

    return {
        "message": f"Center status updated to {center.status}",
        "status": center.status
    }

@router.post("/announcements")
async def create_announcement(
    req: AnnouncementCreate,
    current_user: User = Depends(require_official),
    db: Session = Depends(get_db)
):
    """Broadcasts urgent announcement or instructions to farmers"""
    center = get_official_center(current_user, db)
    official = db.query(Official).filter(Official.user_id == current_user.id).first()

    ann = Announcement(
        center_id=center.id,
        official_id=official.id if official else None,
        title=req.title,
        message=req.message,
        urgency=req.urgency,
        is_active=True
    )
    db.add(ann)
    db.commit()

    await manager.broadcast_to_center(center.id, {
        "event": "ANNOUNCEMENT",
        "center_id": center.id,
        "title": req.title,
        "message": req.message,
        "urgency": req.urgency,
        "timestamp": datetime.utcnow().isoformat()
    })

    return {"message": "Announcement published successfully", "id": ann.id}

@router.get("/commodities", response_model=List[CommodityOut])
def get_official_commodities(db: Session = Depends(get_db)):
    """Lists government-notified commodities with Minimum Support Price (MSP) for schedule creation"""
    return db.query(Commodity).filter(Commodity.is_active == True).order_by(Commodity.name.asc()).all()

@router.get("/schedules", response_model=List[ScheduleOut])
@router.get("/schedule", response_model=List[ScheduleOut])
def get_official_schedules(
    schedule_date: Optional[date] = None,
    current_user: User = Depends(require_official),
    db: Session = Depends(get_db)
):
    """
    Retrieves all procurement schedules and their time slots for the official's assigned center.
    """
    center = get_official_center(current_user, db)
    query = db.query(ProcurementSchedule).filter(ProcurementSchedule.center_id == center.id)
    if schedule_date:
        query = query.filter(ProcurementSchedule.schedule_date == schedule_date)
    schedules = query.order_by(ProcurementSchedule.schedule_date.desc(), ProcurementSchedule.start_time.asc()).all()

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
@router.post("/schedule")
def create_schedule_forbidden():
    """Procurement schedules are managed exclusively by State Administrators."""
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Access denied. Procurement schedule creation is restricted to State Administrators only."
    )

@router.put("/schedules/{schedule_id}")
@router.put("/schedule/{schedule_id}")
def update_schedule_forbidden(schedule_id: int):
    """Procurement schedules are managed exclusively by State Administrators."""
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Access denied. Modifying procurement schedules is restricted to State Administrators only."
    )

@router.delete("/schedules/{schedule_id}")
@router.delete("/schedule/{schedule_id}")
def delete_schedule_forbidden(schedule_id: int):
    """Procurement schedules are managed exclusively by State Administrators."""
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Access denied. Deleting or canceling procurement schedules is restricted to State Administrators only."
    )

# --- CENTRAL OFFICE: FARMER MANAGEMENT & REGISTRATION REGISTRY ---

@router.get("/farmers", response_model=List[FarmerDetailOut])
def get_official_farmers(
    approval_status: Optional[str] = None,
    search: Optional[str] = None,
    current_user: User = Depends(require_official),
    db: Session = Depends(get_db)
):
    """Central Office: Lists farmers in registry with optional search and status filter"""
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
            land_area_acres=float(f.land_size_acres),
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

@router.post("/farmers", response_model=FarmerDetailOut, status_code=status.HTTP_201_CREATED)
def create_official_farmer(
    req: FarmerCreateByOfficial,
    current_user: User = Depends(require_official),
    db: Session = Depends(get_db)
):
    """Central Office: Enrolls a new farmer into the system (submitted for State Admin approval)"""
    if db.query(User).filter(User.username == req.username).first():
        raise HTTPException(status_code=400, detail="Username already registered")
    if db.query(User).filter(User.phone == req.phone).first():
        raise HTTPException(status_code=400, detail="Phone number already registered")

    new_user = User(
        username=req.username,
        password_hash=get_password_hash(req.password),
        role="FARMER",
        full_name=req.full_name,
        phone=req.phone,
        email=req.email,
        language_pref="te",
        is_active=True
    )
    db.add(new_user)
    db.flush()

    land_acres = req.land_area_acres if req.land_area_acres is not None else (req.land_size_acres or 3.0)
    bank_last4 = req.bank_account_last4
    if not bank_last4 and req.bank_account_number:
        bank_last4 = req.bank_account_number[-4:]

    farmer_code = f"FAR-TS-{new_user.id:03d}"
    farmer = Farmer(
        user_id=new_user.id,
        farmer_code=farmer_code,
        village=req.village,
        mandal=req.mandal or "Chivvemla",
        district=req.district,
        state=req.state,
        land_size_acres=land_acres,
        primary_crop=req.primary_crop,
        bank_account_last4=bank_last4 or "1234",
        approval_status="PENDING"
    )
    db.add(farmer)
    db.commit()
    db.refresh(farmer)

    return FarmerDetailOut(
        id=farmer.id,
        user_id=new_user.id,
        username=new_user.username,
        farmer_code=farmer.farmer_code,
        full_name=new_user.full_name,
        phone=new_user.phone,
        email=new_user.email,
        village=farmer.village,
        mandal=farmer.mandal,
        district=farmer.district,
        state=farmer.state,
        land_size_acres=float(farmer.land_size_acres),
        land_area_acres=float(farmer.land_size_acres),
        aadhaar_number=req.aadhaar_number,
        passbook_number=req.passbook_number,
        primary_crop=farmer.primary_crop,
        bank_account_last4=farmer.bank_account_last4,
        profile_image_url=farmer.profile_image_url,
        approval_status=farmer.approval_status,
        approval_remarks=farmer.approval_remarks,
        approved_at=farmer.approved_at,
        created_at=farmer.created_at,
        is_active=new_user.is_active
    )

@router.put("/farmers/{farmer_id}", response_model=FarmerDetailOut)
def update_official_farmer(
    farmer_id: int,
    req: FarmerUpdateByOfficial,
    current_user: User = Depends(require_official),
    db: Session = Depends(get_db)
):
    """Central Office: Updates a farmer's demographic or land record"""
    farmer = db.query(Farmer).filter(Farmer.id == farmer_id).first()
    if not farmer:
        raise HTTPException(status_code=404, detail="Farmer not found")
    user = farmer.user

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

    if req.village is not None:
        farmer.village = req.village
    if req.mandal is not None:
        farmer.mandal = req.mandal
    if req.district is not None:
        farmer.district = req.district
    if req.state is not None:
        farmer.state = req.state
    if req.land_area_acres is not None:
        farmer.land_size_acres = req.land_area_acres
    elif req.land_size_acres is not None:
        farmer.land_size_acres = req.land_size_acres
    if req.primary_crop is not None:
        farmer.primary_crop = req.primary_crop
    if req.bank_account_last4 is not None:
        farmer.bank_account_last4 = req.bank_account_last4
    elif req.bank_account_number:
        farmer.bank_account_last4 = req.bank_account_number[-4:]

    db.commit()
    db.refresh(farmer)

    return FarmerDetailOut(
        id=farmer.id,
        user_id=user.id,
        username=user.username,
        farmer_code=farmer.farmer_code,
        full_name=user.full_name,
        phone=user.phone,
        email=user.email,
        village=farmer.village,
        mandal=farmer.mandal,
        district=farmer.district,
        state=farmer.state,
        land_size_acres=float(farmer.land_size_acres),
        land_area_acres=float(farmer.land_size_acres),
        passbook_number=req.passbook_number,
        primary_crop=farmer.primary_crop,
        bank_account_last4=farmer.bank_account_last4,
        profile_image_url=farmer.profile_image_url,
        approval_status=farmer.approval_status,
        approval_remarks=farmer.approval_remarks,
        approved_at=farmer.approved_at,
        created_at=farmer.created_at,
        is_active=user.is_active
    )

@router.delete("/farmers/{farmer_id}")
def delete_official_farmer(
    farmer_id: int,
    current_user: User = Depends(require_official),
    db: Session = Depends(get_db)
):
    """Central Office: Deletes a farmer record from the registry"""
    farmer = db.query(Farmer).filter(Farmer.id == farmer_id).first()
    if not farmer:
        raise HTTPException(status_code=404, detail="Farmer not found")
    user = farmer.user
    code = farmer.farmer_code
    db.delete(farmer)
    db.delete(user)
    db.commit()
    return {"message": f"Farmer {code} removed from registry successfully", "success": True}

@router.get("/farmers/{farmer_id}/form-data")
def get_farmer_registration_form_data(
    farmer_id: int,
    current_user: User = Depends(require_official),
    db: Session = Depends(get_db)
):
    """Central Office: Fetches complete verifiable certificate data for printing the registration form"""
    farmer = db.query(Farmer).filter(Farmer.id == farmer_id).first()
    if not farmer:
        raise HTTPException(status_code=404, detail="Farmer not found")
    user = farmer.user
    official = db.query(Official).filter(Official.user_id == current_user.id).first()
    center = official.center if official else None

    center_name = center.name if center else "State Central Procurement Center"
    center_code = center.center_code if center else "CPC-01"

    return {
        "portal_name": "National Digital Agricultural Procurement System",
        "ministry": "Ministry of Consumer Affairs, Food & Public Distribution • Govt of India",
        "ps_id": "SIH 2026 PS ID: 26032",
        "certificate_id": f"CERT-{farmer.farmer_code}-{farmer.id:04d}",
        "farmer_code": farmer.farmer_code,
        "full_name": user.full_name,
        "username": user.username,
        "phone": user.phone,
        "email": user.email or "Not Provided",
        "aadhaar_last4": user.phone[-4:],
        "village": farmer.village,
        "mandal": farmer.mandal or "N/A",
        "district": farmer.district,
        "state": farmer.state,
        "land_size_acres": float(farmer.land_size_acres),
        "land_area_acres": float(farmer.land_size_acres),
        "passbook_number": f"TS-PB-{farmer.farmer_code}",
        "primary_crop": farmer.primary_crop,
        "bank_account_masked": f"XXXX-XXXX-{farmer.bank_account_last4 or '1234'}",
        "bank_account_number": farmer.bank_account_last4,
        "bank_ifsc_code": "SBIN0004567",
        "bank_name": "State Bank of India",
        "profile_image_url": farmer.profile_image_url,
        "approval_status": farmer.approval_status,
        "approval_remarks": farmer.approval_remarks,
        "approved_at": farmer.approved_at.strftime("%d-%b-%Y %H:%M") if farmer.approved_at else "Pending Administrator Verification",
        "registration_date": farmer.created_at.strftime("%d-%b-%Y"),
        "center_name": center_name,
        "center_code": center_code,
        "issuing_center": center_name,
        "issuing_officer": current_user.full_name,
        "officer_designation": official.designation if official else "Procurement Officer",
        "generated_at": datetime.utcnow().strftime("%d-%b-%Y %H:%M:%S UTC")
    }

