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
    if not tokens:
        tokens = db.query(Token).filter(
            Token.center_id == center.id
        ).all()

    total_today = len(tokens)
    waiting_count = sum(1 for t in tokens if t.status == "WAITING")
    processing_count = sum(1 for t in tokens if t.status == "PROCESSING")
    completed_count = sum(1 for t in tokens if t.status == "COMPLETED")
    skipped_count = sum(1 for t in tokens if t.status == "SKIPPED")

    current_token_obj = db.query(Token).filter(
        Token.center_id == center.id,
        Token.sequence_number == center.current_token_seq
    ).first()
    if current_token_obj:
        current_token_str = current_token_obj.token_number
    elif center.current_token_seq > 0:
        prefix = center.center_code[0] if center.center_code else "T"
        current_token_str = f"{prefix}{center.current_token_seq:03d}"
    else:
        current_token_str = "None"

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

    if not tokens:
        tokens = db.query(Token).filter(
            Token.center_id == center.id
        ).order_by(Token.sequence_number.asc()).all()

    queue_list = []
    for t in tokens:
        booking = t.booking
        farmer = booking.farmer
        farmer_user = farmer.user
        queue_list.append({
            "token_id": t.id,
            "token_number": t.token_number,
            "sequence_number": t.sequence_number,
            "farmer_name": farmer_user.full_name,
            "farmer_phone": farmer_user.phone,
            "farmer_code": farmer.farmer_code,
            "village": farmer.village,
            "bank_name": farmer.bank_name or "State Bank of India",
            "bank_account_number": farmer.bank_account_number or f"38291048{farmer.bank_account_last4 or '4821'}",
            "bank_ifsc_code": farmer.bank_ifsc_code or "SBIN0020112",
            "commodity": booking.commodity.name,
            "msp_rate": float(booking.commodity.msp_per_quintal),
            "estimated_quantity_qtl": float(booking.estimated_quantity_quintals),
            "vehicle_number": booking.vehicle_number or "N/A",
            "status": t.status,
            "slot_name": booking.slot.slot_name,
            "issued_at": t.issued_at.strftime("%H:%M:%S") if t.issued_at else None,
            "called_at": t.called_at.strftime("%H:%M:%S") if t.called_at else None
        })
    return queue_list

