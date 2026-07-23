-- Pre-seed: Create base data required by V19 seed
-- Property HAI_DANG_1 + 15 rooms + base OWNER user

INSERT INTO hdbhms.properties (property_code, name, address_street, address_ward, address_district, address_city, property_type, total_floors, total_rooms, status, created_at)
VALUES ('HAI_DANG_1', 'Chung cư mini Hải Đăng', 'Số 1 Ngõ 9 Hoàng Quốc Việt', 'Nghĩa Đô', 'Cầu Giấy', 'Hà Nội', 'APARTMENT', 5, 15, 'ACTIVE', '2024-01-01 08:00:00')
ON DUPLICATE KEY UPDATE name=name;

SET @property_id := (SELECT property_id FROM hdbhms.properties WHERE property_code='HAI_DANG_1' LIMIT 1);

-- Insert 15 rooms (401-408, 501-507)
INSERT IGNORE INTO hdbhms.rooms (property_id, room_code, room_type, base_price, deposit_amount, area_sqm, capacity, current_status, internal_note, has_air_conditioner, has_water_heater, has_furniture, has_private_bathroom, has_balcony, has_kitchen, created_at)
VALUES
(@property_id, '401', 'STANDARD', 2500000, 2500000, 22, 2, 'VACANT', 'Phòng tầng 4', TRUE, TRUE, TRUE, TRUE, TRUE, FALSE, '2024-01-01 08:00:00'),
(@property_id, '402', 'STANDARD', 2600000, 2600000, 24, 2, 'VACANT', 'Phòng tầng 4', TRUE, TRUE, TRUE, TRUE, TRUE, FALSE, '2024-01-01 08:00:00'),
(@property_id, '403', 'STANDARD', 2600000, 2600000, 23, 2, 'VACANT', 'Phòng tầng 4', TRUE, TRUE, TRUE, TRUE, FALSE, FALSE, '2024-01-01 08:00:00'),
(@property_id, '404', 'STANDARD', 2450000, 2450000, 25, 3, 'VACANT', 'Phòng tầng 4 - 3 người', TRUE, TRUE, TRUE, TRUE, TRUE, FALSE, '2024-01-01 08:00:00'),
(@property_id, '405', 'STANDARD', 2550000, 2550000, 22, 2, 'VACANT', 'Phòng tầng 4', TRUE, TRUE, TRUE, TRUE, FALSE, FALSE, '2024-01-01 08:00:00'),
(@property_id, '406', 'STANDARD', 2600000, 2600000, 24, 2, 'VACANT', 'Phòng tầng 4', TRUE, TRUE, TRUE, TRUE, TRUE, FALSE, '2024-01-01 08:00:00'),
(@property_id, '407', 'STANDARD', 2700000, 2700000, 26, 2, 'VACANT', 'Phòng tầng 4 - rộng', TRUE, TRUE, TRUE, TRUE, TRUE, TRUE, '2024-01-01 08:00:00'),
(@property_id, '408', 'STANDARD', 3000000, 3000000, 28, 2, 'VACANT', 'Phòng tầng 4 - lớn nhất', TRUE, TRUE, TRUE, TRUE, TRUE, TRUE, '2024-01-01 08:00:00'),
(@property_id, '501', 'STANDARD', 2600000, 2600000, 22, 2, 'VACANT', 'Phòng tầng 5', TRUE, TRUE, TRUE, TRUE, TRUE, FALSE, '2024-01-01 08:00:00'),
(@property_id, '502', 'STANDARD', 2600000, 2600000, 23, 2, 'VACANT', 'Phòng tầng 5', TRUE, TRUE, TRUE, TRUE, TRUE, FALSE, '2024-01-01 08:00:00'),
(@property_id, '503', 'STANDARD', 2400000, 2400000, 20, 2, 'VACANT', 'Phòng tầng 5 - nhỏ', TRUE, TRUE, TRUE, TRUE, FALSE, FALSE, '2024-01-01 08:00:00'),
(@property_id, '504', 'STANDARD', 2700000, 2700000, 25, 2, 'VACANT', 'Phòng tầng 5', TRUE, TRUE, TRUE, TRUE, TRUE, FALSE, '2024-01-01 08:00:00'),
(@property_id, '505', 'STANDARD', 2800000, 2800000, 24, 2, 'VACANT', 'Phòng tầng 5', TRUE, TRUE, TRUE, TRUE, TRUE, TRUE, '2024-01-01 08:00:00'),
(@property_id, '506', 'STANDARD', 2700000, 2700000, 23, 2, 'VACANT', 'Phòng tầng 5', TRUE, TRUE, TRUE, TRUE, TRUE, FALSE, '2024-01-01 08:00:00'),
(@property_id, '507', 'STANDARD', 2900000, 2900000, 26, 2, 'VACANT', 'Phòng tầng 5 - Rộng, view đẹp', TRUE, TRUE, TRUE, TRUE, TRUE, TRUE, '2024-01-01 08:00:00');

-- Create a base OWNER user (required by V19 seed for existing_owner_id)
INSERT IGNORE INTO hdbhms.users (phone, email, password_hash, role, status, email_verified, created_at, updated_at)
VALUES ('0988000001', 'owner@hdbhms.local', '$2a$10$2Dy4Vg1B5BKuiUMPRuTAluvk/0XzLuSgLGaABFHCoWHaUfUtDFGqm', 'OWNER', 'ACTIVE', TRUE, '2024-01-01 08:00:00', '2024-01-01 08:00:00');

