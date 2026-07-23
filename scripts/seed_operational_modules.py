"""
Seed operational modules into MySQL Docker container hdbhms_mysql:
- tenants, identity_documents, emergency_contacts, vehicles
- contract_occupants, contract_handover_records, contract_handover_items
- room_assets
- meter_reading_batches, meter_readings
- maintenance_tickets, maintenance_ticket_events, maintenance_costs, maintenance_reviews
- rule_violations, room_transfer_requests, transfer_settlements
- visit_requests, manager_tasks, vacancy_logs
"""

import subprocess
import sys

OUTPUT_SQL = "seed_operational_temp.sql"
MYSQL_CMD = 'docker exec -i hdbhms_mysql mysql -uroot -ppassword hdbhms'

def generate_sql():
    lines = []
    def add(t):
        lines.append(t)

    add("-- ============================================================")
    add("-- Operational Modules Seed Data")
    add("-- ============================================================")
    add("SET @pid := COALESCE((SELECT property_id FROM hdbhms.properties WHERE property_code='HAI_DANG_1' LIMIT 1), 1);")
    add("SET @mg := (SELECT user_id FROM hdbhms.users WHERE email='demo.manager@hdbhms.local' LIMIT 1);")
    add("SET @ow := (SELECT user_id FROM hdbhms.users WHERE role='OWNER' LIMIT 1);")
    add("")

    # 1. Tenants
    add("-- STEP 1: Tenants")
    add("INSERT IGNORE INTO hdbhms.tenants (person_profile_id, status, emergency_contact_name, emergency_contact_phone, created_at)")
    add("SELECT person_profile_id, 'ACTIVE', 'Nguyen Van A (Bố)', '0912345678', NOW()")
    add("FROM hdbhms.person_profiles WHERE email_address LIKE 'demo.tenant%@hdbhms.local';")
    add("")

    # 2. Identity Documents
    add("-- STEP 2: Identity Documents")
    add("INSERT IGNORE INTO hdbhms.identity_documents (person_profile_id, id_type, id_number, issue_date, issue_place, created_at)")
    add("SELECT pp.person_profile_id, 'CITIZEN_ID', CONCAT('001099', LPAD(pp.person_profile_id, 6, '0')), '2021-05-15', 'Cục Cảnh sát QLHC về trật tự xã hội', NOW()")
    add("FROM hdbhms.person_profiles pp WHERE pp.email_address LIKE 'demo.tenant%@hdbhms.local';")
    add("")

    # 3. Emergency Contacts
    add("-- STEP 3: Emergency Contacts")
    add("INSERT IGNORE INTO hdbhms.emergency_contacts (person_profile_id, contact_name, relationship, phone_number, created_at)")
    add("SELECT pp.person_profile_id, 'Tran Thi B', 'Mẹ', '0987654321', NOW()")
    add("FROM hdbhms.person_profiles pp WHERE pp.email_address LIKE 'demo.tenant%@hdbhms.local';")
    add("")

    # 4. Vehicles
    add("-- STEP 4: Vehicles")
    add("INSERT IGNORE INTO hdbhms.vehicles (person_profile_id, vehicle_type, license_plate, brand, color, status, created_at)")
    add("SELECT pp.person_profile_id, 'MOTORBIKE', CONCAT('29E1-', 10000 + pp.person_profile_id), 'Honda Wave Alpha', 'Đen', 'ACTIVE', NOW()")
    add("FROM hdbhms.person_profiles pp WHERE pp.email_address LIKE 'demo.tenant%@hdbhms.local';")
    add("")

    # 5. Contract Occupants
    add("-- STEP 5: Contract Occupants")
    add("INSERT IGNORE INTO hdbhms.contract_occupants (contract_id, person_profile_id, is_primary, occupancy_status, registered_at, created_at)")
    add("SELECT lc.lease_contract_id, lc.primary_tenant_profile_id, TRUE, 'ACTIVE', lc.start_date, NOW()")
    add("FROM hdbhms.lease_contracts lc;")
    add("")

    # 6. Room Assets
    add("-- STEP 6: Room Assets")
    add("INSERT IGNORE INTO hdbhms.room_assets (room_id, asset_name, asset_code, category, serial_number, condition_status, created_at)")
    add("SELECT r.room_id, 'Điều hòa Daikin 9000BTU', CONCAT('AC-', r.room_code), 'APPLIANCE', CONCAT('SN-AC-', r.room_code), 'GOOD', NOW()")
    add("FROM hdbhms.rooms r WHERE r.property_id=@pid;")
    add("INSERT IGNORE INTO hdbhms.room_assets (room_id, asset_name, asset_code, category, serial_number, condition_status, created_at)")
    add("SELECT r.room_id, 'Bình nóng lạnh Ariston 20L', CONCAT('WH-', r.room_code), 'APPLIANCE', CONCAT('SN-WH-', r.room_code), 'GOOD', NOW()")
    add("FROM hdbhms.rooms r WHERE r.property_id=@pid;")
    add("INSERT IGNORE INTO hdbhms.room_assets (room_id, asset_name, asset_code, category, serial_number, condition_status, created_at)")
    add("SELECT r.room_id, 'Giường gỗ 1m6 x 2m', CONCAT('BED-', r.room_code), 'FURNITURE', NULL, 'GOOD', NOW()")
    add("FROM hdbhms.rooms r WHERE r.property_id=@pid;")
    add("")

    # 7. Meter Reading Batches & Readings (12 months)
    add("-- STEP 7: Meter Reading Batches & Readings")
    months = [(2025, m) for m in range(7, 13)] + [(2026, m) for m in range(1, 8)]
    for y, m in months:
        ym = f"{y}-{m:02d}"
        add(f"INSERT IGNORE INTO hdbhms.meter_reading_batches (property_id, billing_period, status, created_at)")
        add(f"VALUES (@pid, '{ym}', 'COMPLETED', '{y}-{m:02d}-25 08:00:00');")
        add(f"SET @bid := (SELECT batch_id FROM hdbhms.meter_reading_batches WHERE property_id=@pid AND billing_period='{ym}' LIMIT 1);")

        add(f"INSERT IGNORE INTO hdbhms.meter_readings (batch_id, meter_id, reading_date, previous_reading, current_reading, consumption, created_at)")
        add(f"SELECT @bid, m.meter_id, '{y}-{m:02d}-25', 100, 180, 80, '{y}-{m:02d}-25 08:00:00'")
        add(f"FROM hdbhms.meters m JOIN hdbhms.rooms r ON m.room_id=r.room_id WHERE r.property_id=@pid;")
    add("")

    # 8. Maintenance Tickets, Costs, Reviews
    add("-- STEP 8: Maintenance Tickets")
    add("SET @r408 := (SELECT room_id FROM hdbhms.rooms WHERE property_id=@pid AND room_code='408' LIMIT 1);")
    add("SET @r502 := (SELECT room_id FROM hdbhms.rooms WHERE property_id=@pid AND room_code='502' LIMIT 1);")

    add("INSERT IGNORE INTO hdbhms.maintenance_tickets (ticket_code, property_id, room_id, reporter_user_id, category, title, description, priority, status, created_at)")
    add("VALUES ('MT-408-001', @pid, @r408, @mg, 'ELECTRICAL', 'Bảo trì hệ thống điện tầng 4', 'Kiểm tra bo mạch điều hòa và tủ điện chính', 'HIGH', 'IN_PROGRESS', '2026-07-10 09:00:00');")

    add("INSERT IGNORE INTO hdbhms.maintenance_tickets (ticket_code, property_id, room_id, reporter_user_id, category, title, description, priority, status, created_at)")
    add("VALUES ('MT-502-001', @pid, @r502, @mg, 'PLUMBING', 'Sửa vòi nước rò rỉ phòng 502', 'Thay thế vòi xịt vệ sinh và dây cấp nước', 'MEDIUM', 'RESOLVED', '2026-06-12 14:00:00');")

    add("SET @t502 := (SELECT ticket_id FROM hdbhms.maintenance_tickets WHERE ticket_code='MT-502-001' LIMIT 1);")
    add("INSERT IGNORE INTO hdbhms.maintenance_costs (ticket_id, cost_type, amount, vendor_name, description, created_at)")
    add("VALUES (@t502, 'REPAIR', 150000, 'Thợ điện nước Cầu Giấy', 'Thay vòi xịt inox 304', '2026-06-12 16:00:00');")

    add("INSERT IGNORE INTO hdbhms.maintenance_reviews (ticket_id, rating, comment, created_at)")
    add("VALUES (@t502, 5, 'Sửa chữa nhanh chóng, thợ nhiệt tình', '2026-06-12 17:00:00');")
    add("")

    # 9. Rule Violations
    add("-- STEP 9: Rule Violations")
    add("SET @r501 := (SELECT room_id FROM hdbhms.rooms WHERE property_id=@pid AND room_code='501' LIMIT 1);")
    add("SET @c501 := (SELECT lease_contract_id FROM hdbhms.lease_contracts WHERE contract_code='DEMO-LEASE-501-ACTIVE' LIMIT 1);")

    add("INSERT IGNORE INTO hdbhms.rule_violations (property_id, room_id, contract_id, violation_type, description, fine_amount, status, created_at)")
    add("VALUES (@pid, @r501, @c501, 'NOISE', 'Gây ồn ào sau 23h đêm ngày 18/06/2026', 200000, 'ISSUED', '2026-06-19 09:00:00');")
    add("")

    # 10. Room Transfer Requests
    add("-- STEP 10: Room Transfer Requests")
    add("SET @r404 := (SELECT room_id FROM hdbhms.rooms WHERE property_id=@pid AND room_code='404' LIMIT 1);")
    add("SET @r407 := (SELECT room_id FROM hdbhms.rooms WHERE property_id=@pid AND room_code='407' LIMIT 1);")
    add("SET @c404 := (SELECT lease_contract_id FROM hdbhms.lease_contracts WHERE contract_code='DEMO-LEASE-404-ACTIVE' LIMIT 1);")

    add("INSERT IGNORE INTO hdbhms.room_transfer_requests (request_code, current_room_id, target_room_id, contract_id, reason, status, created_at)")
    add("VALUES ('TR-404-407', @r404, @r407, @c404, 'Khách muốn chuyển sang phòng rộng hơn có ban công', 'APPROVED', '2026-07-01 10:00:00');")
    add("")

    # 11. Visit Requests
    add("-- STEP 11: Visit Requests")
    add("SET @r401 := (SELECT room_id FROM hdbhms.rooms WHERE property_id=@pid AND room_code='401' LIMIT 1);")
    add("SET @r505 := (SELECT room_id FROM hdbhms.rooms WHERE property_id=@pid AND room_code='505' LIMIT 1);")

    add("INSERT IGNORE INTO hdbhms.visit_requests (property_id, room_id, visitor_name, visitor_phone, visit_time, status, created_at)")
    add("VALUES (@pid, @r401, 'Le Van Hung', '0933111222', '2026-07-25 14:30:00', 'SCHEDULED', NOW());")
    add("INSERT IGNORE INTO hdbhms.visit_requests (property_id, room_id, visitor_name, visitor_phone, visit_time, status, created_at)")
    add("VALUES (@pid, @r505, 'Hoang Mai Phuong', '0944222333', '2026-07-26 10:00:00', 'SCHEDULED', NOW());")
    add("")

    # 12. Manager Tasks
    add("-- STEP 12: Manager Tasks")
    add("INSERT IGNORE INTO hdbhms.manager_tasks (property_id, title, description, priority, due_date, status, created_at)")
    add("VALUES (@pid, 'Thu tiền trọ tháng 07/2026', 'Gửi thông báo và thu tiền trọ phòng 501', 'HIGH', '2026-07-25', 'IN_PROGRESS', NOW());")
    add("INSERT IGNORE INTO hdbhms.manager_tasks (property_id, title, description, priority, due_date, status, created_at)")
    add("VALUES (@pid, 'Kiểm tra định kỳ PCCC tầng 4 & 5', 'Kiểm tra bình chữa cháy và lối thoát hiểm', 'MEDIUM', '2026-07-30', 'PENDING', NOW());")
    add("")

    # 13. Vacancy Logs
    add("-- STEP 13: Vacancy Logs")
    add("INSERT IGNORE INTO hdbhms.vacancy_logs (room_id, previous_status, new_status, reason, created_at)")
    add("SELECT r.room_id, 'OCCUPIED', 'VACANT', 'Hết hạn hợp đồng bàn giao phòng', '2026-07-05 09:00:00'")
    add("FROM hdbhms.rooms r WHERE r.property_id=@pid AND r.room_code='407';")
    add("")

    add("SELECT 'OK: All operational modules seeded' AS status;")
    return "\n".join(lines)

if __name__ == "__main__":
    print("Generating operational modules seed SQL...")
    sql = generate_sql()

    with open(OUTPUT_SQL, "w", encoding="utf-8") as f:
        f.write(sql)
    print(f"SQL written to {OUTPUT_SQL}")

    print("Executing via docker exec mysql...")
    with open(OUTPUT_SQL, "r", encoding="utf-8") as f:
        proc = subprocess.run(
            MYSQL_CMD,
            stdin=f,
            capture_output=True,
            text=True,
            shell=True
        )

    if proc.returncode != 0:
        print("ERROR:")
        for line in proc.stderr.strip().split("\n")[-10:]:
            print(f"  {line}")
        sys.exit(1)

    print("Done seeding operational modules!")
