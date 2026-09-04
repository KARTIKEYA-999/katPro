-- =============================================================================
-- SMART INDIA HACKATHON 2026 - PROBLEM STATEMENT PS ID: 26032
-- PROJECT: Digital System for Procurement Schedules, Farmer Queues and Real-Time Procurement Status
-- DATABASE SEED DATA: Realistic Indian Agricultural Procurement Context
-- =============================================================================

-- Passwords:
-- farmer123   -> $2b$12$aPFpNXRNjKZN83LUOQOaM.HdXnG.SrqXZeU3DO.rWiOKJh8fsKYAq
-- official123 -> $2b$12$TbbpOp.YpQAxxjJQ6GCzd.83hRYDthARR0lnYaWxnkzC87I4/23k.
-- admin123    -> $2b$12$3flr3/ven/z2zyqaVq/SfO//gQNCmHMBLR7CkX0S8EDmVP7d5oi0q

-- -----------------------------------------------------------------------------
-- 1. PROCUREMENT CENTERS
-- -----------------------------------------------------------------------------
INSERT INTO procurement_centers (id, center_code, name, district, state, address, contact_phone, working_hours_start, working_hours_end, daily_capacity_mt, active_counters, avg_processing_seconds, current_token_seq, status) VALUES
(1, 'CPC-001', 'Central Procurement Center - Suryapet', 'Suryapet', 'Telangana', 'Mandi Road, Near Agricultural Market Yard, Suryapet - 508213', '+91 8684 220101', '08:30:00', '17:30:00', 150.00, 2, 480, 18, 'OPEN'),
(2, 'RPC-002', 'Rural Farmer Mandi - Miryalaguda', 'Nalgonda', 'Telangana', 'FCI Godown Complex, Bypass Road, Miryalaguda - 508207', '+91 8689 252441', '08:00:00', '17:00:00', 120.00, 2, 450, 12, 'OPEN'),
(3, 'VPH-003', 'Village Procurement Hub - Warangal', 'Warangal', 'Telangana', 'Enumamula Market Complex, Warangal - 506002', '+91 870 2445100', '09:00:00', '18:00:00', 200.00, 3, 500, 5, 'IN PROGRESS'),
(4, 'TAC-004', 'Tribal Agri Co-operative - Bhadrachalam', 'Bhadradri Kothagudem', 'Telangana', 'ITC Road, Sarapaka, Bhadrachalam - 507128', '+91 8743 231155', '08:30:00', '16:30:00', 80.00, 1, 600, 0, 'OPEN');

ALTER SEQUENCE procurement_centers_id_seq RESTART WITH 5;

-- -----------------------------------------------------------------------------
-- 2. COMMODITIES
-- -----------------------------------------------------------------------------
INSERT INTO commodities (id, code, name, category, msp_per_quintal, moisture_limit_pct, urgency_level, is_active) VALUES
(1, 'COMM-PDY-A', 'Paddy / Rice (Grade-A)', 'Cereal', 2203.00, 17.00, 3, TRUE),
(2, 'COMM-PDY-C', 'Paddy / Rice (Common)', 'Cereal', 2183.00, 17.00, 3, TRUE),
(3, 'COMM-WHT-F', 'Wheat (FAQ Standard)', 'Cereal', 2275.00, 12.00, 1, TRUE),
(4, 'COMM-MAZ-A', 'Maize (Yellow Corn)', 'Coarse Grain', 2090.00, 14.00, 2, TRUE),
(5, 'COMM-CTN-L', 'Cotton (Medium / Long Staple)', 'Fiber', 7020.00, 8.00, 1, TRUE),
(6, 'COMM-MST-A', 'Mustard / Rapeseed', 'Oilseed', 5650.00, 8.00, 1, TRUE);

ALTER SEQUENCE commodities_id_seq RESTART WITH 7;

-- Center commodities association
INSERT INTO center_commodities (center_id, commodity_id, daily_quota_mt) VALUES
(1, 1, 80.00), (1, 2, 40.00), (1, 4, 30.00),
(2, 1, 70.00), (2, 3, 30.00), (2, 4, 20.00),
(3, 1, 100.00), (3, 4, 50.00), (3, 5, 50.00),
(4, 1, 50.00), (4, 4, 30.00);

-- -----------------------------------------------------------------------------
-- 3. USERS (ADMIN, OFFICIALS, FARMERS)
-- -----------------------------------------------------------------------------

-- Administrators
INSERT INTO users (id, username, password_hash, role, full_name, phone, email, language_pref) VALUES
(1, 'admin1', '$2b$12$3flr3/ven/z2zyqaVq/SfO//gQNCmHMBLR7CkX0S8EDmVP7d5oi0q', 'ADMIN', 'Dr. K. Srinivas Rao, IAS', '+91 94400 11001', 'admin.agri@gov.in', 'en');

