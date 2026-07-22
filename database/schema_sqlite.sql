-- ============================================================
-- HDBHMS - SQLite Schema (Dev/Test)
-- ============================================================

CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    email TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    full_name TEXT NOT NULL,
    phone TEXT,
    avatar_url TEXT,
    is_active INTEGER DEFAULT 1,
    last_login_at TEXT,
    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE roles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE NOT NULL,
    description TEXT
);

CREATE TABLE user_roles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    role_id INTEGER REFERENCES roles(id) ON DELETE CASCADE,
    landlord_id INTEGER DEFAULT 0,
    granted_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE permissions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    role_id INTEGER REFERENCES roles(id) ON DELETE CASCADE,
    resource TEXT NOT NULL,
    action TEXT NOT NULL
);

CREATE TABLE landlords (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
    name TEXT NOT NULL,
    company_name TEXT,
    tax_code TEXT,
    address TEXT,
    phone TEXT,
    email TEXT,
    logo_url TEXT,
    currency TEXT DEFAULT 'VND',
    locale TEXT DEFAULT 'vi-VN',
    timezone TEXT DEFAULT 'Asia/Ho_Chi_Minh',
    settings TEXT DEFAULT '{}',
    is_active INTEGER DEFAULT 1,
    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE properties (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    landlord_id INTEGER NOT NULL REFERENCES landlords(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    name_en TEXT,
    description TEXT,
    address_street TEXT,
    address_ward TEXT,
    address_district TEXT,
    address_city TEXT,
    address_province TEXT,
    latitude REAL,
    longitude REAL,
    property_type TEXT DEFAULT 'APARTMENT',
    total_floors INTEGER DEFAULT 1,
    total_rooms INTEGER DEFAULT 0,
    status TEXT DEFAULT 'ACTIVE',
    amenities TEXT DEFAULT '[]',
    images TEXT DEFAULT '[]',
    rules TEXT,
    electricity_unit_price REAL DEFAULT 0,
    water_unit_price REAL DEFAULT 0,
    service_fee REAL DEFAULT 0,
    billing_cycle_day INTEGER DEFAULT 1,
    due_days INTEGER DEFAULT 15,
    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE floors (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    property_id INTEGER NOT NULL REFERENCES properties(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    level INTEGER DEFAULT 0,
    description TEXT,
    floor_plan_url TEXT
);

CREATE TABLE rooms (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    property_id INTEGER NOT NULL REFERENCES properties(id) ON DELETE CASCADE,
    floor_id INTEGER REFERENCES floors(id) ON DELETE SET NULL,
    landlord_id INTEGER NOT NULL REFERENCES landlords(id) ON DELETE CASCADE,
    room_number TEXT NOT NULL,
    room_type TEXT DEFAULT 'STANDARD',
    base_price REAL NOT NULL,
    deposit_amount REAL DEFAULT 0,
    area_sqm REAL,
    capacity INTEGER DEFAULT 1,
    current_occupants INTEGER DEFAULT 0,
    status TEXT DEFAULT 'VACANT',
    has_air_conditioner INTEGER DEFAULT 0,
    has_water_heater INTEGER DEFAULT 0,
    has_furniture INTEGER DEFAULT 0,
    has_private_bathroom INTEGER DEFAULT 0,
    has_balcony INTEGER DEFAULT 0,
    has_kitchen INTEGER DEFAULT 0,
    amenities TEXT DEFAULT '[]',
    images TEXT DEFAULT '[]',
    notes TEXT,
    is_active INTEGER DEFAULT 1,
    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE tenants (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    full_name TEXT NOT NULL,
    phone TEXT NOT NULL,
    email TEXT,
    identification_number TEXT,
    identification_issue_date TEXT,
    identification_issue_place TEXT,
    identification_front_url TEXT,
    identification_back_url TEXT,
    permanent_address TEXT,
    occupation TEXT,
    workplace TEXT,
    emergency_contact_name TEXT,
    emergency_contact_phone TEXT,
    emergency_contact_relation TEXT,
    date_of_birth TEXT,
    gender TEXT,
    nationality TEXT DEFAULT 'Việt Nam',
    avatar_url TEXT,
    notes TEXT,
    is_active INTEGER DEFAULT 1,
    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE tenant_vehicles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tenant_id INTEGER NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    vehicle_type TEXT,
    license_plate TEXT NOT NULL,
    brand TEXT,
    color TEXT,
    image_url TEXT,
    created_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE co_occupants (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tenant_id INTEGER NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    full_name TEXT NOT NULL,
    phone TEXT,
    identification_number TEXT,
    relationship TEXT,
    is_active INTEGER DEFAULT 1,
    created_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE contracts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    property_id INTEGER NOT NULL REFERENCES properties(id) ON DELETE CASCADE,
    room_id INTEGER NOT NULL REFERENCES rooms(id) ON DELETE CASCADE,
    landlord_id INTEGER NOT NULL REFERENCES landlords(id) ON DELETE CASCADE,
    tenant_id INTEGER NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    contract_number TEXT UNIQUE NOT NULL,
    contract_type TEXT DEFAULT 'RENTAL',
    rent_price REAL NOT NULL,
    deposit_amount REAL DEFAULT 0,
    deposit_note TEXT,
    start_date TEXT NOT NULL,
    end_date TEXT NOT NULL,
    billing_cycle_days INTEGER DEFAULT 30,
    payment_method TEXT DEFAULT 'MONTHLY',
    payment_day INTEGER DEFAULT 15,
    terms_conditions TEXT,
    cancellation_policy TEXT,
    discount_percentage REAL DEFAULT 0,
    discount_amount REAL DEFAULT 0,
    discount_reason TEXT,
    is_vat_applied INTEGER DEFAULT 0,
    vat_percentage REAL DEFAULT 0,
    status TEXT DEFAULT 'ACTIVE',
    termination_date TEXT,
    termination_reason TEXT,
    intent_type TEXT,
    intent_date TEXT,
    signed_by_tenant INTEGER DEFAULT 0,
    signed_by_landlord INTEGER DEFAULT 0,
    signed_at TEXT,
    contract_file_url TEXT,
    renewal_count INTEGER DEFAULT 0,
    is_active INTEGER DEFAULT 1,
    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE contract_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    contract_id INTEGER NOT NULL REFERENCES contracts(id) ON DELETE CASCADE,
    action TEXT NOT NULL,
    old_value TEXT,
    new_value TEXT,
    changed_by INTEGER REFERENCES users(id),
    changed_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE bills (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    contract_id INTEGER NOT NULL REFERENCES contracts(id) ON DELETE CASCADE,
    property_id INTEGER NOT NULL REFERENCES properties(id) ON DELETE CASCADE,
    landlord_id INTEGER NOT NULL REFERENCES landlords(id) ON DELETE CASCADE,
    room_id INTEGER NOT NULL REFERENCES rooms(id) ON DELETE CASCADE,
    tenant_id INTEGER NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    invoice_number TEXT UNIQUE NOT NULL,
    period_start TEXT NOT NULL,
    period_end TEXT NOT NULL,
    due_date TEXT NOT NULL,
    rent_amount REAL DEFAULT 0,
    electricity_old_index REAL DEFAULT 0,
    electricity_new_index REAL DEFAULT 0,
    electricity_consumption REAL DEFAULT 0,
    electricity_unit_price REAL DEFAULT 0,
    electricity_amount REAL DEFAULT 0,
    water_old_index REAL DEFAULT 0,
    water_new_index REAL DEFAULT 0,
    water_consumption REAL DEFAULT 0,
    water_unit_price REAL DEFAULT 0,
    water_amount REAL DEFAULT 0,
    service_amount REAL DEFAULT 0,
    service_details TEXT DEFAULT '[]',
    other_charges REAL DEFAULT 0,
    other_charges_note TEXT,
    discount_amount REAL DEFAULT 0,
    discount_reason TEXT,
    sub_total REAL DEFAULT 0,
    total_amount REAL DEFAULT 0,
    status TEXT DEFAULT 'UNPAID',
    paid_amount REAL DEFAULT 0,
    remaining_amount REAL DEFAULT 0,
    preferred_payment TEXT,
    qr_code_url TEXT,
    bank_transfer_info TEXT,
    notes TEXT,
    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE payments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    bill_id INTEGER NOT NULL REFERENCES bills(id) ON DELETE CASCADE,
    contract_id INTEGER NOT NULL REFERENCES contracts(id) ON DELETE CASCADE,
    paid_amount REAL NOT NULL,
    payment_date TEXT NOT NULL,
    payment_method TEXT,
    payment_reference TEXT,
    bank_account TEXT,
    bank_transaction_id TEXT,
    due_date TEXT,
    days_late INTEGER DEFAULT 0,
    late_fee REAL DEFAULT 0,
    received_by INTEGER REFERENCES users(id),
    notes TEXT,
    receipt_url TEXT,
    created_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE meter_reading_periods (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    property_id INTEGER NOT NULL REFERENCES properties(id) ON DELETE CASCADE,
    period_name TEXT NOT NULL,
    period_start TEXT NOT NULL,
    period_end TEXT NOT NULL,
    status TEXT DEFAULT 'OPEN',
    total_rooms INTEGER DEFAULT 0,
    entered_count INTEGER DEFAULT 0,
    anomaly_count INTEGER DEFAULT 0,
    created_by INTEGER REFERENCES users(id),
    created_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE meter_readings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    period_id INTEGER NOT NULL REFERENCES meter_reading_periods(id) ON DELETE CASCADE,
    room_id INTEGER NOT NULL REFERENCES rooms(id) ON DELETE CASCADE,
    electricity_old_index REAL NOT NULL,
    electricity_new_index REAL,
    electricity_consumption REAL,
    has_anomaly_electricity INTEGER DEFAULT 0,
    anomaly_electricity_note TEXT,
    water_old_index REAL NOT NULL,
    water_new_index REAL,
    water_consumption REAL,
    has_anomaly_water INTEGER DEFAULT 0,
    anomaly_water_note TEXT,
    status TEXT DEFAULT 'PENDING',
    entered_by INTEGER REFERENCES users(id),
    entered_at TEXT,
    verified_by INTEGER REFERENCES users(id),
    verified_at TEXT,
    notes TEXT,
    created_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE issues (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    property_id INTEGER NOT NULL REFERENCES properties(id) ON DELETE CASCADE,
    room_id INTEGER REFERENCES rooms(id) ON DELETE SET NULL,
    reported_by INTEGER NOT NULL REFERENCES users(id),
    assigned_to INTEGER REFERENCES users(id),
    issue_number TEXT UNIQUE NOT NULL,
    category TEXT NOT NULL,
    title TEXT NOT NULL,
    description TEXT NOT NULL,
    priority TEXT DEFAULT 'MEDIUM',
    severity TEXT DEFAULT 'MINOR',
    attachments TEXT DEFAULT '[]',
    status TEXT DEFAULT 'PENDING',
    resolution_notes TEXT,
    resolved_at TEXT,
    resolved_by INTEGER REFERENCES users(id),
    review_rating INTEGER,
    review_comment TEXT,
    review_after_photo TEXT,
    review_submitted_at TEXT,
    cost REAL DEFAULT 0,
    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE deposits (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    property_id INTEGER NOT NULL REFERENCES properties(id) ON DELETE CASCADE,
    room_id INTEGER NOT NULL REFERENCES rooms(id) ON DELETE CASCADE,
    landlord_id INTEGER NOT NULL REFERENCES landlords(id) ON DELETE CASCADE,
    tenant_name TEXT NOT NULL,
    tenant_phone TEXT NOT NULL,
    tenant_email TEXT,
    deposit_amount REAL NOT NULL,
    deposit_date TEXT DEFAULT (datetime('now')),
    payment_method TEXT,
    payment_reference TEXT,
    status TEXT DEFAULT 'HOLDING',
    hold_until TEXT,
    converted_to_contract_id INTEGER REFERENCES contracts(id),
    refund_date TEXT,
    refund_amount REAL,
    notes TEXT,
    created_by INTEGER REFERENCES users(id),
    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE visit_requests (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    property_id INTEGER NOT NULL REFERENCES properties(id) ON DELETE CASCADE,
    room_id INTEGER REFERENCES rooms(id) ON DELETE SET NULL,
    customer_name TEXT NOT NULL,
    customer_phone TEXT NOT NULL,
    customer_email TEXT,
    notes TEXT,
    requested_date TEXT NOT NULL,
    status TEXT DEFAULT 'PENDING',
    handled_by INTEGER REFERENCES users(id),
    feedback TEXT,
    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE notifications (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    landlord_id INTEGER REFERENCES landlords(id) ON DELETE CASCADE,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    type TEXT NOT NULL,
    title TEXT NOT NULL,
    content TEXT,
    reference_type TEXT,
    reference_id INTEGER,
    is_read INTEGER DEFAULT 0,
    is_push_sent INTEGER DEFAULT 0,
    read_at TEXT,
    created_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE vacancy_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    room_id INTEGER NOT NULL REFERENCES rooms(id) ON DELETE CASCADE,
    property_id INTEGER NOT NULL REFERENCES properties(id) ON DELETE CASCADE,
    landlord_id INTEGER NOT NULL REFERENCES landlords(id) ON DELETE CASCADE,
    vacant_from TEXT NOT NULL,
    occupied_at TEXT,
    vacancy_reason TEXT,
    notes TEXT
);

CREATE TABLE audit_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    landlord_id INTEGER REFERENCES landlords(id),
    user_id INTEGER REFERENCES users(id),
    action TEXT NOT NULL,
    resource_type TEXT NOT NULL,
    resource_id INTEGER,
    details TEXT,
    ip_address TEXT,
    user_agent TEXT,
    created_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE ai_reports (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    landlord_id INTEGER NOT NULL REFERENCES landlords(id) ON DELETE CASCADE,
    period TEXT NOT NULL,
    health_score INTEGER,
    health_status TEXT,
    revenue_leakage REAL,
    summary TEXT,
    narrative TEXT,
    opportunities TEXT DEFAULT '[]',
    risks TEXT DEFAULT '[]',
    recommended_actions TEXT DEFAULT '[]',
    generated_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE ai_chat_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    landlord_id INTEGER NOT NULL REFERENCES landlords(id) ON DELETE CASCADE,
    user_id INTEGER REFERENCES users(id),
    question TEXT NOT NULL,
    sql_query TEXT,
    sql_result TEXT,
    ai_response TEXT,
    visualization TEXT,
    is_successful INTEGER DEFAULT 1,
    execution_time_ms INTEGER,
    created_at TEXT DEFAULT (datetime('now'))
);

-- Indexes
CREATE INDEX idx_properties_landlord ON properties(landlord_id);
CREATE INDEX idx_floors_property ON floors(property_id);
CREATE INDEX idx_rooms_property ON rooms(property_id);
CREATE INDEX idx_rooms_landlord ON rooms(landlord_id);
CREATE INDEX idx_rooms_status ON rooms(status);
CREATE INDEX idx_rooms_floor ON rooms(floor_id);
CREATE INDEX idx_tenants_phone ON tenants(phone);
CREATE INDEX idx_tenant_vehicles_tenant ON tenant_vehicles(tenant_id);
CREATE INDEX idx_contracts_room ON contracts(room_id);
CREATE INDEX idx_contracts_tenant ON contracts(tenant_id);
CREATE INDEX idx_contracts_landlord ON contracts(landlord_id);
CREATE INDEX idx_contracts_property ON contracts(property_id);
CREATE INDEX idx_contracts_status ON contracts(status);
CREATE INDEX idx_contracts_end_date ON contracts(end_date);
CREATE INDEX idx_bills_contract ON bills(contract_id);
CREATE INDEX idx_bills_room ON bills(room_id);
CREATE INDEX idx_bills_tenant ON bills(tenant_id);
CREATE INDEX idx_bills_landlord ON bills(landlord_id);
CREATE INDEX idx_bills_status ON bills(status);
CREATE INDEX idx_bills_due_date ON bills(due_date);
CREATE INDEX idx_payments_bill ON payments(bill_id);
CREATE INDEX idx_payments_date ON payments(payment_date);
CREATE INDEX idx_meter_readings_period ON meter_readings(period_id);
CREATE INDEX idx_meter_readings_room ON meter_readings(room_id);
CREATE INDEX idx_meter_reading_periods_prop ON meter_reading_periods(property_id);
CREATE INDEX idx_issues_property ON issues(property_id);
CREATE INDEX idx_issues_room ON issues(room_id);
CREATE INDEX idx_issues_status ON issues(status);
CREATE INDEX idx_deposits_room ON deposits(room_id);
CREATE INDEX idx_deposits_landlord ON deposits(landlord_id);
CREATE INDEX idx_deposits_status ON deposits(status);
CREATE INDEX idx_visit_requests_property ON visit_requests(property_id);
CREATE INDEX idx_visit_requests_status ON visit_requests(status);
CREATE INDEX idx_notifications_user ON notifications(user_id);
CREATE INDEX idx_notifications_read ON notifications(is_read);
CREATE INDEX idx_vacancy_logs_room ON vacancy_logs(room_id);
CREATE INDEX idx_vacancy_logs_landlord ON vacancy_logs(landlord_id);
CREATE INDEX idx_audit_logs_landlord ON audit_logs(landlord_id);
CREATE INDEX idx_audit_logs_user ON audit_logs(user_id);
CREATE INDEX idx_ai_reports_landlord ON ai_reports(landlord_id);
CREATE INDEX idx_ai_reports_period ON ai_reports(period);
CREATE INDEX idx_ai_chat_history_landlord ON ai_chat_history(landlord_id);
