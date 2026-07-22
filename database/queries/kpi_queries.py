"""
SQL Queries cho AI Financial Copilot — MySQL thuần (không cần _convert_params)
- Tất cả cú pháp MySQL: CURDATE(), DATE_FORMAT, DATEDIFF, DATE_SUB
- Mapping landlord_id → property_id:
  * landlord_id là user_id của OWNER (từ API)
  * Truy vấn property_staff_assignments để lấy property_id
- $N parameters → dùng ? positional placeholder (fastapi aiomysql support)
"""

# ============================================================
# QUERY 1: Revenue KPIs
# ============================================================
REVENUE_KPI_QUERY = """
WITH params AS (
    SELECT $1 AS lid, $2 AS pstart, $3 AS pend, $4 AS pprev, $5 AS pyear_start, $6 AS pyear_end
),
landlord_props AS (
    SELECT property_id FROM property_staff_assignments WHERE staff_user_id = $1 AND assignment_status = 'ACTIVE'
    UNION
    SELECT property_id FROM properties WHERE property_code = 'HAI_DANG_1'
    LIMIT 1
),
current_payments AS (
    SELECT
        COALESCE(SUM(sub.amount), 0) AS total,
        COALESCE(SUM(CASE WHEN sub.effective_type = 'ROOM_RENT' THEN sub.amount ELSE 0 END), 0) AS rent,
        COALESCE(SUM(CASE WHEN sub.effective_type = 'ELECTRICITY' THEN sub.amount ELSE 0 END), 0) AS electricity,
        COALESCE(SUM(CASE WHEN sub.effective_type = 'WATER' THEN sub.amount ELSE 0 END), 0) AS water,
        COALESCE(SUM(CASE WHEN sub.effective_type = 'SERVICE_FEE' THEN sub.amount ELSE 0 END), 0) AS service,
        COALESCE(SUM(CASE WHEN sub.effective_type IN ('OTHER', 'VIOLATION_FINE', 'MAINTENANCE_COMPENSATION', 'TRANSFER_DIFFERENCE', 'MANUAL_ADJUSTMENT') THEN sub.amount ELSE 0 END), 0) AS other
    FROM (
        SELECT DISTINCT pa.payment_allocation_id, pa.amount,
            COALESCE(il.line_type, CASE i.invoice_type WHEN 'RENT' THEN 'ROOM_RENT' ELSE i.invoice_type END) AS effective_type
        FROM payment_transactions pt
        JOIN payment_allocations pa ON pt.payment_transaction_id = pa.payment_transaction_id
        JOIN invoices i ON pa.invoice_id = i.invoice_id
        LEFT JOIN invoice_lines il ON i.invoice_id = il.invoice_id
        CROSS JOIN params, landlord_props lp
        WHERE i.property_id = lp.property_id
          AND pt.transaction_time >= params.pstart
          AND pt.transaction_time < params.pend
          AND pt.status = 'ALLOCATED'
    ) sub
),
prev_month AS (
    SELECT COALESCE(SUM(pa.amount), 0) AS prev_month_total
    FROM payment_transactions pt
    JOIN payment_allocations pa ON pt.payment_transaction_id = pa.payment_transaction_id
    JOIN invoices i ON pa.invoice_id = i.invoice_id
    CROSS JOIN params, landlord_props lp
    WHERE i.property_id = lp.property_id
      AND pt.transaction_time >= params.pprev
      AND pt.transaction_time < params.pstart
      AND pt.status = 'ALLOCATED'
),
prev_year AS (
    SELECT COALESCE(SUM(pa.amount), 0) AS prev_year_total
    FROM payment_transactions pt
    JOIN payment_allocations pa ON pt.payment_transaction_id = pa.payment_transaction_id
    JOIN invoices i ON pa.invoice_id = i.invoice_id
    CROSS JOIN params, landlord_props lp
    WHERE i.property_id = lp.property_id
      AND pt.transaction_time >= params.pyear_start
      AND pt.transaction_time < params.pyear_end
      AND pt.status = 'ALLOCATED'
)
SELECT
    cp.total, cp.rent, cp.electricity, cp.water, cp.service, cp.other,
    COALESCE(pm.prev_month_total, 0) AS previous_total,
    COALESCE(py.prev_year_total, 0) AS year_ago_total
FROM current_payments cp, prev_month pm, prev_year py
"""