INSERT INTO administrators (id, user_id, admin_code, department) VALUES
(1, 1, 'ADM-TS-001', 'State Civil Supplies & Food Procurement');

-- Officials
INSERT INTO users (id, username, password_hash, role, full_name, phone, email, language_pref) VALUES
(2, 'official1', '$2b$12$TbbpOp.YpQAxxjJQ6GCzd.83hRYDthARR0lnYaWxnkzC87I4/23k.', 'OFFICIAL', 'Venkat Reddy', '+91 94401 22001', 'official1.suryapet@gov.in', 'te'),
(3, 'official2', '$2b$12$TbbpOp.YpQAxxjJQ6GCzd.83hRYDthARR0lnYaWxnkzC87I4/23k.', 'OFFICIAL', 'Suresh Chandra', '+91 94401 22002', 'official2.nalgonda@gov.in', 'en'),
(4, 'official3', '$2b$12$TbbpOp.YpQAxxjJQ6GCzd.83hRYDthARR0lnYaWxnkzC87I4/23k.', 'OFFICIAL', 'Anuradha Sharma', '+91 94401 22003', 'official3.warangal@gov.in', 'hi'),
(5, 'official4', '$2b$12$TbbpOp.YpQAxxjJQ6GCzd.83hRYDthARR0lnYaWxnkzC87I4/23k.', 'OFFICIAL', 'K. Ramulu', '+91 94401 22004', 'official4.kothagudem@gov.in', 'te');

INSERT INTO officials (id, user_id, center_id, employee_code, designation) VALUES
(1, 2, 1, 'OFF-SUR-01', 'Senior Procurement Inspector'),
(2, 3, 2, 'OFF-MIR-01', 'Mandi Superintendent'),
(3, 4, 3, 'OFF-WAR-01', 'Joint Procurement Officer'),
(4, 5, 4, 'OFF-BHA-01', 'Assistant Procurement Officer');