@router.get("/token-payment-details/{token_id}")
def get_token_payment_details(
    token_id: int,
    current_user: User = Depends(require_official),
    db: Session = Depends(get_db)
):
    """
    Retrieves farmer beneficiary and payment details for a specific token
    to prefill the Razorpay DBT disbursement modal.
    """
    center = get_official_center(current_user, db)
    token = db.query(Token).filter(Token.id == token_id, Token.center_id == center.id).first()
    if not token:
        raise HTTPException(status_code=404, detail="Token not found")

    booking = token.booking
    farmer = booking.farmer
    user = farmer.user
    commodity = booking.commodity

    acc_num = farmer.bank_account_number or f"38291048{farmer.bank_account_last4 or '4821'}"
    ifsc = farmer.bank_ifsc_code or "SBIN0020112"
    bank = farmer.bank_name or "State Bank of India"
    clean_phone = user.phone.replace("+91", "").strip() if user.phone else "farmer"

    txn = db.query(ProcurementTransaction).filter(ProcurementTransaction.token_id == token.id).first()

    return {
        "token_id": token.id,
        "token_number": token.token_number,
        "status": token.status,
        "farmer_id": farmer.id,
        "farmer_code": farmer.farmer_code,
        "farmer_name": user.full_name,
        "farmer_phone": user.phone or "+91 98480 11001",
        "bank_name": bank,
        "bank_account_number": txn.bank_account_number if txn and txn.bank_account_number else acc_num,
        "bank_ifsc_code": txn.bank_ifsc if txn and txn.bank_ifsc else ifsc,
        "upi_id": f"{clean_phone}@upi",
        "commodity_id": commodity.id,
        "commodity_name": commodity.name,
        "msp_rate": float(commodity.msp_per_quintal),
        "estimated_quantity_qtl": float(booking.estimated_quantity_quintals),
        "transaction_ref": txn.transaction_ref if txn else None,
        "payment_status": txn.payment_status if txn else None,
        "failure_reason": txn.failure_reason if txn else None
    }

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

    # Find next waiting token for this center
    next_token = db.query(Token).filter(
        Token.center_id == center.id,
        func.date(Token.issued_at) == date.today(),
        Token.status == "WAITING"
    ).order_by(Token.sequence_number.asc()).first()

    if not next_token:
        # Fallback to any active waiting tokens for this center
        next_token = db.query(Token).filter(
            Token.center_id == center.id,
            Token.status == "WAITING"
        ).order_by(Token.sequence_number.asc()).first()

    if not next_token:
        raise HTTPException(status_code=400, detail=f"No more farmers waiting in queue today for {center.name}.")

    # Update previous processing token if any for this center
    prev_processing = db.query(Token).filter(
        Token.center_id == center.id,
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
    Completes weighing, quality inspection, and records official procurement transaction
    with Razorpay dummy payment integration.
    Supports both SUCCESS and PAYMENT_FAILED statuses.
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

    is_success = (req.payment_status or "SUCCESS").upper() in ["SUCCESS", "COMPLETED", "DIRECT_BENEFIT_TRANSFER"]

    # Check if a transaction was already created for this token
    txn = db.query(ProcurementTransaction).filter(ProcurementTransaction.token_id == token.id).first()
    if txn:
        txn.gross_weight_qtl = req.gross_weight_qtl
        txn.tare_weight_qtl = req.tare_weight_qtl
        txn.net_weight_qtl = net_weight
        txn.moisture_content_pct = req.moisture_content_pct
        txn.quality_grade = req.quality_grade
        txn.msp_rate = msp_rate
        txn.final_amount = final_amount
        txn_ref = txn.transaction_ref
    else:
        base_ref = f"TXN-{date.today().strftime('%Y%m%d')}-{token.id:04d}"
        if db.query(ProcurementTransaction).filter(ProcurementTransaction.transaction_ref == base_ref).first():
            txn_ref = f"{base_ref}-{uuid.uuid4().hex[:4].upper()}"
        else:
            txn_ref = base_ref

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
            payment_status="PENDING",
            processed_by=current_user.official_profile.id if current_user.official_profile else None
        )
        db.add(txn)

    # Store bank details & method
    txn.bank_account_number = req.bank_account_number or booking.farmer.bank_account_number or f"38291048{booking.farmer.bank_account_last4 or '4821'}"
    txn.bank_ifsc = req.bank_ifsc or booking.farmer.bank_ifsc_code or "SBIN0020112"
    txn.payment_method = req.payment_method or "RAZORPAY_DBT"

    farmer_user_id = booking.farmer.user_id

    if is_success:
        payment_id = req.razorpay_payment_id or f"pay_dummy_rzp_{uuid.uuid4().hex[:10]}"
        order_id = req.razorpay_order_id or f"order_dbt_{token.id}_{int(datetime.utcnow().timestamp())}"

        txn.razorpay_payment_id = payment_id
        txn.razorpay_order_id = order_id
        txn.payment_status = "DIRECT_BENEFIT_TRANSFER"
        txn.failure_reason = None

        token.status = "COMPLETED"
        token.completed_at = datetime.utcnow()
        booking.status = "COMPLETED"

        if token.queue_entry:
            token.queue_entry.status = "SERVED"

        # Farmer DBT notification
        notif = Notification(
            user_id=farmer_user_id,
            title=f"DBT Disbursed via Razorpay: {txn_ref}",
            message=f"₹{final_amount:,.2f} disbursed for {net_weight} Qtl {commodity.name}. Razorpay Ref: {payment_id}. Account: {txn.bank_account_number}.",
            notification_type="SUCCESS"
        )
        db.add(notif)
        db.commit()

        # Broadcast completion update
        await manager.broadcast_to_center(center.id, {
            "event": "TRANSACTION_COMPLETED",
            "center_id": center.id,
            "token_id": token.id,
            "token_number": token.token_number,
            "txn_ref": txn_ref,
            "net_weight_qtl": net_weight,
            "final_amount": final_amount,
            "payment_status": "DIRECT_BENEFIT_TRANSFER",
            "razorpay_payment_id": payment_id
        })

        return {
            "success": True,
            "message": f"Procurement completed & Razorpay DBT disbursed for {token.token_number}",
            "token_status": "COMPLETED",
            "transaction_ref": txn_ref,
            "net_weight_qtl": net_weight,
            "final_amount": final_amount,
            "payment_status": "DIRECT_BENEFIT_TRANSFER",
            "razorpay_payment_id": payment_id
        }
    else:
        # Failure flow: Razorpay payment failed
        reason = req.failure_reason or "Razorpay DBT transfer failed: Bank authorization declined"
        txn.payment_status = "PAYMENT_FAILED"
        txn.failure_reason = reason
        txn.razorpay_payment_id = req.razorpay_payment_id

        token.status = "PAYMENT_FAILED"
        booking.status = "PAYMENT_FAILED"

        # Farmer alert notification
        notif = Notification(
            user_id=farmer_user_id,
            title=f"Payment Failed: Token {token.token_number}",
            message=f"Razorpay DBT transfer of ₹{final_amount:,.2f} failed ({reason}). Please visit center counter to re-attempt payment.",
            notification_type="ALERT"
        )
        db.add(notif)
        db.commit()

        # Broadcast failure update
        await manager.broadcast_to_center(center.id, {
            "event": "PAYMENT_FAILED",
            "center_id": center.id,
            "token_id": token.id,
            "token_number": token.token_number,
            "txn_ref": txn_ref,
            "final_amount": final_amount,
            "payment_status": "PAYMENT_FAILED",
            "reason": reason
        })

        return {
            "success": False,
            "message": f"Payment failed for token {token.token_number}: {reason}",
            "token_status": "PAYMENT_FAILED",
            "transaction_ref": txn_ref,
            "net_weight_qtl": net_weight,
            "final_amount": final_amount,
            "payment_status": "PAYMENT_FAILED",
            "reason": reason
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
    """Central Office: Lists farmers assigned to official's procurement center with optional search and status filter"""
    center = get_official_center(current_user, db)
    query = db.query(Farmer).join(User)

    # Strictly scope to the official's assigned procurement center
    query = query.filter(
        (Farmer.center_id == center.id) |
        (Farmer.center_id.is_(None) & (Farmer.district.ilike(f"%{center.district}%")))
    )

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
            center_id=f.center_id or center.id,
            center_name=f.center.name if f.center else center.name,
            center_code=f.center.center_code if f.center else center.center_code,
            full_name=f.user.full_name,
            phone=f.user.phone,
            email=f.user.email,
            village=f.village,
            mandal=f.mandal,
            district=f.district,
            state=f.state,
            land_size_acres=float(f.land_size_acres),
            land_area_acres=float(f.land_size_acres),
            aadhaar_number=f"XXXX-XXXX-{1000 + f.id:04d}",
            passbook_number=f.passbook_number or f"TS-PB-{f.id:04d}",
            primary_crop=f.primary_crop,
            bank_account_number=f.bank_account_number,
            bank_account_last4=f.bank_account_last4 or (f.bank_account_number[-4:] if f.bank_account_number else f"{1000 + f.id}"),
            bank_ifsc_code=f.bank_ifsc_code,
            bank_name=f.bank_name,
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
    """Central Office: Enrolls a new farmer into the system bound to the official's assigned center"""
    center = get_official_center(current_user, db)

    # Check if username or phone exists
    if db.query(User).filter(User.username == req.username).first():
        raise HTTPException(status_code=400, detail="Username is already registered")
    if db.query(User).filter(User.phone == req.phone).first():
        raise HTTPException(status_code=400, detail="Phone number is already registered")

    # Create base user account
    new_user = User(
        username=req.username,
        password_hash=get_password_hash(req.password),
        role="FARMER",
        full_name=req.full_name,
        phone=req.phone,
        email=req.email,
        is_active=True
    )
    db.add(new_user)
    db.flush()

    # Generate sequential farmer code
    farmer_code = f"FAR-TS-{new_user.id:03d}"
    farmer = Farmer(
        user_id=new_user.id,
        farmer_code=farmer_code,
        center_id=center.id,
        village=req.village,
        mandal=req.mandal,
        district=req.district if req.district else center.district,
        state=req.state if req.state else center.state,
        land_size_acres=req.land_area_acres if req.land_area_acres is not None else req.land_size_acres,
        primary_crop=req.primary_crop,
        passbook_number=req.passbook_number,
        bank_account_number=req.bank_account_number,
        bank_account_last4=req.bank_account_number[-4:] if req.bank_account_number else req.bank_account_last4,
        bank_ifsc_code=req.bank_ifsc_code,
        bank_name=req.bank_name,
        approval_status="PENDING", # Requires Admin approval before booking
        approval_remarks=None
    )
    db.add(farmer)
    db.commit()
    db.refresh(farmer)

    return FarmerDetailOut(
        id=farmer.id,
        user_id=new_user.id,
        username=new_user.username,
        farmer_code=farmer.farmer_code,
        center_id=center.id,
        center_name=center.name,
        center_code=center.center_code,
        full_name=new_user.full_name,
        phone=new_user.phone,
        email=new_user.email,
        village=farmer.village,
        mandal=farmer.mandal,
        district=farmer.district,
        state=farmer.state,
        land_size_acres=float(farmer.land_size_acres),
        land_area_acres=float(farmer.land_size_acres),
        aadhaar_number=f"XXXX-XXXX-{1000 + farmer.id:04d}",
        passbook_number=farmer.passbook_number or f"TS-PB-{farmer.id:04d}",
        primary_crop=farmer.primary_crop,
        bank_account_number=farmer.bank_account_number,
        bank_account_last4=farmer.bank_account_last4,
        bank_ifsc_code=farmer.bank_ifsc_code,
        bank_name=farmer.bank_name,
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
    """Central Office: Updates a farmer's demographic or land record (scoped to assigned center)"""
    center = get_official_center(current_user, db)
    farmer = db.query(Farmer).filter(Farmer.id == farmer_id).first()
    if not farmer:
        raise HTTPException(status_code=404, detail="Farmer not found")
    if farmer.center_id is not None and farmer.center_id != center.id:
        raise HTTPException(status_code=403, detail="Access denied. You can only update farmers belonging to your assigned procurement center.")
    user = farmer.user

    if req.full_name is not None and req.full_name.strip():
        user.full_name = req.full_name.strip()
    if req.phone is not None and req.phone.strip():
        new_phone = req.phone.strip()
        if new_phone != user.phone:
            conflict = db.query(User).filter(User.phone == new_phone, User.id != user.id).first()
            if conflict:
                raise HTTPException(status_code=400, detail=f"Phone number '{new_phone}' is already registered to another user.")
            user.phone = new_phone
    if req.email is not None:
        user.email = req.email.strip() if req.email.strip() else None
    if req.is_active is not None:
        user.is_active = req.is_active
    if req.password and req.password.strip():
        user.password_hash = get_password_hash(req.password.strip())

    if req.village is not None and req.village.strip():
        farmer.village = req.village.strip()
    if req.mandal is not None:
        farmer.mandal = req.mandal.strip() if req.mandal.strip() else None
    if req.district is not None and req.district.strip():
        farmer.district = req.district.strip()
    if req.state is not None and req.state.strip():
        farmer.state = req.state.strip()
    if req.land_area_acres is not None and req.land_area_acres > 0:
        farmer.land_size_acres = req.land_area_acres
    elif req.land_size_acres is not None and req.land_size_acres > 0:
        farmer.land_size_acres = req.land_size_acres
    if req.primary_crop is not None and req.primary_crop.strip():
        farmer.primary_crop = req.primary_crop.strip()
    if req.passbook_number is not None:
        farmer.passbook_number = req.passbook_number.strip() if req.passbook_number.strip() else None
    if req.bank_ifsc_code is not None:
        farmer.bank_ifsc_code = req.bank_ifsc_code.strip() if req.bank_ifsc_code.strip() else None
    if req.bank_name is not None:
        farmer.bank_name = req.bank_name.strip() if req.bank_name.strip() else None
    if req.bank_account_number is not None:
        clean_num = req.bank_account_number.strip()
        if clean_num and not clean_num.startswith("•"):
            farmer.bank_account_number = clean_num
            clean_digits = "".join(filter(str.isdigit, clean_num))
            if len(clean_digits) >= 4:
                farmer.bank_account_last4 = clean_digits[-4:]
    elif req.bank_account_last4 is not None and req.bank_account_last4.strip():
        farmer.bank_account_last4 = req.bank_account_last4.strip()[-4:]

    db.commit()
    db.refresh(farmer)
    db.refresh(user)

    return FarmerDetailOut(
        id=farmer.id,
        user_id=user.id,
        username=user.username,
        farmer_code=farmer.farmer_code,
        center_id=farmer.center_id or center.id,
        center_name=farmer.center.name if farmer.center else center.name,
        center_code=farmer.center.center_code if farmer.center else center.center_code,
        full_name=user.full_name,
        phone=user.phone,
        email=user.email,
        village=farmer.village,
        mandal=farmer.mandal,
        district=farmer.district,
        state=farmer.state,
        land_size_acres=float(farmer.land_size_acres),
        land_area_acres=float(farmer.land_size_acres),
        aadhaar_number=f"XXXX-XXXX-{1000 + farmer.id:04d}",
        passbook_number=farmer.passbook_number or f"TS-PB-{farmer.id:04d}",
        primary_crop=farmer.primary_crop,
        bank_account_number=farmer.bank_account_number,
        bank_account_last4=farmer.bank_account_last4,
        bank_ifsc_code=farmer.bank_ifsc_code,
        bank_name=farmer.bank_name,
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
    """Central Office: Deletes a farmer record from the registry (scoped to assigned center)"""
    center = get_official_center(current_user, db)
    farmer = db.query(Farmer).filter(Farmer.id == farmer_id).first()
    if not farmer:
        raise HTTPException(status_code=404, detail="Farmer not found")
    if farmer.center_id is not None and farmer.center_id != center.id:
        raise HTTPException(status_code=403, detail="Access denied. You can only delete farmers belonging to your assigned procurement center.")
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
    center = get_official_center(current_user, db)
    farmer = db.query(Farmer).filter(Farmer.id == farmer_id).first()
    if not farmer:
        raise HTTPException(status_code=404, detail="Farmer not found")
    if farmer.center_id is not None and farmer.center_id != center.id:
        raise HTTPException(status_code=403, detail="Access denied. You can only view certificates for farmers belonging to your assigned procurement center.")
    user = farmer.user
    official = db.query(Official).filter(Official.user_id == current_user.id).first()

    center_name = center.name
    center_code = center.center_code

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