-- ============================================================
-- STEP 1: Update Room Statuses
-- ============================================================
UPDATE hdbhms.rooms SET current_status='OCCUPIED', internal_note='3 người thuê', updated_at=NOW() WHERE property_id=@property_id AND room_code='404';
UPDATE hdbhms.rooms SET current_status='OCCUPIED', internal_note='Có người ở chung chờ hoàn thiện hồ sơ', updated_at=NOW() WHERE property_id=@property_id AND room_code='405';
UPDATE hdbhms.rooms SET current_status='SOON_VACANT', internal_note='Hợp đồng sắp hết hạn, có công nợ', updated_at=NOW() WHERE property_id=@property_id AND room_code='406';
UPDATE hdbhms.rooms SET current_status='EXPIRED', internal_note='Hợp đồng đã hết hạn', updated_at=NOW() WHERE property_id=@property_id AND room_code='407';
UPDATE hdbhms.rooms SET current_status='MAINTENANCE', internal_note='Bảo trì hệ thống điện', updated_at=NOW() WHERE property_id=@property_id AND room_code='408';
UPDATE hdbhms.rooms SET current_status='OCCUPIED', internal_note='Ma trận hóa đơn/công nợ', updated_at=NOW() WHERE property_id=@property_id AND room_code='501';
UPDATE hdbhms.rooms SET current_status='OCCUPIED', internal_note='Vòng đời phiếu sự cố', updated_at=NOW() WHERE property_id=@property_id AND room_code='502';
UPDATE hdbhms.rooms SET current_status='OCCUPIED', internal_note='Chuyển phòng', updated_at=NOW() WHERE property_id=@property_id AND room_code='503';
UPDATE hdbhms.rooms SET current_status='VACANT', internal_note='Phòng trống; có lịch sử', updated_at=NOW() WHERE property_id=@property_id AND room_code='505';
UPDATE hdbhms.rooms SET current_status='OCCUPIED', internal_note='Hợp đồng gia hạn', updated_at=NOW() WHERE property_id=@property_id AND room_code='506';
UPDATE hdbhms.rooms SET current_status='VACANT', internal_note='Đã thanh lý', updated_at=NOW() WHERE property_id=@property_id AND room_code='507';

-- ============================================================
-- STEP 2: Create Demo Users
-- ============================================================
SET @password_hash := '$2a$10$2Dy4Vg1B5BKuiUMPRuTAluvk/0XzLuSgLGaABFHCoWHaUfUtDFGqm';

INSERT IGNORE INTO hdbhms.users (phone, email, password_hash, role, status, last_login_at, email_verified, must_change_password, created_at, updated_at)
VALUES
('0988000002','demo.manager@hdbhms.local',@password_hash,'MANAGER','ACTIVE','2026-07-10 08:10:00',TRUE,FALSE,'2026-01-01 08:05:00','2026-07-10 08:10:00'),
('0988000003','demo.accountant@hdbhms.local',@password_hash,'ACCOUNTANT','ACTIVE','2026-07-10 08:20:00',TRUE,FALSE,'2026-01-01 08:10:00','2026-07-10 08:20:00'),
('0988000004','demo.guest@hdbhms.local',@password_hash,'LEAD','PENDING_CONTRACT',NULL,TRUE,FALSE,'2026-07-01 09:00:00','2026-07-01 09:00:00'),
('0988404001','demo.tenant404@hdbhms.local',@password_hash,'TENANT','ACTIVE','2026-07-10 19:00:00',TRUE,FALSE,'2025-09-01 08:00:00','2026-07-10 19:00:00'),
('0988404002','demo.tenant404.co1@hdbhms.local',@password_hash,'TENANT','ACTIVE','2026-07-09 19:00:00',TRUE,FALSE,'2025-09-01 08:05:00','2026-07-09 19:00:00'),
('0988404003','demo.tenant404.co2@hdbhms.local',@password_hash,'TENANT','ACTIVE',NULL,TRUE,FALSE,'2025-09-01 08:10:00','2025-09-01 08:10:00'),
('0988405001','demo.tenant405@hdbhms.local',@password_hash,'TENANT','ACTIVE','2026-07-08 20:00:00',TRUE,FALSE,'2026-01-01 08:00:00','2026-07-08 20:00:00'),
('0988405002','demo.tenant405.pending@hdbhms.local',@password_hash,'TENANT','PENDING_CONTRACT',NULL,FALSE,TRUE,'2026-07-05 08:00:00','2026-07-05 08:00:00'),
('0988406001','demo.tenant406@hdbhms.local',@password_hash,'TENANT','ACTIVE','2026-07-10 20:00:00',TRUE,FALSE,'2025-09-01 08:00:00','2026-07-10 20:00:00'),
('0988407001','demo.tenant407@hdbhms.local',@password_hash,'TENANT','ACTIVE','2026-07-09 20:00:00',TRUE,FALSE,'2025-07-01 08:00:00','2026-07-09 20:00:00'),
('0988501001','demo.tenant501@hdbhms.local',@password_hash,'TENANT','ACTIVE','2026-07-10 21:00:00',TRUE,FALSE,'2025-10-01 08:00:00','2026-07-10 21:00:00'),
('0988502001','demo.tenant502@hdbhms.local',@password_hash,'TENANT','ACTIVE','2026-07-10 21:10:00',TRUE,FALSE,'2025-10-01 08:00:00','2026-07-10 21:10:00'),
('0988503001','demo.tenant503@hdbhms.local',@password_hash,'TENANT','ACTIVE','2026-07-10 21:20:00',TRUE,FALSE,'2025-01-01 08:00:00','2026-07-10 21:20:00'),
('0988506001','demo.tenant506@hdbhms.local',@password_hash,'TENANT','ACTIVE','2026-07-10 21:30:00',TRUE,FALSE,'2025-01-01 08:00:00','2026-07-10 21:30:00'),
('0988507001','demo.tenant507.history@hdbhms.local',@password_hash,'TENANT','ACTIVE',NULL,TRUE,FALSE,'2024-01-01 08:00:00','2026-06-30 18:00:00');