-- 22 Farmers
INSERT INTO users (id, username, password_hash, role, full_name, phone, email, language_pref) VALUES
(6,  'farmer1',  '$2b$12$aPFpNXRNjKZN83LUOQOaM.HdXnG.SrqXZeU3DO.rWiOKJh8fsKYAq', 'FARMER', 'Ramesh Kumar Goud',  '+91 98480 11001', 'ramesh.farmer@agro.in', 'te'),
(7,  'farmer2',  '$2b$12$aPFpNXRNjKZN83LUOQOaM.HdXnG.SrqXZeU3DO.rWiOKJh8fsKYAq', 'FARMER', 'Mallaiah Nayak',     '+91 98480 11002', NULL, 'te'),
(8,  'farmer3',  '$2b$12$aPFpNXRNjKZN83LUOQOaM.HdXnG.SrqXZeU3DO.rWiOKJh8fsKYAq', 'FARMER', 'Balram Singh',       '+91 98480 11003', NULL, 'hi'),
(9,  'farmer4',  '$2b$12$aPFpNXRNjKZN83LUOQOaM.HdXnG.SrqXZeU3DO.rWiOKJh8fsKYAq', 'FARMER', 'Satyanarayana Murthy','+91 98480 11004', NULL, 'te'),
(10, 'farmer5',  '$2b$12$aPFpNXRNjKZN83LUOQOaM.HdXnG.SrqXZeU3DO.rWiOKJh8fsKYAq', 'FARMER', 'Gurpreet Singh',     '+91 98480 11005', NULL, 'hi'),
(11, 'farmer6',  '$2b$12$aPFpNXRNjKZN83LUOQOaM.HdXnG.SrqXZeU3DO.rWiOKJh8fsKYAq', 'FARMER', 'Laxman Rao',         '+91 98480 11006', NULL, 'te'),
(12, 'farmer7',  '$2b$12$aPFpNXRNjKZN83LUOQOaM.HdXnG.SrqXZeU3DO.rWiOKJh8fsKYAq', 'FARMER', 'Kishan Lal Patel',  '+91 98480 11007', NULL, 'hi'),
(13, 'farmer8',  '$2b$12$aPFpNXRNjKZN83LUOQOaM.HdXnG.SrqXZeU3DO.rWiOKJh8fsKYAq', 'FARMER', 'Nagaraju Reddy',    '+91 98480 11008', NULL, 'te'),
(14, 'farmer9',  '$2b$12$aPFpNXRNjKZN83LUOQOaM.HdXnG.SrqXZeU3DO.rWiOKJh8fsKYAq', 'FARMER', 'Anil Kumar Yadav',   '+91 98480 11009', NULL, 'hi'),
(15, 'farmer10', '$2b$12$aPFpNXRNjKZN83LUOQOaM.HdXnG.SrqXZeU3DO.rWiOKJh8fsKYAq', 'FARMER', 'Chiranjeevi Rao',   '+91 98480 11010', NULL, 'te'),
(16, 'farmer11', '$2b$12$aPFpNXRNjKZN83LUOQOaM.HdXnG.SrqXZeU3DO.rWiOKJh8fsKYAq', 'FARMER', 'Somaiah Kuruma',    '+91 98480 11011', NULL, 'te'),
(17, 'farmer12', '$2b$12$aPFpNXRNjKZN83LUOQOaM.HdXnG.SrqXZeU3DO.rWiOKJh8fsKYAq', 'FARMER', 'Devender Verma',    '+91 98480 11012', NULL, 'hi'),
(18, 'farmer13', '$2b$12$aPFpNXRNjKZN83LUOQOaM.HdXnG.SrqXZeU3DO.rWiOKJh8fsKYAq', 'FARMER', 'Pullarao Naidu',    '+91 98480 11013', NULL, 'te'),
(19, 'farmer14', '$2b$12$aPFpNXRNjKZN83LUOQOaM.HdXnG.SrqXZeU3DO.rWiOKJh8fsKYAq', 'FARMER', 'Harbhajan Ram',     '+91 98480 11014', NULL, 'hi'),
(20, 'farmer15', '$2b$12$aPFpNXRNjKZN83LUOQOaM.HdXnG.SrqXZeU3DO.rWiOKJh8fsKYAq', 'FARMER', 'Govind Naik',       '+91 98480 11015', NULL, 'te'),
(21, 'farmer16', '$2b$12$aPFpNXRNjKZN83LUOQOaM.HdXnG.SrqXZeU3DO.rWiOKJh8fsKYAq', 'FARMER', 'Shankarappa Gowda', '+91 98480 11016', NULL, 'en'),
(22, 'farmer17', '$2b$12$aPFpNXRNjKZN83LUOQOaM.HdXnG.SrqXZeU3DO.rWiOKJh8fsKYAq', 'FARMER', 'Sita Ram Meena',    '+91 98480 11017', NULL, 'hi'),
(23, 'farmer18', '$2b$12$aPFpNXRNjKZN83LUOQOaM.HdXnG.SrqXZeU3DO.rWiOKJh8fsKYAq', 'FARMER', 'Venkataswamy K.',   '+91 98480 11018', NULL, 'te'),
(24, 'farmer19', '$2b$12$aPFpNXRNjKZN83LUOQOaM.HdXnG.SrqXZeU3DO.rWiOKJh8fsKYAq', 'FARMER', 'Mukesh Chand',     '+91 98480 11019', NULL, 'hi'),
(25, 'farmer20', '$2b$12$aPFpNXRNjKZN83LUOQOaM.HdXnG.SrqXZeU3DO.rWiOKJh8fsKYAq', 'FARMER', 'Venkanna Boya',     '+91 98480 11020', NULL, 'te'),
(26, 'farmer21', '$2b$12$aPFpNXRNjKZN83LUOQOaM.HdXnG.SrqXZeU3DO.rWiOKJh8fsKYAq', 'FARMER', 'Dharamvir Singh',   '+91 98480 11021', NULL, 'hi'),
(27, 'farmer22', '$2b$12$aPFpNXRNjKZN83LUOQOaM.HdXnG.SrqXZeU3DO.rWiOKJh8fsKYAq', 'FARMER', 'Narsimha Chary',    '+91 98480 11022', NULL, 'te');

ALTER SEQUENCE users_id_seq RESTART WITH 28;

