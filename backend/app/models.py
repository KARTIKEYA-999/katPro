from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, Text, Numeric, Boolean,
    Time, Date, DateTime, ForeignKey
)
from sqlalchemy.orm import relationship
from backend.app.database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(64), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    role = Column(String(32), nullable=False, index=True) # FARMER, OFFICIAL, ADMIN
    full_name = Column(String(128), nullable=False)
    phone = Column(String(20), unique=True, nullable=False, index=True)
    email = Column(String(128), nullable=True)
    language_pref = Column(String(10), nullable=False, default="en")
    is_active = Column(Boolean, nullable=False, default=True)
    profile_image_url = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)

    farmer_profile = relationship("Farmer", back_populates="user", uselist=False, cascade="all, delete-orphan")
    official_profile = relationship("Official", back_populates="user", uselist=False, cascade="all, delete-orphan")
    admin_profile = relationship("Administrator", back_populates="user", uselist=False, cascade="all, delete-orphan")
    notifications = relationship("Notification", back_populates="user", cascade="all, delete-orphan")


class ProcurementCenter(Base):
    __tablename__ = "procurement_centers"

    id = Column(Integer, primary_key=True, index=True)
    center_code = Column(String(32), unique=True, nullable=False)
    name = Column(String(128), nullable=False)
    district = Column(String(64), nullable=False, index=True)
    state = Column(String(64), nullable=False)
    address = Column(Text, nullable=False)
    contact_phone = Column(String(20), nullable=False)
    working_hours_start = Column(Time, nullable=False)
    working_hours_end = Column(Time, nullable=False)
    daily_capacity_mt = Column(Numeric(10, 2), nullable=False, default=100.00)
    active_counters = Column(Integer, nullable=False, default=2)
    avg_processing_seconds = Column(Integer, nullable=False, default=480)
    current_token_seq = Column(Integer, nullable=False, default=0)
    status = Column(String(32), nullable=False, default="OPEN", index=True) # OPEN, IN PROGRESS, PAUSED, DELAYED, COMPLETED, CLOSED
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)

    officials = relationship("Official", back_populates="center")
    schedules = relationship("ProcurementSchedule", back_populates="center")
    tokens = relationship("Token", back_populates="center")
    announcements = relationship("Announcement", back_populates="center")


class Farmer(Base):
    __tablename__ = "farmers"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False)
    farmer_code = Column(String(32), unique=True, nullable=False)
    village = Column(String(64), nullable=False)
    mandal = Column(String(64), nullable=True)
    district = Column(String(64), nullable=False, index=True)
    state = Column(String(64), nullable=False)
    land_size_acres = Column(Numeric(6, 2), nullable=False, default=2.50)
    primary_crop = Column(String(64), nullable=False, default="Paddy")
    bank_account_last4 = Column(String(4), nullable=True)
    profile_image_url = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)

    user = relationship("User", back_populates="farmer_profile")
    bookings = relationship("Booking", back_populates="farmer")


class Official(Base):
    __tablename__ = "officials"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False)
    center_id = Column(Integer, ForeignKey("procurement_centers.id", ondelete="CASCADE"), nullable=False, index=True)
    employee_code = Column(String(32), unique=True, nullable=False)
    designation = Column(String(64), nullable=False, default="Procurement Officer")
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)

    user = relationship("User", back_populates="official_profile")
    center = relationship("ProcurementCenter", back_populates="officials")


class Administrator(Base):
    __tablename__ = "administrators"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False)
    admin_code = Column(String(32), unique=True, nullable=False)
    department = Column(String(64), nullable=False, default="Civil Supplies")
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)

    user = relationship("User", back_populates="admin_profile")


class Commodity(Base):
    __tablename__ = "commodities"

    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(32), unique=True, nullable=False)
    name = Column(String(64), nullable=False)
    category = Column(String(32), nullable=False, default="Cereal")
    msp_per_quintal = Column(Numeric(10, 2), nullable=False)
    moisture_limit_pct = Column(Numeric(4, 2), nullable=False, default=17.00)
    urgency_level = Column(Integer, nullable=False, default=1)
    is_active = Column(Boolean, nullable=False, default=True)


