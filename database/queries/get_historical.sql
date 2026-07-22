-- Doanh thu thực tế theo tháng (12 tháng gần nhất)
SELECT
    DATE_TRUNC('month', p.payment_date)::DATE AS month,
    SUM(p.paid_amount) AS actual_revenue
FROM payments p
JOIN bills b ON p.bill_id = b.id
JOIN contracts c ON b.contract_id = c.id
JOIN rooms r ON c.room_id = r.id
WHERE r.landlord_id = $1
  AND p.payment_date >= $2
  AND p.payment_date <= $3
GROUP BY DATE_TRUNC('month', p.payment_date)
ORDER BY month;

-- Tỷ lệ lấp đầy theo tháng (12 tháng gần nhất)
SELECT
    DATE_TRUNC('month', d)::DATE AS month,
    COUNT(DISTINCT c.id) FILTER (WHERE c.start_date <= d AND c.end_date >= d) AS occupied_rooms,
    COUNT(DISTINCT rm.id) AS total_rooms,
    CASE
        WHEN COUNT(DISTINCT rm.id) > 0
        THEN COUNT(DISTINCT c.id) FILTER (WHERE c.start_date <= d AND c.end_date >= d)::DECIMAL / COUNT(DISTINCT rm.id)
        ELSE 0
    END AS occupancy_rate
FROM rooms rm
LEFT JOIN contracts c ON c.room_id = rm.id
CROSS JOIN GENERATE_SERIES(
    DATE_TRUNC('month', $2)::DATE,
    DATE_TRUNC('month', $3)::DATE,
    '1 month'
) AS d
WHERE rm.landlord_id = $1
GROUP BY DATE_TRUNC('month', d)
ORDER BY month;

-- Thời gian trống phòng trung bình theo tháng
SELECT
    DATE_TRUNC('month', vl.vacant_from)::DATE AS month,
    AVG(
        COALESCE(vl.occupied_at, CURRENT_DATE) - vl.vacant_from
    ) AS avg_vacancy_days
FROM vacancy_logs vl
JOIN rooms r ON vl.room_id = r.id
WHERE r.landlord_id = $1
  AND vl.vacant_from >= $2
  AND vl.vacant_from <= $3
GROUP BY DATE_TRUNC('month', vl.vacant_from)
ORDER BY month;

-- Số hợp đồng sắp hết hạn (trong 30 ngày)
SELECT
    c.id,
    c.room_id,
    c.tenant_id,
    c.end_date,
    r.room_number,
    t.name AS tenant_name,
    t.phone AS tenant_phone
FROM contracts c
JOIN rooms r ON c.room_id = r.id
JOIN tenants t ON c.tenant_id = t.id
WHERE r.landlord_id = $1
  AND c.is_active = TRUE
  AND c.end_date BETWEEN CURRENT_DATE AND CURRENT_DATE + INTERVAL '30 days'
ORDER BY c.end_date;

-- Khách có lịch sử trễ thanh toán (trễ >= 2 lần trong 6 tháng)
SELECT
    t.id AS tenant_id,
    t.name AS tenant_name,
    t.phone AS tenant_phone,
    r.room_number,
    r.id AS room_id,
    COUNT(*) AS late_count,
    MAX(p.days_late) AS max_days_late,
    AVG(p.days_late)::DECIMAL(5,2) AS avg_days_late
FROM payments p
JOIN bills b ON p.bill_id = b.id
JOIN contracts c ON b.contract_id = c.id
JOIN rooms r ON c.room_id = r.id
JOIN tenants t ON c.tenant_id = t.id
WHERE r.landlord_id = $1
  AND p.payment_date >= $2
  AND p.days_late > 0
GROUP BY t.id, t.name, t.phone, r.room_number, r.id
HAVING COUNT(*) >= 2
ORDER BY late_count DESC, max_days_late DESC;

-- Tổng revenue potential theo tháng (dựa trên base_price)
SELECT
    DATE_TRUNC('month', d)::DATE AS month,
    SUM(rm.base_price) AS potential_revenue
FROM rooms rm
CROSS JOIN GENERATE_SERIES(
    DATE_TRUNC('month', $2)::DATE,
    DATE_TRUNC('month', $3)::DATE,
    '1 month'
) AS d
WHERE rm.landlord_id = $1
  AND rm.status != 'MAINTENANCE'
GROUP BY DATE_TRUNC('month', d)
ORDER BY month;