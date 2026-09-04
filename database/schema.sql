-- =============================================================================
-- SMART INDIA HACKATHON 2026 - PROBLEM STATEMENT PS ID: 26032
-- PROJECT: Digital System for Procurement Schedules, Farmer Queues and Real-Time Procurement Status
-- DATABASE SCHEMA SCRIPT: PostgreSQL 16
-- =============================================================================

-- Drop existing views and tables if rebuilding
DROP VIEW IF EXISTS v_procurement_center_analytics CASCADE;
DROP VIEW IF EXISTS v_farmer_turn_tracker CASCADE;
DROP VIEW IF EXISTS v_live_center_queue_status CASCADE;

DROP TABLE IF EXISTS audit_logs CASCADE;
DROP TABLE IF EXISTS announcements CASCADE;
DROP TABLE IF EXISTS notifications CASCADE;
DROP TABLE IF EXISTS procurement_transactions CASCADE;
DROP TABLE IF EXISTS queue_entries CASCADE;
DROP TABLE IF EXISTS tokens CASCADE;
DROP TABLE IF EXISTS bookings CASCADE;
DROP TABLE IF EXISTS time_slots CASCADE;
DROP TABLE IF EXISTS procurement_schedules CASCADE;
DROP TABLE IF EXISTS center_commodities CASCADE;
DROP TABLE IF EXISTS commodities CASCADE;
DROP TABLE IF EXISTS officials CASCADE;
DROP TABLE IF EXISTS administrators CASCADE;
DROP TABLE IF EXISTS farmers CASCADE;
DROP TABLE IF EXISTS procurement_centers CASCADE;
DROP TABLE IF EXISTS users CASCADE;

-- -----------------------------------------------------------------------------
-- 1. USERS & ROLES TABLE
-- -----------------------------------------------------------------------------
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(64) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    role VARCHAR(32) NOT NULL CHECK (role IN ('FARMER', 'OFFICIAL', 'ADMIN')),
    full_name VARCHAR(128) NOT NULL,
    phone VARCHAR(20) NOT NULL UNIQUE,
    email VARCHAR(128),
    language_pref VARCHAR(10) NOT NULL DEFAULT 'en' CHECK (language_pref IN ('en', 'hi', 'te')),
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_users_role ON users(role);
CREATE INDEX idx_users_phone ON users(phone);