class CenterCommodity(Base):
    __tablename__ = "center_commodities"

    id = Column(Integer, primary_key=True, index=True)
    center_id = Column(Integer, ForeignKey("procurement_centers.id", ondelete="CASCADE"), nullable=False)
    commodity_id = Column(Integer, ForeignKey("commodities.id", ondelete="CASCADE"), nullable=False)
    daily_quota_mt = Column(Numeric(10, 2), nullable=False, default=50.00)
    is_active = Column(Boolean, nullable=False, default=True)


class ProcurementSchedule(Base):
    __tablename__ = "procurement_schedules"

    id = Column(Integer, primary_key=True, index=True)
    center_id = Column(Integer, ForeignKey("procurement_centers.id", ondelete="CASCADE"), nullable=False)
    commodity_id = Column(Integer, ForeignKey("commodities.id", ondelete="CASCADE"), nullable=False)
    schedule_date = Column(Date, nullable=False)
    start_time = Column(Time, nullable=False)
    end_time = Column(Time, nullable=False)
    total_capacity_quintals = Column(Numeric(10, 2), nullable=False, default=500.00)
    booked_capacity_quintals = Column(Numeric(10, 2), nullable=False, default=0.00)
    status = Column(String(32), nullable=False, default="ACTIVE") # ACTIVE, PAUSED, FULL, COMPLETED

    center = relationship("ProcurementCenter", back_populates="schedules")
    commodity = relationship("Commodity")
    slots = relationship("TimeSlot", back_populates="schedule", cascade="all, delete-orphan")
    bookings = relationship("Booking", back_populates="schedule")


class TimeSlot(Base):
    __tablename__ = "time_slots"

    id = Column(Integer, primary_key=True, index=True)
    schedule_id = Column(Integer, ForeignKey("procurement_schedules.id", ondelete="CASCADE"), nullable=False)
    slot_name = Column(String(64), nullable=False)
    start_time = Column(Time, nullable=False)
    end_time = Column(Time, nullable=False)
    max_tokens = Column(Integer, nullable=False, default=15)
    booked_tokens = Column(Integer, nullable=False, default=0)
    is_active = Column(Boolean, nullable=False, default=True)

    schedule = relationship("ProcurementSchedule", back_populates="slots")
    bookings = relationship("Booking", back_populates="slot")


class Booking(Base):
    __tablename__ = "bookings"

    id = Column(Integer, primary_key=True, index=True)
    booking_ref = Column(String(32), unique=True, nullable=False)
    farmer_id = Column(Integer, ForeignKey("farmers.id", ondelete="CASCADE"), nullable=False)
    schedule_id = Column(Integer, ForeignKey("procurement_schedules.id", ondelete="CASCADE"), nullable=False)
    slot_id = Column(Integer, ForeignKey("time_slots.id", ondelete="CASCADE"), nullable=False)
    commodity_id = Column(Integer, ForeignKey("commodities.id", ondelete="CASCADE"), nullable=False)
    estimated_quantity_quintals = Column(Numeric(8, 2), nullable=False)
    vehicle_number = Column(String(32), nullable=True)
    status = Column(String(32), nullable=False, default="CONFIRMED") # CONFIRMED, CHECKED_IN, IN_PROGRESS, COMPLETED, CANCELLED, NO_SHOW
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)

    farmer = relationship("Farmer", back_populates="bookings")
    schedule = relationship("ProcurementSchedule", back_populates="bookings")
    slot = relationship("TimeSlot", back_populates="bookings")
    commodity = relationship("Commodity")
    token = relationship("Token", back_populates="booking", uselist=False, cascade="all, delete-orphan")