# ============================================================
# QUERY 2: Expense KPIs
# ============================================================
EXPENSE_KPI_QUERY = """
WITH params AS (
    SELECT $1 AS lid, $2 AS pstart, $3 AS pend, $4 AS pprev
),
landlord_props AS (
    SELECT property_id FROM property_staff_assignments WHERE staff_user_id = $1 AND assignment_status = 'ACTIVE'
    UNION
    SELECT property_id FROM properties WHERE property_code = 'HAI_DANG_1'
    LIMIT 1
),
exp_invoices AS (
    SELECT
        COALESCE(SUM(CASE WHEN COALESCE(il.line_type, 'ELECTRICITY') = 'ELECTRICITY' THEN COALESCE(il.amount, i.total_amount) ELSE 0 END), 0) AS electricity,
        COALESCE(SUM(CASE WHEN COALESCE(il.line_type, 'WATER') = 'WATER' THEN COALESCE(il.amount, i.total_amount) ELSE 0 END), 0) AS water
    FROM invoices i
    LEFT JOIN invoice_lines il ON i.invoice_id = il.invoice_id
    CROSS JOIN params, landlord_props lp
    WHERE i.property_id = lp.property_id
      AND i.billing_period >= DATE_FORMAT(params.pstart, '%%Y-%%m')
      AND i.billing_period < DATE_FORMAT(params.pend, '%%Y-%%m')
),
exp_maintenance AS (
    SELECT COALESCE(SUM(mc.amount), 0) AS maint
    FROM maintenance_costs mc
    JOIN maintenance_tickets mt ON mc.ticket_id = mt.maintenance_ticket_id
    CROSS JOIN params, landlord_props lp
    WHERE mt.property_id = lp.property_id
      AND mt.completed_at >= params.pstart
      AND mt.completed_at < params.pend
),
prev_exp AS (
    SELECT
        COALESCE(SUM(CASE WHEN COALESCE(il.line_type, 'ELECTRICITY') IN ('ELECTRICITY', 'WATER') THEN COALESCE(il.amount, i.total_amount) ELSE 0 END), 0) AS prev_total
    FROM invoices i
    LEFT JOIN invoice_lines il ON i.invoice_id = il.invoice_id
    CROSS JOIN params, landlord_props lp
    WHERE i.property_id = lp.property_id
      AND i.billing_period >= DATE_FORMAT(params.pprev, '%%Y-%%m')
      AND i.billing_period < DATE_FORMAT(params.pstart, '%%Y-%%m')
)
SELECT
    ei.electricity + ei.water + COALESCE(em.maint, 0) AS total,
    ei.electricity, ei.water,
    COALESCE(em.maint, 0) AS maintenance,
    0 AS penalty, 0 AS other,
    COALESCE(pe.prev_total, 0) AS previous_total
FROM exp_invoices ei, exp_maintenance em, prev_exp pe
"""