-- ============================================================
-- STEP 3: Person Profiles
-- ============================================================
INSERT IGNORE INTO hdbhms.person_profiles (user_id, full_name, dob, gender, phone, email, permanent_address, created_at, updated_at)
SELECT u.user_id, d.full_name, d.dob, d.gender, u.phone, d.email, d.address, d.created_at, d.created_at FROM (
    SELECT 'demo.manager@hdbhms.local' email, 'Trần Mai Quỳnh' full_name, '1990-03-20' dob, 'FEMALE' gender, 'Hà Nội' address, '2026-01-01 08:05:00' created_at UNION ALL
    SELECT 'demo.accountant@hdbhms.local','Lê Hoài An','1992-09-18','FEMALE','Hà Nội','2026-01-01 08:10:00' UNION ALL
    SELECT 'demo.tenant404@hdbhms.local','Đỗ Hoàng Anh','2002-01-15','MALE','Hà Nội','2025-09-01 08:00:00' UNION ALL
    SELECT 'demo.tenant404.co1@hdbhms.local','Vũ Ngọc Mai','2002-06-21','FEMALE','Hà Nội','2025-09-01 08:05:00' UNION ALL
    SELECT 'demo.tenant404.co2@hdbhms.local','Bùi Đức Long','2001-11-02','MALE','Hà Nội','2025-09-01 08:10:00' UNION ALL
    SELECT 'demo.tenant405@hdbhms.local','Nguyễn Minh Khoa','2001-08-09','MALE','Hà Nam','2026-01-01 08:00:00' UNION ALL
    SELECT 'demo.tenant406@hdbhms.local','Trần Thu Hà','2000-12-12','FEMALE','Nam Định','2025-09-01 08:00:00' UNION ALL
    SELECT 'demo.tenant407@hdbhms.local','Lê Văn Huy','1999-07-07','MALE','Thái Bình','2025-07-01 08:00:00' UNION ALL
    SELECT 'demo.tenant501@hdbhms.local','Phạm Quốc Bảo','2002-02-14','MALE','Ninh Bình','2025-10-01 08:00:00' UNION ALL
    SELECT 'demo.tenant502@hdbhms.local','Hoàng Mỹ Linh','2002-10-10','FEMALE','Hải Dương','2025-10-01 08:00:00' UNION ALL
    SELECT 'demo.tenant503@hdbhms.local','Đặng Thành Nam','2000-05-05','MALE','Hà Nội','2025-01-01 08:00:00' UNION ALL
    SELECT 'demo.tenant506@hdbhms.local','Ngô Hồng Nhung','2001-03-03','FEMALE','Bắc Ninh','2025-01-01 08:00:00' UNION ALL
    SELECT 'demo.tenant507.history@hdbhms.local','Đinh Gia Huy','1999-09-09','MALE','Hà Nội','2024-01-01 08:00:00'
) d JOIN hdbhms.users u ON u.email=d.email AND u.deleted_at IS NULL;

-- ============================================================
-- STEP 4: Room Status History
-- ============================================================
INSERT IGNORE INTO hdbhms.room_status_history (room_id, from_status, to_status, reason, changed_by, changed_at)
SELECT r.room_id, 'VACANT', s.to_status, s.reason, s.changed_by, s.changed_at
FROM hdbhms.rooms r
JOIN (
    SELECT '404' rc, 'OCCUPIED' to_status, 'Hợp đồng thuê đã kích hoạt' reason, @approver_id changed_by, '2025-09-01 09:00:00' changed_at UNION ALL
    SELECT '405','OCCUPIED','Hợp đồng thuê đã kích hoạt',@approver_id,'2026-01-01 09:00:00' UNION ALL
    SELECT '406','SOON_VACANT','Người thuê xác nhận chuyển đi',@manager_id,'2026-06-01 09:00:00' UNION ALL
    SELECT '407','EXPIRED','Hợp đồng hết hạn',NULL,'2026-07-06 00:00:00' UNION ALL
    SELECT '501','OCCUPIED','Hợp đồng thuê đã kích hoạt',@approver_id,'2025-10-01 09:00:00' UNION ALL
    SELECT '502','OCCUPIED','Hợp đồng thuê đã kích hoạt',@approver_id,'2025-10-01 09:00:00' UNION ALL
    SELECT '503','OCCUPIED','Hợp đồng thuê đã kích hoạt',@approver_id,'2025-01-01 09:00:00' UNION ALL
    SELECT '506','OCCUPIED','Hợp đồng gia hạn',@approver_id,'2026-01-01 09:00:00'
) s ON r.room_code = s.rc AND r.property_id=@property_id AND r.deleted_at IS NULL
WHERE NOT EXISTS (SELECT 1 FROM hdbhms.room_status_history h WHERE h.room_id = r.room_id AND h.to_status = s.to_status);

-- ============================================================
-- STEP 5: Role Promotions & Staff Assignments
-- ============================================================
SET @manager_id := (SELECT user_id FROM hdbhms.users WHERE email='demo.manager@hdbhms.local' AND deleted_at IS NULL LIMIT 1);
SET @accountant_id := (SELECT user_id FROM hdbhms.users WHERE email='demo.accountant@hdbhms.local' AND deleted_at IS NULL LIMIT 1);
SET @existing_owner_id := (SELECT user_id FROM hdbhms.users WHERE role='OWNER' AND status='ACTIVE' AND deleted_at IS NULL ORDER BY user_id LIMIT 1);
SET @approver_id := COALESCE(@existing_owner_id, @manager_id);

INSERT IGNORE INTO hdbhms.role_promotions (user_id, role, status, property_id, approved_at, created_at, updated_at)
VALUES
(@manager_id, 'MANAGER', 'ACTIVE', @property_id, NOW(), NOW(), NOW()),
(@accountant_id, 'ACCOUNTANT', 'ACTIVE', @property_id, NOW(), NOW(), NOW());

INSERT IGNORE INTO hdbhms.property_staff_assignments (property_id, staff_user_id, assigned_role, assignment_status, is_primary, notes, assigned_by_user_id, started_at, created_at, updated_at)
VALUES
(@property_id, @manager_id, 'MANAGER', 'ACTIVE', TRUE, 'Quản lý chính - dữ liệu demo', @approver_id, '2026-01-01 09:00:00', NOW(), NOW()),
(@property_id, @accountant_id, 'ACCOUNTANT', 'ACTIVE', FALSE, 'Kế toán demo chỉ xem báo cáo', @approver_id, '2026-01-01 09:00:00', NOW(), NOW());

-- ============================================================
-- STEP 6: Utility Tariffs
-- ============================================================
INSERT IGNORE INTO hdbhms.utility_tariffs (property_id, utility_type, unit_price, free_allowance, service_fee_waive_electricity_threshold, effective_from, created_by, created_at)
VALUES
(@property_id, 'ELECTRICITY', 3500, 0, NULL, '2026-01-01', @approver_id, NOW()),
(@property_id, 'WATER', 20000, 6, NULL, '2026-01-01', @approver_id, NOW()),
(@property_id, 'SERVICE_FEE', 50000, 0, 100000, '2026-01-01', @approver_id, NOW());