-- Insert Farmers profiles
INSERT INTO farmers (id, user_id, farmer_code, village, mandal, district, state, land_size_acres, primary_crop, bank_account_last4) VALUES
(1,  6,  'FAR-TS-001', 'Kudakuda',       'Chivvemla',   'Suryapet',            'Telangana', 4.50, 'Paddy / Rice (Grade-A)', '4821'),
(2,  7,  'FAR-TS-002', 'Penpahad',       'Penpahad',    'Suryapet',            'Telangana', 3.00, 'Paddy / Rice (Common)',  '1192'),
(3,  8,  'FAR-TS-003', 'Anantharam',     'Suryapet',    'Suryapet',            'Telangana', 5.00, 'Wheat (FAQ Standard)',   '8831'),
(4,  9,  'FAR-TS-004', 'Dameracharla',   'Miryalaguda', 'Nalgonda',            'Telangana', 6.20, 'Paddy / Rice (Grade-A)', '7734'),
(5,  10, 'FAR-TS-005', 'Tripuraram',     'Tripuraram',  'Nalgonda',            'Telangana', 8.00, 'Wheat (FAQ Standard)',   '9012'),
(6,  11, 'FAR-TS-006', 'Gudur',          'Enumamula',   'Warangal',            'Telangana', 3.50, 'Maize (Yellow Corn)',    '3341'),
(7,  12, 'FAR-TS-007', 'Atmakur',        'Atmakur',     'Warangal',            'Telangana', 4.00, 'Cotton (Medium Staple)', '2891'),
(8,  13, 'FAR-TS-008', 'Sarapaka',       'Burgampahad', 'Bhadradri Kothagudem','Telangana', 2.50, 'Paddy / Rice (Common)',  '5521'),
(9,  14, 'FAR-TS-009', 'Chivvemla',      'Chivvemla',   'Suryapet',            'Telangana', 3.80, 'Paddy / Rice (Grade-A)', '6612'),
(10, 15, 'FAR-TS-010', 'Thallada',       'Thallada',    'Khammam',             'Telangana', 5.50, 'Maize (Yellow Corn)',    '1245'),
(11, 16, 'FAR-TS-011', 'Tirumalagiri',   'Tirumalagiri','Suryapet',            'Telangana', 4.20, 'Paddy / Rice (Grade-A)', '9832'),
(12, 17, 'FAR-TS-012', 'Mothey',         'Mothey',      'Suryapet',            'Telangana', 3.00, 'Paddy / Rice (Common)',  '4523'),
(13, 18, 'FAR-TS-013', 'Garidepally',    'Garidepally', 'Suryapet',            'Telangana', 6.00, 'Paddy / Rice (Grade-A)', '7819'),
(14, 19, 'FAR-TS-014', 'Nereducherla',   'Nereducherla','Suryapet',            'Telangana', 4.50, 'Wheat (FAQ Standard)',   '6634'),
(15, 20, 'FAR-TS-015', 'Huzurnagar',     'Huzurnagar',  'Suryapet',            'Telangana', 7.00, 'Paddy / Rice (Grade-A)', '8812'),
(16, 21, 'FAR-TS-016', 'Kodad',          'Kodad',       'Suryapet',            'Telangana', 5.20, 'Paddy / Rice (Grade-A)', '2234'),
(17, 22, 'FAR-TS-017', 'Munagala',       'Munagala',    'Suryapet',            'Telangana', 3.40, 'Paddy / Rice (Common)',  '9081'),
(18, 23, 'FAR-TS-018', 'Chilkur',        'Chilkur',     'Suryapet',            'Telangana', 4.80, 'Paddy / Rice (Grade-A)', '5543'),
(19, 24, 'FAR-TS-019', 'Mellachervu',    'Mellachervu', 'Suryapet',            'Telangana', 6.50, 'Maize (Yellow Corn)',    '1123'),
(20, 25, 'FAR-TS-020', 'Mattampally',    'Mattampally', 'Suryapet',            'Telangana', 3.20, 'Paddy / Rice (Grade-A)', '4490'),
(21, 26, 'FAR-TS-021', 'Vemulapally',    'Vemulapally', 'Nalgonda',            'Telangana', 5.00, 'Paddy / Rice (Grade-A)', '7731'),
(22, 27, 'FAR-TS-022', 'Miryalaguda Rural','Miryalaguda','Nalgonda',           'Telangana', 4.00, 'Paddy / Rice (Common)',  '3319');

ALTER SEQUENCE farmers_id_seq RESTART WITH 23;

-- -----------------------------------------------------------------------------
-- 4. PROCUREMENT SCHEDULES & TIME SLOTS
-- -----------------------------------------------------------------------------
-- Schedules for Today
INSERT INTO procurement_schedules (id, center_id, commodity_id, schedule_date, start_time, end_time, total_capacity_quintals, booked_capacity_quintals, status) VALUES
(1, 1, 1, CURRENT_DATE, '08:30:00', '17:30:00', 800.00, 520.00, 'ACTIVE'),
(2, 2, 1, CURRENT_DATE, '08:00:00', '17:00:00', 700.00, 360.00, 'ACTIVE'),
(3, 3, 4, CURRENT_DATE, '09:00:00', '18:00:00', 500.00, 200.00, 'ACTIVE'),
(4, 4, 1, CURRENT_DATE, '08:30:00', '16:30:00', 400.00, 100.00, 'ACTIVE'),
-- Schedules for Tomorrow
(5, 1, 1, CURRENT_DATE + INTERVAL '1 day', '08:30:00', '17:30:00', 800.00, 180.00, 'ACTIVE'),
(6, 2, 3, CURRENT_DATE + INTERVAL '1 day', '08:00:00', '17:00:00', 600.00, 80.00, 'ACTIVE');

ALTER SEQUENCE procurement_schedules_id_seq RESTART WITH 7;

