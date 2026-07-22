"""
Seed data generator for HDBHMS — MySQL Version
Based on SE Group's V19__seed_floor_4_5_complete_demo.sql structure
Creates demo data for HAI_DANG_1 property with rooms 401-408, 501-507
"""
import os
import logging
from typing import Optional

log = logging.getLogger("ai-property-advisor")

MYSQL_HOST = os.getenv("MYSQL_HOST", "localhost")
MYSQL_PORT = int(os.getenv("MYSQL_PORT", "3306"))
MYSQL_USER = os.getenv("MYSQL_USER", "root")
MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD", "password")
MYSQL_DB = os.getenv("MYSQL_DB", "hdbhms")

PASSWORD_HASH = "$2a$10$2Dy4Vg1B5BKuiUMPRuTAluvk/0XzLuSgLGaABFHCoWHaUfUtDFGqm"

SEED_SQL = """
-- ============================================================
-- SEED DATA: HAI_DANG_1 Property
-- Rooms 401-408 (Floor 4) and 501-507 (Floor 5)
-- ============================================================

-- 1. USERS
INSERT INTO users (phone, email, password_hash, full_name, role, status, last_login_at, email_verified, must_change_password, created_at, updated_at) VALUES
('0988000001', 'demo.owner@hdbhms.local', '""" + PASSWORD_HASH + """', 'Nguyễn Văn A', 'OWNER', 'ACTIVE', '2026-07-10 08:00:00', TRUE, FALSE, '2026-01-01 08:00:00', '2026-07-10 08:00:00'),
('0988000002', 'demo.manager@hdbhms.local', '""" + PASSWORD_HASH + """', 'Trần Mai Quỳnh', 'MANAGER', 'ACTIVE', '2026-07-10 08:10:00', TRUE, FALSE, '2026-01-01 08:05:00', '2026-07-10 08:10:00'),
('0988000003', 'demo.accountant@hdbhms.local', '""" + PASSWORD_HASH + """', 'Lê Hoài An', 'ACCOUNTANT', 'ACTIVE', '2026-07-10 08:20:00', TRUE, FALSE, '2026-01-01 08:10:00', '2026-07-10 08:20:00'),
('0988000004', 'demo.guest@hdbhms.local', '""" + PASSWORD_HASH + """', 'Phạm Gia Hân', 'LEAD', 'ACTIVE', NULL, TRUE, FALSE, '2026-07-01 09:00:00', '2026-07-01 09:00:00'),
('0988404001', 'demo.tenant404@hdbhms.local', '""" + PASSWORD_HASH + """', 'Đỗ Hoàng Anh', 'TENANT', 'ACTIVE', '2026-07-10 19:00:00', TRUE, FALSE, '2025-09-01 08:00:00', '2026-07-10 19:00:00'),
('0988405001', 'demo.tenant405@hdbhms.local', '""" + PASSWORD_HASH + """', 'Nguyễn Minh Khoa', 'TENANT', 'ACTIVE', '2026-07-08 20:00:00', TRUE, FALSE, '2026-01-01 08:00:00', '2026-07-08 20:00:00'),
('0988406001', 'demo.tenant406@hdbhms.local', '""" + PASSWORD_HASH + """', 'Trần Thu Hà', 'TENANT', 'ACTIVE', '2026-07-10 20:00:00', TRUE, FALSE, '2025-09-01 08:00:00', '2026-07-10 20:00:00'),
('0988407001', 'demo.tenant407@hdbhms.local', '""" + PASSWORD_HASH + """', 'Lê Văn Huy', 'TENANT', 'ACTIVE', '2026-07-09 20:00:00', TRUE, FALSE, '2025-07-01 08:00:00', '2026-07-09 20:00:00'),
('0988501001', 'demo.tenant501@hdbhms.local', '""" + PASSWORD_HASH + """', 'Phạm Quốc Bảo', 'TENANT', 'ACTIVE', '2026-07-10 21:00:00', TRUE, FALSE, '2025-10-01 08:00:00', '2026-07-10 21:00:00'),
('0988502001', 'demo.tenant502@hdbhms.local', '""" + PASSWORD_HASH + """', 'Hoàng Mỹ Linh', 'TENANT', 'ACTIVE', '2026-07-10 21:10:00', TRUE, FALSE, '2025-10-01 08:00:00', '2026-07-10 21:10:00'),
('0988503001', 'demo.tenant503@hdbhms.local', '""" + PASSWORD_HASH + """', 'Đặng Thành Nam', 'TENANT', 'ACTIVE', '2026-07-10 21:20:00', TRUE, FALSE, '2025-01-01 08:00:00', '2026-07-10 21:20:00'),
('0988506001', 'demo.tenant506@hdbhms.local', '""" + PASSWORD_HASH + """', 'Ngô Hồng Nhung', 'TENANT', 'ACTIVE', '2026-07-10 21:30:00', TRUE, FALSE, '2025-01-01 08:00:00', '2026-07-10 21:30:00'),
('0988507001', 'demo.tenant507@hdbhms.local', '""" + PASSWORD_HASH + """', 'Đinh Gia Huy', 'TENANT', 'ACTIVE', NULL, TRUE, FALSE, '2024-01-01 08:00:00', '2026-06-30 18:00:00')
ON DUPLICATE KEY UPDATE full_name = VALUES(full_name);

-- 2. PROPERTY
INSERT INTO properties (property_code, name, description, address_street, address_district, address_city, property_type, total_floors, total_rooms, status) VALUES
('HAI_DANG_1', 'Khu trọ Hải Đăng 1', 'Khu trọ trung tâm - Demo Data', '12 Nguyễn Trãi', 'Thanh Xuân', 'Hà Nội', 'APARTMENT', 5, 15, 'ACTIVE')
ON DUPLICATE KEY UPDATE name = VALUES(name);

-- 3. ROOMS (401-408, 501-507)
INSERT INTO rooms (property_id, room_code, room_type, base_price, deposit_amount, area_sqm, capacity, current_status, internal_note) VALUES
((SELECT property_id FROM properties WHERE property_code='HAI_DANG_1'), '401', 'STANDARD', 5000000, 5000000, 25, 2, 'RESERVED_FOR_TRANSFER', 'DEMO: đơn chuyển phòng đã duyệt'),
((SELECT property_id FROM properties WHERE property_code='HAI_DANG_1'), '402', 'STANDARD', 4800000, 4800000, 22, 2, 'RESERVED', 'DEMO: đặt cọc thành công'),
((SELECT property_id FROM properties WHERE property_code='HAI_DANG_1'), '403', 'STANDARD', 5200000, 5200000, 26, 2, 'ON_HOLD', 'DEMO: QR cọc đang chờ'),
((SELECT property_id FROM properties WHERE property_code='HAI_DANG_1'), '404', 'STANDARD', 4900000, 4900000, 24, 3, 'OCCUPIED', 'DEMO: 3 người thuê'),
((SELECT property_id FROM properties WHERE property_code='HAI_DANG_1'), '405', 'STANDARD', 5100000, 5100000, 25, 2, 'OCCUPIED', 'DEMO: có người ở ghép'),
((SELECT property_id FROM properties WHERE property_code='HAI_DANG_1'), '406', 'STANDARD', 5200000, 5200000, 25, 2, 'SOON_VACANT', 'DEMO: sắp chuyển đi'),
((SELECT property_id FROM properties WHERE property_code='HAI_DANG_1'), '407', 'STANDARD', 5400000, 5400000, 28, 2, 'EXPIRED', 'DEMO: hợp đồng hết hạn'),
((SELECT property_id FROM properties WHERE property_code='HAI_DANG_1'), '408', 'STANDARD', 4500000, 4500000, 22, 2, 'MAINTENANCE', 'DEMO: bảo trì'),
((SELECT property_id FROM properties WHERE property_code='HAI_DANG_1'), '501', 'STANDARD', 5200000, 5200000, 25, 2, 'OCCUPIED', 'DEMO: ma trận hóa đơn'),
((SELECT property_id FROM properties WHERE property_code='HAI_DANG_1'), '502', 'STANDARD', 5200000, 5200000, 25, 2, 'OCCUPIED', 'DEMO: vòng đời phiếu sự cố'),
((SELECT property_id FROM properties WHERE property_code='HAI_DANG_1'), '503', 'STANDARD', 4800000, 4800000, 24, 2, 'OCCUPIED', 'DEMO: chờ chuyển phòng'),
((SELECT property_id FROM properties WHERE property_code='HAI_DANG_1'), '504', 'STANDARD', 5400000, 5400000, 28, 2, 'RESERVED_FOR_TRANSFER', 'DEMO: giữ cho chuyển phòng 503'),
((SELECT property_id FROM properties WHERE property_code='HAI_DANG_1'), '505', 'STANDARD', 5600000, 5600000, 30, 2, 'VACANT', 'DEMO: phòng trống'),
((SELECT property_id FROM properties WHERE property_code='HAI_DANG_1'), '506', 'STANDARD', 5400000, 5400000, 26, 2, 'OCCUPIED', 'DEMO: đã gia hạn'),
((SELECT property_id FROM properties WHERE property_code='HAI_DANG_1'), '507', 'STANDARD', 5800000, 5800000, 30, 2, 'VACANT', 'DEMO: đã thanh lý');

-- 4. STAFF ASSIGNMENTS
INSERT INTO property_staff_assignments (property_id, staff_user_id, assigned_role, assignment_status, is_primary, notes, assigned_by_user_id, started_at) VALUES
((SELECT property_id FROM properties WHERE property_code='HAI_DANG_1'), (SELECT user_id FROM users WHERE email='demo.manager@hdbhms.local'), 'MANAGER', 'ACTIVE', TRUE, 'Quản lý chính - dữ liệu demo', (SELECT user_id FROM users WHERE email='demo.owner@hdbhms.local'), '2026-01-01 09:00:00'),
((SELECT property_id FROM properties WHERE property_code='HAI_DANG_1'), (SELECT user_id FROM users WHERE email='demo.accountant@hdbhms.local'), 'ACCOUNTANT', 'ACTIVE', FALSE, 'Kế toán demo', (SELECT user_id FROM users WHERE email='demo.owner@hdbhms.local'), '2026-01-01 09:00:00');

-- 5. INVOICES (sample billing data)
INSERT INTO invoices (invoice_code, property_id, room_id, invoice_type, billing_period, issue_date, due_date, status, total_amount, paid_amount, remaining_amount) VALUES
('DEMO-INV-404-2026-06', (SELECT property_id FROM properties WHERE property_code='HAI_DANG_1'), (SELECT room_id FROM rooms WHERE room_code='404' AND property_id=(SELECT property_id FROM properties WHERE property_code='HAI_DANG_1')), 'RENT', '2026-06', '2026-06-01', '2026-06-15', 'PAID', 2450000, 2450000, 0),
('DEMO-INV-501-2026-06', (SELECT property_id FROM properties WHERE property_code='HAI_DANG_1'), (SELECT room_id FROM rooms WHERE room_code='501' AND property_id=(SELECT property_id FROM properties WHERE property_code='HAI_DANG_1')), 'RENT', '2026-06', '2026-06-01', '2026-06-15', 'ISSUED', 2600000, 0, 2600000),
('DEMO-INV-501-2026-05', (SELECT property_id FROM properties WHERE property_code='HAI_DANG_1'), (SELECT room_id FROM rooms WHERE room_code='501' AND property_id=(SELECT property_id FROM properties WHERE property_code='HAI_DANG_1')), 'RENT', '2026-05', '2026-05-01', '2026-05-15', 'PAID', 2600000, 2600000, 0),
('DEMO-INV-501-2026-07', (SELECT property_id FROM properties WHERE property_code='HAI_DANG_1'), (SELECT room_id FROM rooms WHERE room_code='501' AND property_id=(SELECT property_id FROM properties WHERE property_code='HAI_DANG_1')), 'RENT', '2026-07', '2026-07-01', '2026-07-15', 'DRAFT', 2500000, 0, 2500000),
('DEMO-INV-501-UTILITY-06', (SELECT property_id FROM properties WHERE property_code='HAI_DANG_1'), (SELECT room_id FROM rooms WHERE room_code='501' AND property_id=(SELECT property_id FROM properties WHERE property_code='HAI_DANG_1')), 'UTILITY', '2026-06', '2026-07-01', '2026-07-05', 'PARTIALLY_PAID', 500000, 200000, 300000),
('DEMO-INV-501-OVERDUE-04', (SELECT property_id FROM properties WHERE property_code='HAI_DANG_1'), (SELECT room_id FROM rooms WHERE room_code='501' AND property_id=(SELECT property_id FROM properties WHERE property_code='HAI_DANG_1')), 'UTILITY', '2026-04', '2026-05-01', '2026-05-05', 'OVERDUE', 1000000, 0, 1000000),
('DEMO-INV-404-UTILITY-06', (SELECT property_id FROM properties WHERE property_code='HAI_DANG_1'), (SELECT room_id FROM rooms WHERE room_code='404' AND property_id=(SELECT property_id FROM properties WHERE property_code='HAI_DANG_1')), 'UTILITY', '2026-06', '2026-07-01', '2026-07-05', 'PAID', 70000, 70000, 0);

-- 6. PAYMENT TRANSACTIONS
INSERT INTO payment_transactions (provider, provider_transaction_id, amount, transaction_time, payer_name, content, status) VALUES
('BANK', 'FT26183040402520', 2520000, '2026-07-02 09:00:00', 'Đỗ Hoàng Anh', 'TIEN PHONG DIEN NUOC P404 T06 2026', 'ALLOCATED'),
('PAYOS', 'FT26123050102600', 2600000, '2026-05-03 09:00:00', 'Phạm Quốc Bảo', 'TIEN PHONG P501 T05 2026', 'ALLOCATED'),
('PAYOS', 'FT26185050100200', 200000, '2026-07-03 09:00:00', 'Phạm Quốc Bảo', 'DIEN NUOC P501 T06 2026', 'PARTIALLY_ALLOCATED');

-- 7. PAYMENT ALLOCATIONS
INSERT INTO payment_allocations (payment_transaction_id, invoice_id, amount) VALUES
((SELECT payment_transaction_id FROM payment_transactions WHERE provider='BANK' AND provider_transaction_id='FT26183040402520'),
 (SELECT invoice_id FROM invoices WHERE invoice_code='DEMO-INV-404-2026-06'), 2450000),
((SELECT payment_transaction_id FROM payment_transactions WHERE provider='BANK' AND provider_transaction_id='FT26183040402520'),
 (SELECT invoice_id FROM invoices WHERE invoice_code='DEMO-INV-404-UTILITY-06'), 70000),
((SELECT payment_transaction_id FROM payment_transactions WHERE provider='PAYOS' AND provider_transaction_id='FT26123050102600'),
 (SELECT invoice_id FROM invoices WHERE invoice_code='DEMO-INV-501-2026-05'), 2600000),
((SELECT payment_transaction_id FROM payment_transactions WHERE provider='PAYOS' AND provider_transaction_id='FT26185050100200'),
 (SELECT invoice_id FROM invoices WHERE invoice_code='DEMO-INV-501-UTILITY-06'), 200000);

-- 8. VACANCY LOGS
INSERT INTO vacancy_logs (room_id, property_id, landlord_id, vacant_from, occupied_at, vacancy_reason) VALUES
((SELECT room_id FROM rooms WHERE room_code='505' AND property_id=(SELECT property_id FROM properties WHERE property_code='HAI_DANG_1')),
 (SELECT property_id FROM properties WHERE property_code='HAI_DANG_1'), 1, '2026-06-01', NULL, 'Phòng trống sau khi khách chuyển đi'),
((SELECT room_id FROM rooms WHERE room_code='507' AND property_id=(SELECT property_id FROM properties WHERE property_code='HAI_DANG_1')),
 (SELECT property_id FROM properties WHERE property_code='HAI_DANG_1'), 1, '2026-07-01', NULL, 'Đã thanh lý xong');
""".strip()


