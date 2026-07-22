# 📐 ARCHITECTURE SPECIFICATION — AI PROPERTY ADVISOR (HARNESS ARCHITECTURE)

Document Version: 3.0 (Harness Agentic Loop & Glassmorphic UI Specification)  
Design Pattern: **Harness Architecture (Model + Harness Environment + Dynamic Code Interpreter + Glassmorphic UI)**

---

## 1. TỔNG QUAN KIẾN TRÚC TOÀN HỆ THỐNG

```
                      +----------------------------------+
                      |    User Input & Glassmorphic UI  |
                      +----------------------------------+
                                       |
                                       v
                      +----------------------------------+
                      |       Dynamic Skill Loader       |
                      |  (Loads matching SKILL.md rules) |
                      +----------------------------------+
                                       |
                                       v
                      +----------------------------------+
                      |    Native Harness Agent Loop     |
                      |  (Model: gemini-3.6-flash-lite)  |
                      +----------------------------------+
                                       |
         +-----------------------------+-----------------------------+
         |                             |                             |
         v                             v                             v
+------------------+         +--------------------+        +---------------------------+
| get_kpi_overview |         | execute_sql_query  |        | execute_dynamic_python    |
+------------------+         +--------------------+        |     (Code Interpreter)    |
         |                             |                   +---------------------------+
         |                             |                                 |
         +-----------------------------+---------------------------------+
                                       |
                                       v
                      +----------------------------------+
                      |     Security & PII Hooks         |
                      |   (Masks phone, CCCD, SQL check) |
                      +----------------------------------+
                                       |
                                       v
                      +----------------------------------+
                      |  Dynamic Turn Follow-Up Generator|
                      |  (Attaches 4 Tailored Question   |
                      |   Chips to every AI Answer turn) |
                      +----------------------------------+
                                       |
                                       v
                      +----------------------------------+
                      |     Database Audit Persistence   |
                      |    (Saved to ai_audit_logs DB)   |
                      +----------------------------------+
                                       |
                                       v
                      +----------------------------------+
                      | Glassmorphic UI + marked.js      |
                      | (Formatted Markdown + Copy Btn)  |
                      +----------------------------------+
```

---

## 2. LỚP TRUY VẤN VÀ BẢO MẬT (SECURITY & DDL CONSTRAINTS)

### Pre-Tool Hook (`src/harness/hooks.py`)
- Kiểm tra truy vấn SQL: Chỉ chấp nhận các câu lệnh `SELECT` và `WITH` (CTE).
- Chặn triệt để các lệnh ghi/xóa: `DROP`, `DELETE`, `UPDATE`, `INSERT`, `ALTER`, `TRUNCATE`.
- Cưỡng chế quy tắc tên cột MySQL DDL:
  - Cột SĐT trong `users`: `u.phone` (KHÔNG DÙNG `u.phone_number`)
  - Cột địa chỉ trong `properties`: `p.address_street` (KHÔNG DÙNG `p.address`)
  - Liên kết người thuê trong `lease_contracts`: `primary_tenant_profile_id` (KHÔNG DÙNG `tenant_id`)
  - Tất cả các bảng liên kết bằng `property_id = $1` (KHÔNG DÙNG `landlord_id`)

### Post-Tool Hook (`src/harness/hooks.py`)
- Mã hóa regex tự động thông tin nhạy cảm trước khi đưa dữ liệu vào LLM Context:
  - Số điện thoại: `0987***321`
  - Số CCCD/CMND: `0360****1234`
  - Email: `usr***@gmail.com`

---

## 3. CODE INTERPRETER ENGINE (`execute_dynamic_python_script`)

Hệ thống cho phép Agent tự biên soạn và thực thi mã Python trực tiếp trong môi trường Sandbox an toàn để thực hiện các tính toán đại số lũy kế, bài toán tối ưu hóa, và dự báo tài chính.

### Môi trường Sandbox:
- Sử dụng trình thông dịch Python cách ly.
- Chặn các module hệ thống nguy hiểm (`os.system`, `subprocess`, `shutil`).
- Kết quả đầu ra được chụp lại qua `sys.stdout` và gửi trực tiếp về Agent Loop.

---

## 4. THIẾT KẾ CSDL AUDIT (`ai_audit_logs`)

```sql
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
```