-- Time slots for Schedule 1 (Center 1 today)
INSERT INTO time_slots (id, schedule_id, slot_name, start_time, end_time, max_tokens, booked_tokens) VALUES
(1, 1, 'Morning Slot 1 (08:30 - 10:30)', '08:30:00', '10:30:00', 10, 10),
(2, 1, 'Morning Slot 2 (10:30 - 12:30)', '10:30:00', '12:30:00', 10, 10),
(3, 1, 'Afternoon Slot 1 (13:00 - 15:00)', '13:00:00', '15:00:00', 10, 8),
(4, 1, 'Afternoon Slot 2 (15:00 - 17:00)', '15:00:00', '17:00:00', 10, 2),
-- Time slots for Schedule 2 (Center 2 today)
(5, 2, 'Morning Slot 1 (08:00 - 10:30)', '08:00:00', '10:30:00', 12, 12),
(6, 2, 'Morning Slot 2 (10:30 - 13:00)', '10:30:00', '13:00:00', 12, 6);

ALTER SEQUENCE time_slots_id_seq RESTART WITH 7;

-- -----------------------------------------------------------------------------
-- 5. BOOKINGS & TOKENS (Center 1 Today)
-- Sequence from A001 to A025
-- A001 to A017: COMPLETED
-- A018: PROCESSING
-- A019 to A025: WAITING (farmer 1 has A023!)
-- -----------------------------------------------------------------------------

-- Completed bookings (Tokens A001 to A017)
INSERT INTO bookings (id, booking_ref, farmer_id, schedule_id, slot_id, commodity_id, estimated_quantity_quintals, vehicle_number, status, created_at) VALUES
(1,  'BK-2026-0001', 2,  1, 1, 1, 35.00, 'TS-29-TA-1234', 'COMPLETED', CURRENT_DATE - INTERVAL '1 day'),
(2,  'BK-2026-0002', 3,  1, 1, 1, 40.00, 'TS-29-TA-2345', 'COMPLETED', CURRENT_DATE - INTERVAL '1 day'),
(3,  'BK-2026-0003', 4,  1, 1, 1, 28.00, 'TS-29-TA-3456', 'COMPLETED', CURRENT_DATE - INTERVAL '1 day'),
(4,  'BK-2026-0004', 5,  1, 1, 1, 45.00, 'TS-29-TA-4567', 'COMPLETED', CURRENT_DATE - INTERVAL '1 day'),
(5,  'BK-2026-0005', 6,  1, 1, 1, 30.00, 'TS-29-TA-5678', 'COMPLETED', CURRENT_DATE - INTERVAL '1 day'),
(6,  'BK-2026-0006', 7,  1, 1, 1, 50.00, 'TS-29-TA-6789', 'COMPLETED', CURRENT_DATE - INTERVAL '1 day'),
(7,  'BK-2026-0007', 8,  1, 1, 1, 25.00, 'TS-29-TA-7890', 'COMPLETED', CURRENT_DATE - INTERVAL '1 day'),
(8,  'BK-2026-0008', 9,  1, 1, 1, 38.00, 'TS-29-TA-8901', 'COMPLETED', CURRENT_DATE - INTERVAL '1 day'),
(9,  'BK-2026-0009', 10, 1, 1, 1, 42.00, 'TS-29-TA-9012', 'COMPLETED', CURRENT_DATE - INTERVAL '1 day'),
(10, 'BK-2026-0010', 11, 1, 1, 1, 33.00, 'TS-29-TB-1122', 'COMPLETED', CURRENT_DATE - INTERVAL '1 day'),
(11, 'BK-2026-0011', 12, 1, 2, 1, 36.00, 'TS-29-TB-2233', 'COMPLETED', CURRENT_DATE - INTERVAL '1 day'),
(12, 'BK-2026-0012', 13, 1, 2, 1, 48.00, 'TS-29-TB-3344', 'COMPLETED', CURRENT_DATE - INTERVAL '1 day'),
(13, 'BK-2026-0013', 14, 1, 2, 1, 29.00, 'TS-29-TB-4455', 'COMPLETED', CURRENT_DATE - INTERVAL '1 day'),
(14, 'BK-2026-0014', 15, 1, 2, 1, 55.00, 'TS-29-TB-5566', 'COMPLETED', CURRENT_DATE - INTERVAL '1 day'),
(15, 'BK-2026-0015', 16, 1, 2, 1, 31.00, 'TS-29-TB-6677', 'COMPLETED', CURRENT_DATE - INTERVAL '1 day'),
(16, 'BK-2026-0016', 17, 1, 2, 1, 44.00, 'TS-29-TB-7788', 'COMPLETED', CURRENT_DATE - INTERVAL '1 day'),
(17, 'BK-2026-0017', 18, 1, 2, 1, 37.00, 'TS-29-TB-8899', 'COMPLETED', CURRENT_DATE - INTERVAL '1 day'),
-- Currently In-Progress Token A018
(18, 'BK-2026-0018', 19, 1, 2, 1, 40.00, 'TS-29-TC-1212', 'IN_PROGRESS', CURRENT_DATE - INTERVAL '1 day'),
-- Waiting Tokens A019 to A025 (Farmer 1 has A023)
(19, 'BK-2026-0019', 20, 1, 2, 1, 32.00, 'TS-29-TC-2323', 'CONFIRMED', CURRENT_DATE - INTERVAL '1 day'),
(20, 'BK-2026-0020', 21, 1, 2, 1, 46.00, 'TS-29-TC-3434', 'CONFIRMED', CURRENT_DATE - INTERVAL '1 day'),
(21, 'BK-2026-0021', 22, 1, 3, 1, 38.00, 'TS-29-TC-4545', 'CONFIRMED', CURRENT_DATE - INTERVAL '1 day'),
(22, 'BK-2026-0022', 2,  1, 3, 1, 25.00, 'TS-29-TC-5656', 'CONFIRMED', CURRENT_DATE - INTERVAL '1 day'),
(23, 'BK-2026-0023', 1,  1, 3, 1, 45.00, 'TS-29-TC-6767', 'CONFIRMED', CURRENT_DATE - INTERVAL '1 day'), -- FARMER 1 TOKEN A023!
(24, 'BK-2026-0024', 3,  1, 3, 1, 30.00, 'TS-29-TC-7878', 'CONFIRMED', CURRENT_DATE - INTERVAL '1 day'),
(25, 'BK-2026-0025', 4,  1, 3, 1, 42.00, 'TS-29-TC-8989', 'CONFIRMED', CURRENT_DATE - INTERVAL '1 day');

