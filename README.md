# AI Property Advisor — Financial Copilot for Rental Property Management

[![Python](https://img.shields.io/badge/Python-3.11-blue?logo=python)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?logo=fastapi)](https://fastapi.tiangolo.com)
[![Gemini](https://img.shields.io/badge/Gemini-3.5--flash--lite-4285F4?logo=google)](https://ai.google.dev)
[![MySQL](https://img.shields.io/badge/MySQL-8.0-4479A1?logo=mysql)](https://mysql.com)

Hệ thống AI financial copilot và operational agent dành cho quản lý nhà trọ. Xây dựng trên **Harness Agent Architecture** — kết hợp agentic reasoning, Text-to-SQL, code interpreter engine, dynamic skill loading, và KPI analytics cấp enterprise.

> **Backend:** FastAPI | **Database:** MySQL 8.0 (61 tables) | **AI:** Google Gemini 3.5 flash-lite  
> **Frontend:** Enterprise SaaS UI (Vanilla JS) | **Container:** Docker Compose

---

## Architecture Overview

```
                    ┌──────────────────────────────┐
                    │     Enterprise SaaS UI        │
                    │   (+ marked.js Markdown)      │
                    └──────────┬───────────────────┘
                               │
                    ┌──────────▼───────────────────┐
                    │      FastAPI REST Layer       │
                    │  KPI / Copilot / Suggestions  │
                    └──────────┬───────────────────┘
                               │
                    ┌──────────▼───────────────────┐
                    │   Harness Agent Loop (AI)     │
                    │  Dynamic Skill Loading +      │
                    │  Real-Time Context Injection  │
                    └──┬───────────────┬───────────┘
                       │               │
              ┌────────▼───┐   ┌───────▼──────────┐
              │  Tools     │   │  Code Interpreter │
              │ (SQL + KPI)│   │  (Python Sandbox) │
              └────────────┘   └──────────────────┘
                       │
              ┌────────▼───────────────────────────┐
              │  Security Hooks (Pre/Post-Tool)     │
              │  SQL Guard + PII Masking            │
              └────────┬───────────────────────────┘
                       │
              ┌────────▼───────────────────────────┐
              │  Audit Logger (DB + JSONL)          │
              └────────────────────────────────────┘
```

---

## Tính Năng

### AI & Agentic

| Component | Mô tả |
|-----------|-------|
| **Native Agent Loop** | Vòng lặp reasoning tự động (`MAX_AGENT_STEPS=10`), tự chọn tool và retry khi lỗi. Không dùng pseudo-agent hay regex fallback. |
| **Text-to-SQL** | Gemini tự sinh và thực thi SQL trên schema MySQL 61 bảng, tuân thủ nghiêm ngặt quy tắc tên cột. |
| **Code Interpreter Engine** | AI tự viết và chạy Python trong sandbox cách ly — tính toán tài chính phức tạp không bị ảo giác (zero hallucination). |
| **Dynamic Skill Loading** | Tự động nạp gói tri thức chuyên môn (`financial_analysis`, `marketing_copywriting`, `sql_best_practices`) theo ngữ cảnh câu hỏi. |
| **Model Fallback Cascade** | `gemini-3.6-flash-lite` → `gemini-3.5-flash-lite` → fallback — đảm bảo luôn có phản hồi. |

### KPI Analytics

- **Doanh thu (Revenue):** Tiền phòng, điện, nước, dịch vụ, phát sinh — kèm % tăng trưởng và lịch sử 12 tháng.
- **Chi phí (Expense):** Điện, nước, sửa chữa, phạt, khác — chi tiết tỷ trọng từng khoản.
- **Công nợ (Debt):** Tỷ lệ thu tiền, số hóa đơn quá hạn, aging report, cảnh báo theo phòng.
- **Lấp đầy (Occupancy):** Tổng phòng, đã thuê, trống — tỷ lệ lấp đầy kèm lịch sử.
- **Lợi nhuận (Profit):** Lợi nhuận ròng, % tăng trưởng, tỷ lệ chi phí.
- **Health Score:** Điểm tổng hợp từ revenue utilization, debt health, occupancy.

### Enterprise

- **Smart Period Reporting:** Kỳ đã qua (VD: 2026-06) được chốt sổ vĩnh viễn; kỳ hiện tại hiển thị số liệu live đến ngày hôm nay.
- **DOCX / Excel Export:** Xuất báo cáo tài chính ra file Word (`.docx`) và Excel (`.xlsx`).
- **Session Management:** Hội thoại multi-turn, lưu in-memory + database fallback.
- **Dynamic Follow-Up Chips:** Gợi ý câu hỏi đào sâu tự động, lọc trùng lặp trong session.
- **Automated Zalo Dispatch:** Gửi báo cáo và tin nhắn qua Zalo OA Enterprise Webhook.
- **Rate Limiting:** Giới hạn request theo cửa sổ thời gian cho AI endpoints.
- **Full Audit Logging:** Question, system prompt, skills, tools, SQL, reply, latency — ghi vào `ai_audit_logs` (DB) và JSONL.
- **Security Hooks:** Pre-tool chặn `DROP`/`DELETE`/`UPDATE`/`INSERT`; post-tool che SĐT, CCCD, email.
- **Evaluation & Monitoring:** Accuracy, latency, fallback rate, cache hit rate, SQL query cache stats.

### SQL Query Cache

Cache các câu Text-to-SQL thường gặp trong bộ nhớ (LRU, TTL) — giảm số lần gọi Gemini API và cải thiện độ trễ.

---

## Project Structure

```
ai-property-advisor-harness/
├── main.py                          # FastAPI entry point
├── Dockerfile                       # Container build
├── docker-compose.yml               # MySQL + App orchestration
├── requirements.txt                 # Python dependencies
├── pytest.ini                       # Test configuration
├── .env.example                     # Environment template
│
├── config/
│   └── settings.py                  # Pydantic settings (DB, Gemini, rate limit, cache)
│
├── database/
│   ├── connection.py                # MySQL async pool (aiomysql)
│   ├── schema_mysql.sql             # Full DDL (61 tables + ai_audit_logs)
│   ├── queries/
│   │   └── kpi_queries.py           # Parameterized SQL queries
│   └── migrations/                  # Flyway-style migration SQL
│
├── src/
│   ├── api/
│   │   ├── router.py                # API route registration
│   │   ├── dependencies.py          # Auth/param dependencies
│   │   └── v1/
│   │       ├── kpi.py               # KPI REST endpoints
│   │       └── copilot.py           # AI Copilot endpoints
│   ├── engines/
│   │   ├── kpi_repository.py        # KPI cache + session store
│   │   ├── metrics_engine.py        # Health score calculation
│   │   ├── context_engine.py        # Period context logic
│   │   └── rate_limiter.py          # Request throttling
│   ├── harness/
│   │   ├── agent_loop.py            # Core agentic loop
│   │   ├── tools.py                 # Tool definitions + dispatch
│   │   ├── skill_loader.py          # Dynamic skill loading
│   │   ├── hooks.py                 # Security hooks (pre/post-tool)
│   │   ├── payload_logger.py        # Audit logging
│   │   └── prompts.py               # System prompts
│   ├── schemas/
│   │   └── kpi_schema.py            # Pydantic models
│   └── services/
│       ├── ai_report_service.py     # Financial report generation
│       ├── ai_ask_service.py        # Multi-turn Q&A service
│       ├── gemini_service.py        # Gemini client + model registry
│       ├── suggestion_service.py    # Follow-up question generator
│       ├── prompt_templates.py      # Prompt templates
│       └── evaluation_logger.py     # Quality metrics
│
├── skills/                          # Domain knowledge packages
│   ├── financial_analysis/
│   ├── marketing_copywriting/
│   └── sql_best_practices/
│
├── static/
│   ├── index.html                   # Enterprise SaaS UI
│   └── logs/                        # Audit JSONL output
│
├── scripts/                         # Utility & benchmark scripts
│   ├── benchmark_10_landlord_scenarios.py
│   ├── benchmark_complex_queries.py
│   ├── test_full_payload_audit.py
│   ├── seed_comprehensive.sql
│   └── ...
│
├── tests/
│   ├── conftest.py
│   ├── test_ai_copilot.py
│   ├── test_comprehensive.py
│   ├── test_kpi_repository.py
│   └── test_rate_limiter.py
│
└── docs/
    ├── ARCHITECTURE.md
    └── TRACKING_REPORT.md
```

---

## Quick Start

### Yêu cầu

- Python 3.11+
- MySQL 8.0 (hoặc Docker)
- Gemini API key ([đăng ký miễn phí](https://aistudio.google.com/apikey))

### Cách 1: Docker Compose (Khuyên dùng)

```bash
# 1. Tạo file .env và cấu hình
cp .env.example .env
# Sửa .env: điền GEMINI_API_KEY=your_key

# 2. Khởi động MySQL + App
docker-compose up -d

# 3. Mở UI
open http://localhost:8000/ui
```

Docker Compose tự động tạo container MySQL, nạp schema 61 bảng + dữ liệu mẫu, và chạy FastAPI server.

### Cách 2: Thủ công

```bash
# 1. Chạy MySQL
docker run -d --name hdbhms_mysql -p 3306:3306 \
  -e MYSQL_ROOT_PASSWORD=password \
  -e MYSQL_DATABASE=hdbhms mysql:8.0

# 2. Nạp schema & seed data
mysql -h 127.0.0.1 -u root -ppassword hdbhms < database/schema_mysql.sql
mysql -h 127.0.0.1 -u root -ppassword hdbhms < scripts/seed_comprehensive.sql

# 3. Cài đặt dependencies
pip install -r requirements.txt
cp .env.example .env
# Sửa .env với Gemini API key và DB settings

# 4. Chạy server
uvicorn main:app --host 0.0.0.0 --port 8000
```

Truy cập UI tại `http://localhost:8000/ui` và API docs tại `http://localhost:8000/docs`.

---

## API Endpoints

### KPI Analytics

| Method | Path | Mô tả |
|--------|------|-------|
| `GET` | `/api/v1/advisor/kpi/overview` | Tổng quan toàn bộ KPI |
| `GET` | `/api/v1/advisor/kpi/revenue` | Chi tiết doanh thu + lịch sử 12 tháng |
| `GET` | `/api/v1/advisor/kpi/expense` | Chi tiết chi phí + lịch sử 12 tháng |
| `GET` | `/api/v1/advisor/kpi/debt` | Công nợ aging, theo phòng, cảnh báo |
| `GET` | `/api/v1/advisor/kpi/occupancy` | Tỷ lệ lấp đầy + lịch sử |
| `GET` | `/api/v1/advisor/kpi/export` | Xuất JSON hoặc Excel (.xlsx) |

### AI Copilot

| Method | Path | Mô tả |
|--------|------|-------|
| `POST` | `/api/v1/advisor/copilot/ask` | Hỏi đáp AI multi-turn (có tool execution) |
| `POST` | `/api/v1/advisor/copilot/report` | Sinh báo cáo tài chính AI |
| `POST` | `/api/v1/advisor/copilot/report/refresh` | Xoá cache và sinh lại báo cáo |
| `GET` | `/api/v1/advisor/copilot/report/export-docx` | Tải báo cáo dạng DOCX |
| `POST` | `/api/v1/advisor/copilot/session` | Tạo session mới |
| `GET` | `/api/v1/advisor/copilot/session/{id}` | Lấy lịch sử hội thoại |
| `GET` | `/api/v1/advisor/copilot/suggestions` | Gợi ý câu hỏi tiếp theo |
| `GET` | `/api/v1/advisor/copilot/analysis` | Phát hiện biến động KPI (proactive) |
| `POST` | `/api/v1/advisor/copilot/send-zalo` | Gửi tin nhắn qua Zalo OA |

### Monitoring

| Method | Path | Mô tả |
|--------|------|-------|
| `GET` | `/api/v1/advisor/copilot/eval` | Chất lượng AI (accuracy, latency, etc.) |
| `GET` | `/api/v1/advisor/copilot/sql-cache/stats` | SQL cache hit/miss stats |
| `GET` | `/health` | Health check |

---

## Testing

```bash
# Chạy toàn bộ test
pytest

# Benchmark 10 kịch bản chủ nhà E2E
python scripts/benchmark_10_landlord_scenarios.py

# Benchmark 5 kịch bản SQL phức tạp
python scripts/benchmark_complex_queries.py

# Kiểm thử audit logger & code interpreter
python scripts/test_full_payload_audit.py
```

---

## Environment Variables

| Variable | Default | Mô tả |
|----------|---------|-------|
| `DATABASE_URL` | `mysql://root:password@localhost:3306/hdbhms` | Chuỗi kết nối MySQL |
| `GEMINI_API_KEY` | — | Google Gemini API key |
| `GEMINI_MODEL` | `gemini-3.6-flash-lite` | Model AI chính |
| `GEMINI_FALLBACK_MODEL` | `gemini-3.5-flash-lite` | Model dự phòng |
| `GEMINI_TEMPERATURE` | `0.0` | Nhiệt độ model |
| `GEMINI_TIMEOUT` | `120` | Timeout API (giây) |
| `RATE_LIMIT_REQUESTS` | `30` | Số request tối đa mỗi cửa sổ |
| `RATE_LIMIT_WINDOW` | `60` | Cửa sổ rate limit (giây) |
| `LOG_LEVEL` | `INFO` | Cấp độ log |
| `ENVIRONMENT` | `development` | Môi trường chạy |

---

## Tech Stack

- **Runtime:** Python 3.11, FastAPI, Uvicorn
- **Database:** MySQL 8.0, aiomysql (async pool), PyMySQL
- **AI:** Google Gemini API (`google-genai` SDK)
- **Validation:** Pydantic v2, Pydantic Settings
- **Testing:** pytest, pytest-asyncio, httpx
- **Export:** openpyxl (Excel)
- **Infrastructure:** Docker, Docker Compose