class Token(Base):
    __tablename__ = "tokens"

    id = Column(Integer, primary_key=True, index=True)
    token_number = Column(String(16), nullable=False) # e.g. "A023"
    booking_id = Column(Integer, ForeignKey("bookings.id", ondelete="CASCADE"), unique=True, nullable=False)
    center_id = Column(Integer, ForeignKey("procurement_centers.id", ondelete="CASCADE"), nullable=False)
    schedule_id = Column(Integer, ForeignKey("procurement_schedules.id", ondelete="CASCADE"), nullable=False)
    sequence_number = Column(Integer, nullable=False)
    session_prefix = Column(String(1), nullable=False, default="A")
    checksum = Column(String(8), nullable=True)
    status = Column(String(32), nullable=False, default="WAITING") # WAITING, CALLED, PROCESSING, COMPLETED, SKIPPED
    issued_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    called_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)

    booking = relationship("Booking", back_populates="token")
    center = relationship("ProcurementCenter", back_populates="tokens")
    queue_entry = relationship("QueueEntry", back_populates="token", uselist=False, cascade="all, delete-orphan")
    transaction = relationship("ProcurementTransaction", back_populates="token", uselist=False)


class QueueEntry(Base):
    __tablename__ = "queue_entries"

    id = Column(Integer, primary_key=True, index=True)
    token_id = Column(Integer, ForeignKey("tokens.id", ondelete="CASCADE"), unique=True, nullable=False)
    center_id = Column(Integer, ForeignKey("procurement_centers.id", ondelete="CASCADE"), nullable=False)
    queue_position = Column(Integer, nullable=False, default=1)
    priority_score = Column(Numeric(8, 2), nullable=False, default=0.00)
    status = Column(String(32), nullable=False, default="IN_QUEUE")
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)

    token = relationship("Token", back_populates="queue_entry")


class ProcurementTransaction(Base):
    __tablename__ = "procurement_transactions"

    id = Column(Integer, primary_key=True, index=True)
    transaction_ref = Column(String(32), unique=True, nullable=False)
    booking_id = Column(Integer, ForeignKey("bookings.id", ondelete="RESTRICT"), nullable=False)
    token_id = Column(Integer, ForeignKey("tokens.id", ondelete="RESTRICT"), nullable=False)
    center_id = Column(Integer, ForeignKey("procurement_centers.id", ondelete="RESTRICT"), nullable=False)
    gross_weight_qtl = Column(Numeric(8, 2), nullable=False)
    tare_weight_qtl = Column(Numeric(8, 2), nullable=False, default=0.00)
    net_weight_qtl = Column(Numeric(8, 2), nullable=False)
    moisture_content_pct = Column(Numeric(4, 2), nullable=False)
    quality_grade = Column(String(16), nullable=False, default="Grade-A")
    msp_rate = Column(Numeric(10, 2), nullable=False)
    final_amount = Column(Numeric(12, 2), nullable=False)
    payment_status = Column(String(32), nullable=False, default="PROCESSED") # PENDING, PROCESSED, DIRECT_BENEFIT_TRANSFER
    processed_by = Column(Integer, ForeignKey("officials.id"), nullable=True)
    processed_at = Column(DateTime(timezone=True), default=datetime.utcnow)

    token = relationship("Token", back_populates="transaction")


class Notification(Base):
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    title = Column(String(128), nullable=False)
    message = Column(Text, nullable=False)
    notification_type = Column(String(32), nullable=False, default="INFO")
    is_read = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)

    user = relationship("User", back_populates="notifications")


class Announcement(Base):
    __tablename__ = "announcements"

    id = Column(Integer, primary_key=True, index=True)
    center_id = Column(Integer, ForeignKey("procurement_centers.id", ondelete="CASCADE"), nullable=True)
    official_id = Column(Integer, ForeignKey("officials.id", ondelete="SET NULL"), nullable=True)
    title = Column(String(128), nullable=False)
    message = Column(Text, nullable=False)
    urgency = Column(String(32), nullable=False, default="NORMAL") # NORMAL, HIGH, EMERGENCY
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)

    center = relationship("ProcurementCenter", back_populates="announcements")


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    action = Column(String(64), nullable=False)
    entity = Column(String(64), nullable=False)
    entity_id = Column(Integer, nullable=True)
    details = Column(Text, nullable=True)
    ip_address = Column(String(45), nullable=True)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