ALTER SEQUENCE bookings_id_seq RESTART WITH 26;

-- Tokens corresponding to bookings
INSERT INTO tokens (id, token_number, booking_id, center_id, schedule_id, sequence_number, session_prefix, checksum, status, issued_at, called_at, completed_at) VALUES
(1,  'A001', 1,  1, 1, 1,  'A', '9F', 'COMPLETED', CURRENT_DATE + TIME '08:30:00', CURRENT_DATE + TIME '08:35:00', CURRENT_DATE + TIME '08:43:00'),
(2,  'A002', 2,  1, 1, 2,  'A', '8A', 'COMPLETED', CURRENT_DATE + TIME '08:30:00', CURRENT_DATE + TIME '08:44:00', CURRENT_DATE + TIME '08:52:00'),
(3,  'A003', 3,  1, 1, 3,  'A', '7B', 'COMPLETED', CURRENT_DATE + TIME '08:30:00', CURRENT_DATE + TIME '08:53:00', CURRENT_DATE + TIME '09:01:00'),
(4,  'A004', 4,  1, 1, 4,  'A', '6C', 'COMPLETED', CURRENT_DATE + TIME '08:30:00', CURRENT_DATE + TIME '09:02:00', CURRENT_DATE + TIME '09:10:00'),
(5,  'A005', 5,  1, 1, 5,  'A', '5D', 'COMPLETED', CURRENT_DATE + TIME '08:30:00', CURRENT_DATE + TIME '09:11:00', CURRENT_DATE + TIME '09:19:00'),
(6,  'A006', 6,  1, 1, 6,  'A', '4E', 'COMPLETED', CURRENT_DATE + TIME '08:30:00', CURRENT_DATE + TIME '09:20:00', CURRENT_DATE + TIME '09:28:00'),
(7,  'A007', 7,  1, 1, 7,  'A', '3F', 'COMPLETED', CURRENT_DATE + TIME '08:30:00', CURRENT_DATE + TIME '09:29:00', CURRENT_DATE + TIME '09:37:00'),
(8,  'A008', 8,  1, 1, 8,  'A', '2A', 'COMPLETED', CURRENT_DATE + TIME '08:30:00', CURRENT_DATE + TIME '09:38:00', CURRENT_DATE + TIME '09:46:00'),
(9,  'A009', 9,  1, 1, 9,  'A', '1B', 'COMPLETED', CURRENT_DATE + TIME '08:30:00', CURRENT_DATE + TIME '09:47:00', CURRENT_DATE + TIME '09:55:00'),
(10, 'A010', 10, 1, 1, 10, 'A', '0C', 'COMPLETED', CURRENT_DATE + TIME '08:30:00', CURRENT_DATE + TIME '09:56:00', CURRENT_DATE + TIME '10:04:00'),
(11, 'A011', 11, 1, 1, 11, 'A', 'F1', 'COMPLETED', CURRENT_DATE + TIME '10:30:00', CURRENT_DATE + TIME '10:32:00', CURRENT_DATE + TIME '10:40:00'),
(12, 'A012', 12, 1, 1, 12, 'A', 'E2', 'COMPLETED', CURRENT_DATE + TIME '10:30:00', CURRENT_DATE + TIME '10:41:00', CURRENT_DATE + TIME '10:49:00'),
(13, 'A013', 13, 1, 1, 13, 'A', 'D3', 'COMPLETED', CURRENT_DATE + TIME '10:30:00', CURRENT_DATE + TIME '10:50:00', CURRENT_DATE + TIME '10:58:00'),
(14, 'A014', 14, 1, 1, 14, 'A', 'C4', 'COMPLETED', CURRENT_DATE + TIME '10:30:00', CURRENT_DATE + TIME '10:59:00', CURRENT_DATE + TIME '11:07:00'),
(15, 'A015', 15, 1, 1, 15, 'A', 'B5', 'COMPLETED', CURRENT_DATE + TIME '10:30:00', CURRENT_DATE + TIME '11:08:00', CURRENT_DATE + TIME '11:16:00'),
(16, 'A016', 16, 1, 1, 16, 'A', 'A6', 'COMPLETED', CURRENT_DATE + TIME '10:30:00', CURRENT_DATE + TIME '11:17:00', CURRENT_DATE + TIME '11:25:00'),
(17, 'A017', 17, 1, 1, 17, 'A', '97', 'COMPLETED', CURRENT_DATE + TIME '10:30:00', CURRENT_DATE + TIME '11:26:00', CURRENT_DATE + TIME '11:34:00'),
-- Active Token A018
(18, 'A018', 18, 1, 1, 18, 'A', '88', 'PROCESSING',CURRENT_DATE + TIME '10:30:00', CURRENT_DATE + TIME '11:35:00', NULL),
-- In Queue Tokens A019 to A025
(19, 'A019', 19, 1, 1, 19, 'A', '79', 'WAITING',   CURRENT_DATE + TIME '10:30:00', NULL, NULL),
(20, 'A020', 20, 1, 1, 20, 'A', '6A', 'WAITING',   CURRENT_DATE + TIME '10:30:00', NULL, NULL),
(21, 'A021', 21, 1, 1, 21, 'A', '5B', 'WAITING',   CURRENT_DATE + TIME '13:00:00', NULL, NULL),
(22, 'A022', 22, 1, 1, 22, 'A', '4C', 'WAITING',   CURRENT_DATE + TIME '13:00:00', NULL, NULL),
(23, 'A023', 23, 1, 1, 23, 'A', '3D', 'WAITING',   CURRENT_DATE + TIME '13:00:00', NULL, NULL), -- RAMESH KUMAR (farmer1)
(24, 'A024', 24, 1, 1, 24, 'A', '2E', 'WAITING',   CURRENT_DATE + TIME '13:00:00', NULL, NULL),
(25, 'A025', 25, 1, 1, 25, 'A', '1F', 'WAITING',   CURRENT_DATE + TIME '13:00:00', NULL, NULL);

