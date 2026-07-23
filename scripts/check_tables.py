import subprocess
import json

tables = [
    'users', 'person_profiles', 'identity_documents', 'login_history', 'file_metadata', 
    'properties', 'rooms', 'room_status_history', 'room_assets', 'tenants', 
    'emergency_contacts', 'vehicles', 'role_promotions', 'property_staff_assignments', 
    'collection_accounts', 'utility_tariffs', 'meters', 'meter_reading_batches', 
    'meter_readings', 'meter_reading_anomalies', 'deposit_forms', 'room_holds', 
    'deposit_agreements', 'lease_contracts', 'contract_occupants', 'contract_events', 
    'contract_termination_notices', 'contract_handover_records', 'contract_handover_items', 
    'contract_liquidations', 'tenant_account_provisionings', 'invoices', 'invoice_lines', 
    'rent_overrides', 'payment_intents', 'payment_transactions', 'payment_allocations', 
    'invoice_payment_groups', 'debt_snapshots', 'debt_notice_trackers', 'maintenance_tickets', 
    'maintenance_ticket_events', 'maintenance_costs', 'maintenance_reviews', 
    'pending_billing_charges', 'operating_expenses', 'ledger_entries', 'rule_violations', 
    'room_transfer_requests', 'transfer_settlements', 'change_requests', 'change_request_events', 
    'visit_requests', 'manager_tasks', 'scheduled_tasks', 'notification_outbox', 
    'notification_deliveries', 'audit_logs', 'ai_reports', 'ai_chat_history', 
    'vacancy_logs', 'ai_audit_logs'
]

results = {}
for t in tables:
    cmd = ["docker", "exec", "-i", "hdbhms_mysql", "mysql", "-uroot", "-ppassword", "hdbhms", "-e", f"SELECT COUNT(*) FROM {t};"]
    res = subprocess.run(cmd, capture_output=True, text=True)
    out = res.stdout.strip().split("\n")
    if len(out) > 1:
        try:
            results[t] = int(out[1])
        except Exception:
            results[t] = 0
    else:
        results[t] = 0

print(json.dumps(results, indent=2))