-- ============================================================
-- STEP 7: Collection Accounts
-- ============================================================
INSERT IGNORE INTO hdbhms.collection_accounts (property_id, account_type, bank_name, account_number, account_holder, provider, status, created_at)
VALUES
(@property_id, 'RENT', 'Ngân hàng TMCP Quân Đội', '190368040401', 'CÔNG TY TNHH DỊCH VỤ HẢI ĐĂNG', 'BANK', 'ACTIVE', NOW()),
(@property_id, 'UTILITY', 'Ngân hàng TMCP Ngoại thương Việt Nam', '1029995501', 'CÔNG TY TNHH DỊCH VỤ HẢI ĐĂNG', 'BANK', 'ACTIVE', NOW()),
(@property_id, 'DEPOSIT', 'Ngân hàng TMCP Đầu tư và Phát triển Việt Nam', '2151000888402', 'CÔNG TY TNHH DỊCH VỤ HẢI ĐĂNG', 'BANK', 'ACTIVE', NOW());

SET @rent_account := (SELECT collection_account_id FROM hdbhms.collection_accounts WHERE account_number='190368040401' LIMIT 1);
SET @utility_account := (SELECT collection_account_id FROM hdbhms.collection_accounts WHERE account_number='1029995501' LIMIT 1);

-- ============================================================
-- STEP 8: Meters
-- ============================================================
INSERT IGNORE INTO hdbhms.meters (room_id, meter_type, meter_code, status, installed_at, created_at)
SELECT r.room_id, m.meter_type, CONCAT('DEMO-', m.prefix, '-', r.room_code), 'ACTIVE', '2025-01-01', NOW()
FROM hdbhms.rooms r
JOIN (SELECT 'ELECTRICITY' meter_type, 'E' prefix UNION ALL SELECT 'WATER', 'W') m
WHERE r.property_id=@property_id AND r.room_code IN ('401','402','403','404','405','406','407','408','501','502','503','504','505','506','507')
AND r.deleted_at IS NULL;

-- ============================================================
-- STEP 9: Lease Contracts
-- ============================================================
SET @r404 := (SELECT room_id FROM hdbhms.rooms WHERE property_id=@property_id AND room_code='404' AND deleted_at IS NULL LIMIT 1);
SET @r405 := (SELECT room_id FROM hdbhms.rooms WHERE property_id=@property_id AND room_code='405' AND deleted_at IS NULL LIMIT 1);
SET @r406 := (SELECT room_id FROM hdbhms.rooms WHERE property_id=@property_id AND room_code='406' AND deleted_at IS NULL LIMIT 1);
SET @r407 := (SELECT room_id FROM hdbhms.rooms WHERE property_id=@property_id AND room_code='407' AND deleted_at IS NULL LIMIT 1);
SET @r501 := (SELECT room_id FROM hdbhms.rooms WHERE property_id=@property_id AND room_code='501' AND deleted_at IS NULL LIMIT 1);
SET @r502 := (SELECT room_id FROM hdbhms.rooms WHERE property_id=@property_id AND room_code='502' AND deleted_at IS NULL LIMIT 1);
SET @r503 := (SELECT room_id FROM hdbhms.rooms WHERE property_id=@property_id AND room_code='503' AND deleted_at IS NULL LIMIT 1);
SET @r506 := (SELECT room_id FROM hdbhms.rooms WHERE property_id=@property_id AND room_code='506' AND deleted_at IS NULL LIMIT 1);