ALTER SEQUENCE tokens_id_seq RESTART WITH 26;

-- Queue entries for active center 1
INSERT INTO queue_entries (token_id, center_id, queue_position, priority_score, status) VALUES
(18, 1, 1, 100.00, 'PROCESSING'),
(19, 1, 2, 95.00,  'IN_QUEUE'),
(20, 1, 3, 90.00,  'IN_QUEUE'),
(21, 1, 4, 85.00,  'IN_QUEUE'),
(22, 1, 5, 80.00,  'IN_QUEUE'),
(23, 1, 6, 75.00,  'IN_QUEUE'), -- farmer1 is 5 ahead after current
(24, 1, 7, 70.00,  'IN_QUEUE'),
(25, 1, 8, 65.00,  'IN_QUEUE');

-- -----------------------------------------------------------------------------
-- 6. PROCUREMENT TRANSACTIONS (Completed for A001 to A017)
-- -----------------------------------------------------------------------------
INSERT INTO procurement_transactions (id, transaction_ref, booking_id, token_id, center_id, gross_weight_qtl, tare_weight_qtl, net_weight_qtl, moisture_content_pct, quality_grade, msp_rate, final_amount, payment_status, processed_by) VALUES
(1,  'TXN-2026-0001', 1,  1,  1, 37.20, 2.20, 35.00, 14.20, 'Grade-A', 2203.00, 77105.00,  'DIRECT_BENEFIT_TRANSFER', 1),
(2,  'TXN-2026-0002', 2,  2,  1, 42.50, 2.50, 40.00, 15.10, 'Grade-A', 2203.00, 88120.00,  'DIRECT_BENEFIT_TRANSFER', 1),
(3,  'TXN-2026-0003', 3,  3,  1, 29.80, 1.80, 28.00, 13.80, 'Grade-A', 2203.00, 61684.00,  'DIRECT_BENEFIT_TRANSFER', 1),
(4,  'TXN-2026-0004', 4,  4,  1, 47.90, 2.90, 45.00, 16.00, 'Grade-A', 2203.00, 99135.00,  'DIRECT_BENEFIT_TRANSFER', 1),
(5,  'TXN-2026-0005', 5,  5,  1, 32.00, 2.00, 30.00, 14.50, 'Grade-A', 2203.00, 66090.00,  'DIRECT_BENEFIT_TRANSFER', 1),
(6,  'TXN-2026-0006', 6,  6,  1, 53.00, 3.00, 50.00, 15.80, 'Grade-A', 2203.00, 110150.00, 'DIRECT_BENEFIT_TRANSFER', 1),
(7,  'TXN-2026-0007', 7,  7,  1, 26.60, 1.60, 25.00, 13.20, 'Grade-A', 2203.00, 55075.00,  'DIRECT_BENEFIT_TRANSFER', 1),
(8,  'TXN-2026-0008', 8,  8,  1, 40.40, 2.40, 38.00, 14.90, 'Grade-A', 2203.00, 83714.00,  'DIRECT_BENEFIT_TRANSFER', 1),
(9,  'TXN-2026-0009', 9,  9,  1, 44.60, 2.60, 42.00, 15.40, 'Grade-A', 2203.00, 92526.00,  'DIRECT_BENEFIT_TRANSFER', 1),
(10, 'TXN-2026-0010', 10, 10, 1, 35.10, 2.10, 33.00, 13.90, 'Grade-A', 2203.00, 72699.00,  'DIRECT_BENEFIT_TRANSFER', 1),
(11, 'TXN-2026-0011', 11, 11, 1, 38.30, 2.30, 36.00, 14.60, 'Grade-A', 2203.00, 79308.00,  'DIRECT_BENEFIT_TRANSFER', 1),
(12, 'TXN-2026-0012', 12, 12, 1, 51.00, 3.00, 48.00, 15.90, 'Grade-A', 2203.00, 105744.00, 'DIRECT_BENEFIT_TRANSFER', 1),
(13, 'TXN-2026-0013', 13, 13, 1, 30.90, 1.90, 29.00, 14.00, 'Grade-A', 2203.00, 63887.00,  'DIRECT_BENEFIT_TRANSFER', 1),
(14, 'TXN-2026-0014', 14, 14, 1, 58.50, 3.50, 55.00, 16.20, 'Grade-A', 2203.00, 121165.00, 'DIRECT_BENEFIT_TRANSFER', 1),
(15, 'TXN-2026-0015', 15, 15, 1, 33.00, 2.00, 31.00, 13.50, 'Grade-A', 2203.00, 68293.00,  'DIRECT_BENEFIT_TRANSFER', 1),
(16, 'TXN-2026-0016', 16, 16, 1, 46.80, 2.80, 44.00, 15.00, 'Grade-A', 2203.00, 96932.00,  'DIRECT_BENEFIT_TRANSFER', 1),
(17, 'TXN-2026-0017', 17, 17, 1, 39.40, 2.40, 37.00, 14.70, 'Grade-A', 2203.00, 81511.00,  'DIRECT_BENEFIT_TRANSFER', 1);

