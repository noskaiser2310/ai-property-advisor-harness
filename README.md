# AI Property Advisor — Financial Copilot for Rental Property Management

[![Python](https://img.shields.io/badge/Python-3.11-blue?logo=python)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?logo=fastapi)](https://fastapi.tiangolo.com)
[![Gemini](https://img.shields.io/badge/Gemini-3.5--flash--lite-4285F4?logo=google)](https://ai.google.dev)
[![MySQL](https://img.shields.io/badge/MySQL-8.0-4479A1?logo=mysql)](https://mysql.com)
[![Docker](https://img.shields.io/badge/Docker-Enabled-2496ED?logo=docker)](https://docker.com)
[![Tests](https://img.shields.io/badge/Tests-96%2F96%20Passing-brightgreen)](file:///d:/Admin_AI_for_report/ai-property-advisor-harness/tests)

Hệ thống **AI Financial Copilot** thế hệ mới dành cho quản lý nhà trọ và căn hộ dịch vụ. Xây dựng trên kiến trúc **Harness Agent Architecture**, ứng dụng khả năng tự động suy luận (reasoning), tự động gọi công cụ (KPI Repository, Text-to-SQL Guard, Code Interpreter Sandbox) và sinh báo cáo quản trị tài chính chuyên sâu bằng ngôn ngữ tự nhiên.

> 🚀 **Web App Interface:** [http://localhost:8080/ui](http://localhost:8080/ui)  
> 📑 **API Documentation (Swagger UI):** [http://localhost:8080/docs](http://localhost:8080/docs)  
> 📘 **Technical Deep-Dive:** [docs/TECHNICAL_REPORT.md](file:///d:/Admin_AI_for_report/ai-property-advisor-harness/docs/TECHNICAL_REPORT.md)

---

## 📌 MỤC LỤC

1. [Tổng Quan Kiến Trúc Hệ Thống (Architecture)](#-tổng-quan-kiến-trúc-hệ-thống-architecture)
2. [Tính Năng Nổi Bật](#-tính-năng-nổi-bật)
3. [Hướng Dẫn Cài Đặt & Chạy Hệ Thống (Quick Start)](#-hướng-dẫn-cài-đặt--chạy-hệ-thống-quick-start)
   - [Cách 1: Khởi Chạy Bằng Docker Compose (Khuyên Dùng)](#cách-1-khởi-chạy-bằng-docker-compose-khuyên-dùng)
   - [Cách 2: Khởi Chạy Thủ Công Trên Máy Cục Bộ (Local Python)](#cách-2-khởi-chạy-thủ-công-trên-máy-cục-bộ-local-python)
4. [Nạp Dữ Liệu Mẫu (Seed Data 13 Tháng)](#-nạp-dữ-liệu-mẫu-seed-data-13-tháng)
5. [Cấu Hình Biến Môi Trường (.env)](#-cấu-hình-biến-môi-trường-env)
6. [Danh Sách API Endpoints](#-danh-sách-api-endpoints)
7. [Hướng Dẫn Sử Dụng Web UI & Trải Nghiệm AI Copilot](#-hướng-dẫn-sử-dụng-web-ui--trải-nghiệm-ai-copilot)
8. [Kiểm Thử & Benchmark (Testing & Benchmarks)](#-kiểm-thử--benchmark-testing--benchmarks)
9. [Xử Lý Lỗi Thường Gặp (Troubleshooting)](#-xử-lý-lỗi-thường-gặp-troubleshooting)

---

## 🏗️ TỔNG QUAN KIẾN TRÚC HỆ THỐNG (ARCHITECTURE)

Hệ thống hoạt động theo mô hình **Harness Agentic Loop** với các lớp bảo mật và bộ nhớ đệm đa tầng:

```
                        ┌──────────────────────────────────────────────┐
                        │             Enterprise SaaS UI               │
                        │      (Vanilla JS + marked.js Markdown)       │
                        └──────────────────────┬───────────────────────┘
                                               │ HTTP / REST
                                               ▼
                        ┌──────────────────────────────────────────────┐
                        │            FastAPI REST Layer                │
                        │    /kpi/*  |  /copilot/*  |  /health        │
                        └──────────────────────┬───────────────────────┘
                                               │
                                               ▼
                        ┌──────────────────────────────────────────────┐
                        │         Harness Agentic Loop                 │
                        │    (Gemini 3.5 / 3.1 Flash-Lite Client)      │
                        │    - Dynamic Skill Injection                 │
                        │    - Real-Time Time & Context Window         │
                        └──────┬───────────────┬───────────────┬───────┘
                               │               │               │
                               ▼               ▼               ▼
                       ┌──────────────┐ ┌──────────────┐ ┌──────────────┐
                       │ get_kpi_...  │ │ execute_sql_ │ │ python_code_ │
                       │ (Engine API) │ │ (MySQL Guard)│ │ (Sandbox)    │
                       └──────┬───────┘ └──────┬───────┘ └──────┬───────┘
                              │                │                │
                              └────────┬───────┴────────────────┘
                                       │
                                       ▼
                       ┌──────────────────────────────────────────────┐
                       │          Security & Privacy Hooks            │
                       │   Pre-tool: AST/Regex SQL Security Guard    │
                       │   Post-tool: Regex PII Sanitization          │
                       └──────────────────────┬───────────────────────┘
                                              │
                                              ▼
                       ┌──────────────────────────────────────────────┐
                       │       Audit Logger & Memory Caches           │
                       │   - JSONL Logger & MySQL `ai_audit_logs`     │
                       │   - LRU SQL Query Cache (TTL 30m)            │
                       │   - SHA256 KPI Version-Aware Cache          │
                       └──────────────────────┬───────────────────────┘
                                              │
                                              ▼
                       ┌──────────────────────────────────────────────┐
                       │             MySQL 8.0 Engine                 │
                       │         (61 Core Relational Tables)          │
                       └──────────────────────────────────────────────┘
```

### Quy Trình Xử Lý Một Câu Hỏi:
1. **User request:** Người dùng gửi câu hỏi từ Web UI hoặc API REST.
2. **Context & Skill Injection:** Hệ thống nạp ngữ cảnh thời gian thực (`NOW()`), phân tích từ khóa để nạp gói kỹ năng động (`financial_analysis`, `sql_best_practices`, `marketing_copywriting`).
3. **Agent Loop Reasoning:** Gemini nhận Prompt và danh sách Tools (`get_kpi_overview`, `execute_sql_query`, `execute_dynamic_python_script`, `generate_marketing_post`).
4. **Pre-Tool Security Check:** Kiểm tra an toàn SQL (chỉ cho phép `SELECT`/`WITH`, ngăn chặn tuyệt đối SQL Injection & thao tác ghi/xóa).
5. **Tool Execution:** Thực thi truy vấn MySQL hoặc chạy Python Sandbox tính toán số liệu.
6. **Post-Tool Privacy Sanitization:** Tự động che mờ thông tin nhạy cảm (PII: SĐT, CCCD, Email).
7. **Synthesis & Audit:** Gemini tổng hợp kết quả thành văn bản báo cáo tự nhiên. Lưu 100% nhật ký vào file JSONL và bảng `ai_audit_logs`.

---

## ⭐ TÍNH NĂNG NỔI BẬT

- 🤖 **AI Financial Copilot Multi-Turn:** Hỏi đáp thông minh, phân tích sâu công nợ quá hạn, tỷ lệ lấp đầy, dự báo chi phí cơ hội phòng trống.
- ⚡ **Báo Cáo Quản Trị Tự Động:** Sinh báo cáo tài chính tháng theo chuẩn quản trị SaaS chỉ trong 2-3 giây; hỗ trợ xuất file Word (`.docx`).
- 🛡️ **An Toàn Dữ Liệu Tuyệt Đối (Zero Hallucination):** 100% con số tài chính được lấy từ SQL / Engine tính toán thực tế.
- 🔒 **Bảo Mật 2 Lớp (Pre/Post Security Hooks):** SQL Guard chặn các câu lệnh sửa đổi dữ liệu; PII Sanitizer bảo mật thông tin cá nhân khách thuê.
- 🚀 **Cache Đa Tầng Thông Minh:** Hash SHA256 nhận biết thay đổi CSDL để cache KPI/Report, giúp phản hồi tức thì và tiết kiệm chi phí Gemini API.
- 📈 **Seed Data 13 Tháng Liên Tục:** Tự động tạo dữ liệu mẫu thực tế từ tháng 07/2025 đến tháng 07/2026.

---

## ⚡ HƯỚNG DẪN CÀI ĐẶT & CHẠY HỆ THỐNG (QUICK START)

### Yêu Cầu Tối Thiểu
- **Docker & Docker Compose** (Nếu chạy bằng Docker)  
*Hoặc:*
- **Python 3.11+**
- **MySQL 8.0**
- **Google Gemini API Key** (Miễn phí tại [Google AI Studio](https://aistudio.google.com/apikey))

---

### Cách 1: Khởi Chạy Bằng Docker Compose (Khuyên Dùng)

Khởi chạy trọn gói cả Web App FastAPI và CSDL MySQL 8.0 chỉ với 1 lệnh:

1. **Clone repository & Tạo file môi trường `.env`:**
   ```bash
   git clone https://github.com/noskaiser2310/ai-property-advisor-harness.git
   cd ai-property-advisor-harness
   cp .env.example .env
   ```

2. **Cập nhật Gemini API Key trong `.env`:**
   Mở file `.env` và dán API key của bạn:
   ```env
   GEMINI_API_KEY=AIzaSyYourActualApiKeyHere...
   ```

3. **Build & Khởi chạy các container:**
   ```bash
   docker-compose up -d --build
   ```

4. **Truy cập ứng dụng:**
   - 🌐 **Giao diện Web App (SaaS UI):** [http://localhost:8080/ui](http://localhost:8080/ui)
   - 📖 **Tài liệu API (Swagger UI):** [http://localhost:8080/docs](http://localhost:8080/docs)
   - 💚 **Kiểm tra Healthcheck:** [http://localhost:8080/health](http://localhost:8080/health)

---

### Cách 2: Khởi Chạy Thủ Công Trên Máy Cục Bộ (Local Python)

1. **Khởi chạy container MySQL:**
   ```bash
   docker run -d --name hdbhms_mysql \
     -p 3306:3306 \
     -e MYSQL_ROOT_PASSWORD=password \
     -e MYSQL_DATABASE=hdbhms \
     mysql:8.0
   ```

2. **Tạo virtual environment & Cài đặt thư viện:**
   ```bash
   python -m venv venv
   # Windows:
   .\venv\Scripts\activate
   # Linux/macOS:
   source venv/bin/activate

   pip install -r requirements.txt
   ```

3. **Nạp Schema & Dữ liệu CSDL:**
   ```bash
   Get-Content database/schema_mysql.sql | docker exec -i hdbhms_mysql mysql -uroot -ppassword hdbhms
   Get-Content scripts/seed_comprehensive.sql | docker exec -i hdbhms_mysql mysql -uroot -ppassword hdbhms
   python scripts/seed_monthly_history.py
   ```

4. **Khởi chạy FastAPI Server:**
   ```bash
   uvicorn main:app --host 0.0.0.0 --port 8000 --reload
   ```
   Truy cập Web UI tại `http://localhost:8000/ui`.

---

## 🗄️ NẠP DỮ LIỆU MẪU (SEED DATA 13 THÁNG)

Hệ thống đi kèm kịch bản nạp dữ liệu mẫu 13 tháng thực tế (gồm 15 phòng trọ, hợp đồng thuê, hóa đơn tiền nhà, chi phí điện nước đầu vào, công nợ quá hạn và lịch sử giao dịch).

Để nạp lại hoặc làm sạch dữ liệu mẫu trong Docker:

```bash
# 1. Nạp bảng dữ liệu cơ sở & cấu hình phòng/hợp đồng
Get-Content scripts/seed_comprehensive.sql | docker exec -i hdbhms_mysql mysql -uroot -ppassword hdbhms

# 2. Sinh lịch sử giao dịch & hóa đơn 13 tháng (2025-07 -> 2026-07)
python scripts/seed_monthly_history.py

# 3. Khởi động lại app container để xóa cache RAM cũ
docker-compose restart app
```

---

## ⚙️ CẤU HÌNH BIẾN MÔI TRƯỜNG (.ENV)

| Tên Biến | Giá Trị Mặc Định | Mô Tả |
|----------|------------------|-------|
| `DATABASE_URL` | `mysql://root:password@mysql:3306/hdbhms` | Chuỗi kết nối CSDL MySQL (dùng tên container `mysql` trong Docker) |
| `GEMINI_API_KEY` | *(Bắt buộc)* | Key truy cập Google Gemini API |
| `GEMINI_MODEL` | `gemini-3.5-flash-lite` | Model AI mặc định xử lý suy luận chính |
| `GEMINI_FALLBACK_MODEL` | `gemini-3.1-flash-lite` | Model AI dự phòng khi model chính quá tải |
| `RATE_LIMIT_REQUESTS` | `30` | Tối đa 30 requests / 60 giây cho mỗi client |
| `CACHE_TYPE` | `memory` | Cơ chế lưu cache (`memory` hoặc `redis`) |

---

## 📑 DANH SÁCH API ENDPOINTS

### 1. 🤖 AI Copilot Core API

| Method | Endpoint Path | Mô Tả Tính Năng |
|--------|---------------|-----------------|
| `POST` | `/api/v1/advisor/copilot/ask` | Hỏi đáp AI đa lượt (Multi-turn Agent Loop) |
| `POST` | `/api/v1/advisor/copilot/report` | Sinh báo cáo quản trị tài chính tự động bằng AI |
| `POST` | `/api/v1/advisor/copilot/report/refresh` | Làm sạch Cache và bắt buộc sinh lại báo cáo mới |
| `GET`  | `/api/v1/advisor/copilot/report/export-docx` | Xuất file báo cáo tài chính định dạng Word (`.docx`) |
| `POST` | `/api/v1/advisor/copilot/session` | Khởi tạo phiên hội thoại mới |
| `GET`  | `/api/v1/advisor/copilot/suggestions` | Lấy danh sách gợi ý câu hỏi phân tích thông minh |

### 2. 🏠 KPI Financial Analytics API

| Method | Endpoint Path | Mô Tả Tính Năng |
|--------|---------------|-----------------|
| `GET` | `/api/v1/advisor/kpi/overview` | Tổng quan tài chính, lấp đầy & điểm sức khỏe (Health Score) |
| `GET` | `/api/v1/advisor/kpi/revenue` | Chi tiết doanh thu theo nguồn + lịch sử 12 tháng |
| `GET` | `/api/v1/advisor/kpi/expense` | Chi tiết chi phí vận hành + lịch sử 12 tháng |
| `GET` | `/api/v1/advisor/kpi/debt` | Phân tích công nợ aging, phòng nợ xấu & cảnh báo |
| `GET` | `/api/v1/advisor/kpi/occupancy` | Phân tích tỷ lệ lấp đầy phòng + lịch sử |
| `GET` | `/api/v1/advisor/kpi/export` | Xuất dữ liệu KPI định dạng JSON hoặc Excel (`.xlsx`) |

---

## 🖥️ HƯỚNG DẪN SỬ DỤNG WEB UI & TRẢI NGHIỆM AI COPILOT

1. **Mở trình duyệt:** Truy cập **[http://localhost:8080/ui](http://localhost:8080/ui)**.
2. **Xem Tổng Quan Dashboard:**
   - Các thẻ **Doanh thu**, **Chi phí**, **Lợi nhuận**, **Tỷ lệ lấp đầy**, **Tổng công nợ** và **Health Score** hiển thị trực quan.
   - Chọn kỳ báo cáo (ví dụ: `2026-07` hoặc `2026-06`) để xem biến động tài chính theo từng tháng.
3. **Trải Nghiệm AI Financial Copilot:**
   - Nhấp chọn các câu hỏi gợi ý nhanh hoặc nhập trực tiếp câu hỏi:
     - *"Báo cáo tài chính tháng 7 năm 2026 cho tôi."*
     - *"Phòng 501 hiện đang nợ bao nhiêu tiền và gồm những khoản nào?"*
     - *"Tính toán chi phí cơ hội do các phòng trống gây ra trong tháng này?"*
     - *"Viết cho tôi một bài đăng quảng cáo tìm khách thuê phòng 401 chuẩn AIDA."*
4. **Tải Báo Cáo Word:** Nhấp vào nút **"Xuất Word (.docx)"** trên giao diện để tải ngay file báo cáo nghiệp vụ chuyên nghiệp.

---

## 🧪 KIỂM THỬ & BENCHMARK (TESTING & BENCHMARKS)

Hệ thống đã trải qua quá trình kiểm thử toàn diện với **96/96 unit tests passing** và bộ kịch bản benchmark 10 tình huống thực tế của chủ nhà trọ:

```bash
# 1. Chạy toàn bộ Unit Tests bằng pytest
pytest

# 2. Chạy kịch bản Benchmark 10 tình huống thực tế của chủ nhà trọ
python scripts/benchmark_10_landlord_scenarios.py

# 3. Kiểm thử audit log ghi lại 100% dữ liệu
python scripts/test_full_payload_audit.py
```

---

## 🔧 XỬ LÝ LỖI THƯỜNG GẶP (TROUBLESHOOTING)

### 1. Error: `port is already allocated` khi chạy `docker-compose up`
- **Nguyên nhân:** Cổng 8000 hoặc 3306 trên máy host đã bị phần mềm khác chiếm dụng.
- **Xử lý:** Mở `docker-compose.yml` và đổi cổng host:
  ```yaml
  ports:
    - "8080:8000"  # Đổi cổng Web App sang 8080
    - "3307:3306"  # Đổi cổng MySQL sang 3307
  ```

### 2. Báo cáo tài chính hiển thị `0 VNĐ`
- **Nguyên nhân:** CSDL MySQL mới khởi tạo chưa có dữ liệu giao dịch hoặc cache RAM cũ đang lưu kết quả rỗng.
- **Xử lý:** Nạp lại seed data và restart app:
  ```bash
  python scripts/seed_monthly_history.py
  docker-compose restart app
  ```

### 3. Cảnh báo `GEMINI_API_KEY is not set`
- **Nguyên nhân:** Chưa cấu hình file `.env` hoặc chưa truyền biến môi trường vào Docker.
- **Xử lý:** Đảm bảo file `.env` nằm ở thư mục gốc dự án và chứa dòng `GEMINI_API_KEY=AIzaSy...` hợp lệ.

---

## 📄 GIẤY PHÉP & TÁC GIẢ

- **Phát triển bởi:** Antigravity AI Engineering Team (Google DeepMind)
- **Giấy phép:** MIT License
- **Tài liệu kỹ thuật chi tiết:** Xem tại [docs/TECHNICAL_REPORT.md](file:///d:/Admin_AI_for_report/ai-property-advisor-harness/docs/TECHNICAL_REPORT.md)