# ============================================================
# QUERY 3: Debt KPIs
# ============================================================
DEBT_KPI_QUERY = """
WITH params AS (SELECT $1 AS lid),
landlord_props AS (
    SELECT property_id FROM property_staff_assignments WHERE staff_user_id = $1 AND assignment_status = 'ACTIVE'
    UNION
    SELECT property_id FROM properties WHERE property_code = 'HAI_DANG_1'
    LIMIT 1
),
debt_summary AS (
    SELECT
        SUM(CASE WHEN i.status IN ('ISSUED', 'PARTIALLY_PAID', 'OVERDUE') AND i.due_date < CURDATE() THEN 1 ELSE 0 END) AS overdue_count,
        COALESCE(SUM(CASE WHEN i.status IN ('ISSUED', 'PARTIALLY_PAID', 'OVERDUE') AND i.due_date < CURDATE() THEN i.remaining_amount ELSE 0 END), 0) AS overdue_amount,
        SUM(CASE WHEN i.status = 'PAID' THEN 1 ELSE 0 END) AS paid_count,
        SUM(CASE WHEN i.status IN ('ISSUED', 'PARTIALLY_PAID', 'OVERDUE') THEN 1 ELSE 0 END) AS total_unpaid
    FROM invoices i
    CROSS JOIN params, landlord_props lp
    WHERE i.property_id = lp.property_id
)
SELECT
    CASE WHEN (paid_count + total_unpaid) > 0
         THEN ROUND(100.0 * paid_count / (paid_count + total_unpaid), 1)
         ELSE 100.0 END AS collection_rate,
    COALESCE(overdue_count, 0) AS overdue_count,
    COALESCE(overdue_amount, 0) AS overdue_amount
FROM debt_summary
"""

# ============================================================
# QUERY 4: Debt by Room
# ============================================================
DEBT_BY_ROOM_QUERY = """
WITH params AS (SELECT $1 AS lid),
landlord_props AS (
    SELECT property_id FROM property_staff_assignments WHERE staff_user_id = $1 AND assignment_status = 'ACTIVE'
    UNION
    SELECT property_id FROM properties WHERE property_code = 'HAI_DANG_1'
    LIMIT 1
)
SELECT
    r.room_code AS room,
    i.remaining_amount AS total_debt,
    CASE
        WHEN i.invoice_type = 'UTILITY' THEN 'UTILITY'
        ELSE 'RENT'
    END AS type,
    TIMESTAMPDIFF(MONTH, i.due_date, CURDATE()) AS months
FROM invoices i
JOIN rooms r ON i.room_id = r.room_id
CROSS JOIN params, landlord_props lp
WHERE i.property_id = lp.property_id
  AND i.status IN ('ISSUED', 'PARTIALLY_PAID', 'OVERDUE')
  AND i.remaining_amount > 0
ORDER BY i.remaining_amount DESC
LIMIT 20
"""

# ============================================================
# QUERY 5: Occupancy KPIs
# ============================================================
OCCUPANCY_KPI_QUERY = """
WITH params AS (SELECT $1 AS lid),
landlord_props AS (
    SELECT property_id FROM property_staff_assignments WHERE staff_user_id = $1 AND assignment_status = 'ACTIVE'
    UNION
    SELECT property_id FROM properties WHERE property_code = 'HAI_DANG_1'
    LIMIT 1
),
room_stats AS (
    SELECT
        COUNT(*) AS total_rooms,
        SUM(CASE WHEN r.current_status IN ('OCCUPIED', 'SOON_VACANT', 'EXPIRED') THEN 1 ELSE 0 END) AS occupied_rooms
    FROM rooms r
    CROSS JOIN params, landlord_props lp
    WHERE r.property_id = lp.property_id
      AND r.deleted_at IS NULL
      AND r.current_status != 'MAINTENANCE'
)
SELECT
    COALESCE(rs.total_rooms, 0) AS total_rooms,
    COALESCE(rs.occupied_rooms, 0) AS occupied_rooms,
    COALESCE(rs.total_rooms - rs.occupied_rooms, 0) AS vacant_rooms,
    CASE WHEN COALESCE(rs.total_rooms, 0) > 0
         THEN ROUND(100.0 * rs.occupied_rooms / rs.total_rooms, 1)
         ELSE 0 END AS occupancy_rate
FROM room_stats rs
"""