ALTER SEQUENCE procurement_transactions_id_seq RESTART WITH 18;

-- -----------------------------------------------------------------------------
-- 7. NOTIFICATIONS & ANNOUNCEMENTS
-- -----------------------------------------------------------------------------
INSERT INTO announcements (center_id, official_id, title, message, urgency, is_active) VALUES
(1, 1, 'Digital Weighbridge Calibration Completed', 'Counter 1 and Counter 2 weighbridges have been inspected and calibrated by Legal Metrology Dept. Accuracy guaranteed within 0.05%.', 'NORMAL', TRUE),
(1, 1, 'Moisture Limit Adherence Notice', 'Paddy procurement requires moisture content strictly <= 17.0%. Sun-drying facility is operational at Platform C.', 'HIGH', TRUE),
(2, 2, 'Direct Benefit Transfer (DBT) Update', 'Procurement payments will be credited within 48 hours directly into Aadhaar-seeded bank accounts.', 'NORMAL', TRUE);

INSERT INTO notifications (user_id, title, message, notification_type, is_read) VALUES
(6, 'Digital Token Generated: A023', 'Your booking for Paddy procurement at Central Procurement Center - Suryapet is confirmed. Token A023 is scheduled for Afternoon Slot 1.', 'SCHEDULE', FALSE),
(6, 'Queue Movement Alert', 'Procurement center has reached Token A018. You have 5 farmers ahead of you. Estimated wait: ~45 minutes.', 'TURN_ALERT', FALSE),
(7, 'Procurement Completed Successfully', 'Your procurement transaction TXN-2026-0001 for 35.00 Quintals has been recorded. Payout of Rs 77,105 sent for DBT credit.', 'SUCCESS', TRUE);