-- -----------------------------------------------------------------------------
-- 2. PROCUREMENT CENTERS TABLE
-- -----------------------------------------------------------------------------
CREATE TABLE procurement_centers (
    id SERIAL PRIMARY KEY,
    center_code VARCHAR(32) NOT NULL UNIQUE,
    name VARCHAR(128) NOT NULL,
    district VARCHAR(64) NOT NULL,
    state VARCHAR(64) NOT NULL,
    address TEXT NOT NULL,
    contact_phone VARCHAR(20) NOT NULL,
    working_hours_start TIME NOT NULL DEFAULT '08:00:00',
    working_hours_end TIME NOT NULL DEFAULT '17:00:00',
    daily_capacity_mt NUMERIC(10, 2) NOT NULL DEFAULT 100.00 CHECK (daily_capacity_mt > 0),
    active_counters INTEGER NOT NULL DEFAULT 2 CHECK (active_counters >= 1),
    avg_processing_seconds INTEGER NOT NULL DEFAULT 480 CHECK (avg_processing_seconds >= 60),
    current_token_seq INTEGER NOT NULL DEFAULT 0,
    status VARCHAR(32) NOT NULL DEFAULT 'OPEN' CHECK (status IN ('OPEN', 'IN PROGRESS', 'PAUSED', 'DELAYED', 'COMPLETED', 'CLOSED')),
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_procurement_centers_district ON procurement_centers(district);
CREATE INDEX idx_procurement_centers_status ON procurement_centers(status);

-- -----------------------------------------------------------------------------
-- 3. FARMERS PROFILE TABLE
-- -----------------------------------------------------------------------------
CREATE TABLE farmers (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL UNIQUE REFERENCES users(id) ON DELETE CASCADE,
    farmer_code VARCHAR(32) NOT NULL UNIQUE,
    village VARCHAR(64) NOT NULL,
    mandal VARCHAR(64),
    district VARCHAR(64) NOT NULL,
    state VARCHAR(64) NOT NULL,
    land_size_acres NUMERIC(6, 2) NOT NULL DEFAULT 2.50 CHECK (land_size_acres >= 0),
    primary_crop VARCHAR(64) NOT NULL DEFAULT 'Paddy',
    bank_account_last4 VARCHAR(4),
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_farmers_district ON farmers(district);

-- -----------------------------------------------------------------------------
-- 4. OFFICIALS PROFILE TABLE
-- -----------------------------------------------------------------------------
CREATE TABLE officials (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL UNIQUE REFERENCES users(id) ON DELETE CASCADE,
    center_id INTEGER NOT NULL REFERENCES procurement_centers(id) ON DELETE CASCADE,
    employee_code VARCHAR(32) NOT NULL UNIQUE,
    designation VARCHAR(64) NOT NULL DEFAULT 'Procurement Officer',
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_officials_center ON officials(center_id);

-- -----------------------------------------------------------------------------
-- 5. ADMINISTRATORS PROFILE TABLE
-- -----------------------------------------------------------------------------
CREATE TABLE administrators (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL UNIQUE REFERENCES users(id) ON DELETE CASCADE,
    admin_code VARCHAR(32) NOT NULL UNIQUE,
    department VARCHAR(64) NOT NULL DEFAULT 'Civil Supplies & Agriculture',
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- -----------------------------------------------------------------------------
-- 6. COMMODITIES TABLE
-- -----------------------------------------------------------------------------
CREATE TABLE commodities (
    id SERIAL PRIMARY KEY,
    code VARCHAR(32) NOT NULL UNIQUE,
    name VARCHAR(64) NOT NULL,
    category VARCHAR(32) NOT NULL DEFAULT 'Cereal',
    msp_per_quintal NUMERIC(10, 2) NOT NULL CHECK (msp_per_quintal > 0),
    moisture_limit_pct NUMERIC(4, 2) NOT NULL DEFAULT 17.00,
    urgency_level INTEGER NOT NULL DEFAULT 1 CHECK (urgency_level BETWEEN 1 AND 3),
    is_active BOOLEAN NOT NULL DEFAULT TRUE
);

-- -----------------------------------------------------------------------------
-- 7. CENTER COMMODITIES MAPPING
-- -----------------------------------------------------------------------------
CREATE TABLE center_commodities (
    id SERIAL PRIMARY KEY,
    center_id INTEGER NOT NULL REFERENCES procurement_centers(id) ON DELETE CASCADE,
    commodity_id INTEGER NOT NULL REFERENCES commodities(id) ON DELETE CASCADE,
    daily_quota_mt NUMERIC(10, 2) NOT NULL DEFAULT 50.00,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    UNIQUE(center_id, commodity_id)
);

-- -----------------------------------------------------------------------------
-- 8. PROCUREMENT SCHEDULES TABLE
-- -----------------------------------------------------------------------------
CREATE TABLE procurement_schedules (
    id SERIAL PRIMARY KEY,
    center_id INTEGER NOT NULL REFERENCES procurement_centers(id) ON DELETE CASCADE,
    commodity_id INTEGER NOT NULL REFERENCES commodities(id) ON DELETE CASCADE,
    schedule_date DATE NOT NULL,
    start_time TIME NOT NULL DEFAULT '08:30:00',
    end_time TIME NOT NULL DEFAULT '16:30:00',
    total_capacity_quintals NUMERIC(10, 2) NOT NULL DEFAULT 500.00 CHECK (total_capacity_quintals > 0),
    booked_capacity_quintals NUMERIC(10, 2) NOT NULL DEFAULT 0.00 CHECK (booked_capacity_quintals >= 0),
    status VARCHAR(32) NOT NULL DEFAULT 'ACTIVE' CHECK (status IN ('ACTIVE', 'PAUSED', 'FULL', 'COMPLETED', 'CANCELLED')),
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(center_id, commodity_id, schedule_date)
);

CREATE INDEX idx_procurement_schedules_center_date ON procurement_schedules(center_id, schedule_date);

-- -----------------------------------------------------------------------------
-- 9. TIME SLOTS TABLE
-- -----------------------------------------------------------------------------
CREATE TABLE time_slots (
    id SERIAL PRIMARY KEY,
    schedule_id INTEGER NOT NULL REFERENCES procurement_schedules(id) ON DELETE CASCADE,
    slot_name VARCHAR(64) NOT NULL, -- e.g. "Morning Slot 1 (08:30 - 10:00)"
    start_time TIME NOT NULL,
    end_time TIME NOT NULL,
    max_tokens INTEGER NOT NULL DEFAULT 15 CHECK (max_tokens > 0),
    booked_tokens INTEGER NOT NULL DEFAULT 0 CHECK (booked_tokens >= 0),
    is_active BOOLEAN NOT NULL DEFAULT TRUE
);

CREATE INDEX idx_time_slots_schedule ON time_slots(schedule_id);

-- -----------------------------------------------------------------------------
-- 10. BOOKINGS TABLE
-- -----------------------------------------------------------------------------
CREATE TABLE bookings (
    id SERIAL PRIMARY KEY,
    booking_ref VARCHAR(32) NOT NULL UNIQUE,
    farmer_id INTEGER NOT NULL REFERENCES farmers(id) ON DELETE CASCADE,
    schedule_id INTEGER NOT NULL REFERENCES procurement_schedules(id) ON DELETE CASCADE,
    slot_id INTEGER NOT NULL REFERENCES time_slots(id) ON DELETE CASCADE,
    commodity_id INTEGER NOT NULL REFERENCES commodities(id) ON DELETE CASCADE,
    estimated_quantity_quintals NUMERIC(8, 2) NOT NULL CHECK (estimated_quantity_quintals > 0),
    vehicle_number VARCHAR(32),
    status VARCHAR(32) NOT NULL DEFAULT 'CONFIRMED' CHECK (status IN ('CONFIRMED', 'CHECKED_IN', 'IN_PROGRESS', 'COMPLETED', 'CANCELLED', 'NO_SHOW')),
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_bookings_farmer ON bookings(farmer_id);
CREATE INDEX idx_bookings_schedule ON bookings(schedule_id);
CREATE INDEX idx_bookings_status ON bookings(status);

-- -----------------------------------------------------------------------------
-- 11. TOKENS TABLE (Generated with C module assistance)
-- -----------------------------------------------------------------------------
CREATE TABLE tokens (
    id SERIAL PRIMARY KEY,
    token_number VARCHAR(16) NOT NULL, -- e.g. "A023"
    booking_id INTEGER NOT NULL UNIQUE REFERENCES bookings(id) ON DELETE CASCADE,
    center_id INTEGER NOT NULL REFERENCES procurement_centers(id) ON DELETE CASCADE,
    schedule_id INTEGER NOT NULL REFERENCES procurement_schedules(id) ON DELETE CASCADE,
    sequence_number INTEGER NOT NULL CHECK (sequence_number > 0),
    session_prefix CHAR(1) NOT NULL DEFAULT 'A',
    checksum VARCHAR(8),
    status VARCHAR(32) NOT NULL DEFAULT 'WAITING' CHECK (status IN ('WAITING', 'CALLED', 'PROCESSING', 'COMPLETED', 'SKIPPED', 'CANCELLED')),
    issued_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    called_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,
    UNIQUE(center_id, schedule_id, sequence_number)
);

CREATE INDEX idx_tokens_center_schedule_status ON tokens(center_id, schedule_id, status);
CREATE INDEX idx_tokens_sequence ON tokens(sequence_number);

-- -----------------------------------------------------------------------------
-- 12. QUEUE ENTRIES TABLE (Fast Lookup & State tracking)
-- -----------------------------------------------------------------------------
CREATE TABLE queue_entries (
    id SERIAL PRIMARY KEY,
    token_id INTEGER NOT NULL UNIQUE REFERENCES tokens(id) ON DELETE CASCADE,
    center_id INTEGER NOT NULL REFERENCES procurement_centers(id) ON DELETE CASCADE,
    queue_position INTEGER NOT NULL DEFAULT 1,
    priority_score NUMERIC(8, 2) NOT NULL DEFAULT 0.00,
    status VARCHAR(32) NOT NULL DEFAULT 'IN_QUEUE' CHECK (status IN ('IN_QUEUE', 'PROCESSING', 'SERVED', 'NO_SHOW')),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_queue_entries_center_pos ON queue_entries(center_id, queue_position);

-- -----------------------------------------------------------------------------
-- 13. PROCUREMENT TRANSACTIONS TABLE
-- -----------------------------------------------------------------------------
CREATE TABLE procurement_transactions (
    id SERIAL PRIMARY KEY,
    transaction_ref VARCHAR(32) NOT NULL UNIQUE,
    booking_id INTEGER NOT NULL REFERENCES bookings(id) ON DELETE RESTRICT,
    token_id INTEGER NOT NULL REFERENCES tokens(id) ON DELETE RESTRICT,
    center_id INTEGER NOT NULL REFERENCES procurement_centers(id) ON DELETE RESTRICT,
    gross_weight_qtl NUMERIC(8, 2) NOT NULL CHECK (gross_weight_qtl > 0),
    tare_weight_qtl NUMERIC(8, 2) NOT NULL DEFAULT 0.00 CHECK (tare_weight_qtl >= 0),
    net_weight_qtl NUMERIC(8, 2) NOT NULL CHECK (net_weight_qtl > 0),
    moisture_content_pct NUMERIC(4, 2) NOT NULL CHECK (moisture_content_pct >= 0),
    quality_grade VARCHAR(16) NOT NULL DEFAULT 'Grade-A' CHECK (quality_grade IN ('Grade-A', 'Grade-B', 'FAQ', 'Rejected')),
    msp_rate NUMERIC(10, 2) NOT NULL CHECK (msp_rate > 0),
    final_amount NUMERIC(12, 2) NOT NULL CHECK (final_amount >= 0),
    payment_status VARCHAR(32) NOT NULL DEFAULT 'PROCESSED' CHECK (payment_status IN ('PENDING', 'PROCESSED', 'DIRECT_BENEFIT_TRANSFER')),
    processed_by INTEGER REFERENCES officials(id),
    processed_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_transactions_center ON procurement_transactions(center_id);
CREATE INDEX idx_transactions_date ON procurement_transactions(processed_at);

-- -----------------------------------------------------------------------------
-- 14. NOTIFICATIONS TABLE
-- -----------------------------------------------------------------------------
CREATE TABLE notifications (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    title VARCHAR(128) NOT NULL,
    message TEXT NOT NULL,
    notification_type VARCHAR(32) NOT NULL DEFAULT 'INFO' CHECK (notification_type IN ('INFO', 'TURN_ALERT', 'SCHEDULE', 'DELAY', 'SUCCESS')),
    is_read BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_notifications_user_unread ON notifications(user_id, is_read);

-- -----------------------------------------------------------------------------
-- 15. ANNOUNCEMENTS TABLE
-- -----------------------------------------------------------------------------
CREATE TABLE announcements (
    id SERIAL PRIMARY KEY,
    center_id INTEGER REFERENCES procurement_centers(id) ON DELETE CASCADE,
    official_id INTEGER REFERENCES officials(id) ON DELETE SET NULL,
    title VARCHAR(128) NOT NULL,
    message TEXT NOT NULL,
    urgency VARCHAR(32) NOT NULL DEFAULT 'NORMAL' CHECK (urgency IN ('NORMAL', 'HIGH', 'EMERGENCY')),
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_announcements_center ON announcements(center_id, is_active);

-- -----------------------------------------------------------------------------
-- 16. AUDIT LOGS TABLE
-- -----------------------------------------------------------------------------
CREATE TABLE audit_logs (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
    action VARCHAR(64) NOT NULL,
    entity VARCHAR(64) NOT NULL,
    entity_id INTEGER,
    details TEXT,
    ip_address VARCHAR(45),
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_audit_logs_user ON audit_logs(user_id);
CREATE INDEX idx_audit_logs_created ON audit_logs(created_at);

-- =============================================================================
-- POSTGRESQL VIEWS FOR REAL-TIME REPORTING & MONITORING
-- =============================================================================

-- View 1: Real-time procurement center queue status
CREATE OR REPLACE VIEW v_live_center_queue_status AS
SELECT 
    pc.id AS center_id,
    pc.center_code,
    pc.name AS center_name,
    pc.district,
    pc.status AS center_status,
    pc.current_token_seq,
    pc.active_counters,
    pc.avg_processing_seconds,
    COUNT(t.id) FILTER (WHERE t.status = 'WAITING') AS waiting_farmers,
    COUNT(t.id) FILTER (WHERE t.status = 'PROCESSING') AS processing_farmers,
    COUNT(t.id) FILTER (WHERE t.status = 'COMPLETED') AS completed_farmers,
    COUNT(t.id) FILTER (WHERE t.status = 'SKIPPED') AS skipped_farmers,
    COUNT(t.id) AS total_tokens_today
FROM procurement_centers pc
LEFT JOIN tokens t ON t.center_id = pc.id AND DATE(t.issued_at) = CURRENT_DATE
GROUP BY pc.id, pc.center_code, pc.name, pc.district, pc.status, pc.current_token_seq, pc.active_counters, pc.avg_processing_seconds;

-- View 2: Farmer turn tracker view (Calculates queue metrics directly in SQL)
CREATE OR REPLACE VIEW v_farmer_turn_tracker AS
SELECT 
    t.id AS token_id,
    t.token_number,
    t.sequence_number,
    t.status AS token_status,
    f.id AS farmer_id,
    u.id AS user_id,
    u.full_name AS farmer_name,
    u.phone AS farmer_phone,
    b.id AS booking_id,
    b.estimated_quantity_quintals,
    c.name AS commodity_name,
    pc.id AS center_id,
    pc.name AS center_name,
    pc.status AS center_status,
    pc.current_token_seq,
    GREATEST(0, t.sequence_number - NULLIF(pc.current_token_seq, 0)) AS farmers_ahead,
    CASE 
        WHEN pc.current_token_seq = t.sequence_number THEN 1 
        ELSE 0 
    END AS is_current_turn,
    ROUND((GREATEST(0, t.sequence_number - NULLIF(pc.current_token_seq, 0)) * pc.avg_processing_seconds) / (GREATEST(1, pc.active_counters) * 60.0)) AS estimated_wait_minutes
FROM tokens t
JOIN bookings b ON t.booking_id = b.id
JOIN farmers f ON b.farmer_id = f.id
JOIN users u ON f.user_id = u.id
JOIN commodities c ON b.commodity_id = c.id
JOIN procurement_centers pc ON t.center_id = pc.id;

-- View 3: Procurement center analytics view
CREATE OR REPLACE VIEW v_procurement_center_analytics AS
SELECT 
    pc.id AS center_id,
    pc.name AS center_name,
    pc.district,
    COUNT(pt.id) AS total_transactions,
    COALESCE(SUM(pt.net_weight_qtl), 0) AS total_procured_quintals,
    COALESCE(SUM(pt.final_amount), 0) AS total_payout_amount,
    COALESCE(AVG(pt.moisture_content_pct), 0) AS avg_moisture_pct,
    COUNT(DISTINCT b.farmer_id) AS distinct_farmers_served
FROM procurement_centers pc
LEFT JOIN procurement_transactions pt ON pc.id = pt.center_id
LEFT JOIN bookings b ON pt.booking_id = b.id
GROUP BY pc.id, pc.name, pc.district;