# ============================================================
# QUERY 6: Monthly Expense History (12 months)
# ============================================================
MONTHLY_EXPENSE_QUERY = """
WITH params AS (SELECT $1 AS lid),
landlord_props AS (
    SELECT property_id FROM property_staff_assignments WHERE staff_user_id = $1 AND assignment_status = 'ACTIVE'
    UNION
    SELECT property_id FROM properties WHERE property_code = 'HAI_DANG_1'
    LIMIT 1
),
months AS (
    SELECT DATE_FORMAT(DATE_SUB(CURDATE(), INTERVAL (11 - t) MONTH), '%%Y-%%m') AS m
    FROM (SELECT 0 AS t UNION ALL SELECT 1 UNION ALL SELECT 2 UNION ALL SELECT 3
          UNION ALL SELECT 4 UNION ALL SELECT 5 UNION ALL SELECT 6 UNION ALL SELECT 7
          UNION ALL SELECT 8 UNION ALL SELECT 9 UNION ALL SELECT 10 UNION ALL SELECT 11) nums
)
SELECT
    m.m AS month,
    COALESCE(
        (SELECT SUM(COALESCE(il.amount, i.total_amount, 0))
         FROM invoices i
         LEFT JOIN invoice_lines il ON i.invoice_id = il.invoice_id
         CROSS JOIN landlord_props lp
         WHERE i.property_id = lp.property_id
           AND i.billing_period = m.m
           AND COALESCE(il.line_type, 'ELECTRICITY') IN ('ELECTRICITY', 'WATER', 'MAINTENANCE', 'OTHER', 'VIOLATION_FINE')
        ), 0
    ) AS total
FROM months m
ORDER BY m.m
"""

# ============================================================
# QUERY 7: Monthly Revenue History (12 months)
# ============================================================
MONTHLY_REVENUE_QUERY = """
WITH params AS (SELECT $1 AS lid),
landlord_props AS (
    SELECT property_id FROM property_staff_assignments WHERE staff_user_id = $1 AND assignment_status = 'ACTIVE'
    UNION
    SELECT property_id FROM properties WHERE property_code = 'HAI_DANG_1'
    LIMIT 1
)
SELECT
    DATE_FORMAT(pt.transaction_time, '%%Y-%%m') AS month,
    SUM(pt.amount) AS total
FROM payment_transactions pt
JOIN payment_allocations pa ON pt.payment_transaction_id = pa.payment_transaction_id
JOIN invoices i ON pa.invoice_id = i.invoice_id
CROSS JOIN params, landlord_props lp
WHERE i.property_id = lp.property_id
  AND pt.transaction_time >= DATE_SUB(CURDATE(), INTERVAL 12 MONTH)
  AND pt.status = 'ALLOCATED'
GROUP BY DATE_FORMAT(pt.transaction_time, '%%Y-%%m')
ORDER BY month
"""

