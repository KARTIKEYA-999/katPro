from datetime import datetime, date
from decimal import Decimal
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func
from backend.app.database import get_db
from backend.app.models import (
    User, Farmer, ProcurementCenter, Commodity, ProcurementSchedule,
    TimeSlot, Booking, Token, QueueEntry, ProcurementTransaction, Notification
)
from backend.app.schemas import (
    CenterOut, CommodityOut, ScheduleOut, TimeSlotOut, BookingCreate,
    DigitalTokenOut, FarmerActiveStatus, NotificationOut
)
from backend.app.auth import require_farmer
from backend.app.c_bridge import compute_queue_metrics_fast, generate_token_fast
from backend.app.websocket_manager import manager

router = APIRouter(prefix="/api/farmer", tags=["Farmer Module"])

@router.get("/profile")
def get_farmer_profile(current_user: User = Depends(require_farmer), db: Session = Depends(get_db)):
    """Retrieves authenticated farmer's comprehensive agricultural profile"""
    farmer = db.query(Farmer).filter(Farmer.user_id == current_user.id).first()
    if not farmer:
        raise HTTPException(status_code=404, detail="Farmer profile not found")

    return {
        "user_id": current_user.id,
        "farmer_id": farmer.id,
        "farmer_code": farmer.farmer_code,
        "full_name": current_user.full_name,
        "phone": current_user.phone,
        "email": current_user.email,
        "language_pref": current_user.language_pref,
        "profile_image_url": farmer.profile_image_url or current_user.profile_image_url,
        "village": farmer.village,
        "mandal": farmer.mandal,
        "district": farmer.district,
        "state": farmer.state,
        "land_size_acres": float(farmer.land_size_acres),
        "primary_crop": farmer.primary_crop,
        "bank_account_last4": farmer.bank_account_last4
    }

@router.put("/language")
def update_language_preference(
    lang: str,
    current_user: User = Depends(require_farmer),
    db: Session = Depends(get_db)
):
    """Updates preferred language (en, hi, te)"""
    if lang not in ["en", "hi", "te"]:
        raise HTTPException(status_code=400, detail="Supported languages: en, hi, te")
    current_user.language_pref = lang
    db.commit()
    return {"message": "Language preference updated", "language_pref": lang}

@router.get("/centers", response_model=List[CenterOut])
def get_procurement_centers(db: Session = Depends(get_db)):
    """Lists all available procurement centers and their current live status"""
    return db.query(ProcurementCenter).order_by(ProcurementCenter.id).all()

@router.get("/commodities", response_model=List[CommodityOut])
def get_commodities(db: Session = Depends(get_db)):
    """Lists government-notified commodities with Minimum Support Price (MSP)"""
    return db.query(Commodity).filter(Commodity.is_active == True).all()

@router.get("/schedules")
def get_procurement_schedules(
    center_id: Optional[int] = None,
    commodity_id: Optional[int] = None,
    target_date: Optional[date] = None,
    db: Session = Depends(get_db)
):
    """Searches active procurement schedules with slot availability"""
    query = db.query(ProcurementSchedule).filter(ProcurementSchedule.status == "ACTIVE")
    if center_id:
        query = query.filter(ProcurementSchedule.center_id == center_id)
    if commodity_id:
        query = query.filter(ProcurementSchedule.commodity_id == commodity_id)
    if target_date:
        query = query.filter(ProcurementSchedule.schedule_date >= target_date)
    else:
        query = query.filter(ProcurementSchedule.schedule_date >= date.today())

    schedules = query.order_by(ProcurementSchedule.schedule_date.asc()).all()

    results = []
    for s in schedules:
        slots = db.query(TimeSlot).filter(TimeSlot.schedule_id == s.id, TimeSlot.is_active == True).all()
        results.append({
            "id": s.id,
            "center_id": s.center_id,
            "center_name": s.center.name,
            "center_district": s.center.district,
            "commodity_id": s.commodity_id,
            "commodity_name": s.commodity.name,
            "msp_per_quintal": float(s.commodity.msp_per_quintal),
            "schedule_date": str(s.schedule_date),
            "start_time": s.start_time.strftime("%H:%M"),
            "end_time": s.end_time.strftime("%H:%M"),
            "total_capacity_quintals": float(s.total_capacity_quintals),
            "booked_capacity_quintals": float(s.booked_capacity_quintals),
            "available_capacity_quintals": float(s.total_capacity_quintals - s.booked_capacity_quintals),
            "status": s.status,
            "slots": [
                {
                    "id": slot.id,
                    "slot_name": slot.slot_name,
                    "start_time": slot.start_time.strftime("%H:%M"),
                    "end_time": slot.end_time.strftime("%H:%M"),
                    "max_tokens": slot.max_tokens,
                    "booked_tokens": slot.booked_tokens,
                    "available_tokens": slot.max_tokens - slot.booked_tokens,
                    "is_full": slot.booked_tokens >= slot.max_tokens
                }
                for slot in slots
            ]
        })
    return results

