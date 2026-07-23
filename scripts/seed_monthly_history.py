"""
Seed Monthly History Data — 12 months (2025-07 to 2026-06)
Creates monthly RENT invoices + ALLOCATED payments for rooms 503 and 404,
plus UTILITY invoices for expense history.

Usage: cd D:/Admin_AI_for_report/ai-property-advisor && python scripts/seed_monthly_history.py
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
    add(lines, "SET @r503 := COALESCE((SELECT room_id FROM hdbhms.rooms WHERE property_id=@pid AND room_code='503' AND deleted_at IS NULL LIMIT 1), 11);")
    add(lines, "SET @r404 := COALESCE((SELECT room_id FROM hdbhms.rooms WHERE property_id=@pid AND room_code='404' AND deleted_at IS NULL LIMIT 1), 4);")
    add(lines, "SET @r405 := COALESCE((SELECT room_id FROM hdbhms.rooms WHERE property_id=@pid AND room_code='405' AND deleted_at IS NULL LIMIT 1), 5);")
    add(lines, "SET @r501 := COALESCE((SELECT room_id FROM hdbhms.rooms WHERE property_id=@pid AND room_code='501' AND deleted_at IS NULL LIMIT 1), 9);")
    add(lines, "SET @c503 := (SELECT lease_contract_id FROM hdbhms.lease_contracts WHERE contract_code='DEMO-LEASE-503-ACTIVE' LIMIT 1);")
    add(lines, "SET @c404 := (SELECT lease_contract_id FROM hdbhms.lease_contracts WHERE contract_code='DEMO-LEASE-404-ACTIVE' LIMIT 1);")
    add(lines, "SET @c405 := (SELECT lease_contract_id FROM hdbhms.lease_contracts WHERE contract_code='DEMO-LEASE-405-ACTIVE' LIMIT 1);")
    add(lines, "SET @c501 := (SELECT lease_contract_id FROM hdbhms.lease_contracts WHERE contract_code='DEMO-LEASE-501-ACTIVE' LIMIT 1);")
    add(lines, "SET @ra := COALESCE((SELECT collection_account_id FROM hdbhms.collection_accounts WHERE account_number='190368040401' LIMIT 1), 1);")
    add(lines, "SET @ua := COALESCE((SELECT collection_account_id FROM hdbhms.collection_accounts WHERE account_number='1029995501' LIMIT 1), 2);")
    add(lines, "SET @mg := (SELECT user_id FROM hdbhms.users WHERE email='demo.manager@hdbhms.local' LIMIT 1);")
    add(lines, "")

    # Generate 13 months: 2025-07 to 2026-07
    months = []
    for i in range(13):
        y = 2025 + (7 + i - 1) // 12
        m = (7 + i - 1) % 12 + 1
        months.append((y, m))

    # ================================================================
    # ROOM 503: Monthly rent invoices + payments (all 12 months)
    # ================================================================
    add(lines, "-- ROOM 503: Monthly rent (12 months, 2,400,000 VND each)")
    for idx, (y, m) in enumerate(months):
        ym = f"{y}-{m:02d}"
        inv_code = f"DEMO-INV-503-{ym}-RENT"
        tx_code = f"BANK-P503-{ym}-RENT"
        pay_time = f"{y}-{m:02d}-02 09:00:00"

        add(lines, f"INSERT IGNORE INTO hdbhms.invoices (invoice_code, property_id, room_id, lease_contract_id, invoice_type, revision_no, billing_period, issue_date, due_date, status, subtotal_amount, total_amount, paid_amount, remaining_amount, collection_account_id, created_by, created_at, updated_at)")
        add(lines, f"VALUES ('{inv_code}', @pid, @r503, @c503, 'RENT', 1, '{ym}', '{y}-{m:02d}-01 08:00:00', '{y}-{m:02d}-15 23:59:59', 'PAID', 2400000, 2400000, 2400000, 0, @ra, @mg, '{y}-{m:02d}-01 08:00:00', '{pay_time}');")

        add(lines, f"INSERT IGNORE INTO hdbhms.invoice_lines (invoice_id, line_type, description, quantity, unit_price, created_at)")
        add(lines, f"SELECT invoice_id, 'ROOM_RENT', 'Tien phong 503 thang {ym}', 1, 2400000, '{y}-{m:02d}-01 08:00:00' FROM hdbhms.invoices WHERE invoice_code='{inv_code}' LIMIT 1;")

        add(lines, f"INSERT IGNORE INTO hdbhms.payment_transactions (provider, provider_transaction_id, collection_account_id, amount, transaction_time, payer_name, payer_account, content, status, created_at)")
        add(lines, f"VALUES ('BANK', '{tx_code}', @ra, 2400000, '{pay_time}', 'Dang Thanh Nam', '9704185030501001', 'TIEN PHONG P503 {ym}', 'ALLOCATED', '{pay_time}');")

        add(lines, f"INSERT IGNORE INTO hdbhms.payment_allocations (payment_transaction_id, invoice_id, amount, allocated_by, allocated_at)")
        add(lines, f"SELECT pt.payment_transaction_id, i.invoice_id, 2400000, @mg, '{pay_time}'")
        add(lines, f"FROM hdbhms.payment_transactions pt, hdbhms.invoices i")
        add(lines, f"WHERE pt.provider_transaction_id='{tx_code}' AND i.invoice_code='{inv_code}' LIMIT 1;")
        add(lines, "")

    # ================================================================
    # ROOM 404: Monthly rent (2025-09 to 2026-07)
    # ================================================================
    add(lines, "-- ROOM 404: Monthly rent (2025-09 to 2026-07, 2,450,000 VND each)")
    for idx, (y, m) in enumerate(months):
        ym = f"{y}-{m:02d}"
        if ym < "2025-09":
            continue

        inv_code = f"DEMO-INV-404-{ym}-RENT"
        tx_code = f"BANK-P404-{ym}-RENT"
        pay_time = f"{y}-{m:02d}-02 09:00:00"

        add(lines, f"INSERT IGNORE INTO hdbhms.invoices (invoice_code, property_id, room_id, lease_contract_id, invoice_type, revision_no, billing_period, issue_date, due_date, status, subtotal_amount, total_amount, paid_amount, remaining_amount, collection_account_id, created_by, created_at, updated_at)")
        add(lines, f"VALUES ('{inv_code}', @pid, @r404, @c404, 'RENT', 1, '{ym}', '{y}-{m:02d}-01 08:00:00', '{y}-{m:02d}-15 23:59:59', 'PAID', 2450000, 2450000, 2450000, 0, @ra, @mg, '{y}-{m:02d}-01 08:00:00', '{pay_time}');")

        add(lines, f"INSERT IGNORE INTO hdbhms.invoice_lines (invoice_id, line_type, description, quantity, unit_price, created_at)")
        add(lines, f"SELECT invoice_id, 'ROOM_RENT', 'Tien phong 404 thang {ym}', 1, 2450000, '{y}-{m:02d}-01 08:00:00' FROM hdbhms.invoices WHERE invoice_code='{inv_code}' LIMIT 1;")

        add(lines, f"INSERT IGNORE INTO hdbhms.payment_transactions (provider, provider_transaction_id, collection_account_id, amount, transaction_time, payer_name, payer_account, content, status, created_at)")
        add(lines, f"VALUES ('BANK', '{tx_code}', @ra, 2450000, '{pay_time}', 'Do Hoang Anh', '9704364040404001', 'TIEN PHONG P404 {ym}', 'ALLOCATED', '{pay_time}');")

        add(lines, f"INSERT IGNORE INTO hdbhms.payment_allocations (payment_transaction_id, invoice_id, amount, allocated_by, allocated_at)")
        add(lines, f"SELECT pt.payment_transaction_id, i.invoice_id, 2450000, @mg, '{pay_time}'")
        add(lines, f"FROM hdbhms.payment_transactions pt, hdbhms.invoices i")
        add(lines, f"WHERE pt.provider_transaction_id='{tx_code}' AND i.invoice_code='{inv_code}' LIMIT 1;")
        add(lines, "")

    # ================================================================
    # ROOM 405: Monthly rent (2026-01 to 2026-07)
    # ================================================================
    add(lines, "-- ROOM 405: Monthly rent (2026-01 to 2026-07, 2,550,000 VND each)")
    for idx, (y, m) in enumerate(months):
        ym = f"{y}-{m:02d}"
        if ym < "2026-01":
            continue

        inv_code = f"DEMO-INV-405-{ym}-RENT"
        tx_code = f"BANK-P405-{ym}-RENT"
        pay_time = f"{y}-{m:02d}-02 09:00:00"

        add(lines, f"INSERT IGNORE INTO hdbhms.invoices (invoice_code, property_id, room_id, lease_contract_id, invoice_type, revision_no, billing_period, issue_date, due_date, status, subtotal_amount, total_amount, paid_amount, remaining_amount, collection_account_id, created_by, created_at, updated_at)")
        add(lines, f"VALUES ('{inv_code}', @pid, @r405, @c405, 'RENT', 1, '{ym}', '{y}-{m:02d}-01 08:00:00', '{y}-{m:02d}-15 23:59:59', 'PAID', 2550000, 2550000, 2550000, 0, @ra, @mg, '{y}-{m:02d}-01 08:00:00', '{pay_time}');")

        add(lines, f"INSERT IGNORE INTO hdbhms.invoice_lines (invoice_id, line_type, description, quantity, unit_price, created_at)")
        add(lines, f"SELECT invoice_id, 'ROOM_RENT', 'Tien phong 405 thang {ym}', 1, 2550000, '{y}-{m:02d}-01 08:00:00' FROM hdbhms.invoices WHERE invoice_code='{inv_code}' LIMIT 1;")

        add(lines, f"INSERT IGNORE INTO hdbhms.payment_transactions (provider, provider_transaction_id, collection_account_id, amount, transaction_time, payer_name, payer_account, content, status, created_at)")
        add(lines, f"VALUES ('BANK', '{tx_code}', @ra, 2550000, '{pay_time}', 'Nguyen Minh Khoa', '9704364050505001', 'TIEN PHONG P405 {ym}', 'ALLOCATED', '{pay_time}');")

        add(lines, f"INSERT IGNORE INTO hdbhms.payment_allocations (payment_transaction_id, invoice_id, amount, allocated_by, allocated_at)")
        add(lines, f"SELECT pt.payment_transaction_id, i.invoice_id, 2550000, @mg, '{pay_time}'")
        add(lines, f"FROM hdbhms.payment_transactions pt, hdbhms.invoices i")
        add(lines, f"WHERE pt.provider_transaction_id='{tx_code}' AND i.invoice_code='{inv_code}' LIMIT 1;")
        add(lines, "")

    # ================================================================
    # ROOM 501: Monthly utility invoices for expense history (10 months)
    # Skip 2026-04 (OVERDUE exists) and 2026-06 (PARTIALLY_PAID exists)
    # ================================================================
    add(lines, "-- ROOM 501: Monthly utility invoices (10 months for expense history)")
    for idx, (y, m) in enumerate(months):
        ym = f"{y}-{m:02d}"
        if ym in ("2026-04", "2026-06"):
            continue

        # Varying electricity usage to show trend
        elec_kwh = 50 + idx * 4  # 50 to 94 kWh
        water_unit = 1
        total_amt = elec_kwh * 3500 + water_unit * 20000 + 50000

        inv_code = f"DEMO-INV-501-{ym}-UTILITY"
        # Next month for due date / payment
        ny, nm = (y + 1, 1) if m == 12 else (y, m + 1)
        pay_time = f"{ny}-{nm:02d}-02 09:00:00"

        add(lines, f"INSERT IGNORE INTO hdbhms.invoices (invoice_code, property_id, room_id, lease_contract_id, invoice_type, revision_no, billing_period, issue_date, due_date, status, subtotal_amount, total_amount, paid_amount, remaining_amount, collection_account_id, created_by, created_at, updated_at)")
        add(lines, f"VALUES ('{inv_code}', @pid, @r501, @c501, 'UTILITY', 1, '{ym}', '{y}-{m:02d}-25 08:00:00', '{ny}-{nm:02d}-05 23:59:59', 'PAID', {total_amt}, {total_amt}, {total_amt}, 0, @ua, @mg, '{y}-{m:02d}-25 08:00:00', '{pay_time}');")

        add(lines, f"INSERT IGNORE INTO hdbhms.invoice_lines (invoice_id, line_type, description, quantity, unit_price, created_at)")
        add(lines, f"SELECT invoice_id, 'ELECTRICITY', 'Dien P501 thang {ym}', {elec_kwh}, 3500, '{y}-{m:02d}-25 08:00:00' FROM hdbhms.invoices WHERE invoice_code='{inv_code}' LIMIT 1;")

        add(lines, f"INSERT IGNORE INTO hdbhms.invoice_lines (invoice_id, line_type, description, quantity, unit_price, created_at)")
        add(lines, f"SELECT invoice_id, 'WATER', 'Nuoc P501 thang {ym}', {water_unit}, 20000, '{y}-{m:02d}-25 08:00:00' FROM hdbhms.invoices WHERE invoice_code='{inv_code}' LIMIT 1;")

        add(lines, f"INSERT IGNORE INTO hdbhms.invoice_lines (invoice_id, line_type, description, quantity, unit_price, created_at)")
        add(lines, f"SELECT invoice_id, 'SERVICE_FEE', 'Phi dich vu P501 thang {ym}', 1, 50000, '{y}-{m:02d}-25 08:00:00' FROM hdbhms.invoices WHERE invoice_code='{inv_code}' LIMIT 1;")

        tx_code = f"PAYOS-P501-{ym}-UTILITY"
        add(lines, f"INSERT IGNORE INTO hdbhms.payment_transactions (provider, provider_transaction_id, collection_account_id, amount, transaction_time, payer_name, payer_account, content, status, created_at)")
        add(lines, f"VALUES ('PAYOS', '{tx_code}', @ua, {total_amt}, '{pay_time}', 'Pham Quoc Bao', '9704185010501001', 'DIEN NUOC P501 {ym}', 'ALLOCATED', '{pay_time}');")

        add(lines, f"INSERT IGNORE INTO hdbhms.payment_allocations (payment_transaction_id, invoice_id, amount, allocated_by, allocated_at)")
        add(lines, f"SELECT pt.payment_transaction_id, i.invoice_id, {total_amt}, @mg, '{pay_time}'")
        add(lines, f"FROM hdbhms.payment_transactions pt, hdbhms.invoices i")
        add(lines, f"WHERE pt.provider_transaction_id='{tx_code}' AND i.invoice_code='{inv_code}' LIMIT 1;")
        add(lines, "")

    # ================================================================
    # Verify results
    # ================================================================
    add(lines, "-- Verify")
    add(lines, "SELECT 'OK: Monthly seed data added' AS status;")
    add(lines, "")
    add(lines, "SELECT CONCAT('Revenue months: ', COUNT(DISTINCT DATE_FORMAT(transaction_time, '%Y-%m'))) AS result")
    add(lines, "FROM hdbhms.payment_transactions")
    add(lines, "WHERE transaction_time >= DATE_SUB(CURDATE(), INTERVAL 12 MONTH)")
    add(lines, "  AND status = 'ALLOCATED';")
    add(lines, "")
    add(lines, "SELECT CONCAT('Total invoices: ', COUNT(*)) AS result FROM hdbhms.invoices;")
    add(lines, "SELECT CONCAT('Total payments: ', COUNT(*)) AS result FROM hdbhms.payment_transactions;")

    sql_content = "\n".join(lines)
    return sql_content


if __name__ == "__main__":
    print("Generating monthly seed SQL...")
    sql = generate_sql()

    # Write to file first (avoids encoding issues)
    with open(OUTPUT_SQL, "w", encoding="utf-8") as f:
        f.write(sql)
    print(f"SQL written to {OUTPUT_SQL}")

    # Execute via docker
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