# ============================================================
# QUERY 8: Monthly Occupancy History (12 months) — REAL historical data
# Sử dụng room_status_history để tính occupancy từng tháng thay vì chỉ CURDATE()
# ============================================================
MONTHLY_OCCUPANCY_QUERY = """
WITH params AS (SELECT $1 AS lid),
landlord_props AS (
    SELECT property_id FROM property_staff_assignments WHERE staff_user_id = $1 AND assignment_status = 'ACTIVE'
    UNION
    SELECT property_id FROM properties WHERE property_code = 'HAI_DANG_1'
    LIMIT 1
),
-- 12 months: tính cả month_start và month_end để xác định trạng thái cuối tháng
months AS (
    SELECT
        DATE_FORMAT(DATE_SUB(CURDATE(), INTERVAL (11 - t) MONTH), '%%Y-%%m') AS m,
        LAST_DAY(DATE_SUB(CURDATE(), INTERVAL (11 - t) MONTH)) AS month_end
    FROM (SELECT 0 AS t UNION ALL SELECT 1 UNION ALL SELECT 2 UNION ALL SELECT 3
          UNION ALL SELECT 4 UNION ALL SELECT 5 UNION ALL SELECT 6 UNION ALL SELECT 7
          UNION ALL SELECT 8 UNION ALL SELECT 9 UNION ALL SELECT 10 UNION ALL SELECT 11) nums
),
-- Tất cả rooms (chỉ loại soft-deleted, KHÔNG lọc MAINTENANCE ở đây
-- vì MAINTENANCE là trạng thái lịch sử, cần xử lý theo từng tháng)
active_rooms AS (
    SELECT r.room_id, r.current_status, r.created_at
    FROM rooms r
    CROSS JOIN landlord_props lp
    WHERE r.property_id = lp.property_id
      AND r.deleted_at IS NULL
),
-- Helper: historical_status của mỗi room tại mỗi month_end
-- Tránh lặp correlated subquery 2 lần trong SELECT
-- Nếu không có room_status_history (trống), fallback về current_status cho tất cả months
room_status AS (
    SELECT
        m.m,
        m.month_end,
        ar.room_id,
        COALESCE(
            (SELECT rsh.to_status
             FROM room_status_history rsh
             WHERE rsh.room_id = ar.room_id
               AND rsh.changed_at <= m.month_end
             ORDER BY rsh.changed_at DESC
             LIMIT 1),
            ar.current_status  -- fallback: dùng current_status khi không có history
        ) AS historical_status
    FROM months m
    CROSS JOIN active_rooms ar
)
SELECT
    rs.m AS month,
    -- total_rooms: đếm rooms tồn tại trong tháng đó (không MAINTENANCE, không NULL)
    SUM(CASE WHEN rs.historical_status IS NOT NULL AND rs.historical_status != 'MAINTENANCE' THEN 1 ELSE 0 END) AS total_rooms,
    -- occupied_rooms: rooms có historical_status thuộc diện 'có khách'
    SUM(CASE WHEN rs.historical_status IN ('OCCUPIED', 'SOON_VACANT', 'EXPIRED') THEN 1 ELSE 0 END) AS occupied_rooms,
    CASE WHEN SUM(CASE WHEN rs.historical_status IS NOT NULL AND rs.historical_status != 'MAINTENANCE' THEN 1 ELSE 0 END) > 0
         THEN ROUND(100.0 * SUM(CASE WHEN rs.historical_status IN ('OCCUPIED', 'SOON_VACANT', 'EXPIRED') THEN 1 ELSE 0 END)
                    / SUM(CASE WHEN rs.historical_status IS NOT NULL AND rs.historical_status != 'MAINTENANCE' THEN 1 ELSE 0 END), 1)
         ELSE 0 END AS occupancy_rate
FROM room_status rs
GROUP BY rs.m, rs.month_end
ORDER BY rs.m
"""

# ============================================================
# QUERY 9: Debt Aging
# ============================================================
DEBT_AGING_QUERY = """
WITH params AS (SELECT $1 AS lid),
landlord_props AS (
    SELECT property_id FROM property_staff_assignments WHERE staff_user_id = $1 AND assignment_status = 'ACTIVE'
    UNION
    SELECT property_id FROM properties WHERE property_code = 'HAI_DANG_1'
    LIMIT 1
)
SELECT
    COALESCE(SUM(CASE WHEN i.due_date >= DATE_SUB(CURDATE(), INTERVAL 7 DAY) THEN i.remaining_amount ELSE 0 END), 0) AS age_0_7,
    COALESCE(SUM(CASE WHEN i.due_date < DATE_SUB(CURDATE(), INTERVAL 7 DAY) AND i.due_date >= DATE_SUB(CURDATE(), INTERVAL 30 DAY) THEN i.remaining_amount ELSE 0 END), 0) AS age_8_30,
    COALESCE(SUM(CASE WHEN i.due_date < DATE_SUB(CURDATE(), INTERVAL 30 DAY) AND i.due_date >= DATE_SUB(CURDATE(), INTERVAL 60 DAY) THEN i.remaining_amount ELSE 0 END), 0) AS age_31_60,
    COALESCE(SUM(CASE WHEN i.due_date < DATE_SUB(CURDATE(), INTERVAL 60 DAY) THEN i.remaining_amount ELSE 0 END), 0) AS age_60_plus
FROM invoices i
CROSS JOIN params, landlord_props lp
WHERE i.property_id = lp.property_id
  AND i.status IN ('ISSUED', 'PARTIALLY_PAID', 'OVERDUE')
  AND i.remaining_amount > 0
"""