INSERT IGNORE INTO hdbhms.lease_contracts (contract_code, room_id, primary_tenant_profile_id, start_date, end_date, rent_start_date, monthly_rent, payment_cycle_months, deposit_amount, status, created_by, created_at, updated_at)
SELECT * FROM (
    SELECT 'DEMO-LEASE-404-ACTIVE' cc, @r404 room, pp.person_profile_id pid, '2025-09-01' sd, '2027-08-31' ed, '2025-09-01' rs, 2450000 mr, 1 pcm, 2450000 da, 'ACTIVE' st, u.user_id cb, '2025-09-01 09:00:00' ca, '2025-09-01 09:00:00' ua FROM hdbhms.users u JOIN hdbhms.person_profiles pp ON pp.user_id=u.user_id WHERE u.email='demo.tenant404@hdbhms.local' AND NOT EXISTS (SELECT 1 FROM hdbhms.lease_contracts lc WHERE lc.contract_code='DEMO-LEASE-404-ACTIVE')
    UNION ALL
    SELECT 'DEMO-LEASE-405-ACTIVE',@r405,pp.person_profile_id,'2026-01-01','2026-12-31','2026-01-01',2550000,1,2550000,'ACTIVE',u.user_id,'2026-01-01 09:00:00','2026-01-01 09:00:00' FROM hdbhms.users u JOIN hdbhms.person_profiles pp ON pp.user_id=u.user_id WHERE u.email='demo.tenant405@hdbhms.local' AND NOT EXISTS (SELECT 1 FROM hdbhms.lease_contracts lc WHERE lc.contract_code='DEMO-LEASE-405-ACTIVE')
    UNION ALL
    SELECT 'DEMO-LEASE-406-EXPIRING',@r406,pp.person_profile_id,'2025-09-01','2026-08-31','2025-09-01',2600000,3,2600000,'EXPIRING_SOON',u.user_id,'2025-09-01 09:00:00','2025-09-01 09:00:00' FROM hdbhms.users u JOIN hdbhms.person_profiles pp ON pp.user_id=u.user_id WHERE u.email='demo.tenant406@hdbhms.local' AND NOT EXISTS (SELECT 1 FROM hdbhms.lease_contracts lc WHERE lc.contract_code='DEMO-LEASE-406-EXPIRING')
    UNION ALL
    SELECT 'DEMO-LEASE-407-EXPIRED',@r407,pp.person_profile_id,'2025-07-01','2026-07-05','2025-07-01',2700000,1,2700000,'EXPIRED',u.user_id,'2025-07-01 09:00:00','2025-07-01 09:00:00' FROM hdbhms.users u JOIN hdbhms.person_profiles pp ON pp.user_id=u.user_id WHERE u.email='demo.tenant407@hdbhms.local' AND NOT EXISTS (SELECT 1 FROM hdbhms.lease_contracts lc WHERE lc.contract_code='DEMO-LEASE-407-EXPIRED')
    UNION ALL
    SELECT 'DEMO-LEASE-501-ACTIVE',@r501,pp.person_profile_id,'2025-10-01','2027-09-30','2025-10-01',2600000,1,2600000,'ACTIVE',u.user_id,'2025-10-01 09:00:00','2025-10-01 09:00:00' FROM hdbhms.users u JOIN hdbhms.person_profiles pp ON pp.user_id=u.user_id WHERE u.email='demo.tenant501@hdbhms.local' AND NOT EXISTS (SELECT 1 FROM hdbhms.lease_contracts lc WHERE lc.contract_code='DEMO-LEASE-501-ACTIVE')
    UNION ALL
    SELECT 'DEMO-LEASE-502-ACTIVE',@r502,pp.person_profile_id,'2025-10-01','2027-09-30','2025-10-01',2600000,1,2600000,'ACTIVE',u.user_id,'2025-10-01 09:00:00','2025-10-01 09:00:00' FROM hdbhms.users u JOIN hdbhms.person_profiles pp ON pp.user_id=u.user_id WHERE u.email='demo.tenant502@hdbhms.local' AND NOT EXISTS (SELECT 1 FROM hdbhms.lease_contracts lc WHERE lc.contract_code='DEMO-LEASE-502-ACTIVE')
    UNION ALL
    SELECT 'DEMO-LEASE-503-ACTIVE',@r503,pp.person_profile_id,'2025-01-01','2027-12-31','2025-01-01',2400000,3,2400000,'ACTIVE',u.user_id,'2025-01-01 09:00:00','2025-01-01 09:00:00' FROM hdbhms.users u JOIN hdbhms.person_profiles pp ON pp.user_id=u.user_id WHERE u.email='demo.tenant503@hdbhms.local' AND NOT EXISTS (SELECT 1 FROM hdbhms.lease_contracts lc WHERE lc.contract_code='DEMO-LEASE-503-ACTIVE')
    UNION ALL
    SELECT 'DEMO-LEASE-506-ACTIVE',@r506,pp.person_profile_id,'2026-01-01','2026-12-31','2026-01-01',2700000,1,2700000,'ACTIVE',u.user_id,'2026-01-01 09:00:00','2026-01-01 09:00:00' FROM hdbhms.users u JOIN hdbhms.person_profiles pp ON pp.user_id=u.user_id WHERE u.email='demo.tenant506@hdbhms.local' AND NOT EXISTS (SELECT 1 FROM hdbhms.lease_contracts lc WHERE lc.contract_code='DEMO-LEASE-506-ACTIVE')
) sub;

-- ============================================================
-- STEP 10: Invoices
-- ============================================================
SET @c404 := (SELECT lease_contract_id FROM hdbhms.lease_contracts WHERE contract_code='DEMO-LEASE-404-ACTIVE' LIMIT 1);
SET @c501 := (SELECT lease_contract_id FROM hdbhms.lease_contracts WHERE contract_code='DEMO-LEASE-501-ACTIVE' LIMIT 1);
SET @r404 := (SELECT room_id FROM hdbhms.rooms WHERE property_id=@property_id AND room_code='404' AND deleted_at IS NULL LIMIT 1);
SET @r501 := (SELECT room_id FROM hdbhms.rooms WHERE property_id=@property_id AND room_code='501' AND deleted_at IS NULL LIMIT 1);

INSERT IGNORE INTO hdbhms.invoices (invoice_code, property_id, room_id, lease_contract_id, invoice_type, revision_no, billing_period, issue_date, due_date, status, subtotal_amount, total_amount, paid_amount, remaining_amount, collection_account_id, created_by, created_at, updated_at)
VALUES
('DEMO-INV-404-2026-06-RENT', @property_id, @r404, @c404, 'RENT', 1, '2026-06', '2026-06-01 08:00:00', '2026-06-15 23:59:59', 'PAID', 2450000, 2450000, 2450000, 0, @rent_account, @manager_id, '2026-06-01 08:00:00', '2026-06-02 09:00:00'),
('DEMO-INV-501-2026-06-RENT', @property_id, @r501, @c501, 'RENT', 1, '2026-06', '2026-06-01 08:00:00', '2026-06-15 23:59:59', 'ISSUED', 2600000, 2600000, 0, 2600000, @rent_account, @manager_id, '2026-06-01 08:00:00', '2026-06-01 08:00:00'),
('DEMO-INV-501-2026-06-UTILITY', @property_id, @r501, @c501, 'UTILITY', 1, '2026-06', '2026-07-01 08:00:00', '2026-07-05 23:59:59', 'PARTIALLY_PAID', 500000, 500000, 200000, 300000, @utility_account, @manager_id, '2026-07-01 08:00:00', '2026-07-03 09:00:00'),
('DEMO-INV-501-2026-05-RENT', @property_id, @r501, @c501, 'RENT', 1, '2026-05', '2026-05-01 08:00:00', '2026-05-15 23:59:59', 'PAID', 2600000, 2600000, 2600000, 0, @rent_account, @manager_id, '2026-05-01 08:00:00', '2026-05-03 09:00:00'),
('DEMO-INV-501-2026-04-OVERDUE', @property_id, @r501, @c501, 'UTILITY', 1, '2026-04', '2026-05-01 08:00:00', '2026-05-05 23:59:59', 'OVERDUE', 1000000, 1000000, 0, 1000000, @utility_account, @manager_id, '2026-05-01 08:00:00', '2026-05-06 00:00:00'),
('DEMO-INV-501-WIFI-FINE', @property_id, @r501, @c501, 'OTHER', 1, '2026-06', '2026-06-20 08:00:00', '2026-06-25 23:59:59', 'ISSUED', 200000, 200000, 0, 200000, @rent_account, @manager_id, '2026-06-20 08:00:00', '2026-06-20 08:00:00'),
('DEMO-INV-501-2026-07-DRAFT', @property_id, @r501, @c501, 'RENT', 1, '2026-07', '2026-07-01 08:00:00', '2026-07-15 23:59:59', 'DRAFT', 2500000, 2500000, 0, 2500000, @rent_account, @manager_id, '2026-07-01 08:00:00', '2026-07-01 08:00:00'),
('DEMO-INV-404-2026-05-RENT', @property_id, @r404, @c404, 'RENT', 1, '2026-05', '2026-05-01 08:00:00', '2026-05-15 23:59:59', 'PAID', 2450000, 2450000, 2450000, 0, @rent_account, @manager_id, '2026-05-01 08:00:00', '2026-05-03 09:00:00');

