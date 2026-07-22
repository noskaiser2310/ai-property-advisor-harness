-- ============================================================
-- HDBHMS - Hai Dang Boarding House Management System
-- Enhanced Database Schema (PostgreSQL)
-- Kết hợp: MicroRealEstate (properties/tenants/leases) +
--          ORPMS (billing/accounting) +
--          OpenKoda (RBAC/audit/multi-tenancy) +
--          Ai_arch.md (AI Advisor)
-- ============================================================

-- ============================================================
-- 1. ACCOUNTS & AUTH (từ OpenKoda RBAC)
-- ============================================================

-- Người dùng (có thể là Owner, Manager, Accountant, Tenant, Staff)
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    full_name VARCHAR(255) NOT NULL,
    phone VARCHAR(20),
    avatar_url VARCHAR(500),
    is_active BOOLEAN DEFAULT TRUE,
    last_login_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Vai trò (RBAC)
CREATE TABLE roles (
    id SERIAL PRIMARY KEY,
    name VARCHAR(50) UNIQUE NOT NULL, -- OWNER, MANAGER, ACCOUNTANT, TENANT, STAFF
    description VARCHAR(255)
);

-- Gán quyền cho người dùng (OpenKoda-style RBAC)
CREATE TABLE user_roles (
    id SERIAL PRIMARY KEY,
    user_id INT REFERENCES users(id) ON DELETE CASCADE,
    role_id INT REFERENCES roles(id) ON DELETE CASCADE,
    landlord_id INT, -- NULL nếu là role hệ thống
    granted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, role_id, COALESCE(landlord_id, 0))
);

-- Quyền hạn chi tiết
CREATE TABLE permissions (
    id SERIAL PRIMARY KEY,
    role_id INT REFERENCES roles(id) ON DELETE CASCADE,
    resource VARCHAR(100) NOT NULL, -- rooms, tenants, contracts, bills, etc.
    action VARCHAR(50) NOT NULL, -- CREATE, READ, UPDATE, DELETE, EXPORT
    CONSTRAINT unique_role_permission UNIQUE (role_id, resource, action)
);

-- ============================================================
-- 2. PROPERTY MANAGEMENT (từ MicroRealEstate)
-- ============================================================

