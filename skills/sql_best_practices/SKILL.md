---
name: sql_best_practices
description: Quy tắc và kinh nghiệm viết SQL MySQL chuẩn xác cho dữ liệu quản lý nhà trọ hdbhms.
---

# REPOSITORY QUERY RULES (MYSQL)

## 1. CÚ PHÁP THỜI GIAN
- Dùng `CURDATE()` thay cho `NOW()` khi lấy ngày.
- Định dạng tháng: `DATE_FORMAT(date_col, '%Y-%m')`.
- Luôn escape `%` thành `%%` nếu làm việc với pymysql / format strings.

## 2. QUY TẮC JOIN
- `invoices` JOIN `rooms` qua `i.room_id = r.room_id`.
- `invoices` JOIN `lease_contracts` qua `i.lease_contract_id = lc.lease_contract_id`.
- `payment_allocations` JOIN `invoices` qua `pa.invoice_id = i.invoice_id`.
- `payment_allocations` JOIN `payment_transactions` qua `pa.payment_transaction_id = pt.payment_transaction_id`.

## 3. LỌC AN TOÀN THEO PROPERTY
- Luôn kiểm tra `property_id = $1` ở bảng chính để không bị lộ dữ liệu giữa các khu trọ.