-- ============================================================
-- STEP 11: Invoice Lines
-- ============================================================
SET @inv404r := (SELECT invoice_id FROM hdbhms.invoices WHERE invoice_code='DEMO-INV-404-2026-06-RENT' LIMIT 1);
SET @inv501r := (SELECT invoice_id FROM hdbhms.invoices WHERE invoice_code='DEMO-INV-501-2026-06-RENT' LIMIT 1);
SET @inv501u := (SELECT invoice_id FROM hdbhms.invoices WHERE invoice_code='DEMO-INV-501-2026-06-UTILITY' LIMIT 1);
SET @inv501p := (SELECT invoice_id FROM hdbhms.invoices WHERE invoice_code='DEMO-INV-501-2026-05-RENT' LIMIT 1);
SET @inv501o := (SELECT invoice_id FROM hdbhms.invoices WHERE invoice_code='DEMO-INV-501-2026-04-OVERDUE' LIMIT 1);
SET @inv501f := (SELECT invoice_id FROM hdbhms.invoices WHERE invoice_code='DEMO-INV-501-WIFI-FINE' LIMIT 1);

INSERT IGNORE INTO hdbhms.invoice_lines (invoice_id, line_type, description, quantity, unit_price, created_at)
VALUES
(@inv404r, 'ROOM_RENT', 'Tiền phòng 404 tháng 06/2026', 1, 2450000, '2026-06-01 08:00:00'),
(@inv501r, 'ROOM_RENT', 'Tiền phòng 501 tháng 06/2026 chưa thanh toán', 1, 2600000, '2026-06-01 08:00:00'),
(@inv501u, 'ELECTRICITY', 'Điện 90 kWh', 90, 3500, '2026-07-01 08:00:00'),
(@inv501u, 'WATER', 'Nước sau định mức', 2, 20000, '2026-07-01 08:00:00'),
(@inv501u, 'SERVICE_FEE', 'Phí dịch vụ tháng 06/2026', 1, 50000, '2026-07-01 08:00:00'),
(@inv501p, 'ROOM_RENT', 'Tiền phòng 501 tháng 05/2026', 1, 2600000, '2026-05-01 08:00:00'),
(@inv501o, 'ELECTRICITY', 'Điện kỳ 04/2026', 30, 3500, '2026-05-01 08:00:00'),
(@inv501o, 'WATER', 'Nước kỳ 04/2026', 1, 20000, '2026-05-01 08:00:00'),
(@inv501o, 'SERVICE_FEE', 'Phí dịch vụ kỳ 04/2026', 1, 50000, '2026-05-01 08:00:00'),
(@inv501o, 'MANUAL_ADJUSTMENT', 'Khoản phát sinh quá hạn', 1, 825000, '2026-05-01 08:00:00'),
(@inv501f, 'VIOLATION_FINE', 'Phạt tự ý reset modem Wi-Fi', 1, 200000, '2026-06-20 08:00:00'),
((SELECT invoice_id FROM hdbhms.invoices WHERE invoice_code='DEMO-INV-404-2026-05-RENT' LIMIT 1), 'ROOM_RENT', 'Tiền phòng 404 tháng 05/2026', 1, 2450000, '2026-05-01 08:00:00');

-- ============================================================
-- STEP 12: Payment Transactions & Allocations
-- ============================================================
INSERT IGNORE INTO hdbhms.payment_transactions (provider, provider_transaction_id, collection_account_id, amount, transaction_time, payer_name, payer_account, content, status, created_at)
VALUES
('BANK', 'BANK-P404-2026-06-RENT', @rent_account, 2450000, '2026-06-02 09:00:00', 'Đỗ Hoàng Anh', '9704364040404001', 'TIEN PHONG P404 T06 2026', 'ALLOCATED', '2026-06-02 09:00:00'),
('PAYOS', 'PAYOS-P501-2026-05-RENT', @rent_account, 2600000, '2026-05-03 09:00:00', 'Phạm Quốc Bảo', '9704185010501001', 'TIEN PHONG P501 T05 2026', 'ALLOCATED', '2026-05-03 09:00:00'),
('PAYOS', 'PAYOS-P501-2026-06-UTILITY', @utility_account, 200000, '2026-07-03 09:00:00', 'Phạm Quốc Bảo', '9704185010501001', 'DIEN NUOC P501 T06 2026', 'PARTIALLY_ALLOCATED', '2026-07-03 09:00:00'),
('PAYOS', 'PAYOS-P501-2026-04-REJECTED', @utility_account, 1000000, '2026-06-01 09:00:00', 'Phạm Quốc Bảo', '9704185010501001', 'DIEN NUOC P501 T04 2026', 'REJECTED', '2026-06-01 09:00:00'),
('BANK', 'BANK-P404-2026-05-RENT', @rent_account, 2450000, '2026-05-02 09:00:00', 'Đỗ Hoàng Anh', '9704364040404001', 'TIEN PHONG P404 T05 2026', 'ALLOCATED', '2026-05-02 09:00:00');

SET @tx404 := (SELECT payment_transaction_id FROM hdbhms.payment_transactions WHERE provider_transaction_id='BANK-P404-2026-06-RENT' LIMIT 1);
SET @tx501p := (SELECT payment_transaction_id FROM hdbhms.payment_transactions WHERE provider_transaction_id='PAYOS-P501-2026-05-RENT' LIMIT 1);
SET @tx501u := (SELECT payment_transaction_id FROM hdbhms.payment_transactions WHERE provider_transaction_id='PAYOS-P501-2026-06-UTILITY' LIMIT 1);
SET @tx404m := (SELECT payment_transaction_id FROM hdbhms.payment_transactions WHERE provider_transaction_id='BANK-P404-2026-05-RENT' LIMIT 1);
SET @inv404m := (SELECT invoice_id FROM hdbhms.invoices WHERE invoice_code='DEMO-INV-404-2026-05-RENT' LIMIT 1);