-- Chủ trọ / Landlord / Realm (MicroRealEstate concept)
CREATE TABLE landlords (
    id SERIAL PRIMARY KEY,
    user_id INT REFERENCES users(id) ON DELETE SET NULL,
    name VARCHAR(255) NOT NULL,
    company_name VARCHAR(255),
    tax_code VARCHAR(50),
    address TEXT,
    phone VARCHAR(20),
    email VARCHAR(255),
    logo_url VARCHAR(500),
    currency VARCHAR(10) DEFAULT 'VND',
    locale VARCHAR(10) DEFAULT 'vi-VN',
    timezone VARCHAR(50) DEFAULT 'Asia/Ho_Chi_Minh',
    settings JSONB DEFAULT '{}', -- Cấu hình mở rộng
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Khu trọ / Tòa nhà / Property (mở rộng từ MicroRealEstate + ORPMS)
CREATE TABLE properties (
    id SERIAL PRIMARY KEY,
    landlord_id INT NOT NULL REFERENCES landlords(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    name_en VARCHAR(255), -- Tên tiếng Anh (đa ngôn ngữ - MicroRealEstate feature)
    description TEXT,
    address_street VARCHAR(255),
    address_ward VARCHAR(100),
    address_district VARCHAR(100),
    address_city VARCHAR(100),
    address_province VARCHAR(100),
    latitude DECIMAL(10, 7),
    longitude DECIMAL(10, 7),
    property_type VARCHAR(50) DEFAULT 'APARTMENT', -- APARTMENT, HOUSE, DORMITORY, OFFICE
    total_floors INT DEFAULT 1,
    total_rooms INT DEFAULT 0,
    status VARCHAR(50) DEFAULT 'ACTIVE', -- ACTIVE, INACTIVE, MAINTENANCE
    amenities JSONB DEFAULT '[]', -- Tiện ích: wifi, máy giặt, bảo vệ...
    images JSONB DEFAULT '[]',
    rules TEXT, -- Nội quy khu trọ
    -- Cấu hình hóa đơn (từ ORPMS)
    electricity_unit_price DECIMAL(12, 2) DEFAULT 0,
    water_unit_price DECIMAL(12, 2) DEFAULT 0,
    service_fee DECIMAL(12, 2) DEFAULT 0,
    billing_cycle_day INT DEFAULT 1, -- Ngày chốt hóa đơn hàng tháng
    due_days INT DEFAULT 15, -- Hạn thanh toán (ngày sau kỳ)
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Tầng (Floor) - quản lý theo tầng
CREATE TABLE floors (
    id SERIAL PRIMARY KEY,
    property_id INT NOT NULL REFERENCES properties(id) ON DELETE CASCADE,
    name VARCHAR(100) NOT NULL, -- "Tầng 1", "Tầng 2", ...
    level INT NOT NULL DEFAULT 0,
    description VARCHAR(255),
    floor_plan_url VARCHAR(500) -- Sơ đồ mặt bằng
);

-- ============================================================
-- 3. ROOM MANAGEMENT (từ MicroRealEstate + current)
-- ============================================================

-- Phòng (Room) - mở rộng từ schema hiện tại
CREATE TABLE rooms (
    id SERIAL PRIMARY KEY,
    property_id INT NOT NULL REFERENCES properties(id) ON DELETE CASCADE,
    floor_id INT REFERENCES floors(id) ON DELETE SET NULL,
    landlord_id INT NOT NULL REFERENCES landlords(id) ON DELETE CASCADE,
    room_number VARCHAR(50) NOT NULL,
    room_type VARCHAR(50) DEFAULT 'STANDARD', -- STANDARD, VIP, STUDIO, DORMITORY
    base_price DECIMAL(12, 2) NOT NULL,
    deposit_amount DECIMAL(12, 2) DEFAULT 0,
    area_sqm DECIMAL(8, 2), -- Diện tích (m²)
    capacity INT DEFAULT 1, -- Số người tối đa
    current_occupants INT DEFAULT 0,
    -- Trạng thái (mở rộng từ MicroRealEstate)
    status VARCHAR(50) DEFAULT 'VACANT', -- VACANT, RENTED, RESERVED, MAINTENANCE
    -- Tiện nghi
    has_air_conditioner BOOLEAN DEFAULT FALSE,
    has_water_heater BOOLEAN DEFAULT FALSE,
    has_furniture BOOLEAN DEFAULT FALSE,
    has_private_bathroom BOOLEAN DEFAULT FALSE,
    has_balcony BOOLEAN DEFAULT FALSE,
    has_kitchen BOOLEAN DEFAULT FALSE,
    amenities JSONB DEFAULT '[]',
    images JSONB DEFAULT '[]',
    notes TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT unique_room_per_property UNIQUE (property_id, room_number)
);

-- ============================================================
-- 4. TENANT MANAGEMENT (từ MicroRealEstate + ORPMS)
-- ============================================================

-- Khách thuê (Tenant) - mở rộng
CREATE TABLE tenants (
    id SERIAL PRIMARY KEY,
    full_name VARCHAR(255) NOT NULL,
    phone VARCHAR(20) NOT NULL,
    email VARCHAR(255),
    -- Danh tính (từ ORPMS)
    identification_number VARCHAR(50), -- CCCD/CMND
    identification_issue_date DATE,
    identification_issue_place VARCHAR(255),
    identification_front_url VARCHAR(500),
    identification_back_url VARCHAR(500),
    -- Địa chỉ thường trú
    permanent_address TEXT,
    -- Nghề nghiệp
    occupation VARCHAR(255),
    workplace VARCHAR(255),
    -- Liên hệ khẩn cấp (từ MicroRealEstate)
    emergency_contact_name VARCHAR(255),
    emergency_contact_phone VARCHAR(20),
    emergency_contact_relation VARCHAR(100),
    -- Hồ sơ
    date_of_birth DATE,
    gender VARCHAR(10),
    nationality VARCHAR(100) DEFAULT 'Việt Nam',
    avatar_url VARCHAR(500),
    notes TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Xe của khách thuê (từ Screen Design Spec)
CREATE TABLE tenant_vehicles (
    id SERIAL PRIMARY KEY,
    tenant_id INT NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    vehicle_type VARCHAR(50), -- MOTORBIKE, CAR, BICYCLE, ELECTRIC
    license_plate VARCHAR(50) NOT NULL,
    brand VARCHAR(100),
    color VARCHAR(50),
    image_url VARCHAR(500),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Người ở ghép (Co-occupant) - từ MicroRealEstate
CREATE TABLE co_occupants (
    id SERIAL PRIMARY KEY,
    tenant_id INT NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    full_name VARCHAR(255) NOT NULL,
    phone VARCHAR(20),
    identification_number VARCHAR(50),
    relationship VARCHAR(100),
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================
-- 5. CONTRACT MANAGEMENT (từ MicroRealEstate lease)
-- ============================================================

-- Hợp đồng thuê (Contract/Lease) - mở rộng
CREATE TABLE contracts (
    id SERIAL PRIMARY KEY,
    property_id INT NOT NULL REFERENCES properties(id) ON DELETE CASCADE,
    room_id INT NOT NULL REFERENCES rooms(id) ON DELETE CASCADE,
    landlord_id INT NOT NULL REFERENCES landlords(id) ON DELETE CASCADE,
    tenant_id INT NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    contract_number VARCHAR(100) UNIQUE NOT NULL, -- Số hợp đồng (từ ORPMS)
    contract_type VARCHAR(50) DEFAULT 'RENTAL', -- RENTAL, DEPOSIT, SERVICE
    -- Giá thuê (mở rộng tính linh hoạt)
    rent_price DECIMAL(12, 2) NOT NULL,
    deposit_amount DECIMAL(12, 2) DEFAULT 0,
    deposit_note TEXT,
    -- Thời hạn
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    billing_cycle_days INT DEFAULT 30,
    -- Thanh toán
    payment_method VARCHAR(50) DEFAULT 'MONTHLY', -- MONTHLY, QUARTERLY, YEARLY
    payment_day INT DEFAULT 15, -- Ngày thanh toán hàng tháng
    -- Điều khoản
    terms_conditions TEXT,
    cancellation_policy TEXT,
    -- Giảm giá (từ ORPMS)
    discount_percentage DECIMAL(5, 2) DEFAULT 0,
    discount_amount DECIMAL(12, 2) DEFAULT 0,
    discount_reason VARCHAR(255),
    -- VAT (từ ORPMS)
    is_vat_applied BOOLEAN DEFAULT FALSE,
    vat_percentage DECIMAL(5, 2) DEFAULT 0,
    -- Trạng thái
    status VARCHAR(50) DEFAULT 'ACTIVE', -- ACTIVE, EXPIRED, TERMINATED, RENEWED
    termination_date DATE,
    termination_reason TEXT,
    -- Intent (từ Screen Design Spec - renew/terminate)
    intent_type VARCHAR(50), -- RENEW, MOVE_OUT, NONE
    intent_date DATE,
    -- Chữ ký số
    signed_by_tenant BOOLEAN DEFAULT FALSE,
    signed_by_landlord BOOLEAN DEFAULT FALSE,
    signed_at TIMESTAMP,
    contract_file_url VARCHAR(500), -- File PDF hợp đồng
    renewal_count INT DEFAULT 0, -- Số lần gia hạn
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Lịch sử hợp đồng (Audit log - từ OpenKoda)
CREATE TABLE contract_history (
    id SERIAL PRIMARY KEY,
    contract_id INT NOT NULL REFERENCES contracts(id) ON DELETE CASCADE,
    action VARCHAR(50) NOT NULL, -- CREATED, RENEWED, TERMINATED, MODIFIED
    old_value JSONB,
    new_value JSONB,
    changed_by INT REFERENCES users(id),
    changed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================
-- 6. BILLING & PAYMENT (từ ORPMS + current)
-- ============================================================

-- Hóa đơn (Bill) - mở rộng
CREATE TABLE bills (
    id SERIAL PRIMARY KEY,
    contract_id INT NOT NULL REFERENCES contracts(id) ON DELETE CASCADE,
    property_id INT NOT NULL REFERENCES properties(id) ON DELETE CASCADE,
    landlord_id INT NOT NULL REFERENCES landlords(id) ON DELETE CASCADE,
    room_id INT NOT NULL REFERENCES rooms(id) ON DELETE CASCADE,
    tenant_id INT NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    invoice_number VARCHAR(100) UNIQUE NOT NULL, -- Mã hóa đơn (từ ORPMS)
    -- Kỳ thanh toán
    period_start DATE NOT NULL,
    period_end DATE NOT NULL,
    due_date DATE NOT NULL,
    -- Chi tiết tiền phòng
    rent_amount DECIMAL(12, 2) NOT NULL DEFAULT 0,
    -- Chi tiết điện nước (từ Screen Design - Meter Readings)
    electricity_old_index DECIMAL(10, 2) DEFAULT 0,
    electricity_new_index DECIMAL(10, 2) DEFAULT 0,
    electricity_consumption DECIMAL(10, 2) DEFAULT 0,
    electricity_unit_price DECIMAL(12, 2) DEFAULT 0,
    electricity_amount DECIMAL(12, 2) DEFAULT 0,
    water_old_index DECIMAL(10, 2) DEFAULT 0,
    water_new_index DECIMAL(10, 2) DEFAULT 0,
    water_consumption DECIMAL(10, 2) DEFAULT 0,
    water_unit_price DECIMAL(12, 2) DEFAULT 0,
    water_amount DECIMAL(12, 2) DEFAULT 0,
    -- Dịch vụ
    service_amount DECIMAL(12, 2) DEFAULT 0,
    service_details JSONB DEFAULT '[]',
    -- Phí khác
    other_charges DECIMAL(12, 2) DEFAULT 0,
    other_charges_note TEXT,
    -- Giảm giá
    discount_amount DECIMAL(12, 2) DEFAULT 0,
    discount_reason VARCHAR(255),
    -- Tổng cộng
    sub_total DECIMAL(12, 2) NOT NULL DEFAULT 0,
    total_amount DECIMAL(12, 2) NOT NULL DEFAULT 0,
    -- Trạng thái (mở rộng)
    status VARCHAR(50) DEFAULT 'UNPAID', -- UNPAID, PARTIALLY_PAID, PAID, OVERDUE, CANCELLED
    paid_amount DECIMAL(12, 2) DEFAULT 0,
    remaining_amount DECIMAL(12, 2) DEFAULT 0,
    -- Phương thức thanh toán ưu tiên
    preferred_payment VARCHAR(50), -- CASH, BANK_TRANSFER, QR_CODE, MOMO
    -- QR Payment (từ Screen Design Spec)
    qr_code_url VARCHAR(500),
    bank_transfer_info TEXT,
    -- Ghi chú
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Lịch sử thanh toán (Payment) - mở rộng
CREATE TABLE payments (
    id SERIAL PRIMARY KEY,
    bill_id INT NOT NULL REFERENCES bills(id) ON DELETE CASCADE,
    contract_id INT NOT NULL REFERENCES contracts(id) ON DELETE CASCADE,
    paid_amount DECIMAL(12, 2) NOT NULL,
    payment_date TIMESTAMP NOT NULL,
    payment_method VARCHAR(50), -- CASH, BANK_TRANSFER, QR_CODE, MOMO, PAYOS
    payment_reference VARCHAR(255), -- Mã giao dịch
    bank_account VARCHAR(100),
    bank_transaction_id VARCHAR(255),
    -- Trễ hạn
    due_date DATE,
    days_late INT DEFAULT 0,
    late_fee DECIMAL(12, 2) DEFAULT 0,
    -- Người thu
    received_by INT REFERENCES users(id),
    notes TEXT,
    receipt_url VARCHAR(500),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================
-- 7. METER READINGS (từ Screen Design Spec)
-- ============================================================

-- Kỳ ghi chỉ số điện nước
CREATE TABLE meter_reading_periods (
    id SERIAL PRIMARY KEY,
    property_id INT NOT NULL REFERENCES properties(id) ON DELETE CASCADE,
    period_name VARCHAR(50) NOT NULL, -- "Tháng 06/2026"
    period_start DATE NOT NULL,
    period_end DATE NOT NULL,
    status VARCHAR(50) DEFAULT 'OPEN', -- OPEN, COMPLETED, CANCELLED
    total_rooms INT DEFAULT 0,
    entered_count INT DEFAULT 0,
    anomaly_count INT DEFAULT 0,
    created_by INT REFERENCES users(id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Chỉ số điện nước từng phòng
CREATE TABLE meter_readings (
    id SERIAL PRIMARY KEY,
    period_id INT NOT NULL REFERENCES meter_reading_periods(id) ON DELETE CASCADE,
    room_id INT NOT NULL REFERENCES rooms(id) ON DELETE CASCADE,
    -- Điện
    electricity_old_index DECIMAL(10, 2) NOT NULL,
    electricity_new_index DECIMAL(10, 2),
    electricity_consumption DECIMAL(10, 2),
    has_anomaly_electricity BOOLEAN DEFAULT FALSE,
    anomaly_electricity_note VARCHAR(255),
    -- Nước
    water_old_index DECIMAL(10, 2) NOT NULL,
    water_new_index DECIMAL(10, 2),
    water_consumption DECIMAL(10, 2),
    has_anomaly_water BOOLEAN DEFAULT FALSE,
    anomaly_water_note VARCHAR(255),
    -- Trạng thái
    status VARCHAR(50) DEFAULT 'PENDING', -- PENDING, ENTERED, VERIFIED
    entered_by INT REFERENCES users(id),
    entered_at TIMESTAMP,
    verified_by INT REFERENCES users(id),
    verified_at TIMESTAMP,
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================
-- 8. ISSUE / MAINTENANCE MANAGEMENT (từ Screen Design Spec)
-- ============================================================

-- Vấn đề / Bảo trì
CREATE TABLE issues (
    id SERIAL PRIMARY KEY,
    property_id INT NOT NULL REFERENCES properties(id) ON DELETE CASCADE,
    room_id INT REFERENCES rooms(id) ON DELETE SET NULL,
    reported_by INT NOT NULL REFERENCES users(id),
    assigned_to INT REFERENCES users(id),
    issue_number VARCHAR(50) UNIQUE NOT NULL,
    category VARCHAR(100) NOT NULL, -- ELECTRIC, PLUMBING, STRUCTURAL, FURNITURE, OTHER
    title VARCHAR(255) NOT NULL,
    description TEXT NOT NULL,
    priority VARCHAR(50) DEFAULT 'MEDIUM', -- LOW, MEDIUM, HIGH, URGENT
    severity VARCHAR(50) DEFAULT 'MINOR', -- MINOR, MAJOR, CRITICAL
    attachments JSONB DEFAULT '[]',
    status VARCHAR(50) DEFAULT 'PENDING', -- PENDING, IN_PROGRESS, RESOLVED, CLOSED
    resolution_notes TEXT,
    resolved_at TIMESTAMP,
    resolved_by INT REFERENCES users(id),
    -- Review (từ Screen Design Spec)
    review_rating INT, -- 1-5 sao
    review_comment TEXT,
    review_after_photo VARCHAR(500),
    review_submitted_at TIMESTAMP,
    cost DECIMAL(12, 2) DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================
-- 9. DEPOSIT MANAGEMENT (từ Screen Design Spec)
-- ============================================================

CREATE TABLE deposits (
    id SERIAL PRIMARY KEY,
    property_id INT NOT NULL REFERENCES properties(id) ON DELETE CASCADE,
    room_id INT NOT NULL REFERENCES rooms(id) ON DELETE CASCADE,
    landlord_id INT NOT NULL REFERENCES landlords(id) ON DELETE CASCADE,
    tenant_name VARCHAR(255) NOT NULL,
    tenant_phone VARCHAR(20) NOT NULL,
    tenant_email VARCHAR(255),
    deposit_amount DECIMAL(12, 2) NOT NULL,
    deposit_date TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    payment_method VARCHAR(50), -- CASH, BANK_TRANSFER, QR_CODE
    payment_reference VARCHAR(255),
    status VARCHAR(50) DEFAULT 'HOLDING', -- HOLDING, CONVERTED_TO_CONTRACT, REFUNDED, CANCELLED
    hold_until DATE, -- Ngày hết hạn giữ chỗ
    converted_to_contract_id INT REFERENCES contracts(id),
    refund_date TIMESTAMP,
    refund_amount DECIMAL(12, 2),
    notes TEXT,
    created_by INT REFERENCES users(id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================
-- 10. VISIT / VIEWING MANAGEMENT (từ Screen Design Spec)
-- ============================================================

CREATE TABLE visit_requests (
    id SERIAL PRIMARY KEY,
    property_id INT NOT NULL REFERENCES properties(id) ON DELETE CASCADE,
    room_id INT REFERENCES rooms(id) ON DELETE SET NULL,
    customer_name VARCHAR(255) NOT NULL,
    customer_phone VARCHAR(20) NOT NULL,
    customer_email VARCHAR(255),
    notes TEXT,
    requested_date TIMESTAMP NOT NULL,
    status VARCHAR(50) DEFAULT 'PENDING', -- PENDING, CONFIRMED, COMPLETED, CANCELLED
    handled_by INT REFERENCES users(id),
    feedback TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================
-- 11. NOTIFICATION CENTER (từ Screen Design Spec + all 3)
-- ============================================================

CREATE TABLE notifications (
    id SERIAL PRIMARY KEY,
    landlord_id INT REFERENCES landlords(id) ON DELETE CASCADE,
    user_id INT REFERENCES users(id) ON DELETE CASCADE,
    type VARCHAR(100) NOT NULL, -- PAYMENT_DUE, CONTRACT_EXPIRY, AI_REPORT, ISSUE_UPDATE, MAINTENANCE
    title VARCHAR(255) NOT NULL,
    content TEXT,
    reference_type VARCHAR(50), -- bill, contract, issue, deposit
    reference_id INT,
    is_read BOOLEAN DEFAULT FALSE,
    is_push_sent BOOLEAN DEFAULT FALSE,
    read_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================
-- 12. VACANCY LOGS (từ current schema - cho AI Analytics)
-- ============================================================

CREATE TABLE vacancy_logs (
    id SERIAL PRIMARY KEY,
    room_id INT NOT NULL REFERENCES rooms(id) ON DELETE CASCADE,
    property_id INT NOT NULL REFERENCES properties(id) ON DELETE CASCADE,
    landlord_id INT NOT NULL REFERENCES landlords(id) ON DELETE CASCADE,
    vacant_from DATE NOT NULL,
    occupied_at DATE,
    vacancy_reason VARCHAR(255),
    notes TEXT
);

-- ============================================================
-- 13. AUDIT LOG (từ OpenKoda)
-- ============================================================

CREATE TABLE audit_logs (
    id SERIAL PRIMARY KEY,
    landlord_id INT REFERENCES landlords(id),
    user_id INT REFERENCES users(id),
    action VARCHAR(50) NOT NULL, -- CREATE, UPDATE, DELETE, VIEW, EXPORT
    resource_type VARCHAR(100) NOT NULL,
    resource_id INT,
    details JSONB,
    ip_address VARCHAR(50),
    user_agent TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================
-- 14. AI ADVISOR (từ Ai_arch.md)
-- ============================================================

-- Lịch sử báo cáo AI
CREATE TABLE ai_reports (
    id SERIAL PRIMARY KEY,
    landlord_id INT NOT NULL REFERENCES landlords(id) ON DELETE CASCADE,
    period VARCHAR(7) NOT NULL, -- YYYY-MM
    health_score INT,
    health_status VARCHAR(50),
    revenue_leakage DECIMAL(12, 2),
    summary TEXT,
    narrative TEXT,
    opportunities JSONB DEFAULT '[]',
    risks JSONB DEFAULT '[]',
    recommended_actions JSONB DEFAULT '[]',
    generated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Lịch sử Chat AI (Text-to-SQL)
CREATE TABLE ai_chat_history (
    id SERIAL PRIMARY KEY,
    landlord_id INT NOT NULL REFERENCES landlords(id) ON DELETE CASCADE,
    user_id INT REFERENCES users(id),
    question TEXT NOT NULL,
    sql_query TEXT,
    sql_result JSONB,
    ai_response TEXT,
    visualization JSONB,
    is_successful BOOLEAN DEFAULT TRUE,
    execution_time_ms INT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================
-- INDEXES
-- ============================================================

-- Accounts & Auth
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_user_roles_user ON user_roles(user_id);
CREATE INDEX idx_permissions_role ON permissions(role_id);

-- Properties
CREATE INDEX idx_properties_landlord ON properties(landlord_id);
CREATE INDEX idx_floors_property ON floors(property_id);

-- Rooms
CREATE INDEX idx_rooms_property ON rooms(property_id);
CREATE INDEX idx_rooms_landlord ON rooms(landlord_id);
CREATE INDEX idx_rooms_status ON rooms(status);
CREATE INDEX idx_rooms_floor ON rooms(floor_id);

-- Tenants
CREATE INDEX idx_tenants_phone ON tenants(phone);
CREATE INDEX idx_tenants_identification ON tenants(identification_number);
CREATE INDEX idx_tenant_vehicles_tenant ON tenant_vehicles(tenant_id);

-- Contracts
CREATE INDEX idx_contracts_room ON contracts(room_id);
CREATE INDEX idx_contracts_tenant ON contracts(tenant_id);
CREATE INDEX idx_contracts_landlord ON contracts(landlord_id);
CREATE INDEX idx_contracts_property ON contracts(property_id);
CREATE INDEX idx_contracts_status ON contracts(status);
CREATE INDEX idx_contracts_end_date ON contracts(end_date);
CREATE INDEX idx_contracts_number ON contracts(contract_number);

-- Bills
CREATE INDEX idx_bills_contract ON bills(contract_id);
CREATE INDEX idx_bills_room ON bills(room_id);
CREATE INDEX idx_bills_tenant ON bills(tenant_id);
CREATE INDEX idx_bills_landlord ON bills(landlord_id);
CREATE INDEX idx_bills_status ON bills(status);
CREATE INDEX idx_bills_due_date ON bills(due_date);
CREATE INDEX idx_bills_period ON bills(period_start, period_end);

-- Payments
CREATE INDEX idx_payments_bill ON payments(bill_id);
CREATE INDEX idx_payments_date ON payments(payment_date);
CREATE INDEX idx_payments_method ON payments(payment_method);

-- Meter Readings
CREATE INDEX idx_meter_readings_period ON meter_readings(period_id);
CREATE INDEX idx_meter_readings_room ON meter_readings(room_id);
CREATE INDEX idx_meter_reading_periods_property ON meter_reading_periods(property_id);

-- Issues
CREATE INDEX idx_issues_property ON issues(property_id);
CREATE INDEX idx_issues_room ON issues(room_id);
CREATE INDEX idx_issues_status ON issues(status);
CREATE INDEX idx_issues_priority ON issues(priority);

-- Deposits
CREATE INDEX idx_deposits_room ON deposits(room_id);
CREATE INDEX idx_deposits_landlord ON deposits(landlord_id);
CREATE INDEX idx_deposits_status ON deposits(status);

-- Visits
CREATE INDEX idx_visit_requests_property ON visit_requests(property_id);
CREATE INDEX idx_visit_requests_status ON visit_requests(status);

-- Notifications
CREATE INDEX idx_notifications_user ON notifications(user_id);
CREATE INDEX idx_notifications_read ON notifications(is_read);
CREATE INDEX idx_notifications_created ON notifications(created_at);

-- Vacancy Logs
CREATE INDEX idx_vacancy_logs_room ON vacancy_logs(room_id);
CREATE INDEX idx_vacancy_logs_landlord ON vacancy_logs(landlord_id);

-- Audit Logs
CREATE INDEX idx_audit_logs_landlord ON audit_logs(landlord_id);
CREATE INDEX idx_audit_logs_user ON audit_logs(user_id);
CREATE INDEX idx_audit_logs_action ON audit_logs(action);
CREATE INDEX idx_audit_logs_created ON audit_logs(created_at);

-- AI
CREATE INDEX idx_ai_reports_landlord ON ai_reports(landlord_id);
CREATE INDEX idx_ai_reports_period ON ai_reports(period);
CREATE INDEX idx_ai_chat_history_landlord ON ai_chat_history(landlord_id);
