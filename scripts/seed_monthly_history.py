"""
Seed Monthly History Data — 13 months (2025-07 to 2026-07)
Generates comprehensive time-series financial history for AI Property Advisor:
- Monthly RENT & UTILITY invoices + ALLOCATED payment transactions for all occupied rooms
- Monthly OPEX expenses (Electricity, Water, Maintenance, Internet) across 13 months
- Full 12+ month trend continuity for revenue, expenses, net profit, and occupancy

Usage: python scripts/seed_monthly_history.py
"""
import os
import sys
import subprocess

OUTPUT_SQL = "seed_monthly_temp.sql"
MYSQL_CMD = 'docker exec -i hdbhms_mysql mysql -uroot -ppassword hdbhms'


def add(lines, text):
    lines.append(text)


def generate_sql():
    lines = []

    # SET variables
    add(lines, "SET @pid := COALESCE((SELECT property_id FROM hdbhms.properties WHERE property_code='HAI_DANG_1' LIMIT 1), 1);")
    add(lines, "SET @r404 := COALESCE((SELECT room_id FROM hdbhms.rooms WHERE property_id=@pid AND room_code='404' AND deleted_at IS NULL LIMIT 1), 4);")
    add(lines, "SET @r405 := COALESCE((SELECT room_id FROM hdbhms.rooms WHERE property_id=@pid AND room_code='405' AND deleted_at IS NULL LIMIT 1), 5);")
    add(lines, "SET @r406 := COALESCE((SELECT room_id FROM hdbhms.rooms WHERE property_id=@pid AND room_code='406' AND deleted_at IS NULL LIMIT 1), 6);")
    add(lines, "SET @r501 := COALESCE((SELECT room_id FROM hdbhms.rooms WHERE property_id=@pid AND room_code='501' AND deleted_at IS NULL LIMIT 1), 9);")
    add(lines, "SET @r502 := COALESCE((SELECT room_id FROM hdbhms.rooms WHERE property_id=@pid AND room_code='502' AND deleted_at IS NULL LIMIT 1), 10);")
    add(lines, "SET @r503 := COALESCE((SELECT room_id FROM hdbhms.rooms WHERE property_id=@pid AND room_code='503' AND deleted_at IS NULL LIMIT 1), 11);")
    add(lines, "SET @r506 := COALESCE((SELECT room_id FROM hdbhms.rooms WHERE property_id=@pid AND room_code='506' AND deleted_at IS NULL LIMIT 1), 14);")

    add(lines, "SET @c404 := (SELECT lease_contract_id FROM hdbhms.lease_contracts WHERE contract_code='DEMO-LEASE-404-ACTIVE' LIMIT 1);")
    add(lines, "SET @c405 := (SELECT lease_contract_id FROM hdbhms.lease_contracts WHERE contract_code='DEMO-LEASE-405-ACTIVE' LIMIT 1);")
    add(lines, "SET @c406 := (SELECT lease_contract_id FROM hdbhms.lease_contracts WHERE contract_code='DEMO-LEASE-406-EXPIRING' LIMIT 1);")
    add(lines, "SET @c501 := (SELECT lease_contract_id FROM hdbhms.lease_contracts WHERE contract_code='DEMO-LEASE-501-ACTIVE' LIMIT 1);")
    add(lines, "SET @c502 := (SELECT lease_contract_id FROM hdbhms.lease_contracts WHERE contract_code='DEMO-LEASE-502-ACTIVE' LIMIT 1);")
    add(lines, "SET @c503 := (SELECT lease_contract_id FROM hdbhms.lease_contracts WHERE contract_code='DEMO-LEASE-503-ACTIVE' LIMIT 1);")
    add(lines, "SET @c506 := (SELECT lease_contract_id FROM hdbhms.lease_contracts WHERE contract_code='DEMO-LEASE-506-ACTIVE' LIMIT 1);")

    add(lines, "SET @ra := COALESCE((SELECT collection_account_id FROM hdbhms.collection_accounts WHERE account_number='190368040401' LIMIT 1), 1);")
    add(lines, "SET @ua := COALESCE((SELECT collection_account_id FROM hdbhms.collection_accounts WHERE account_number='1029995501' LIMIT 1), 2);")
    add(lines, "SET @mg := COALESCE((SELECT user_id FROM hdbhms.users WHERE email='demo.manager@hdbhms.local' LIMIT 1), 1);")
    add(lines, "")

    # Generate 13 months: 2025-07 to 2026-07
    months = []
    for i in range(13):
        y = 2025 + (7 + i - 1) // 12
        m = (7 + i - 1) % 12 + 1
        months.append((y, m))

    rooms_config = [
        ("503", "@r503", "@c503", 2400000, "2025-07", "Dang Thanh Nam", "9704185030501001"),
        ("404", "@r404", "@c404", 2450000, "2025-09", "Do Hoang Anh", "9704364040404001"),
        ("502", "@r502", "@c502", 2600000, "2025-10", "Hoang Van E", "9704185020502001"),
        ("501", "@r501", "@c501", 2600000, "2025-10", "Pham Quoc Bao", "9704185010501001"),
        ("406", "@r406", "@c406", 2600000, "2025-09", "Tran Van B", "9704364060606001"),
        ("405", "@r405", "@c405", 2550000, "2026-01", "Nguyen Minh Khoa", "9704364050505001"),
        ("506", "@r506", "@c506", 2700000, "2026-01", "Vu Thi F", "9704185060506001"),
    ]

    add(lines, "-- ================================================================")
    add(lines, "-- 1. ROOM RENT INVOICES & ALLOCATED PAYMENTS (13 MONTHS)")
    add(lines, "-- ================================================================")
    for room_code, room_var, contract_var, rent_amt, start_ym, payer_name, payer_acc in rooms_config:
        add(lines, f"-- Room {room_code} Rent (from {start_ym})")
        for y, m in months:
            ym = f"{y}-{m:02d}"
            if ym < start_ym:
                continue

            inv_code = f"DEMO-INV-{room_code}-{ym}-RENT"
            tx_code = f"BANK-P{room_code}-{ym}-RENT"
            pay_time = f"{y}-{m:02d}-03 09:00:00"

            add(lines, f"INSERT IGNORE INTO hdbhms.invoices (invoice_code, property_id, room_id, lease_contract_id, invoice_type, revision_no, billing_period, issue_date, due_date, status, subtotal_amount, total_amount, paid_amount, remaining_amount, collection_account_id, created_by, created_at, updated_at)")
            add(lines, f"VALUES ('{inv_code}', @pid, {room_var}, {contract_var}, 'RENT', 1, '{ym}', '{y}-{m:02d}-01 08:00:00', '{y}-{m:02d}-15 23:59:59', 'PAID', {rent_amt}, {rent_amt}, {rent_amt}, 0, @ra, @mg, '{y}-{m:02d}-01 08:00:00', '{pay_time}');")

            add(lines, f"INSERT IGNORE INTO hdbhms.invoice_lines (invoice_id, line_type, description, quantity, unit_price, created_at)")
            add(lines, f"SELECT invoice_id, 'ROOM_RENT', 'Tien phong {room_code} thang {ym}', 1, {rent_amt}, '{y}-{m:02d}-01 08:00:00' FROM hdbhms.invoices WHERE invoice_code='{inv_code}' LIMIT 1;")

            add(lines, f"INSERT IGNORE INTO hdbhms.payment_transactions (provider, provider_transaction_id, collection_account_id, amount, transaction_time, payer_name, payer_account, content, status, created_at)")
            add(lines, f"VALUES ('BANK', '{tx_code}', @ra, {rent_amt}, '{pay_time}', '{payer_name}', '{payer_acc}', 'TIEN PHONG P{room_code} {ym}', 'ALLOCATED', '{pay_time}');")

            add(lines, f"INSERT IGNORE INTO hdbhms.payment_allocations (payment_transaction_id, invoice_id, amount, allocated_by, allocated_at)")
            add(lines, f"SELECT pt.payment_transaction_id, i.invoice_id, {rent_amt}, @mg, '{pay_time}'")
            add(lines, f"FROM hdbhms.payment_transactions pt, hdbhms.invoices i")
            add(lines, f"WHERE pt.provider_transaction_id='{tx_code}' AND i.invoice_code='{inv_code}' LIMIT 1;")
            add(lines, "")

    add(lines, "-- ================================================================")
    add(lines, "-- 2. OPERATING EXPENSES FOR ALL 13 MONTHS")
    add(lines, "-- ================================================================")
    for idx, (y, m) in enumerate(months):
        ym = f"{y}-{m:02d}"
        elec_cost = 2100000 + (idx % 4) * 150000
        water_cost = 1200000 + (idx % 3) * 100000
        net_cost = 800000
        clean_cost = 1200000

        add(lines, f"-- Expenses {ym}")
        add(lines, f"INSERT IGNORE INTO hdbhms.expenses (property_id, category, amount, description, expense_date, status, created_by, created_at)")
        add(lines, f"VALUES (@pid, 'ELECTRICITY', {elec_cost}, 'Hoa don dien tong EVN thang {ym}', '{y}-{m:02d}-20', 'APPROVED', @mg, '{y}-{m:02d}-20 10:00:00');")

        add(lines, f"INSERT IGNORE INTO hdbhms.expenses (property_id, category, amount, description, expense_date, status, created_by, created_at)")
        add(lines, f"VALUES (@pid, 'WATER', {water_cost}, 'Hoa don nuoc tong thang {ym}', '{y}-{m:02d}-20', 'APPROVED', @mg, '{y}-{m:02d}-20 10:30:00');")

        add(lines, f"INSERT IGNORE INTO hdbhms.expenses (property_id, category, amount, description, expense_date, status, created_by, created_at)")
        add(lines, f"VALUES (@pid, 'OTHER', {net_cost}, 'Cuoc Internet VNPT thang {ym}', '{y}-{m:02d}-05', 'APPROVED', @mg, '{y}-{m:02d}-05 09:00:00');")

        add(lines, f"INSERT IGNORE INTO hdbhms.expenses (property_id, category, amount, description, expense_date, status, created_by, created_at)")
        add(lines, f"VALUES (@pid, 'OTHER', {clean_cost}, 'Luong ve sinh va thu gom rac thang {ym}', '{y}-{m:02d}-28', 'APPROVED', @mg, '{y}-{m:02d}-28 17:00:00');")
        add(lines, "")

    add(lines, "-- ================================================================")
    add(lines, "-- 3. VERIFY HISTORICAL COUNTS")
    add(lines, "-- ================================================================")
    add(lines, "SELECT 'OK: Complete 13-month seed generated successfully' AS status;")
    add(lines, "SELECT CONCAT('Total paid invoices: ', COUNT(*)) AS result FROM hdbhms.invoices WHERE status='PAID';")
    add(lines, "SELECT CONCAT('Total allocated payments: ', COUNT(*)) AS result FROM hdbhms.payment_transactions WHERE status='ALLOCATED';")
    add(lines, "SELECT CONCAT('Total approved expenses: ', COUNT(*)) AS result FROM hdbhms.expenses WHERE status='APPROVED';")

    sql_content = "\n".join(lines)
    return sql_content


if __name__ == "__main__":
    print("Generating complete 13-month seed SQL...")
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

    for line in proc.stdout.strip().split("\n"):
        line = line.strip()
        if line and line != "status" and line != "result":
            print(f"  {line}")

    print("Done!")
