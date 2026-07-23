-- ============================================================
-- HDBHMS - MySQL Schema (Production)
-- Based on SE Group's V19 seed data structure
-- ============================================================

DROP DATABASE IF EXISTS hdbhms;
CREATE DATABASE hdbhms DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE hdbhms;

SET NAMES utf8mb4;
SET FOREIGN_KEY_CHECKS = 0;

-- ============================================================
-- 1. ACCOUNTS & AUTH
-- ============================================================

CREATE TABLE users (
    user_id BIGINT AUTO_INCREMENT PRIMARY KEY,
    phone VARCHAR(20),
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    full_name VARCHAR(255),
    role ENUM('OWNER','MANAGER','ACCOUNTANT','TENANT','LEAD','STAFF') NOT NULL DEFAULT 'TENANT',
    status ENUM('ACTIVE','INACTIVE','PENDING_CONTRACT','SUSPENDED') NOT NULL DEFAULT 'ACTIVE',
    last_login_at DATETIME,
    email_verified TINYINT(1) DEFAULT 0,
    must_change_password TINYINT(1) DEFAULT 0,
    avatar_url VARCHAR(500),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    deleted_at DATETIME NULL,
    INDEX idx_users_email (email),
    INDEX idx_users_role (role),
    INDEX idx_users_status (status),
    INDEX idx_users_deleted (deleted_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE person_profiles (
    person_profile_id BIGINT AUTO_INCREMENT PRIMARY KEY,
    user_id BIGINT NOT NULL,
    full_name VARCHAR(255) NOT NULL,
    dob DATE,
    gender ENUM('MALE','FEMALE','UNKNOWN') DEFAULT 'UNKNOWN',
    phone VARCHAR(20),
    email VARCHAR(255),
    permanent_address TEXT,
    portrait_file_id BIGINT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    deleted_at DATETIME NULL,
    INDEX idx_profiles_user (user_id),
    INDEX idx_profiles_deleted (deleted_at),
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE identity_documents (
    identity_document_id BIGINT AUTO_INCREMENT PRIMARY KEY,
    profile_id BIGINT NOT NULL,
    doc_type VARCHAR(50) NOT NULL DEFAULT 'CCCD',
    doc_number VARCHAR(50) NOT NULL,
    issued_date DATE,
    issued_place VARCHAR(255),
    expiry_date DATE,
    raw_ocr_data JSON,
    front_file_id BIGINT,
    back_file_id BIGINT,
    status ENUM('ACTIVE','EXPIRED','PENDING') DEFAULT 'ACTIVE',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_identity_profile (profile_id),
    FOREIGN KEY (profile_id) REFERENCES person_profiles(person_profile_id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE login_history (
    login_history_id BIGINT AUTO_INCREMENT PRIMARY KEY,
    user_id BIGINT NOT NULL,
    status VARCHAR(50) NOT NULL,
    ip_address VARCHAR(50),
    user_agent TEXT,
    method VARCHAR(50) DEFAULT 'PASSWORD',
    session_id VARCHAR(255),
    device_id VARCHAR(255),
    logged_in_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_login_user (user_id),
    INDEX idx_login_time (logged_in_at),
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================================
-- 2. FILE MANAGEMENT
-- ============================================================

CREATE TABLE file_metadata (
    file_metadata_id BIGINT AUTO_INCREMENT PRIMARY KEY,
    owner_user_id BIGINT,
    storage_key VARCHAR(500) NOT NULL,
    original_name VARCHAR(255) NOT NULL,
    mime_type VARCHAR(100),
    size_bytes BIGINT DEFAULT 0,
    sha256_checksum VARCHAR(64),
    category VARCHAR(100),
    is_sensitive TINYINT(1) DEFAULT 0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    deleted_at DATETIME NULL,
    INDEX idx_file_owner (owner_user_id),
    INDEX idx_file_category (category),
    INDEX idx_file_deleted (deleted_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================================
-- 3. PROPERTY MANAGEMENT
-- ============================================================

CREATE TABLE properties (
    property_id BIGINT AUTO_INCREMENT PRIMARY KEY,
    property_code VARCHAR(50) UNIQUE NOT NULL,
    name VARCHAR(255) NOT NULL,
    name_en VARCHAR(255),
    description TEXT,
    address_street VARCHAR(255),
    address_ward VARCHAR(100),
    address_district VARCHAR(100),
    address_city VARCHAR(100),
    address_province VARCHAR(100),
    latitude DECIMAL(10, 7),
    longitude DECIMAL(10, 7),
    property_type VARCHAR(50) DEFAULT 'APARTMENT',
    total_floors INT DEFAULT 1,
    total_rooms INT DEFAULT 0,
    status VARCHAR(50) DEFAULT 'ACTIVE',
    amenities JSON DEFAULT (JSON_ARRAY()),
    images JSON DEFAULT (JSON_ARRAY()),
    rules TEXT,
    electricity_unit_price DECIMAL(12, 2) DEFAULT 0,
    water_unit_price DECIMAL(12, 2) DEFAULT 0,
    service_fee DECIMAL(12, 2) DEFAULT 0,
    billing_cycle_day INT DEFAULT 1,
    due_days INT DEFAULT 15,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    deleted_at DATETIME NULL,
    INDEX idx_properties_code (property_code),
    INDEX idx_properties_status (status),
    INDEX idx_properties_deleted (deleted_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================================
-- 4. ROOM MANAGEMENT
-- ============================================================

CREATE TABLE rooms (
    room_id BIGINT AUTO_INCREMENT PRIMARY KEY,
    property_id BIGINT NOT NULL,
    floor_id BIGINT,
    room_code VARCHAR(50) NOT NULL,
    room_type VARCHAR(50) DEFAULT 'STANDARD',
    base_price DECIMAL(12, 2) NOT NULL,
    deposit_amount DECIMAL(12, 2) DEFAULT 0,
    area_sqm DECIMAL(8, 2),
    capacity INT DEFAULT 1,
    current_occupants INT DEFAULT 0,
    current_status VARCHAR(50) DEFAULT 'VACANT',
    internal_note TEXT,
    has_air_conditioner TINYINT(1) DEFAULT 0,
    has_water_heater TINYINT(1) DEFAULT 0,
    has_furniture TINYINT(1) DEFAULT 0,
    has_private_bathroom TINYINT(1) DEFAULT 0,
    has_balcony TINYINT(1) DEFAULT 0,
    has_kitchen TINYINT(1) DEFAULT 0,
    amenities JSON DEFAULT (JSON_ARRAY()),
    images JSON DEFAULT (JSON_ARRAY()),
    notes TEXT,
    is_active TINYINT(1) DEFAULT 1,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    deleted_at DATETIME NULL,
    UNIQUE KEY uk_rooms_prop_code (property_id, room_code),
    INDEX idx_rooms_property (property_id),
    INDEX idx_rooms_status (current_status),
    INDEX idx_rooms_code (room_code),
    INDEX idx_rooms_deleted (deleted_at),
    FOREIGN KEY (property_id) REFERENCES properties(property_id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE room_status_history (
    room_status_history_id BIGINT AUTO_INCREMENT PRIMARY KEY,
    room_id BIGINT NOT NULL,
    from_status VARCHAR(50),
    to_status VARCHAR(50) NOT NULL,
    reason TEXT,
    changed_by BIGINT,
    changed_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_rsh_room (room_id),
    INDEX idx_rsh_time (changed_at),
    FOREIGN KEY (room_id) REFERENCES rooms(room_id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE room_assets (
    room_asset_id BIGINT AUTO_INCREMENT PRIMARY KEY,
    room_id BIGINT NOT NULL,
    asset_name VARCHAR(255) NOT NULL,
    asset_category VARCHAR(100) DEFAULT 'APPLIANCE',
    quantity INT DEFAULT 1,
    current_condition VARCHAR(50) DEFAULT 'GOOD',
    description TEXT,
    image_file_id BIGINT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    deleted_at DATETIME NULL,
    UNIQUE KEY uk_assets_room_name (room_id, asset_name),
    INDEX idx_assets_room (room_id),
    FOREIGN KEY (room_id) REFERENCES rooms(room_id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================================
-- 5. TENANT & STAFF MANAGEMENT
-- ============================================================

CREATE TABLE tenants (
    tenant_id BIGINT AUTO_INCREMENT PRIMARY KEY,
    user_id BIGINT NOT NULL,
    property_id BIGINT NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    deleted_at DATETIME NULL,
    UNIQUE KEY uk_tenants_user_prop (user_id, property_id),
    INDEX idx_tenants_user (user_id),
    INDEX idx_tenants_property (property_id),
    INDEX idx_tenants_deleted (deleted_at),
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
    FOREIGN KEY (property_id) REFERENCES properties(property_id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE emergency_contacts (
    emergency_contact_id BIGINT AUTO_INCREMENT PRIMARY KEY,
    tenant_profile_id BIGINT NOT NULL,
    full_name VARCHAR(255),
    relationship VARCHAR(100),
    phone VARCHAR(20),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_emergency_profile (tenant_profile_id),
    FOREIGN KEY (tenant_profile_id) REFERENCES person_profiles(person_profile_id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE vehicles (
    vehicle_id BIGINT AUTO_INCREMENT PRIMARY KEY,
    profile_id BIGINT NOT NULL,
    vehicle_type VARCHAR(50),
    license_plate VARCHAR(50) NOT NULL,
    brand VARCHAR(100),
    color VARCHAR(50),
    image_file_id BIGINT,
    status VARCHAR(50) DEFAULT 'ACTIVE',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    deleted_at DATETIME NULL,
    INDEX idx_vehicles_profile (profile_id),
    FOREIGN KEY (profile_id) REFERENCES person_profiles(person_profile_id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE role_promotions (
    role_promotion_id BIGINT AUTO_INCREMENT PRIMARY KEY,
    user_id BIGINT NOT NULL,
    role VARCHAR(50) NOT NULL,
    status VARCHAR(50) DEFAULT 'PENDING',
    property_id BIGINT,
    approved_at DATETIME,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    deleted_at DATETIME NULL,
    INDEX idx_rp_user (user_id),
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE property_staff_assignments (
    property_staff_assignment_id BIGINT AUTO_INCREMENT PRIMARY KEY,
    property_id BIGINT NOT NULL,
    staff_user_id BIGINT NOT NULL,
    assigned_role VARCHAR(50) NOT NULL,
    assignment_status VARCHAR(50) DEFAULT 'ACTIVE',
    is_primary TINYINT(1) DEFAULT 0,
    notes TEXT,
    assigned_by_user_id BIGINT,
    started_at DATETIME,
    ended_at DATETIME,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_psa_property (property_id),
    INDEX idx_psa_staff (staff_user_id),
    INDEX idx_psa_status (assignment_status),
    FOREIGN KEY (property_id) REFERENCES properties(property_id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================================
-- 6. FINANCIAL - COLLECTION ACCOUNTS & TARIFFS
-- ============================================================

CREATE TABLE collection_accounts (
    collection_account_id BIGINT AUTO_INCREMENT PRIMARY KEY,
    property_id BIGINT NOT NULL,
    account_type VARCHAR(50) NOT NULL,
    bank_name VARCHAR(255),
    account_number VARCHAR(100),
    account_holder VARCHAR(255),
    provider VARCHAR(50) DEFAULT 'BANK',
    status VARCHAR(50) DEFAULT 'ACTIVE',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_ca_property (property_id),
    FOREIGN KEY (property_id) REFERENCES properties(property_id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE utility_tariffs (
    utility_tariff_id BIGINT AUTO_INCREMENT PRIMARY KEY,
    property_id BIGINT NOT NULL,
    utility_type ENUM('ELECTRICITY','WATER','SERVICE_FEE','OTHER') NOT NULL,
    unit_price DECIMAL(12, 2) NOT NULL,
    free_allowance DECIMAL(10, 2) DEFAULT 0,
    service_fee_waive_electricity_threshold DECIMAL(12, 2),
    effective_from DATE NOT NULL,
    effective_to DATE,
    created_by BIGINT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_ut_property (property_id),
    INDEX idx_ut_effective (effective_from, effective_to),
    FOREIGN KEY (property_id) REFERENCES properties(property_id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================================
-- 7. METER READING SYSTEM
-- ============================================================

CREATE TABLE meters (
    meter_id BIGINT AUTO_INCREMENT PRIMARY KEY,
    room_id BIGINT NOT NULL,
    meter_type ENUM('ELECTRICITY','WATER') NOT NULL,
    meter_code VARCHAR(100) NOT NULL,
    status VARCHAR(50) DEFAULT 'ACTIVE',
    installed_at DATETIME,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_meters_room (room_id),
    INDEX idx_meters_code (meter_code),
    FOREIGN KEY (room_id) REFERENCES rooms(room_id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE meter_reading_batches (
    meter_reading_batch_id BIGINT AUTO_INCREMENT PRIMARY KEY,
    property_id BIGINT NOT NULL,
    reading_period VARCHAR(7) NOT NULL,
    status VARCHAR(50) DEFAULT 'OPEN',
    imported_file_id BIGINT,
    created_by BIGINT,
    confirmed_by BIGINT,
    confirmed_at DATETIME,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    total_rooms INT DEFAULT 0,
    completed_rooms INT DEFAULT 0,
    anomaly_count INT DEFAULT 0,
    INDEX idx_mrb_property (property_id),
    INDEX idx_mrb_period (reading_period),
    FOREIGN KEY (property_id) REFERENCES properties(property_id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE meter_readings (
    meter_reading_id BIGINT AUTO_INCREMENT PRIMARY KEY,
    batch_id BIGINT NOT NULL,
    meter_id BIGINT NOT NULL,
    room_id BIGINT NOT NULL,
    reading_period VARCHAR(7) NOT NULL,
    revision_no INT DEFAULT 1,
    previous_value DECIMAL(12, 2) NOT NULL,
    current_value DECIMAL(12, 2) NOT NULL,
    consumption DECIMAL(12, 2) GENERATED ALWAYS AS (current_value - previous_value) STORED,
    reading_date DATE,
    photo_file_id BIGINT,
    status VARCHAR(50) DEFAULT 'PENDING',
    void_reason TEXT,
    purpose VARCHAR(50) DEFAULT 'MONTHLY',
    source VARCHAR(50) DEFAULT 'MANUAL',
    review_status VARCHAR(50) DEFAULT 'NONE',
    review_count INT DEFAULT 0,
    created_by BIGINT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_mr_batch (batch_id),
    INDEX idx_mr_meter (meter_id),
    INDEX idx_mr_room (room_id),
    INDEX idx_mr_period (reading_period),
    FOREIGN KEY (batch_id) REFERENCES meter_reading_batches(meter_reading_batch_id) ON DELETE CASCADE,
    FOREIGN KEY (meter_id) REFERENCES meters(meter_id) ON DELETE CASCADE,
    FOREIGN KEY (room_id) REFERENCES rooms(room_id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE meter_reading_anomalies (
    meter_reading_anomaly_id BIGINT AUTO_INCREMENT PRIMARY KEY,
    meter_reading_id BIGINT NOT NULL,
    anomaly_type VARCHAR(100) NOT NULL,
    message TEXT,
    severity VARCHAR(50) DEFAULT 'MEDIUM',
    resolved_at DATETIME,
    resolved_by BIGINT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    batch_id BIGINT,
    INDEX idx_mra_reading (meter_reading_id),
    FOREIGN KEY (meter_reading_id) REFERENCES meter_readings(meter_reading_id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================================
-- 8. DEPOSIT MANAGEMENT
-- ============================================================

CREATE TABLE deposit_forms (
    deposit_form_id BIGINT AUTO_INCREMENT PRIMARY KEY,
    room_id BIGINT NOT NULL,
    id_number VARCHAR(50),
    id_issue_date DATE,
    id_issue_place VARCHAR(255),
    id_front_file_id BIGINT,
    id_back_file_id BIGINT,
    portrait_file_id BIGINT,
    full_name VARCHAR(255),
    dob DATE,
    email VARCHAR(255),
    phone VARCHAR(20),
    permanent_address TEXT,
    expected_move_in_date DATE,
    expected_lease_sign_date DATE,
    payment_due_at DATETIME,
    deposit_expires_at DATETIME,
    status VARCHAR(50) DEFAULT 'PENDING',
    confirmed_at DATETIME,
    reject_reason TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    deposit_months INT DEFAULT 1,
    payment_cycle_months INT DEFAULT 1,
    occupant_count INT DEFAULT 1,
    INDEX idx_df_room (room_id),
    INDEX idx_df_status (status),
    FOREIGN KEY (room_id) REFERENCES rooms(room_id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE room_holds (
    room_hold_id BIGINT AUTO_INCREMENT PRIMARY KEY,
    room_id BIGINT NOT NULL,
    tenant_id BIGINT,
    status VARCHAR(50) NOT NULL,
    expires_at DATETIME,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    released_at DATETIME,
    INDEX idx_rh_room (room_id),
    INDEX idx_rh_status (status),
    FOREIGN KEY (room_id) REFERENCES rooms(room_id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE deposit_agreements (
    deposit_agreement_id BIGINT AUTO_INCREMENT PRIMARY KEY,
    deposit_code VARCHAR(100) UNIQUE NOT NULL,
    room_id BIGINT NOT NULL,
    room_hold_id BIGINT,
    deposit_form_id BIGINT,
    tenant_id BIGINT,
    lead_id BIGINT,
    depositor_person_profile_id BIGINT,
    amount DECIMAL(12, 2) NOT NULL,
    expected_move_in_date DATE,
    expected_lease_sign_date DATE,
    payment_due_at DATETIME,
    deposit_expires_at DATETIME,
    extension_count INT DEFAULT 0,
    max_extensions INT DEFAULT 1,
    status VARCHAR(50) DEFAULT 'PENDING_PAYMENT',
    confirmed_at DATETIME,
    contract_file_id BIGINT,
    signed_file_id BIGINT,
    signed_at DATETIME,
    signed_uploaded_by BIGINT,
    note TEXT,
    forfeiture_reason TEXT,
    refunded_amount DECIMAL(12, 2),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_da_room (room_id),
    INDEX idx_da_code (deposit_code),
    INDEX idx_da_status (status),
    FOREIGN KEY (room_id) REFERENCES rooms(room_id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================================
-- 9. LEASE CONTRACT MANAGEMENT
-- ============================================================

CREATE TABLE lease_contracts (
    lease_contract_id BIGINT AUTO_INCREMENT PRIMARY KEY,
    contract_code VARCHAR(100) UNIQUE NOT NULL,
    room_id BIGINT NOT NULL,
    deposit_agreement_id BIGINT,
    primary_tenant_profile_id BIGINT,
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    rent_start_date DATE,
    monthly_rent DECIMAL(12, 2) NOT NULL,
    payment_cycle_months INT DEFAULT 1,
    deposit_amount DECIMAL(12, 2) DEFAULT 0,
    status VARCHAR(50) DEFAULT 'DRAFT',
    tenant_intention VARCHAR(50),
    expected_vacant_date DATE,
    intention_recorded_at DATETIME,
    previous_contract_id BIGINT,
    contract_file_id BIGINT,
    signed_file_id BIGINT,
    signed_uploaded_by BIGINT,
    signed_at DATETIME,
    created_by BIGINT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    deleted_at DATETIME NULL,
    version INT DEFAULT 0,
    INDEX idx_lc_room (room_id),
    INDEX idx_lc_code (contract_code),
    INDEX idx_lc_status (status),
    INDEX idx_lc_dates (start_date, end_date),
    INDEX idx_lc_deleted (deleted_at),
    FOREIGN KEY (room_id) REFERENCES rooms(room_id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE contract_occupants (
    contract_occupant_id BIGINT AUTO_INCREMENT PRIMARY KEY,
    contract_id BIGINT NOT NULL,
    tenant_id BIGINT,
    tenant_profile_id BIGINT,
    occupant_role VARCHAR(50) DEFAULT 'PRIMARY',
    move_in_date DATE,
    move_out_date DATE,
    status VARCHAR(50) DEFAULT 'ACTIVE',
    disabled_reason TEXT,
    disabled_by BIGINT,
    disabled_at DATETIME,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_co_contract (contract_id),
    INDEX idx_co_status (status),
    FOREIGN KEY (contract_id) REFERENCES lease_contracts(lease_contract_id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE contract_events (
    contract_event_id BIGINT AUTO_INCREMENT PRIMARY KEY,
    contract_id BIGINT NOT NULL,
    event_type VARCHAR(50) NOT NULL,
    event_data JSON,
    created_by BIGINT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_ce_contract (contract_id),
    INDEX idx_ce_type (event_type),
    FOREIGN KEY (contract_id) REFERENCES lease_contracts(lease_contract_id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE contract_termination_notices (
    termination_notice_id BIGINT AUTO_INCREMENT PRIMARY KEY,
    contract_id BIGINT NOT NULL,
    notice_by VARCHAR(50),
    notice_user_id BIGINT,
    notice_date DATE,
    expected_termination_date DATE,
    reason TEXT,
    evidence_file_id BIGINT,
    status VARCHAR(50) DEFAULT 'SUBMITTED',
    decided_by BIGINT,
    decided_at DATETIME,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_ctn_contract (contract_id),
    FOREIGN KEY (contract_id) REFERENCES lease_contracts(lease_contract_id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE contract_handover_records (
    contract_handover_record_id BIGINT AUTO_INCREMENT PRIMARY KEY,
    contract_id BIGINT NOT NULL,
    room_id BIGINT NOT NULL,
    handover_type VARCHAR(50) NOT NULL,
    handover_date DATETIME,
    electricity_reading_id BIGINT,
    water_reading_id BIGINT,
    note TEXT,
    status VARCHAR(50) DEFAULT 'PENDING',
    confirmed_by BIGINT,
    confirmed_at DATETIME,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    signed_document_id BIGINT,
    INDEX idx_chr_contract (contract_id),
    INDEX idx_chr_room (room_id),
    FOREIGN KEY (contract_id) REFERENCES lease_contracts(lease_contract_id) ON DELETE CASCADE,
    FOREIGN KEY (room_id) REFERENCES rooms(room_id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE contract_handover_items (
    contract_handover_item_id BIGINT AUTO_INCREMENT PRIMARY KEY,
    handover_record_id BIGINT NOT NULL,
    room_asset_id BIGINT,
    asset_name VARCHAR(255),
    quantity INT DEFAULT 1,
    condition_status VARCHAR(50),
    note TEXT,
    evidence_file_id BIGINT,
    compensation_amount DECIMAL(12, 2),
    compensation_invoice_id BIGINT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_chi_handover (handover_record_id),
    FOREIGN KEY (handover_record_id) REFERENCES contract_handover_records(contract_handover_record_id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE contract_liquidations (
    contract_liquidation_id BIGINT AUTO_INCREMENT PRIMARY KEY,
    contract_id BIGINT NOT NULL,
    liquidation_date DATE,
    reason TEXT,
    deposit_amount DECIMAL(12, 2),
    deposit_deduction_amount DECIMAL(12, 2),
    deposit_deduction_reason TEXT,
    deposit_refund_amount DECIMAL(12, 2),
    final_invoice_id BIGINT,
    signed_file_id BIGINT,
    status VARCHAR(50) DEFAULT 'PENDING',
    created_by BIGINT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_cl_contract (contract_id),
    FOREIGN KEY (contract_id) REFERENCES lease_contracts(lease_contract_id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE tenant_account_provisionings (
    tenant_account_provisioning_id BIGINT AUTO_INCREMENT PRIMARY KEY,
    tenant_profile_id BIGINT NOT NULL,
    user_id BIGINT NOT NULL,
    first_contract_id BIGINT,
    latest_contract_id BIGINT,
    status VARCHAR(50) DEFAULT 'PENDING',
    recipient_email VARCHAR(255),
    sent_at DATETIME,
    failed_at DATETIME,
    failure_reason TEXT,
    attempt_count INT DEFAULT 0,
    last_attempt_at DATETIME,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_tap_profile (tenant_profile_id),
    INDEX idx_tap_status (status),
    FOREIGN KEY (tenant_profile_id) REFERENCES person_profiles(person_profile_id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================================
-- 10. INVOICING & BILLING
-- ============================================================

CREATE TABLE invoices (
    invoice_id BIGINT AUTO_INCREMENT PRIMARY KEY,
    invoice_code VARCHAR(100) UNIQUE NOT NULL,
    property_id BIGINT NOT NULL,
    room_id BIGINT NOT NULL,
    lease_contract_id BIGINT,
    deposit_agreement_id BIGINT,
    deposit_batch_id BIGINT,
    invoice_type VARCHAR(50) NOT NULL,
    revision_no INT DEFAULT 1,
    billing_period VARCHAR(7) NOT NULL,
    issue_date DATE,
    due_date DATE,
    status VARCHAR(50) DEFAULT 'DRAFT',
    subtotal_amount DECIMAL(12, 2) DEFAULT 0,
    discount_amount DECIMAL(12, 2) DEFAULT 0,
    total_amount DECIMAL(12, 2) NOT NULL,
    paid_amount DECIMAL(12, 2) DEFAULT 0,
    remaining_amount DECIMAL(12, 2) DEFAULT 0,
    collection_account_id BIGINT,
    created_by BIGINT,
    issued_at DATETIME,
    voided_at DATETIME,
    void_reason TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    version INT DEFAULT 0,
    INDEX idx_inv_property (property_id),
    INDEX idx_inv_room (room_id),
    INDEX idx_inv_code (invoice_code),
    INDEX idx_inv_status (status),
    INDEX idx_inv_period (billing_period),
    INDEX idx_inv_due (due_date),
    FOREIGN KEY (property_id) REFERENCES properties(property_id) ON DELETE CASCADE,
    FOREIGN KEY (room_id) REFERENCES rooms(room_id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE invoice_lines (
    invoice_line_id BIGINT AUTO_INCREMENT PRIMARY KEY,
    invoice_id BIGINT NOT NULL,
    line_type VARCHAR(50) NOT NULL,
    description TEXT,
    quantity DECIMAL(12, 2) DEFAULT 1,
    unit_price DECIMAL(12, 2) NOT NULL,
    amount DECIMAL(12, 2) GENERATED ALWAYS AS (quantity * unit_price) STORED,
    meter_reading_id BIGINT,
    source_type VARCHAR(50),
    source_id BIGINT,
    collection_account_id BIGINT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_il_invoice (invoice_id),
    INDEX idx_il_type (line_type),
    FOREIGN KEY (invoice_id) REFERENCES invoices(invoice_id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE rent_overrides (
    rent_override_id BIGINT AUTO_INCREMENT PRIMARY KEY,
    contract_id BIGINT NOT NULL,
    billing_period VARCHAR(7) NOT NULL,
    override_monthly_rent DECIMAL(12, 2) NOT NULL,
    reason TEXT,
    approved_by BIGINT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_ro_contract (contract_id),
    INDEX idx_ro_period (billing_period),
    FOREIGN KEY (contract_id) REFERENCES lease_contracts(lease_contract_id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================================
-- 11. PAYMENT SYSTEM
-- ============================================================

CREATE TABLE payment_intents (
    payment_intent_id BIGINT AUTO_INCREMENT PRIMARY KEY,
    invoice_id BIGINT,
    deposit_agreement_id BIGINT,
    deposit_batch_id BIGINT,
    invoice_payment_group_id BIGINT,
    amount DECIMAL(12, 2) NOT NULL,
    provider VARCHAR(50) DEFAULT 'PAYOS',
    collection_account_id BIGINT,
    payment_content VARCHAR(255),
    provider_order_code VARCHAR(255),
    qr_payload TEXT,
    status VARCHAR(50) DEFAULT 'PENDING',
    expires_at DATETIME,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_pi_invoice (invoice_id),
    INDEX idx_pi_status (status),
    INDEX idx_pi_order (provider_order_code)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE payment_transactions (
    payment_transaction_id BIGINT AUTO_INCREMENT PRIMARY KEY,
    provider VARCHAR(50) NOT NULL,
    provider_transaction_id VARCHAR(255),
    collection_account_id BIGINT,
    amount DECIMAL(12, 2) NOT NULL,
    transaction_time DATETIME,
    payer_name VARCHAR(255),
    payer_account VARCHAR(100),
    content VARCHAR(255),
    status VARCHAR(50) DEFAULT 'PENDING',
    raw_payload JSON,
    confirmed_by BIGINT,
    confirmed_at DATETIME,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_pt_provider (provider, provider_transaction_id),
    INDEX idx_pt_status (status),
    INDEX idx_pt_time (transaction_time)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE payment_allocations (
    payment_allocation_id BIGINT AUTO_INCREMENT PRIMARY KEY,
    payment_transaction_id BIGINT NOT NULL,
    invoice_id BIGINT NOT NULL,
    amount DECIMAL(12, 2) NOT NULL,
    allocated_by BIGINT,
    allocated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_pa_transaction (payment_transaction_id),
    INDEX idx_pa_invoice (invoice_id),
    FOREIGN KEY (payment_transaction_id) REFERENCES payment_transactions(payment_transaction_id) ON DELETE CASCADE,
    FOREIGN KEY (invoice_id) REFERENCES invoices(invoice_id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE invoice_payment_groups (
    invoice_payment_group_id BIGINT AUTO_INCREMENT PRIMARY KEY,
    invoice_id BIGINT NOT NULL,
    collection_account_id BIGINT,
    group_type VARCHAR(50),
    amount DECIMAL(12, 2),
    payment_intent_id BIGINT,
    status VARCHAR(50) DEFAULT 'PENDING',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_ipg_invoice (invoice_id),
    FOREIGN KEY (invoice_id) REFERENCES invoices(invoice_id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================================
-- 12. DEBT MANAGEMENT
-- ============================================================

CREATE TABLE debt_snapshots (
    debt_snapshot_id BIGINT AUTO_INCREMENT PRIMARY KEY,
    room_id BIGINT NOT NULL,
    contract_id BIGINT,
    snapshot_date DATE NOT NULL,
    rent_debt_amount DECIMAL(12, 2) DEFAULT 0,
    utility_debt_amount DECIMAL(12, 2) DEFAULT 0,
    other_debt_amount DECIMAL(12, 2) DEFAULT 0,
    rent_debt_months INT DEFAULT 0,
    utility_debt_months INT DEFAULT 0,
    mixed_debt_amount DECIMAL(12, 2) DEFAULT 0,
    debt_limit_amount DECIMAL(12, 2),
    is_over_limit TINYINT(1) DEFAULT 0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_ds_room (room_id),
    INDEX idx_ds_date (snapshot_date),
    FOREIGN KEY (room_id) REFERENCES rooms(room_id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE debt_notice_trackers (
    debt_notice_tracker_id BIGINT AUTO_INCREMENT PRIMARY KEY,
    lease_contract_id BIGINT NOT NULL,
    unresponsive_count INT DEFAULT 0,
    last_notice_date DATE,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_dnt_contract (lease_contract_id),
    FOREIGN KEY (lease_contract_id) REFERENCES lease_contracts(lease_contract_id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================================
-- 13. MAINTENANCE / ISSUE MANAGEMENT
-- ============================================================

CREATE TABLE maintenance_tickets (
    maintenance_ticket_id BIGINT AUTO_INCREMENT PRIMARY KEY,
    ticket_code VARCHAR(100) UNIQUE NOT NULL,
    property_id BIGINT NOT NULL,
    room_id BIGINT,
    contract_id BIGINT,
    created_by BIGINT NOT NULL,
    ticket_scope VARCHAR(50) DEFAULT 'TENANT_ROOM',
    priority VARCHAR(50) DEFAULT 'MEDIUM',
    category VARCHAR(100) NOT NULL,
    title VARCHAR(255) NOT NULL,
    description TEXT,
    status VARCHAR(50) DEFAULT 'PENDING_ACCEPTANCE',
    rejection_reason TEXT,
    assigned_to BIGINT,
    worker_name VARCHAR(255),
    external_repairman_name VARCHAR(255),
    external_repairman_phone VARCHAR(20),
    external_repair_provider VARCHAR(255),
    external_repair_note TEXT,
    repairman_phone VARCHAR(20),
    repair_items TEXT,
    completed_at DATETIME,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_mt_property (property_id),
    INDEX idx_mt_room (room_id),
    INDEX idx_mt_status (status),
    INDEX idx_mt_priority (priority),
    FOREIGN KEY (property_id) REFERENCES properties(property_id) ON DELETE CASCADE,
    FOREIGN KEY (room_id) REFERENCES rooms(room_id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE maintenance_ticket_events (
    maintenance_ticket_event_id BIGINT AUTO_INCREMENT PRIMARY KEY,
    ticket_id BIGINT NOT NULL,
    from_status VARCHAR(50),
    to_status VARCHAR(50) NOT NULL,
    action VARCHAR(50),
    note TEXT,
    created_by BIGINT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_mte_ticket (ticket_id),
    FOREIGN KEY (ticket_id) REFERENCES maintenance_tickets(maintenance_ticket_id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE maintenance_costs (
    maintenance_cost_id BIGINT AUTO_INCREMENT PRIMARY KEY,
    ticket_id BIGINT NOT NULL,
    cost_type VARCHAR(50) NOT NULL,
    description TEXT,
    amount DECIMAL(12, 2) NOT NULL,
    paid_by VARCHAR(50),
    cost_responsibility VARCHAR(50),
    charge_invoice_id BIGINT,
    receipt_file_id BIGINT,
    created_by BIGINT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_mc_ticket (ticket_id),
    FOREIGN KEY (ticket_id) REFERENCES maintenance_tickets(maintenance_ticket_id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE maintenance_reviews (
    maintenance_review_id BIGINT AUTO_INCREMENT PRIMARY KEY,
    ticket_id BIGINT NOT NULL,
    reviewer_user_id BIGINT,
    rating INT,
    comment TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_mr_ticket (ticket_id),
    FOREIGN KEY (ticket_id) REFERENCES maintenance_tickets(maintenance_ticket_id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE pending_billing_charges (
    pending_billing_charge_id BIGINT AUTO_INCREMENT PRIMARY KEY,
    property_id BIGINT NOT NULL,
    room_id BIGINT,
    contract_id BIGINT,
    source_type VARCHAR(50),
    source_id BIGINT,
    line_type VARCHAR(50),
    description TEXT,
    amount DECIMAL(12, 2) NOT NULL,
    billing_period VARCHAR(7),
    scheduled_issue_at DATETIME,
    due_date DATE,
    status VARCHAR(50) DEFAULT 'SCHEDULED',
    invoice_id BIGINT,
    failure_reason TEXT,
    created_by BIGINT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_pbc_property (property_id),
    INDEX idx_pbc_status (status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================================
-- 14. OPERATING EXPENSES
-- ============================================================

CREATE TABLE operating_expenses (
    operating_expense_id BIGINT AUTO_INCREMENT PRIMARY KEY,
    property_id BIGINT NOT NULL,
    room_id BIGINT,
    ticket_id BIGINT,
    expense_code VARCHAR(100) UNIQUE NOT NULL,
    expense_type VARCHAR(50) NOT NULL,
    description TEXT,
    amount DECIMAL(12, 2) NOT NULL,
    expense_date DATE,
    paid_by_user_id BIGINT,
    receipt_file_id BIGINT,
    status VARCHAR(50) DEFAULT 'PENDING',
    approved_by BIGINT,
    approved_at DATETIME,
    created_by BIGINT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_oe_property (property_id),
    INDEX idx_oe_type (expense_type),
    FOREIGN KEY (property_id) REFERENCES properties(property_id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================================
-- 15. ACCOUNTING (LEDGER)
-- ============================================================

CREATE TABLE ledger_entries (
    ledger_entry_id BIGINT AUTO_INCREMENT PRIMARY KEY,
    entry_code VARCHAR(100) UNIQUE NOT NULL,
    entry_date DATE NOT NULL,
    source_type VARCHAR(50),
    source_id BIGINT,
    account_code VARCHAR(50) NOT NULL,
    debit_amount DECIMAL(12, 2) DEFAULT 0,
    credit_amount DECIMAL(12, 2) DEFAULT 0,
    description TEXT,
    posted_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    reversed_entry_id BIGINT,
    INDEX idx_le_date (entry_date),
    INDEX idx_le_account (account_code),
    INDEX idx_le_source (source_type, source_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================================
-- 16. RULE VIOLATIONS
-- ============================================================

CREATE TABLE rule_violations (
    rule_violation_id BIGINT AUTO_INCREMENT PRIMARY KEY,
    property_id BIGINT NOT NULL,
    room_id BIGINT,
    contract_id BIGINT,
    tenant_profile_id BIGINT,
    rule_id BIGINT,
    violation_date DATE,
    description TEXT,
    fine_amount DECIMAL(12, 2) DEFAULT 0,
    invoice_id BIGINT,
    evidence_file_id BIGINT,
    status VARCHAR(50) DEFAULT 'REPORTED',
    created_by BIGINT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_rv_property (property_id),
    INDEX idx_rv_room (room_id),
    FOREIGN KEY (property_id) REFERENCES properties(property_id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================================
-- 17. ROOM TRANSFER
-- ============================================================

CREATE TABLE room_transfer_requests (
    room_transfer_request_id BIGINT AUTO_INCREMENT PRIMARY KEY,
    request_code VARCHAR(100) UNIQUE NOT NULL,
    requester_id BIGINT NOT NULL,
    old_contract_id BIGINT NOT NULL,
    old_room_id BIGINT NOT NULL,
    target_room_id BIGINT NOT NULL,
    transferring_tenant_profile_ids JSON,
    nominated_holder_profile_id BIGINT,
    target_transfer_type VARCHAR(50),
    target_contract_id BIGINT,
    requested_transfer_date DATE,
    reason TEXT,
    reserved_slots INT DEFAULT 1,
    reservation_expires_at DATETIME,
    target_holder_approved_by BIGINT,
    target_holder_approved_at DATETIME,
    target_holder_rejected_at DATETIME,
    status VARCHAR(50) DEFAULT 'REQUESTED',
    positive_difference_settlement_type VARCHAR(50),
    debt_snapshot_id BIGINT,
    new_contract_id BIGINT,
    replacement_old_contract_id BIGINT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_rtr_requester (requester_id),
    INDEX idx_rtr_status (status),
    INDEX idx_rtr_old_room (old_room_id),
    INDEX idx_rtr_target_room (target_room_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE transfer_settlements (
    transfer_settlement_id BIGINT AUTO_INCREMENT PRIMARY KEY,
    transfer_request_id BIGINT NOT NULL,
    old_room_remaining_value DECIMAL(12, 2),
    new_room_required_value DECIMAL(12, 2),
    difference_amount DECIMAL(12, 2),
    settlement_type VARCHAR(50),
    positive_difference_settlement_type VARCHAR(50),
    old_room_final_invoice_id BIGINT,
    transfer_difference_invoice_id BIGINT,
    confirmed_by BIGINT,
    confirmed_at DATETIME,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_ts_request (transfer_request_id),
    FOREIGN KEY (transfer_request_id) REFERENCES room_transfer_requests(room_transfer_request_id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================================
-- 18. CHANGE REQUESTS (Workflow)
-- ============================================================

CREATE TABLE change_requests (
    change_request_id BIGINT AUTO_INCREMENT PRIMARY KEY,
    request_code VARCHAR(100) UNIQUE NOT NULL,
    request_type VARCHAR(50) NOT NULL,
    requester_id BIGINT NOT NULL,
    requester_role VARCHAR(50),
    target_type VARCHAR(50),
    target_id BIGINT,
    title VARCHAR(255),
    description TEXT,
    request_payload JSON,
    evidence_file_id BIGINT,
    assigned_role VARCHAR(50),
    assigned_to BIGINT,
    status VARCHAR(50) DEFAULT 'PENDING',
    resolution_note TEXT,
    resolved_by BIGINT,
    resolved_at DATETIME,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_cr_requester (requester_id),
    INDEX idx_cr_status (status),
    INDEX idx_cr_type (request_type)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE change_request_events (
    change_request_event_id BIGINT AUTO_INCREMENT PRIMARY KEY,
    request_id BIGINT NOT NULL,
    from_status VARCHAR(50),
    to_status VARCHAR(50),
    note TEXT,
    acted_by BIGINT,
    acted_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_cre_request (request_id),
    FOREIGN KEY (request_id) REFERENCES change_requests(change_request_id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================================
-- 19. VISIT MANAGEMENT
-- ============================================================

CREATE TABLE visit_requests (
    visit_request_id BIGINT AUTO_INCREMENT PRIMARY KEY,
    property_id BIGINT NOT NULL,
    room_id BIGINT,
    visitor_name VARCHAR(255) NOT NULL,
    visitor_phone VARCHAR(20) NOT NULL,
    visitor_email VARCHAR(255),
    preferred_start DATETIME,
    notes TEXT,
    status VARCHAR(50) DEFAULT 'NOT_VIEWED',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    deleted_at DATETIME NULL,
    deleted_by BIGINT,
    INDEX idx_vr_property (property_id),
    INDEX idx_vr_room (room_id),
    INDEX idx_vr_status (status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================================
-- 20. TASK MANAGEMENT
-- ============================================================

CREATE TABLE manager_tasks (
    manager_task_id BIGINT AUTO_INCREMENT PRIMARY KEY,
    title VARCHAR(255) NOT NULL,
    description TEXT,
    assignee_id BIGINT,
    room_id BIGINT,
    lease_contract_id BIGINT,
    status VARCHAR(50) DEFAULT 'PENDING',
    due_date DATE,
    completed_at DATETIME,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_mt_assignee (assignee_id),
    INDEX idx_mt_status (status),
    INDEX idx_mt_due (due_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE scheduled_tasks (
    scheduled_task_id BIGINT AUTO_INCREMENT PRIMARY KEY,
    task_type VARCHAR(100) NOT NULL,
    target_type VARCHAR(50),
    target_id BIGINT,
    due_at DATETIME,
    status VARCHAR(50) DEFAULT 'PENDING',
    retry_count INT DEFAULT 0,
    payload JSON,
    executed_at DATETIME,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_st_type (task_type),
    INDEX idx_st_status (status),
    INDEX idx_st_due (due_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================================
-- 21. NOTIFICATION SYSTEM
-- ============================================================

CREATE TABLE notification_outbox (
    notification_outbox_id BIGINT AUTO_INCREMENT PRIMARY KEY,
    event_type VARCHAR(100) NOT NULL,
    target_type VARCHAR(50),
    target_id BIGINT,
    recipient_user_id BIGINT NOT NULL,
    channel VARCHAR(50) DEFAULT 'PUSH',
    title VARCHAR(255),
    body TEXT,
    payload JSON,
    status VARCHAR(50) DEFAULT 'PENDING',
    retry_count INT DEFAULT 0,
    max_retries INT DEFAULT 3,
    last_error TEXT,
    scheduled_at DATETIME,
    sent_at DATETIME,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    is_read TINYINT(1) DEFAULT 0,
    read_at DATETIME,
    next_retry_at DATETIME,
    INDEX idx_no_recipient (recipient_user_id),
    INDEX idx_no_status (status),
    INDEX idx_no_event (event_type)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE notification_deliveries (
    notification_delivery_id BIGINT AUTO_INCREMENT PRIMARY KEY,
    outbox_id BIGINT NOT NULL,
    provider_message_id VARCHAR(255),
    delivery_status VARCHAR(50),
    error_message TEXT,
    delivered_at DATETIME,
    read_at DATETIME,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_nd_outbox (outbox_id),
    FOREIGN KEY (outbox_id) REFERENCES notification_outbox(notification_outbox_id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================================
-- 22. AUDIT LOG
-- ============================================================

CREATE TABLE audit_logs (
    audit_log_id BIGINT AUTO_INCREMENT PRIMARY KEY,
    actor_user_id BIGINT,
    action VARCHAR(100) NOT NULL,
    entity_type VARCHAR(100),
    entity_id BIGINT,
    before_json JSON,
    after_json JSON,
    ip_address VARCHAR(50),
    user_agent TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_al_actor (actor_user_id),
    INDEX idx_al_action (action),
    INDEX idx_al_entity (entity_type, entity_id),
    INDEX idx_al_time (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================================
-- 23. AI ADVISOR
-- ============================================================

CREATE TABLE ai_reports (
    ai_report_id BIGINT AUTO_INCREMENT PRIMARY KEY,
    landlord_id BIGINT NOT NULL,
    period VARCHAR(7) NOT NULL,
    health_score INT,
    health_status VARCHAR(50),
    revenue_leakage DECIMAL(12, 2),
    summary TEXT,
    narrative TEXT,
    opportunities JSON DEFAULT (JSON_ARRAY()),
    risks JSON DEFAULT (JSON_ARRAY()),
    recommended_actions JSON DEFAULT (JSON_ARRAY()),
    generated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_air_landlord (landlord_id),
    INDEX idx_air_period (period)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE ai_chat_history (
    ai_chat_history_id BIGINT AUTO_INCREMENT PRIMARY KEY,
    landlord_id BIGINT NOT NULL,
    user_id BIGINT,
    session_id VARCHAR(255),
    question TEXT NOT NULL,
    sql_query TEXT,
    sql_result JSON,
    ai_response TEXT,
    visualization JSON,
    is_successful TINYINT(1) DEFAULT 1,
    execution_time_ms INT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_aich_landlord (landlord_id),
    INDEX idx_aich_session (session_id),
    INDEX idx_aich_time (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================================
-- 24. VACANCY LOGS
-- ============================================================

CREATE TABLE vacancy_logs (
    vacancy_log_id BIGINT AUTO_INCREMENT PRIMARY KEY,
    room_id BIGINT NOT NULL,
    property_id BIGINT NOT NULL,
    landlord_id BIGINT NOT NULL,
    vacant_from DATE NOT NULL,
    occupied_at DATE,
    vacancy_reason VARCHAR(255),
    notes TEXT,
    INDEX idx_vl_room (room_id),
    INDEX idx_vl_property (property_id),
    INDEX idx_vl_landlord (landlord_id),
    FOREIGN KEY (room_id) REFERENCES rooms(room_id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================================
-- 25. AI AUDIT LOGS
-- ============================================================

CREATE TABLE IF NOT EXISTS ai_audit_logs (
    log_id BIGINT AUTO_INCREMENT PRIMARY KEY,
    session_id VARCHAR(100),
    landlord_id BIGINT NOT NULL,
    period VARCHAR(20) NOT NULL,
    question TEXT NOT NULL,
    system_instruction_len INT,
    skills_loaded TEXT,
    method VARCHAR(100),
    tools_called JSON,
    reply TEXT,
    latency_ms DOUBLE,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_audit_landlord (landlord_id, period),
    INDEX idx_audit_created (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

SET FOREIGN_KEY_CHECKS = 1;
