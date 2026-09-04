-- =============================================================================
-- SMART INDIA HACKATHON 2026 - PROBLEM STATEMENT PS ID: 26032
-- PROJECT: Digital System for Procurement Schedules, Farmer Queues and Real-Time Procurement Status
-- USEFUL OPERATIONAL, REPORTING & ANALYTICAL SQL QUERIES
-- =============================================================================

-- -----------------------------------------------------------------------------
-- QUERY 1: Real-Time Queue Status for a Given Procurement Center
-- Shows current active token, total waiting, total completed, and estimated backlog
-- -----------------------------------------------------------------------------
SELECT 
    pc.id AS center_id,
    pc.name AS center_name,
    pc.district,
    pc.status AS center_status,
    pc.current_token_seq,
    COUNT(t.id) FILTER (WHERE t.status = 'WAITING') AS farmers_waiting,
    COUNT(t.id) FILTER (WHERE t.status = 'PROCESSING') AS farmers_processing,
    COUNT(t.id) FILTER (WHERE t.status = 'COMPLETED') AS farmers_completed,
    ROUND((COUNT(t.id) FILTER (WHERE t.status = 'WAITING') * pc.avg_processing_seconds) / (GREATEST(1, pc.active_counters) * 60.0)) AS total_backlog_minutes
FROM procurement_centers pc
LEFT JOIN tokens t ON pc.id = t.center_id AND DATE(t.issued_at) = CURRENT_DATE
WHERE pc.id = 1
GROUP BY pc.id, pc.name, pc.district, pc.status, pc.current_token_seq, pc.avg_processing_seconds, pc.active_counters;

-- -----------------------------------------------------------------------------
-- QUERY 2: Farmer Queue Tracking & ETA Calculation for a Specific Farmer
-- Shows farmer token, current token being served, farmers ahead, and estimated wait
-- -----------------------------------------------------------------------------
SELECT 
    f.farmer_code,
    u.full_name AS farmer_name,
    u.phone AS contact_phone,
    t.token_number AS farmer_token,
    t.sequence_number AS farmer_seq,
    pc.name AS procurement_center,
    pc.current_token_seq AS current_serving_token_seq,
    CONCAT('A', LPAD(pc.current_token_seq::TEXT, 3, '0')) AS current_serving_token,
    GREATEST(0, t.sequence_number - pc.current_token_seq) AS farmers_ahead,
    ROUND((GREATEST(0, t.sequence_number - pc.current_token_seq) * pc.avg_processing_seconds) / (GREATEST(1, pc.active_counters) * 60.0)) AS estimated_wait_minutes,
    t.status AS token_status,
    c.name AS commodity,
    b.estimated_quantity_quintals
FROM tokens t
JOIN bookings b ON t.booking_id = b.id
JOIN farmers f ON b.farmer_id = f.id
JOIN users u ON f.user_id = u.id
JOIN procurement_centers pc ON t.center_id = pc.id
JOIN commodities c ON b.commodity_id = c.id
WHERE u.id = 6 -- Ramesh Kumar (farmer1)
  AND t.status IN ('WAITING', 'CALLED', 'PROCESSING');

-- -----------------------------------------------------------------------------
-- QUERY 3: Center-Wise Procurement Summary (Aggregations & Metrics)
-- -----------------------------------------------------------------------------
SELECT 
    pc.center_code,
    pc.name AS center_name,
    pc.district,
    COUNT(DISTINCT pt.id) AS completed_transactions,
    COALESCE(SUM(pt.net_weight_qtl), 0) AS total_procured_quintals,
    COALESCE(SUM(pt.final_amount), 0) AS total_payout_inr,
    ROUND(COALESCE(AVG(pt.moisture_content_pct), 0), 2) AS avg_moisture_percentage,
    COUNT(DISTINCT b.farmer_id) AS distinct_farmers_benefitted
FROM procurement_centers pc
LEFT JOIN procurement_transactions pt ON pc.id = pt.center_id
LEFT JOIN bookings b ON pt.booking_id = b.id
GROUP BY pc.id, pc.center_code, pc.name, pc.district
ORDER BY total_procured_quintals DESC;

-- -----------------------------------------------------------------------------
-- QUERY 4: Commodity-Wise Procurement & Financial Payouts
-- -----------------------------------------------------------------------------
SELECT 
    c.name AS commodity_name,
    c.category,
    c.msp_per_quintal,
    COUNT(pt.id) AS total_lots_procured,
    COALESCE(SUM(pt.net_weight_qtl), 0) AS total_weight_quintals,
    ROUND(COALESCE(SUM(pt.net_weight_qtl) / 10.0, 0), 2) AS total_weight_metric_tonnes,
    COALESCE(SUM(pt.final_amount), 0) AS total_payout_amount,
    ROUND(COALESCE(AVG(pt.moisture_content_pct), 0), 2) AS avg_moisture_pct
FROM commodities c
LEFT JOIN bookings b ON c.id = b.commodity_id
LEFT JOIN procurement_transactions pt ON b.id = pt.booking_id
GROUP BY c.id, c.name, c.category, c.msp_per_quintal
ORDER BY total_weight_quintals DESC;

-- -----------------------------------------------------------------------------
-- QUERY 5: Daily Procurement Trends & Transaction Throughput
-- -----------------------------------------------------------------------------
SELECT 
    DATE(pt.processed_at) AS procurement_date,
    COUNT(pt.id) AS total_transactions,
    ROUND(SUM(pt.net_weight_qtl), 2) AS total_procured_quintals,
    ROUND(SUM(pt.final_amount), 2) AS total_disbursed_amount,
    COUNT(DISTINCT pt.center_id) AS active_centers_count
FROM procurement_transactions pt
GROUP BY DATE(pt.processed_at)
ORDER BY procurement_date DESC;

-- -----------------------------------------------------------------------------
-- QUERY 6: Schedule Slot Capacity & Utilization
-- -----------------------------------------------------------------------------
SELECT 
    ps.schedule_date,
    pc.name AS center_name,
    c.name AS commodity_name,
    ts.slot_name,
    ts.max_tokens,
    ts.booked_tokens,
    ROUND((ts.booked_tokens::NUMERIC / ts.max_tokens::NUMERIC) * 100.0, 1) AS slot_utilization_pct,
    (ts.max_tokens - ts.booked_tokens) AS slots_available
FROM time_slots ts
JOIN procurement_schedules ps ON ts.schedule_id = ps.id
JOIN procurement_centers pc ON ps.center_id = pc.id
JOIN commodities c ON ps.commodity_id = c.id
WHERE ps.schedule_date >= CURRENT_DATE
ORDER BY ps.schedule_date ASC, ts.start_time ASC;

-- -----------------------------------------------------------------------------
-- QUERY 7: Official Call Next Token Operation (Transactional Atomic Advance)
-- -----------------------------------------------------------------------------
-- UPDATE procurement_centers 
-- SET current_token_seq = current_token_seq + 1 
-- WHERE id = 1 
-- RETURNING current_token_seq;

-- UPDATE tokens 
-- SET status = 'PROCESSING', called_at = CURRENT_TIMESTAMP 
-- WHERE center_id = 1 AND sequence_number = (SELECT current_token_seq FROM procurement_centers WHERE id = 1);