INSERT IGNORE INTO hdbhms.payment_allocations (payment_transaction_id, invoice_id, amount, allocated_by, allocated_at)
VALUES
(@tx404, @inv404r, 2450000, @manager_id, '2026-06-02 09:05:00'),
(@tx501p, @inv501p, 2600000, @manager_id, '2026-05-03 09:05:00'),
(@tx501u, @inv501u, 200000, @manager_id, '2026-07-03 09:05:00'),
(@tx404m, @inv404m, 2450000, @manager_id, '2026-05-02 09:05:00');

-- ============================================================
-- STEP 13: Operating Expenses
-- ============================================================
INSERT IGNORE INTO hdbhms.operating_expenses (property_id, expense_code, expense_type, description, amount, expense_date, paid_by_user_id, status, approved_by, approved_at, created_by, created_at)
VALUES
(@property_id, 'DEMO-EXP-COMMON-ELECTRIC', 'COMMON_UTILITY', 'Tiền điện khu vực chung tháng 06/2026', 600000, '2026-06-30', @approver_id, 'PAID', @approver_id, '2026-06-30 09:00:00', @accountant_id, '2026-06-30 08:00:00'),
(@property_id, 'DEMO-EXP-SUPPLIES', 'SUPPLIES', 'Vật tư vệ sinh tháng 06/2026', 300000, '2026-06-25', @approver_id, 'APPROVED', @approver_id, '2026-06-25 09:00:00', @manager_id, '2026-06-25 08:00:00'),
(@property_id, 'DEMO-EXP-COMMON-WATER', 'COMMON_UTILITY', 'Tiền nước khu vực chung tháng 06/2026', 200000, '2026-06-30', @approver_id, 'PAID', @approver_id, '2026-06-30 09:00:00', @accountant_id, '2026-06-30 08:00:00');

-- ============================================================
-- STEP 14: Debt Snapshots
-- ============================================================
INSERT IGNORE INTO hdbhms.debt_snapshots (room_id, snapshot_date, rent_debt_amount, utility_debt_amount, other_debt_amount, rent_debt_months, utility_debt_months, mixed_debt_amount, is_over_limit, created_at)
VALUES
(@r501, '2026-07-10', 2600000, 1300000, 200000, 1, 2, 4100000, TRUE, '2026-07-10 07:00:00'),
((SELECT room_id FROM hdbhms.rooms WHERE property_id=@property_id AND room_code='406' AND deleted_at IS NULL LIMIT 1), '2026-07-10', 2600000, 400000, 0, 1, 1, 3000000, FALSE, '2026-07-10 07:00:00');

-- ============================================================
-- STEP 15: Tenants, Occupants & Vehicles
-- ============================================================
INSERT IGNORE INTO hdbhms.tenants (user_id, property_id, created_at)
SELECT u.user_id, @property_id, NOW()
FROM hdbhms.users u WHERE u.email LIKE 'demo.tenant%@hdbhms.local';

INSERT IGNORE INTO hdbhms.identity_documents (profile_id, doc_type, doc_number, issued_date, issued_place, created_at)
SELECT pp.person_profile_id, 'CCCD', CONCAT('001099', LPAD(pp.person_profile_id, 6, '0')), '2021-05-15', 'Cục Cảnh sát QLHC về trật tự xã hội', NOW()
FROM hdbhms.person_profiles pp WHERE pp.email LIKE 'demo.tenant%@hdbhms.local';

INSERT IGNORE INTO hdbhms.emergency_contacts (tenant_profile_id, full_name, relationship, phone, created_at)
SELECT pp.person_profile_id, 'Trần Thị B', 'Mẹ', '0987654321', NOW()
FROM hdbhms.person_profiles pp WHERE pp.email LIKE 'demo.tenant%@hdbhms.local';

INSERT IGNORE INTO hdbhms.vehicles (profile_id, vehicle_type, license_plate, brand, color, status, created_at)
SELECT pp.person_profile_id, 'MOTORBIKE', CONCAT('29E1-', 10000 + pp.person_profile_id), 'Honda Wave Alpha', 'Đen', 'ACTIVE', NOW()
FROM hdbhms.person_profiles pp WHERE pp.email LIKE 'demo.tenant%@hdbhms.local';

INSERT IGNORE INTO hdbhms.contract_occupants (contract_id, tenant_profile_id, occupant_role, move_in_date, status, created_at)
SELECT lc.lease_contract_id, lc.primary_tenant_profile_id, 'PRIMARY', lc.start_date, 'ACTIVE', NOW()
FROM hdbhms.lease_contracts lc;

-- ============================================================
-- STEP 16: Room Assets
-- ============================================================
INSERT IGNORE INTO hdbhms.room_assets (room_id, asset_name, asset_category, quantity, current_condition, created_at)
SELECT r.room_id, 'Điều hòa Daikin 9000BTU', 'APPLIANCE', 1, 'GOOD', NOW()
FROM hdbhms.rooms r WHERE r.property_id=@property_id;

INSERT IGNORE INTO hdbhms.room_assets (room_id, asset_name, asset_category, quantity, current_condition, created_at)
SELECT r.room_id, 'Bình nóng lạnh Ariston 20L', 'APPLIANCE', 1, 'GOOD', NOW()
FROM hdbhms.rooms r WHERE r.property_id=@property_id;

INSERT IGNORE INTO hdbhms.room_assets (room_id, asset_name, asset_category, quantity, current_condition, created_at)
SELECT r.room_id, 'Giường gỗ 1m6 x 2m', 'FURNITURE', 1, 'GOOD', NOW()
FROM hdbhms.rooms r WHERE r.property_id=@property_id;

-- ============================================================
-- STEP 17: Maintenance Tickets & Costs
-- ============================================================
SET @r408 := (SELECT room_id FROM hdbhms.rooms WHERE property_id=@property_id AND room_code='408' LIMIT 1);
SET @r502 := (SELECT room_id FROM hdbhms.rooms WHERE property_id=@property_id AND room_code='502' LIMIT 1);