@router.post("/book", response_model=DigitalTokenOut)
async def book_procurement_slot(
    req: BookingCreate,
    current_user: User = Depends(require_farmer),
    db: Session = Depends(get_db)
):
    """
    Core Farmer Booking Workflow:
    1. Validates slot capacity and prevents duplicate active bookings
    2. Atomically reserves capacity
    3. Invokes C module to generate unique secure digital token (e.g. A024)
    4. Enters token into queue
    5. Dispatches real-time WebSocket event
    """
    farmer = db.query(Farmer).filter(Farmer.user_id == current_user.id).first()
    if not farmer:
        raise HTTPException(status_code=404, detail="Farmer record not found")

    # Check for existing active booking for this farmer
    existing_booking = db.query(Booking).join(Token).filter(
        Booking.farmer_id == farmer.id,
        Token.status.in_(["WAITING", "CALLED", "PROCESSING"])
    ).first()

    if existing_booking:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"You already have an active procurement token ({existing_booking.token.token_number}). Please complete or cancel it before creating a new booking."
        )

    # Validate slot
    slot = db.query(TimeSlot).filter(TimeSlot.id == req.slot_id, TimeSlot.schedule_id == req.schedule_id).first()
    if not slot or not slot.is_active:
        raise HTTPException(status_code=400, detail="Invalid time slot selected")

    if slot.booked_tokens >= slot.max_tokens:
        raise HTTPException(status_code=400, detail="No tokens available for this time slot. Please choose another slot.")

    schedule = db.query(ProcurementSchedule).filter(ProcurementSchedule.id == req.schedule_id).first()
    if not schedule or schedule.status != "ACTIVE":
        raise HTTPException(status_code=400, detail="Selected procurement schedule is no longer active")

    center = schedule.center

    # Determine sequence number for today's center schedule
    last_token = db.query(func.max(Token.sequence_number)).filter(
        Token.center_id == center.id,
        Token.schedule_id == schedule.id
    ).scalar()
    sequence_num = (last_token or 0) + 1

    # Call C module for fast, tamper-evident token generation!
    token_str = generate_token_fast("A", sequence_num, center.id)

    # Create Booking
    booking_ref = f"BK-{date.today().strftime('%Y%m%d')}-{farmer.id:03d}-{sequence_num:03d}"
    booking = Booking(
        booking_ref=booking_ref,
        farmer_id=farmer.id,
        schedule_id=schedule.id,
        slot_id=slot.id,
        commodity_id=req.commodity_id,
        estimated_quantity_quintals=Decimal(str(req.estimated_quantity_quintals)),
        vehicle_number=req.vehicle_number,
        status="CONFIRMED"
    )
    db.add(booking)
    db.flush()

    # Create Token
    token_obj = Token(
        token_number=token_str,
        booking_id=booking.id,
        center_id=center.id,
        schedule_id=schedule.id,
        sequence_number=sequence_num,
        session_prefix="A",
        checksum="OK",
        status="WAITING"
    )
    db.add(token_obj)
    db.flush()

    # Add to Queue
    queue_entry = QueueEntry(
        token_id=token_obj.id,
        center_id=center.id,
        queue_position=sequence_num,
        priority_score=Decimal("70.00"),
        status="IN_QUEUE"
    )
    db.add(queue_entry)

    # Increment slot booked count
    slot.booked_tokens += 1
    schedule.booked_capacity_quintals += Decimal(str(req.estimated_quantity_quintals))

    # Create confirmation notification
    notif = Notification(
        user_id=current_user.id,
        title=f"Token {token_str} Confirmed",
        message=f"Your procurement slot at {center.name} is booked for {schedule.schedule_date}. Digital Token: {token_str}.",
        notification_type="SCHEDULE"
    )
    db.add(notif)
    db.commit()

    # Calculate queue metrics using compiled C library
    metrics = compute_queue_metrics_fast(
        current_token_seq=center.current_token_seq,
        farmer_token_seq=sequence_num,
        total_tokens_today=sequence_num,
        avg_proc_seconds=center.avg_processing_seconds,
        active_counters=center.active_counters
    )

    current_token_str = f"A{center.current_token_seq:03d}" if center.current_token_seq > 0 else "None"

    # Broadcast real-time queue update via WebSocket
    await manager.broadcast_to_center(center.id, {
        "event": "NEW_TOKEN_BOOKED",
        "center_id": center.id,
        "token_number": token_str,
        "sequence_number": sequence_num,
        "timestamp": datetime.utcnow().isoformat()
    })

    return DigitalTokenOut(
        token_id=token_obj.id,
        token_number=token_str,
        booking_ref=booking_ref,
        center_id=center.id,
        center_name=center.name,
        center_address=center.address,
        commodity_name=schedule.commodity.name,
        msp_rate=float(schedule.commodity.msp_per_quintal),
        schedule_date=schedule.schedule_date,
        slot_name=slot.slot_name,
        sequence_number=sequence_num,
        current_token_seq=center.current_token_seq,
        current_token_str=current_token_str,
        farmers_ahead=metrics["farmers_ahead"],
        estimated_wait_minutes=metrics["estimated_wait_minutes"],
        is_farmer_turn=metrics["is_farmer_turn"],
        is_approaching=metrics["is_approaching"],
        status=token_obj.status,
        checksum=token_obj.checksum,
        issued_at=token_obj.issued_at
    )

