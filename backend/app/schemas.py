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
    aadhaar_number: Optional[str] = None
    village: Optional[str] = "Kudakuda"
    mandal: Optional[str] = "Chivvemla"
    district: Optional[str] = "Suryapet"
    state: Optional[str] = "Telangana"
    land_size_acres: Optional[float] = 3.0
    land_area_acres: Optional[float] = None
    passbook_number: Optional[str] = None
    primary_crop: Optional[str] = "Paddy / Rice (Grade-A)"
    bank_account_number: Optional[str] = None
    bank_account_last4: Optional[str] = "1234"
    bank_ifsc_code: Optional[str] = None
    bank_name: Optional[str] = None

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
    latitude: Optional[float] = None
    longitude: Optional[float] = None

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
    status: Optional[str] = "OPEN"
    latitude: Optional[float] = None
    longitude: Optional[float] = None

class CenterUpdate(BaseModel):
    center_code: Optional[str] = None
    name: Optional[str] = None
    district: Optional[str] = None
    state: Optional[str] = None
    address: Optional[str] = None
    contact_phone: Optional[str] = None
    working_hours_start: Optional[str] = None
    working_hours_end: Optional[str] = None
    daily_capacity_mt: Optional[float] = None
    active_counters: Optional[int] = None
    avg_processing_seconds: Optional[int] = None
    status: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None

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
    payment_status: Optional[str] = "SUCCESS"  # SUCCESS, PAYMENT_FAILED
    payment_method: Optional[str] = "RAZORPAY_DBT"
    razorpay_payment_id: Optional[str] = None
    razorpay_order_id: Optional[str] = None
    bank_account_number: Optional[str] = None
    bank_ifsc: Optional[str] = None
    upi_id: Optional[str] = None
    failure_reason: Optional[str] = None

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

# --- CENTRAL OFFICE OFFICIAL USER MANAGEMENT SCHEMAS ---
class OfficialCreate(BaseModel):
    username: str
    password: str
    full_name: str
    phone: str
    email: Optional[str] = None
    center_id: int
    designation: str = "Procurement Officer"
    employee_code: Optional[str] = None

class OfficialUpdate(BaseModel):
    full_name: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    center_id: Optional[int] = None
    designation: Optional[str] = None
    employee_code: Optional[str] = None
    password: Optional[str] = None
    is_active: Optional[bool] = None

class OfficialDetailOut(BaseModel):
    id: int
    user_id: int
    username: str
    full_name: str
    phone: str
    email: Optional[str] = None
    center_id: int
    center_name: Optional[str] = None
    center_code: Optional[str] = None
    employee_code: str
    designation: str
    is_active: bool
    created_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)

# --- FARMER MANAGEMENT & APPROVAL SCHEMAS ---
class FarmerCreateByOfficial(BaseModel):
    username: str
    password: str
    full_name: str
    phone: str
    email: Optional[str] = None
    village: str
    mandal: Optional[str] = "Chivvemla"
    district: str = "Suryapet"
    state: str = "Telangana"
    pincode: Optional[str] = None
    land_size_acres: Optional[float] = 3.0
    land_area_acres: Optional[float] = None
    passbook_number: Optional[str] = None
    aadhaar_number: Optional[str] = None
    primary_crop: str = "Paddy / Rice (Grade-A)"
    bank_account_number: Optional[str] = None
    bank_account_last4: Optional[str] = "1234"
    bank_ifsc_code: Optional[str] = None
    bank_name: Optional[str] = None
    center_id: Optional[int] = None
    profile_image: Optional[str] = None

class FarmerUpdateByOfficial(BaseModel):
    full_name: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    village: Optional[str] = None
    mandal: Optional[str] = None
    district: Optional[str] = None
    state: Optional[str] = None
    land_size_acres: Optional[float] = None
    land_area_acres: Optional[float] = None
    passbook_number: Optional[str] = None
    primary_crop: Optional[str] = None
    bank_account_number: Optional[str] = None
    bank_account_last4: Optional[str] = None
    bank_ifsc_code: Optional[str] = None
    bank_name: Optional[str] = None
    center_id: Optional[int] = None
    password: Optional[str] = None
    is_active: Optional[bool] = None

class FarmerDetailOut(BaseModel):
    id: int
    user_id: int
    username: str
    farmer_code: str
    full_name: str
    phone: str
    email: Optional[str] = None
    village: str
    mandal: Optional[str] = None
    district: str
    state: str
    land_size_acres: float
    land_area_acres: Optional[float] = None
    aadhaar_number: Optional[str] = None
    passbook_number: Optional[str] = None
    primary_crop: str
    bank_account_number: Optional[str] = None
    bank_account_last4: Optional[str] = None
    bank_ifsc_code: Optional[str] = None
    bank_name: Optional[str] = None
    center_id: Optional[int] = None
    center_name: Optional[str] = None
    center_code: Optional[str] = None
    profile_image_url: Optional[str] = None
    approval_status: str
    approval_remarks: Optional[str] = None
    approved_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    is_active: bool

    model_config = ConfigDict(from_attributes=True)

class FarmerApprovalAction(BaseModel):
    remarks: Optional[str] = None