INSERT IGNORE INTO hdbhms.maintenance_tickets (ticket_code, property_id, room_id, created_by, category, title, description, priority, status, created_at)
VALUES ('MT-408-001', @property_id, @r408, @manager_id, 'ELECTRICAL', 'Bảo trì hệ thống điện tầng 4', 'Kiểm tra bo mạch điều hòa và tủ điện chính', 'HIGH', 'IN_PROGRESS', '2026-07-10 09:00:00');

INSERT IGNORE INTO hdbhms.maintenance_tickets (ticket_code, property_id, room_id, created_by, category, title, description, priority, status, created_at)
VALUES ('MT-502-001', @property_id, @r502, @manager_id, 'PLUMBING', 'Sửa vòi nước rò rỉ phòng 502', 'Thay thế vòi xịt vệ sinh và dây cấp nước', 'MEDIUM', 'RESOLVED', '2026-06-12 14:00:00');

SET @t502 := (SELECT maintenance_ticket_id FROM hdbhms.maintenance_tickets WHERE ticket_code='MT-502-001' LIMIT 1);
INSERT IGNORE INTO hdbhms.maintenance_costs (ticket_id, cost_type, description, amount, created_at)
VALUES (@t502, 'REPAIR', 'Thay vòi xịt inox 304', 150000, '2026-06-12 16:00:00');

INSERT IGNORE INTO hdbhms.maintenance_reviews (ticket_id, rating, comment, created_at)
VALUES (@t502, 5, 'Sửa chữa nhanh chóng, thợ nhiệt tình', '2026-06-12 17:00:00');

-- ============================================================
-- STEP 18: Violations, Transfers, Visits & Tasks
-- ============================================================
INSERT IGNORE INTO hdbhms.rule_violations (property_id, room_id, contract_id, violation_date, description, fine_amount, status, created_at)
VALUES (@property_id, @r501, @c501, '2026-06-18', 'Gây ồn ào sau 23h đêm ngày 18/06/2026', 200000, 'REPORTED', '2026-06-19 09:00:00');

INSERT IGNORE INTO hdbhms.room_transfer_requests (request_code, requester_id, old_contract_id, old_room_id, target_room_id, reason, status, created_at)
VALUES ('TR-404-407', @manager_id, @c404, @r404, (SELECT room_id FROM hdbhms.rooms WHERE property_id=@property_id AND room_code='407' LIMIT 1), 'Khách muốn chuyển sang phòng rộng hơn có ban công', 'APPROVED', '2026-07-01 10:00:00');

INSERT IGNORE INTO hdbhms.visit_requests (property_id, room_id, visitor_name, visitor_phone, preferred_start, status, created_at)
VALUES (@property_id, (SELECT room_id FROM hdbhms.rooms WHERE property_id=@property_id AND room_code='401' LIMIT 1), 'Lê Văn Hùng', '0933111222', '2026-07-25 14:30:00', 'SCHEDULED', NOW()),
(@property_id, (SELECT room_id FROM hdbhms.rooms WHERE property_id=@property_id AND room_code='505' LIMIT 1), 'Hoàng Phương Mai', '0944222333', '2026-07-26 10:00:00', 'SCHEDULED', NOW());

INSERT IGNORE INTO hdbhms.manager_tasks (title, description, assignee_id, room_id, status, due_date, created_at)
VALUES ('Thu tiền trọ tháng 07/2026', 'Gửi thông báo và thu tiền trọ phòng 501', @manager_id, @r501, 'IN_PROGRESS', '2026-07-25', NOW()),
('Kiểm tra định kỳ PCCC tầng 4 & 5', 'Kiểm tra bình chữa cháy và lối thoát hiểm', @manager_id, @r408, 'PENDING', '2026-07-30', NOW());

INSERT IGNORE INTO hdbhms.vacancy_logs (room_id, property_id, landlord_id, vacant_from, vacancy_reason)
VALUES ((SELECT room_id FROM hdbhms.rooms WHERE property_id=@property_id AND room_code='407' LIMIT 1), @property_id, @ow, '2026-07-05', 'Hết hạn hợp đồng bàn giao phòng');

-- ============================================================
-- STEP 19: Verify Results
-- ============================================================
SELECT '=== SEED COMPLETED ===' status;
SELECT CONCAT('Rooms total: ', COUNT(*)) info FROM hdbhms.rooms WHERE property_id=@property_id AND deleted_at IS NULL;
SELECT CONCAT('Occupied: ', SUM(CASE WHEN current_status IN ('OCCUPIED','SOON_VACANT','EXPIRED') THEN 1 ELSE 0 END), '/', COUNT(*), ' (', ROUND(100*SUM(CASE WHEN current_status IN ('OCCUPIED','SOON_VACANT','EXPIRED') THEN 1 ELSE 0 END)/COUNT(*),1), '%)') info FROM hdbhms.rooms WHERE property_id=@property_id AND deleted_at IS NULL;
SELECT CONCAT('Active leases: ', COUNT(*)) info FROM hdbhms.lease_contracts WHERE status IN ('ACTIVE','EXPIRING_SOON');
SELECT CONCAT('Invoices: ', COUNT(*)) info FROM hdbhms.invoices WHERE property_id=@property_id;
SELECT CONCAT('Payments: ', COUNT(*)) info FROM hdbhms.payment_transactions;
SELECT CONCAT('Expenses: ', COUNT(*)) info FROM hdbhms.operating_expenses WHERE property_id=@property_id;
SELECT CONCAT('Debt snapshots: ', COUNT(*)) info FROM hdbhms.debt_snapshots;
SELECT CONCAT('Revenue (PAID invoices): ', COALESCE(SUM(total_amount), 0)) info FROM hdbhms.invoices WHERE property_id=@property_id AND status='PAID';
SELECT CONCAT('Overdue count: ', COUNT(*)) info FROM hdbhms.invoices WHERE property_id=@property_id AND status='OVERDUE';
SELECT CONCAT('Total overdue amount: ', COALESCE(SUM(remaining_amount), 0)) info FROM hdbhms.invoices WHERE property_id=@property_id AND status='OVERDUE';