@router.get("/active-token", response_model=FarmerActiveStatus)
def get_active_token_status(
    current_user: User = Depends(require_farmer),
    db: Session = Depends(get_db)
):
    """
    Live Queue Status for Farmer:
    Calculates exact live position, farmers ahead, and estimated wait using the C engine!
    """
    farmer = db.query(Farmer).filter(Farmer.user_id == current_user.id).first()
    if not farmer:
        return FarmerActiveStatus(has_active_token=False)

    token = db.query(Token).join(Booking).filter(
        Booking.farmer_id == farmer.id,
        Token.status.in_(["WAITING", "CALLED", "PROCESSING"])
    ).order_by(Token.id.desc()).first()

    if not token:
        return FarmerActiveStatus(has_active_token=False)

    center = token.center
    booking = token.booking
    schedule = booking.schedule

    # Total tokens issued today for center
    total_tokens_today = db.query(func.count(Token.id)).filter(
        Token.center_id == center.id,
        Token.schedule_id == schedule.id
    ).scalar() or 25

    # High-performance C calculation
    metrics = compute_queue_metrics_fast(
        current_token_seq=center.current_token_seq,
        farmer_token_seq=token.sequence_number,
        total_tokens_today=total_tokens_today,
        avg_proc_seconds=center.avg_processing_seconds,
        active_counters=center.active_counters
    )

    current_token_str = f"A{center.current_token_seq:03d}" if center.current_token_seq > 0 else "None"

    token_dto = DigitalTokenOut(
        token_id=token.id,
        token_number=token.token_number,
        booking_ref=booking.booking_ref,
        center_id=center.id,
        center_name=center.name,
        center_address=center.address,
        commodity_name=schedule.commodity.name,
        msp_rate=float(schedule.commodity.msp_per_quintal),
        schedule_date=schedule.schedule_date,
        slot_name=booking.slot.slot_name,
        sequence_number=token.sequence_number,
        current_token_seq=center.current_token_seq,
        current_token_str=current_token_str,
        farmers_ahead=metrics["farmers_ahead"],
        estimated_wait_minutes=metrics["estimated_wait_minutes"],
        is_farmer_turn=metrics["is_farmer_turn"],
        is_approaching=metrics["is_approaching"],
        status=token.status,
        checksum=token.checksum,
        issued_at=token.issued_at
    )

    return FarmerActiveStatus(
        has_active_token=True,
        token=token_dto,
        center_status=center.status
    )

@router.get("/history")
def get_farmer_history(
    current_user: User = Depends(require_farmer),
    db: Session = Depends(get_db)
):
    """Retrieves farmer's past procurement transactions, tokens, weights, and DBT status"""
    farmer = db.query(Farmer).filter(Farmer.user_id == current_user.id).first()
    if not farmer:
        return []

    bookings = db.query(Booking).filter(Booking.farmer_id == farmer.id).order_by(Booking.id.desc()).all()

    history = []
    for b in bookings:
        token = b.token
        txn = token.transaction if token else None
        history.append({
            "booking_id": b.id,
            "booking_ref": b.booking_ref,
            "date": str(b.schedule.schedule_date),
            "center_name": b.schedule.center.name,
            "commodity_name": b.commodity.name,
            "token_number": token.token_number if token else "N/A",
            "booking_status": b.status,
            "token_status": token.status if token else "N/A",
            "estimated_quantity_qtl": float(b.estimated_quantity_quintals),
            "transaction_ref": txn.transaction_ref if txn else None,
            "gross_weight_qtl": float(txn.gross_weight_qtl) if txn else None,
            "net_weight_qtl": float(txn.net_weight_qtl) if txn else None,
            "moisture_content_pct": float(txn.moisture_content_pct) if txn else None,
            "quality_grade": txn.quality_grade if txn else None,
            "msp_rate": float(txn.msp_rate) if txn else float(b.commodity.msp_per_quintal),
            "final_amount": float(txn.final_amount) if txn else None,
            "payment_status": txn.payment_status if txn else "PENDING"
        })
    return history

@router.get("/notifications", response_model=List[NotificationOut])
def get_farmer_notifications(
    current_user: User = Depends(require_farmer),
    db: Session = Depends(get_db)
):
    """Retrieves farmer's alerts and announcements"""
    return db.query(Notification).filter(Notification.user_id == current_user.id).order_by(Notification.id.desc()).all()

@router.put("/notifications/{notif_id}/read")
def mark_notification_read(
    notif_id: int,
    current_user: User = Depends(require_farmer),
    db: Session = Depends(get_db)
):
    """Marks a notification as read"""
    notif = db.query(Notification).filter(Notification.id == notif_id, Notification.user_id == current_user.id).first()
    if notif:
        notif.is_read = True
        db.commit()
    return {"message": "Notification marked as read"}