def create_seed(db_url: Optional[str] = None) -> None:
    """Create seed data in MySQL database"""
    import aiomysql
    
    async def _seed():
        # Parse URL or use defaults
        if db_url and db_url.startswith("mysql://"):
            parts = db_url.replace("mysql://", "").split("@")
            user_pass = parts[0].split(":")
            host_port_db = parts[1].split("/")
            host_port = host_port_db[0].split(":")
            
            user = user_pass[0]
            password = user_pass[1] if len(user_pass) > 1 else MYSQL_PASSWORD
            host = host_port[0] if host_port[0] else MYSQL_HOST
            port = int(host_port[1]) if len(host_port) > 1 else MYSQL_PORT
            db_name = host_port_db[1] if len(host_port_db) > 1 else MYSQL_DB
        else:
            user, password, host, port, db_name = MYSQL_USER, MYSQL_PASSWORD, MYSQL_HOST, MYSQL_PORT, MYSQL_DB
        
        pool = await aiomysql.create_pool(
            host=host, port=port, user=user, password=password, db=db_name,
            charset='utf8mb4', autocommit=True, minsize=1, maxsize=2
        )
        
        async with pool.acquire() as conn:
            async with conn.cursor() as cursor:
                # Run each statement separately
                for statement in SEED_SQL.split(';'):
                    stmt = statement.strip()
                    if not stmt:
                        continue
                    # Strip leading comment lines
                    lines = [l for l in stmt.split('\n') if not l.strip().startswith('--')]
                    clean_sql = '\n'.join(lines).strip()
                    if not clean_sql:
                        continue
                    try:
                        await cursor.execute(clean_sql)
                    except Exception as e:
                        log.warning("Seed statement warning: %s", str(e)[:100])
            
            log.info("Seed data created successfully in %s@%s/%s", user, host, db_name)
        
        pool.close()
        await pool.wait_closed()
    
    import asyncio
    asyncio.run(_seed())


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    create_seed()
