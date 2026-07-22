-- Danh sách phòng của landlord
SELECT
    r.id,
    r.room_number,
    r.base_price,
    r.status
FROM rooms r
WHERE r.landlord_id = $1
  AND r.status != 'MAINTENANCE'
ORDER BY r.room_number;

-- Hợp đồng đang hoạt động trong kỳ
SELECT
    c.id,
    c.room_id,
    c.tenant_id,
    c.rent_price,
    c.start_date,
    c.end_date,
    c.billing_cycle_days,
    c.is_active,
    t.name AS tenant_name,
    t.phone AS tenant_phone,
    r.room_number,
    r.base_price
FROM contracts c
JOIN rooms r ON c.room_id = r.id
JOIN tenants t ON c.tenant_id = t.id
WHERE c.landlord_id = $1
  AND c.is_active = TRUE
  AND c.start_date <= $3
  AND c.end_date >= $2
ORDER BY r.room_number;

-- Hóa đơn trong kỳ báo cáo
SELECT
    b.id,
    b.contract_id,
    b.period_start,
    b.period_end,
    b.rent_amount,
    b.service_amount,
    b.total_amount,
    b.due_date,
    b.status,
    c.room_id,
    r.room_number
FROM bills b
JOIN contracts c ON b.contract_id = c.id
JOIN rooms r ON c.room_id = r.id
WHERE c.landlord_id = $1
  AND b.period_start >= $2
  AND b.period_end <= $3
ORDER BY r.room_number, b.period_start;

-- Thanh toán trong kỳ
SELECT
    p.id,
    p.bill_id,
    p.paid_amount,
    p.payment_date,
    p.days_late,
    b.contract_id,
    c.room_id,
    r.room_number,
    b.total_amount
FROM payments p
JOIN bills b ON p.bill_id = b.id
JOIN contracts c ON b.contract_id = c.id
JOIN rooms r ON c.room_id = r.id
WHERE c.landlord_id = $1
  AND p.payment_date >= $2
  AND p.payment_date <= $3
ORDER BY r.room_number, p.payment_date;

-- Nhật ký trống phòng giao thoa với kỳ báo cáo
SELECT
    vl.id,
    vl.room_id,
    vl.vacant_from,
    vl.occupied_at,
    r.room_number,
    r.base_price
FROM vacancy_logs vl
JOIN rooms r ON vl.room_id = r.id
WHERE r.landlord_id = $1
  AND vl.vacant_from <= $3
  AND (vl.occupied_at IS NULL OR vl.occupied_at >= $2)
ORDER BY r.room_number, vl.vacant_from;