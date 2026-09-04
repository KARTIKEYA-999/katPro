from datetime import date, time, datetime
from typing import Optional, List
from pydantic import BaseModel, Field, ConfigDict

# --- AUTH SCHEMAS ---
class UserLogin(BaseModel):
    username: str
    password: str
    role: Optional[str] = None

class UserRegister(BaseModel):
    username: str
    password: str
    role: str = Field(default="FARMER", description="FARMER, OFFICIAL, or ADMIN")
    full_name: str
    phone: str
    email: Optional[str] = None
    language_pref: str = "en"
    profile_image: Optional[str] = None
    # Farmer specific fields
    village: Optional[str] = "Kudakuda"
    mandal: Optional[str] = "Chivvemla"
    district: Optional[str] = "Suryapet"
    state: Optional[str] = "Telangana"
    land_size_acres: Optional[float] = 3.0
    primary_crop: Optional[str] = "Paddy / Rice (Grade-A)"
    bank_account_last4: Optional[str] = "1234"

class UserOut(BaseModel):
    id: int
    username: str
    role: str
    full_name: str
    phone: str
    email: Optional[str]
    language_pref: str
    profile_image_url: Optional[str] = None
    created_at: Optional[datetime]

    model_config = ConfigDict(from_attributes=True)

class AuthToken(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut

# --- PROCUREMENT CENTER SCHEMAS ---
class CenterOut(BaseModel):
    id: int
    center_code: str
    name: str
    district: str
    state: str
    address: str
    contact_phone: str
    working_hours_start: time
    working_hours_end: time
    daily_capacity_mt: float
    active_counters: int
    avg_processing_seconds: int
    current_token_seq: int
    status: str

    model_config = ConfigDict(from_attributes=True)

class CenterCreate(BaseModel):
    center_code: str
    name: str
    district: str
    state: str
    address: str
    contact_phone: str
    working_hours_start: str = "08:30:00"
    working_hours_end: str = "17:30:00"
    daily_capacity_mt: float = 100.0
    active_counters: int = 2
    avg_processing_seconds: int = 480

class CenterStatusUpdate(BaseModel):
    status: str = Field(..., description="OPEN, IN PROGRESS, PAUSED, DELAYED, COMPLETED, CLOSED")
    notes: Optional[str] = None

# --- COMMODITY SCHEMAS ---
class CommodityOut(BaseModel):
    id: int
    code: str
    name: str
    category: str
    msp_per_quintal: float
    moisture_limit_pct: float
    urgency_level: int
    is_active: bool

    model_config = ConfigDict(from_attributes=True)

# --- SCHEDULE & SLOT SCHEMAS ---
class TimeSlotOut(BaseModel):
    id: int
    slot_name: str
    start_time: time
    end_time: time
    max_tokens: int
    booked_tokens: int
    is_active: bool

    model_config = ConfigDict(from_attributes=True)

class ScheduleOut(BaseModel):
    id: int
    center_id: int
    commodity_id: int
    commodity_name: Optional[str] = None
    center_name: Optional[str] = None
    schedule_date: date
    start_time: time
    end_time: time
    total_capacity_quintals: float
    booked_capacity_quintals: float
    status: str
    slots: List[TimeSlotOut] = []

    model_config = ConfigDict(from_attributes=True)

class ScheduleCreate(BaseModel):
    center_id: Optional[int] = None
    commodity_id: int
    schedule_date: date
    start_time: str = "08:30:00"
    end_time: str = "17:30:00"
    total_capacity_quintals: float = 500.0
    slot_names: List[str] = ["Morning Slot 1 (08:30 - 10:30)", "Morning Slot 2 (10:30 - 12:30)", "Afternoon Slot (13:00 - 15:30)"]
    tokens_per_slot: int = 15

class ScheduleUpdate(BaseModel):
    commodity_id: Optional[int] = None
    schedule_date: Optional[date] = None
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    total_capacity_quintals: Optional[float] = None
    status: Optional[str] = None

# --- BOOKING & TOKEN SCHEMAS ---
class BookingCreate(BaseModel):
    schedule_id: int
    slot_id: int
    commodity_id: int
    estimated_quantity_quintals: float
    vehicle_number: Optional[str] = None

class DigitalTokenOut(BaseModel):
    token_id: int
    token_number: str
    booking_ref: str
    center_id: int
    center_name: str
    center_address: str
    commodity_name: str
    msp_rate: float
    schedule_date: date
    slot_name: str
    sequence_number: int
    current_token_seq: int
    current_token_str: str
    farmers_ahead: int
    estimated_wait_minutes: int
    is_farmer_turn: bool
    is_approaching: bool
    status: str
    checksum: Optional[str]
    issued_at: datetime

class FarmerActiveStatus(BaseModel):
    has_active_token: bool
    token: Optional[DigitalTokenOut] = None
    center_status: Optional[str] = None

# --- OFFICIAL ACTIONS ---
class CallNextRequest(BaseModel):
    center_id: int
    counter_number: int = 1

class CompleteTransactionRequest(BaseModel):
    token_id: int
    gross_weight_qtl: float
    tare_weight_qtl: float = 0.0
    moisture_content_pct: float
    quality_grade: str = "Grade-A"

class SkipTokenRequest(BaseModel):
    token_id: int
    reason: Optional[str] = "No-show / Farmer absent when called"

# --- ANNOUNCEMENTS & NOTIFICATIONS ---
class AnnouncementCreate(BaseModel):
    center_id: Optional[int] = None
    title: str
    message: str
    urgency: str = "NORMAL"

class AnnouncementOut(BaseModel):
    id: int
    center_id: Optional[int]
    title: str
    message: str
    urgency: str
    is_active: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

class NotificationOut(BaseModel):
    id: int
    title: str
    message: str
    notification_type: str
    is_read: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

# --- OPTIMIZATION SCHEMAS ---
class OptimizationRunRequest(BaseModel):
    center_id: int
    active_counters: int = 2
    operating_hours: int = 8
    target_max_wait_minutes: int = 45

class OptimizationRunResponse(BaseModel):
    center_id: int
    center_name: str
    average_wait_minutes: float
    peak_wait_minutes: float
    counter_utilization_pct: float
    recommended_counters: int
    peak_bottleneck_hour: int
    recommended_slot_capacity: int
    status_summary: str
