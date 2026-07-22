# 🏠 AI Property Advisor — Harness Agent Architecture

Hệ thống **AI Financial Copilot & Operational Agent** cao cấp dành cho quản lý nhà trọ (HDBHMS).  
Được xây dựng trên **Harness Agent Architecture**, tích hợp **Text-to-SQL SOTA**, **Code Interpreter Engine**, **Smart Period Financial Reporting**, **Dynamic Skill Loading**, **Full Database Audit Logging**, và **Enterprise SaaS UI/UX**.

> **Database:** MySQL 8.0+ (Schema 61 tables + `ai_audit_logs`)  
> **Backend:** FastAPI + aiomysql + Pydantic v2  
> **Frontend:** Vanilla JS + Enterprise SaaS UI + `Plus Jakarta Sans` & `Outfit` Fonts + `marked.js` Markdown  
> **Primary AI Model:** `gemini-3.6-flash-lite`

---

## ✨ Các Tính Năng & Kiến Trúc AI Nổi Bật

| Tính năng / Hợp phần | Mô tả chi tiết & Điểm mạnh kiến trúc |
|----------------------|--------------------------------------|
| **🤖 Native Agent Loop** | Vòng lặp Agentic Loop tự động suy luận & gọi Tool (`while step < MAX_AGENT_STEPS`). Loại bỏ hoàn toàn pseudo-agents và Regex cứng. |
| **🔒 Smart Period Financial Reporting** | Phân loại báo cáo tài chính thông minh: Các tháng đã qua (`2026-06`) được **chốt sổ & lưu vĩnh viễn**; Tháng hiện tại (`2026-07`) hiển thị mốc **tính đến ngày hiện tại** kèm nút cập nhật số liệu live. |
| **⏰ Auto Real-Time Time Injection** | Hàm `get_current_time_context()` tự động lấy và tiêm mốc thời gian thực tế của hệ thống (`Thứ Năm, 23/07/2026 00:45:00`) vào mọi luồng xử lý AI. |
| **💡 Dynamic Non-Repeating Follow-Up Chips** | Sinh gợi ý câu hỏi đào sâu tự động sau mỗi lượt thoại. Duy trì bộ lọc `askedQuestionsInSession` để **tự động loại bỏ các câu hỏi user đã từng hỏi**, đảm bảo gợi ý luôn mới 100%. |
| **🎨 Enterprise SaaS UI/UX** | Thiết kế chuẩn SaaS với **Sidebar dọc 250px (chỉ 3 mục tinh gọn)**, Top Bar chọn kỳ báo cáo & landlord, và Khung Chat Full-Width siêu sạch sẽ, không nút bấm rác. |
| **📲 Automated Zalo Dispatcher** | API `POST /copilot/send-zalo` hỗ trợ bắn báo cáo & tin nhắn tự động sang Zalo OA Enterprise Webhook trực tiếp tới SĐT Chủ nhà. |
| **🐍 Code Interpreter Engine** | Tự động sinh và thực thi mã Python (`execute_dynamic_python_script`) trong môi trường Sandbox cách ly để tính toán công thức tài chính, lãi suất lũy kế, và dự báo tăng trưởng **không bị ảo giác (Zero Math Hallucination)**. |
| **💡 Dynamic Skill Loading** | Tự động quét và nạp gói tri thức chuyên môn (`skills/financial_analysis`, `skills/marketing_copywriting`, `skills/sql_best_practices`) vào System Instruction theo chủ đề câu hỏi. |
| **🛡️ Lifecycle Security Hooks** | **Pre-tool Hook** (chặn lệnh `DROP/DELETE`), **Post-tool Hook** (mã hóa dữ liệu nhạy cảm SĐT, CCCD, Email). |
| **🗄️ Database Audit Logging** | Tự động lưu 100% dữ liệu 360 độ (Question, System Prompt, Skills, Tools, SQL, Answer, Latency) vào CSDL bảng `ai_audit_logs` & file `static/logs/full_server_audit.jsonl`. |

---

## 🗂️ Cấu Trúc Thư Mục Dự Án

```
ai-property-advisor-harness/
├── config/
│   └── settings.py                     # Cấu hình Pydantic & gemini-3.6-flash-lite
├── database/
│   ├── connection.py                   # aiomysql Connection Pool & Query Timeout
│   ├── schema_mysql.sql                # DDL MySQL Schema (61 tables + ai_audit_logs)
│   └── temp/                           # Thư mục chứa các file SQLite backup & test tạm
├── skills/                             # Dynamic Skill Packages
│   ├── financial_analysis/             # Tri thức đánh giá sức khỏe KPI & công nợ
│   ├── marketing_copywriting/          # Bài đăng quảng cáo tìm khách chuẩn AIDA
│   └── sql_best_practices/             # Quy tắc JOIN & tên cột chuẩn MySQL DDL
├── src/
│   ├── harness/
│   │   ├── agent_loop.py               # Native Harness Agentic Loop + Real-Time Context
│   │   ├── tools.py                    # Core Tools & Code Interpreter Engine
│   │   ├── skill_loader.py             # Dynamic Skill Loader
│   │   ├── hooks.py                    # Security Hooks & Data Masking
│   │   ├── payload_logger.py           # Database Audit Logger (ai_audit_logs + jsonl)
│   │   └── prompts.py                  # Executive Financial Reporting Rules & Constraints
│   ├── api/v1/copilot.py               # REST API Copilot, Report, Ask & Zalo Dispatcher
│   ├── services/
│   │   ├── ai_report_service.py        # Smart Period Financial Report Engine (Cache/Live)
│   │   ├── ai_ask_service.py           # Multi-turn Ask Service
│   │   ├── suggestion_service.py       # Dynamic Follow-Up Question Generator
│   │   └── gemini_service.py           # Gemini SDK Client & Model Registry
├── static/
│   ├── index.html                      # Enterprise SaaS UI (Plus Jakarta Sans + Outfit + Marked.js)
│   └── logs/
│       └── full_server_audit.jsonl     # Local Payload Audit Log File
├── scripts/
│   ├── benchmark_10_landlord_scenarios.py # Suite kiểm thử 10 kịch bản chủ nhà E2E
│   ├── benchmark_complex_queries.py       # Benchmark 5 kịch bản SQL siêu phức tạp
│   └── test_full_payload_audit.py         # Kiểm thử hệ thống Audit Log
└── requirements.txt
```

---

## 🚀 Hướng Dẫn Chạy Hệ Thống

### 1. Cài đặt môi trường Python

```bash
pip install -r requirements.txt
```

### 2. Cấu hình file `.env`

```ini
GEMINI_API_KEY=your_gemini_api_key_here
GEMINI_MODEL=gemini-3.6-flash-lite
GEMINI_FALLBACK_MODEL=gemini-3.5-flash-lite
DATABASE_URL=mysql://root:password@localhost:3306/hdbhms
```

### 3. Khởi chạy Web Server FastAPI

```bash
uvicorn main:app --host 0.0.0.0 --port 8000
```

TRUY CẬP GIAO DIỆN WEB APP: **`http://localhost:8000/ui`**

---

## 📊 Chạy Suite Kiểm Thử Benchmark Tự Động

```bash
# 1. Kiểm thử 10 kịch bản End-to-End thực tế của Chủ nhà
python scripts/benchmark_10_landlord_scenarios.py

# 2. Kiểm thử 5 kịch bản SQL siêu phức tạp
python scripts/benchmark_complex_queries.py

# 3. Kiểm thử Audit Logger & Code Interpreter
python scripts/test_full_payload_audit.py
```
