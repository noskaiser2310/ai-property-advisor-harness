# TECHNICAL REPORT: AI PROPERTY ADVISOR (HARNESS AGENTIC FINANCIAL COPILOT)

**Date:** July 24, 2026  
**System Version:** 3.0.0  
**Target Environment:** Enterprise Production / Docker Containerized  
**Architecture Pattern:** Harness Agent Architecture (Model + Harness Environment + Dynamic Code Interpreter)

---

## TABLE OF CONTENTS

1. [EXECUTIVE SUMMARY](#executive-summary)
2. [SYSTEM ARCHITECTURE & COMPONENT TOPOLOGY](#1-system-architecture--component-topology)
3. [HARNESS AGENTIC LOOP — DEEP DIVE](#2-harness-agentic-loop--deep-dive)
4. [INTENT FILTERING & DOMAIN CLASSIFICATION](#3-intent-filtering--domain-classification)
5. [SUGGESTION & PROACTIVE ANALYSIS ENGINE](#4-suggestion--proactive-analysis-engine)
6. [API REFERENCE & ENDPOINT MAP](#5-api-reference--endpoint-map)
7. [DEPLOYMENT ARCHITECTURE](#6-deployment-architecture)

---

## EXECUTIVE SUMMARY

**AI Property Advisor** is an enterprise-grade financial copilot engineered specifically for rental property management, built on the **Harness Agent Architecture**. By integrating **Google Gemini 3.5 Flash-Lite** with a robust, multi-layered Python agentic loop, the system translates complex natural language queries into safe MySQL data extractions, Python sandboxed code execution, proactive KPI calculations, and strategic operational recommendations.

### Design Philosophy

The system is built on four core design principles:

1. **Zero Hallucination on Financial Data:** Every number presented to the user originates from either a deterministic SQL query or a formally verified KPI calculation engine. The LLM is never allowed to generate financial figures from its training data — it can only interpret and synthesize results returned by the tool layer.

2. **Defense-in-Depth Security:** SQL injection is prevented at three independent layers: (a) the LLM system prompt instructs it to only generate SELECT/WITH queries, (b) the Pre-Tool Hook performs regex-based enforcement, and (c) the database user has read-only permissions. PII is masked at the post-tool layer before data reaches the LLM context window.

3. **Cache-Optimized Economics:** Four independent cache layers (KPI, SQL, AI Report, Session) work together to minimize expensive LLM API calls. The SHA256 version-aware KPI cache ensures that reports are only regenerated when underlying data actually changes, not on every request.

4. **Production-Grade Observability:** Every single interaction — user question, system prompt, skills loaded, tool calls with arguments, raw SQL queries, AI responses, and latency — is logged to both append-only JSONL files and the MySQL `ai_audit_logs` table.

### Key Architectural Highlights
- **Harness Agentic Loop:** Iterative reasoning loop with function calling capabilities (`get_kpi_overview`, `execute_sql_query`, `execute_dynamic_python_script`, `generate_marketing_post`).
- **Deep Security & Privacy Control:** Pre-tool SQL security guard enforcing strict `SELECT`/`WITH` statements and post-tool PII masking (redacting phone numbers, national IDs).
- **Gemini Model Fallback Cascade:** Automatic fallback from `gemini-3.5-flash-lite` to `gemini-3.1-flash-lite` on rate limits or errors.
- **Production-Grade Audit & Observability:** 100% payload audit logging persisted to both local JSONL append logs and MySQL `ai_audit_logs` table with execution timing metrics.

---

## 1. SYSTEM ARCHITECTURE & COMPONENT TOPOLOGY

### 1.1 High-Level Component Diagram

```mermaid
graph TB
    subgraph UI_Layer["🎨 Presentation Layer"]
        UI["Enterprise SaaS UI<br/>(Vanilla JS + marked.js)"]
    end

    subgraph API_Layer["⚡ FastAPI REST Layer"]
        KPI["/kpi/*<br/>6 KPI Endpoints"]
        COPILOT["/copilot/*<br/>12 Copilot Endpoints"]
        HEALTH["/health<br/>Health Check"]
        MW["Middleware Stack<br/>• CORS · Request Logging<br/>• Rate Limiting (30/60s)<br/>• Global Exception Handler"]
    end

    subgraph Harness_Layer["🧠 Harness Agentic Loop"]
        GL["Gemini LLM Client<br/>(3.5 Flash-Lite → 3.1 Flash-Lite)"]
        SK["Dynamic Skill Injector<br/>(Keyword → Skill Package)"]
        TC["Time & Context Window<br/>(Vietnam TZ GMT+7)"]
        CH["Context History Compactor<br/>(Summary + Last 8 turns)"]
    end

    subgraph Tool_Layer["🔧 Agent Tools"]
        KPI_T["get_kpi_overview<br/>KPI Repository API"]
        SQL_T["execute_sql_query<br/>MySQL Text-to-SQL (SELECT/WITH only)"]
        PY_T["execute_dynamic_python_script<br/>Code Interpreter Sandbox"]
        MKT_T["generate_marketing_post<br/>AIDA Copy Generator"]
    end

    subgraph Security_Layer["🛡️ Security & Privacy"]
        PRE_HOOK["Pre-Tool Hook<br/>SQL Injection Guard"]
        POST_HOOK["Post-Tool Hook<br/>PII Sanitizer"]
    end

    subgraph Cache_Layer["💾 Cache Layer"]
        KPI_CACHE["SHA256 Version-Aware KPI Cache"]
        SQL_CACHE["LRU SQL Query Cache<br/>(100 slots · Jaccard ≥ 0.8)"]
        AI_CACHE["AI Report Cache<br/>(Background Generation)"]
        SESSION["Session Store<br/>(TTL 30m · DB Persistence)"]
    end

    subgraph Data_Layer["🗄️ MySQL 8.0 Engine"]
        DB["61 Core Relational Tables<br/>Properties · Rooms · Invoices<br/>Payments · Tenants · Audit"]
    end

    UI -->|HTTP/REST| API_Layer
    API_Layer --> Harness_Layer
    GL --> SK & TC & CH
    Harness_Layer --> Tool_Layer
    Tool_Layer --> Security_Layer
    Security_Layer --> Cache_Layer
    Cache_Layer --> Data_Layer
```

### 1.2 Request Processing Pipeline

```mermaid
flowchart LR
    A["👤 User Question"] --> B["Intent Filter<br/>(Out-of-Domain?)"]
    B -->|"In-domain"| C1["Check KPI Cache<br/>(SHA256 version)"]
    B -->|"Out-of-domain"| D["❌ Reject with Message"]
    C1 --> C2["Skill Injection<br/>(Keyword Match → Skill Packages)"]
    C2 --> C3["Build System Prompt<br/>(Schema + Few-Shot SQL + Skills)"]
    C3 --> E["Harness Agent Loop<br/>(Max 10 Steps · 3 Retries/Tool)"]
    E --> F{"Gemini Response<br/>contains Function Call?"}
    F -->|"Yes"| G["Pre-Tool Hook<br/>(SQL Security Guard)"]
    F -->|"No"| H["Synthesize Final Answer<br/>(Strip LaTeX · Format)"]
    G -->|"Allowed"| I{"Tool Execution<br/>(3 retries with backoff)"}
    G -->|"Blocked"| J["Return Security Error"]
    I -->|"Success"| K["Post-Tool Hook<br/>(PII Masking)"]
    I -->|"Fail"| E
    K --> L{"Step < 10 &<br/>Need more data?"}
    L -->|"Yes"| E
    L -->|"No"| H
    H --> M["Payload Audit Logger<br/>(JSONL + DB ai_audit_logs)"]
    M --> N["Session Store<br/>(In-memory + DB persist)"]
    N --> O["Generate Suggestions<br/>(4 dynamic follow-up chips)"]
    O --> P["📋 Return to User<br/>{reply, session_id, suggestions, type}"]
```

### 1.3 Agentic Loop Sequence Diagram

```mermaid
sequenceDiagram
    actor User
    participant FastAPI as FastAPI REST
    participant RateLimit as Rate Limiter
    participant AIAsk as AIAskService
    participant Harness as HarnessAgentLoop
    participant Gemini as Gemini LLM
    participant Tools as Tool Dispatcher
    participant MySQL as MySQL 8.0
    participant Cache as Cache Layer
    participant Audit as PayloadAuditLogger
    participant Sugg as SuggestionService

    User->>FastAPI: POST /copilot/ask<br/>{question, landlord_id, period, session_id?}
    FastAPI->>RateLimit: Check Rate Limit (30 req / 60s)
    RateLimit-->>FastAPI: ✅ Allowed

    FastAPI->>AIAsk: process_question()
    AIAsk->>AIAsk: Intent Filter (Out-of-Domain Check)
    AIAsk->>Cache: get_kpi(landlord_id, period)
    Cache-->>AIAsk: KPIObject or None

    AIAsk->>Harness: run(question, landlord_id, period, history)

    loop Agent Loop (max 10 steps)
        Harness->>Harness: Step {N}: Build prompt with context
        Harness->>Gemini: generate_content(prompt, tools, config)

        alt Primary Model Available
            Gemini-->>Harness: Response (gemini-3.5-flash-lite)
        else Primary Rate Limited/Failed
            Gemini-->>Harness: Response (gemini-3.1-flash-lite)
        end

        alt function_call detected
            Harness->>Harness: Pre-Tool Hook (SQL Security Guard)
            Harness->>Tools: dispatch_tool(name, args)
            Tools->>MySQL: Execute Query / Compute KPI
            MySQL-->>Tools: Result
            Tools-->>Harness: Tool Result (JSON)
            Harness->>Harness: Post-Tool Hook (PII Masking)
            Harness->>Harness: Append to Messages
        else text response
            Harness->>Harness: Strip LaTeX, Format response
            Harness-->>AIAsk: {reply, type, plan}
        end
    end

    AIAsk->>Audit: log_turn(question, skills, tools, reply, latency)
    AIAsk->>AIAsk: SessionStore.persist_turn()
    AIAsk->>Sugg: get_suggestions(landlord_id, period, kpi)
    Sugg-->>AIAsk: [4-8 suggested questions]
    AIAsk-->>FastAPI: {reply, session_id, suggestions, type}
    FastAPI-->>User: {status: success, data: {reply, session_id, suggestions}}
```

### 1.4 Source Code Module Map

```mermaid
graph TB
    subgraph Entry["🚪 Entry Point"]
        MAIN["main.py — FastAPI app, lifespan, middleware, static files"]
    end

    subgraph Config["⚙️ Configuration"]
        SETT["config/settings.py — Pydantic settings, env variables"]
    end

    subgraph DB_Layer["🗄️ Database Layer"]
        CONN["database/connection.py — aiomysql pool, param converter"]
        QUERIES["database/queries/kpi_queries.py — 9 KPI SQL queries"]
    end

    subgraph API_Layer["🌐 API Layer"]
        ROUTER["src/api/router.py — Prefix /api/v1/advisor"]
        DDEPS["src/api/dependencies.py — landlord_id, period parsing"]
        V1_KPI["src/api/v1/kpi.py — 6 KPI endpoints"]
        V1_COPILOT["src/api/v1/copilot.py — 12 Copilot endpoints"]
    end

    subgraph Engine_Layer["⚡ Engines"]
        KPI_REPO["src/engines/kpi_repository.py — Cache, Session, Version Tracking"]
        METRICS["src/engines/metrics_engine.py — Health Score, Leakage Calc"]
        RATE["src/engines/rate_limiter.py — Sliding Window 30/60s"]
    end

    subgraph Core_Layer["🧠 Harness Core"]
        LOOP["src/harness/agent_loop.py — Agentic Reasoning Loop"]
        TOOLS["src/harness/tools.py — 4 Tool Implementations"]
        PROMPTS["src/harness/prompts.py — System Prompt, Schema, Few-Shot"]
        HOOKS["src/harness/hooks.py — Pre/Post Security Hooks"]
        SKILLS["src/harness/skill_loader.py — Dynamic Skill Injection"]
        PAYLOAD["src/harness/payload_logger.py — 360° Audit Logger"]
    end

    subgraph Service_Layer["📦 Services"]
        GEMINI["src/services/gemini_service.py — Gemini Client, ModelRegistry"]
        AI_ASK["src/services/ai_ask_service.py — Question Processing, Intent Filter"]
        AI_REPORT["src/services/ai_report_service.py — Report Generation, DOCX Export"]
        SUGGEST["src/services/suggestion_service.py — Rule-based Suggestions"]
        ANALYSIS["src/services/suggested_analysis_service.py — Proactive Analysis"]
        EVAL_LOGGER["src/services/evaluation_logger.py — Metrics Tracking"]
    end

    subgraph Schema["📐 Schemas"]
        KPI_SCHEMA["src/schemas/kpi_schema.py — 8 Pydantic Models"]
    end

    subgraph Static["🎨 Frontend"]
        INDEX["static/index.html — Glassmorphic UI, marked.js"]
    end

    MAIN --> SETT & CONN & ROUTER
    ROUTER --> V1_KPI & V1_COPILOT
    V1_KPI --> KPI_REPO & METRICS & QUERIES & CONN
    V1_COPILOT --> AI_ASK & AI_REPORT & SUGGEST & ANALYSIS & EVAL_LOGGER
    AI_ASK --> LOOP & KPI_REPO & EVAL_LOGGER
    AI_REPORT --> LOOP & KPI_REPO
    LOOP --> TOOLS & PROMPTS & SKILLS & GEMINI & PAYLOAD
    TOOLS --> HOOKS & KPI_REPO & CONN
    GEMINI --> SETT
    KPI_REPO --> KPI_SCHEMA & METRICS & SETT
    SUGGEST --> KPI_REPO & GEMINI
    ANALYSIS --> KPI_REPO
    CONN --> SETT
```

---

## 2. HARNESS AGENTIC LOOP — DEEP DIVE

### 2.1 Loop Architecture & State Machine

The core execution engine (`src/harness/agent_loop.py`) implements a **deterministic state machine** that orchestrates the interaction between the Gemini LLM and the tool ecosystem:

```mermaid
stateDiagram-v2
    [*] --> SKILL_LOADING
    SKILL_LOADING --> CONTEXT_ASSEMBLY: Skills loaded
    CONTEXT_ASSEMBLY --> LLM_INVOCATION: Prompt built

    LLM_INVOCATION --> FUNCTION_CALL: Gemini responds with function_call
    LLM_INVOCATION --> TEXT_RESPONSE: Gemini responds with text
    LLM_INVOCATION --> ERROR: API error / timeout
    LLM_INVOCATION --> FALLBACK: Primary model rate limited

    FALLBACK --> LLM_INVOCATION: Fallback model invoked

    FUNCTION_CALL --> PRE_HOOK: Tool name + args
    PRE_HOOK --> BLOCKED: SQL violation detected
    PRE_HOOK --> TOOL_EXECUTION: Allowed

    TOOL_EXECUTION --> TOOL_SUCCESS: Tool returns result
    TOOL_EXECUTION --> TOOL_RETRY: Error (attempt < 3)
    TOOL_EXECUTION --> TOOL_ERROR: Error (attempt = 3)

    TOOL_RETRY --> TOOL_EXECUTION: Retry with backoff

    TOOL_SUCCESS --> POST_HOOK: PII masking
    POST_HOOK --> LLM_INVOCATION: Tool result appended

    BLOCKED --> LLM_INVOCATION: Security error appended
    TOOL_ERROR --> LLM_INVOCATION: Runtime error appended

    TEXT_RESPONSE --> SYNTHESIS: Raw text from LLM
    SYNTHESIS --> AUDIT_LOGGING: LaTeX stripped, formatted
    AUDIT_LOGGING --> [*]: Return to user

    ERROR --> [*]: Raise RuntimeError
```

**Key Configuration Parameters:**

| Parameter | Value | Purpose |
|-----------|-------|---------|
| `MAX_AGENT_STEPS` | 10 | Maximum reasoning iterations before partial results |
| `MAX_TOOL_RETRY` | 2 | Retry attempts per tool execution (total 3) |
| `temperature` | 0.2 | Low temperature for deterministic responses |
| `max_output_tokens` | 2048 | Maximum tokens per Gemini response |

**State Transition Rules:**

| Transition | Trigger | Description |
|-----------|---------|-------------|
| SKILL_LOADING → CONTEXT_ASSEMBLY | Skills loaded unconditionally | Question keywords → skill packages appended to system prompt |
| CONTEXT_ASSEMBLY → LLM_INVOCATION | Prompt built | Time context, history, skills, schema, few-shot examples compiled |
| LLM_INVOCATION → FUNCTION_CALL | `function_call` part in Gemini response | Tool invocation requested |
| LLM_INVOCATION → TEXT_RESPONSE | Plain text in Gemini response | Final answer ready |
| LLM_INVOCATION → FALLBACK | Primary model rate-limited or error | Automatic cascade to fallback model |
| FUNCTION_CALL → PRE_HOOK | Before every tool execution | Validate SQL safety |
| PRE_HOOK → BLOCKED | Dangerous SQL detected | DROP, DELETE, UPDATE, INSERT, etc. |
| TOOL_EXECUTION → TOOL_RETRY | Tool execution error | Up to 2 retries with exponential backoff |
| TOOL_SUCCESS → POST_HOOK | After successful execution | PII masking before data reaches LLM |

### 2.2 Dynamic Skill Injection Mechanism

The `SkillLoader` (`src/harness/skill_loader.py`) performs keyword-based dynamic skill injection:

```mermaid
flowchart TD
    Q["💬 User Question"] --> N["Normalize to lowercase"]
    N --> KW["Keyword Analysis"]

    KW -->|"báo cáo, tài chính, doanh thu, chi phí,<br/>lợi nhuận, nợ, công nợ, sức khỏe,<br/>dòng tiền, tỉ suất, biên lợi, tăng trưởng,<br/>thất thoát, lãi, lỗ, thu nhập"| FIN["📊 Load financial_analysis SKILL.md"]

    KW -->|"bài đăng, tìm khách, cho thuê, viết bài,<br/>phòng trống, tiện ích, quảng cáo, marketing,<br/>đăng tin, facebook, zalo, chợ tốt"| MKT["📣 Load marketing_copywriting SKILL.md"]

    KW -->|"danh sách, tra cứu, sql, phòng, hóa đơn,<br/>hợp đồng, bảo trì, trạng thái, chi tiết,<br/>mã phòng, chỉ số, điện nước, khách thuê,<br/>người thuê, liệt kê, thống kê, số liệu"| SQL["💾 Load sql_best_practices SKILL.md"]

    KW -->|"No match"| DEFAULT["📊 Load financial_analysis (default)"]

    FIN & MKT & SQL & DEFAULT --> ASSEMBLE["Assemble into System Prompt Append"]
    ASSEMBLE --> SYSTEM["Add to HARNESS_SYSTEM_PROMPT"]
```

**Skill Package Specifications:**

| Skill Package | Trigger Keywords | Content |
|--------------|-----------------|---------|
| `financial_analysis` | báo cáo, tài chính, doanh thu, chi phí, lợi nhuận, nợ, sức khỏe, dòng tiền, tỉ suất, biên lợi, tăng trưởng, thất thoát, lãi, lỗ, thu nhập | Financial ratio formulas, health score interpretation, revenue leakage analysis, cash flow optimization strategies |
| `marketing_copywriting` | bài đăng, tìm khách, cho thuê, viết bài, phòng trống, tiện ích, quảng cáo, marketing, đăng tin, facebook, zalo, chợ tốt | AIDA framework, social media best practices for Vietnamese rental market, attention-grabbing headlines |
| `sql_best_practices` | danh sách, tra cứu, sql, phòng, hóa đơn, hợp đồng, bảo trì, trạng thái, chi tiết, mã phòng, chỉ số, điện nước, khách thuê, người thuê, liệt kê, thống kê, số liệu | MySQL column naming conventions, JOIN patterns, performance optimization tips, common pitfalls |

**Dynamic Skill Selection Algorithm:**
1. Question is lowercased and split into words
2. Each word is matched against keyword groups for each skill package
3. All matching skill packages are loaded from `skills/<name>/SKILL.md`
4. Skill content is appended to the `HARNESS_SYSTEM_PROMPT` with a separator
5. If no skills match, `financial_analysis` is loaded as default

### 2.3 Context Compaction & History Management

The agent loop implements a **semantic compaction strategy** to handle multi-turn conversations within Gemini's context window limits:

```python
@staticmethod
def _compact_context_if_needed(history: str, max_turns: int = 8) -> str:
    if not history:
        return ""
    turns = history.strip().split("\n")
    if len(turns) <= max_turns * 2:
        return history

    # Semantic summarization: extract key topics from old turns
    old_turns = turns[:-8]
    recent_turns = turns[-8:]
    old_questions = []
    for t in old_turns:
        if t.startswith("User:") or t.startswith("Q:"):
            old_questions.append(t.split(":", 1)[-1].strip()[:80])
    question_summary = "; ".join(old_questions[-5:]) if old_questions else "các câu hỏi trước"
    summary_line = f"[TÓM TẮT ({len(old_turns)//2} lượt thoại trước): {question_summary}]"
    return summary_line + "\n" + "\n".join(recent_turns)
```

**Compaction Strategy:**
- **Threshold:** 8 turns (4 full Q&A pairs)
- **Old turns (>8):** Summarized into a single line with extracted user question topics
- **Recent turns (last 8):** Preserved verbatim for immediate context
- **Question extraction:** Only `User:` and `Q:` prefixes are scanned to avoid extracting AI responses

### 2.4 Gemini Model Fallback Cascade

The system implements a **two-tier model cascade** with automatic fallback on rate limits or errors:

```mermaid
flowchart TD
    START["API Request"] --> CHECK{"ModelRegistry<br/>check_available()"}

    CHECK -->|"RPM OK & RPD OK"| PRIMARY["Try Primary Model<br/>gemini-3.5-flash-lite<br/>temperature=0.2"]
    CHECK -->|"Rate Limited"| PRIMARY_RETRY_EXHAUSTED

    PRIMARY --> SUCCESS{"Success?"}
    SUCCESS -->|"Yes"| DONE["✅ Record call, Return response"]
    SUCCESS -->|"No"| RETRY{"Retry < 2?"}

    RETRY -->|"Yes"| BACKOFF["Exponential Backoff<br/>wait = 2^attempt + 1s"]
    BACKOFF --> PRIMARY

    RETRY -->|"No"| PRIMARY_RETRY_EXHAUSTED
    PRIMARY_RETRY_EXHAUSTED --> FALLBACK_CHECK{"Fallback model<br/>gemini-3.1-flash-lite<br/>configured?"}

    FALLBACK_CHECK -->|"Yes"| WAIT["Sleep 1s (cool-off)"]
    WAIT --> FALLBACK["Try Fallback Model<br/>gemini-3.1-flash-lite"]
    FALLBACK --> FB_SUCCESS{"Success?"}
    FB_SUCCESS -->|"Yes"| DONE_FB["✅ Record fallback call, Return response"]
    FB_SUCCESS -->|"No"| FB_ERROR["❌ Raise last exception"]

    FALLBACK_CHECK -->|"No"| RAISE["❌ Raise RuntimeError"]
```

**Model Registry Specifications:**

| Model | RPM | TPM | RPD | Priority | Role |
|-------|-----|-----|-----|----------|------|
| `gemini-3.5-flash-lite` | 30 | 500,000 | 1,500 | 1 (primary) | Main reasoning engine |
| `gemini-3.1-flash-lite` | 30 | 500,000 | 1,500 | 2 (fallback) | Failover on rate limits |

**API Key Resolution Chain:**
1. `settings.GEMINI_API_KEY` (from `.env` file)
2. `os.environ.get("GOOGLE_API_KEY")` (environment fallback)
3. If neither: `ValueError("CHƯA CẤU HÌNH GEMINI_API_KEY")` — fails fast at agent loop start

### 2.5 Error Recovery & Self-Healing

```mermaid
flowchart LR
    subgraph Tool_Errors["🛠️ Tool Error Recovery"]
        TE["Tool Execution Error"] --> IS_RETRY{"Retry count < 3?"}
        IS_RETRY -->|"Yes"| BACKOFF["Exponential Backoff<br/>2^attempt + 1s"]
        BACKOFF --> RETRY_EXEC["Retry tool execution"]
        RETRY_EXEC --> IS_RETRY

        IS_RETRY -->|"No"| RAISE_ERR["Raise RuntimeError"]
    end

    subgraph LLM_Errors["🧠 LLM Error Recovery"]
        LE["LLM Call Error"] --> IS_RETRY_L{"Retry < 2?"}
        IS_RETRY_L -->|"Yes"| BACKOFF_L["Exponential Backoff"]
        BACKOFF_L --> RETRY_L["Retry primary model"]
        RETRY_L --> IS_RETRY_L

        IS_RETRY_L -->|"No"| FALLBACK_L["Try fallback model"]
        FALLBACK_L --> FB_RESULT{"Success?"}
        FB_RESULT -->|"Yes"| DONE_FB_L["✅ Return result"]
        FB_RESULT -->|"No"| RAISE_LAST["Raise last exception"]
    end

    subgraph Max_Steps["⚠️ Max Steps Graceful Degradation"]
        MS["Step = 10"] --> EXTRACT["Extract last model text<br/>from message history"]
        EXTRACT --> HAS_TEXT{"Has text > 30 chars?"}
        HAS_TEXT -->|"Yes"| RETURN_PARTIAL["Return partial reply<br/>type: MAX_STEPS"]
        HAS_TEXT -->|"No"| GENERIC["Return generic message"]
    end

    subgraph DB_Errors["🗄️ Database Error Handling"]
        DE["DB Connection Failed"] --> OFFLINE["Tool returns DATABASE_OFFLINE"]
        OFFLINE --> LLM_HANDLE["LLM informs user: system under maintenance"]
    end
```

**Error Recovery Strategies:**

| Error Type | Recovery Strategy | Max Retries |
|-----------|-------------------|-------------|
| Tool execution error | Exponential backoff: `2^attempt + 1` seconds | 2 (3 total attempts) |
| LLM API error | Exponential backoff + model fallback | 2 per model |
| Rate limit (primary) | Immediate fallback to secondary model | 0 retries on primary |
| Database offline | Graceful error message to user via LLM | N/A (informational) |
| Max agent steps (10) | Extract partial response from last model turn | N/A (degradation) |

### 2.6 Tool Definitions & Function Calling Contract

```mermaid
flowchart TB
    subgraph Schema["📐 Function Declaration Contract"]
        KPI_DEF["get_kpi_overview<br/>Input: {landlord_id: int, period: string}<br/>Output: KPIObject JSON<br/>Purpose: Pre-computed financial metrics"]
        SQL_DEF["execute_sql_query<br/>Input: {sql_query: string, landlord_id: int}<br/>Output: {status, row_count, columns, data}<br/>Purpose: Ad-hoc data queries"]
        PY_DEF["execute_dynamic_python_script<br/>Input: {code: string}<br/>Output: {execution_status, output}<br/>Purpose: Complex calculations"]
        MKT_DEF["generate_marketing_post<br/>Input: {room_number, base_price, ...}<br/>Output: {marketing_post}<br/>Purpose: AIDA rental copy"]
    end

    subgraph Dispatch["🔀 Dispatcher"]
        DISPATCHER["dispatch_tool(tool_name, args, landlord_id)"]
        DISPATCHER -->|"get_kpi_overview"| KPI_IMPL
        DISPATCHER -->|"execute_sql_query"| SQL_IMPL
        DISPATCHER -->|"execute_dynamic_python_script"| PY_IMPL
        DISPATCHER -->|"generate_marketing_post"| MKT_IMPL
    end
```

**Tool Output Contract:**

```python
# Successful SQL query
{
    "status": "SUCCESS",
    "row_count": 5,
    "columns": ["room_code", "remaining_amount", "due_date"],
    "data": [{"room_code": "501", "remaining_amount": 4500000, "due_date": "2026-06-15"}]
}

# Empty result (zero hallucination policy)
{
    "status": "SUCCESS",
    "row_count": 0,
    "data": [],
    "note": "Không có dữ liệu — KHÔNG ĐƯỢC BỊA SỐ LIỆU."
}

# SQL error with self-correction
{
    "error": "Lỗi SQL: Unknown column 'phone_number'...",
    "sql_attempted": "SELECT phone_number FROM users...",
    "self_correct_hint": "Hãy sửa câu SQL dựa trên lỗi trên và thử lại."
}

# Database offline
{
    "error": "DATABASE_OFFLINE",
    "warning": "CSDL hiện không khả dụng. Vui lòng thông báo cho người dùng rằng hệ thống đang bảo trì."
}
```


---



## 3. INTENT FILTERING & DOMAIN CLASSIFICATION

### 3.1 Out-of-Domain Detection Algorithm

```mermaid
flowchart TD
    Q["💬 User Question"] --> STRIP["Strip Vietnamese accents<br/>(á→a, đ→d, ê→e, etc.)"]
    STRIP --> DOMAIN_CHECK{"Contains domain keywords?<br/>doanh thu, chi phi, loi nhuan,<br/>no, phong, hoa don, bao cao,<br/>kpi, lap day, khach thue, ..."}

    DOMAIN_CHECK -->|"Yes ✅"| PASS_DOMAIN["In-domain → Proceed"]

    DOMAIN_CHECK -->|"No ❌"| OOD_CHECK{"Matches out-of-domain<br/>pattern?"}

    OOD_CHECK -->|"Politics"| POL["❌ chinh tri, bau cu, dang, cong san"]
    OOD_CHECK -->|"Security"| SEC["❌ hack, crack, exploit, inject"]
    OOD_CHECK -->|"Superstition"| SUP["❌ boi toan, tu vi, phong thuy"]
    OOD_CHECK -->|"Chat"| SOC["❌ chat, tan gau, hen ho, thoi tiet"]
    OOD_CHECK -->|"Coding"| CODE["❌ code, viet code, lap trinh app<br/>(unless SQL/bao cao context)"]

    OOD_CHECK -->|"No match"| LEN_CHECK{"Length < 2 chars?"}
    LEN_CHECK -->|"Yes ❌"| SHORT["Too short → Reject"]
    LEN_CHECK -->|"No"| DEFAULT_PASS["Default: In-domain (conservative)"]

    POL & SEC & SUP & SOC & CODE & SHORT --> REJECT["Reject with OOD message"]
    REJECT --> RESP["Xin lỗi, tôi là AI Trợ lý Tài chính & Vận hành Nhà trọ..."]
```

**Domain Keywords (30 terms):**
```
doanh thu, chi phi, loi nhuan, no, phong, hoa don, bao cao, kpi, lap day,
khach thue, cho thue, bao tri, dien, nuoc, tien, hop dong, dong tien,
tai chinh, suc khoe, thang, ky, tro, nha tro, chu nha
```

**Rejection Response:**
> "Xin lỗi, tôi là AI Trợ lý Tài chính & Vận hành Nhà trọ. Tôi chỉ có thể trả lời các câu hỏi về doanh thu, chi phí, công nợ, tỉ lệ lấp đầy, bảo trì phòng trọ và các vấn đề vận hành nhà trọ. Vui lòng đặt câu hỏi liên quan."

### 3.2 Intent Inference via Tool Selection

The system uses a **two-tier classification approach** — a fast rule-based filter (Tier 1) followed by implicit classification via tool selection (Tier 2):

| Intent | Tools Likely Called | Example Questions |
|--------|---------------------|-------------------|
| FINANCIAL_OVERVIEW | `get_kpi_overview` | "Báo cáo tài chính tháng này" |
| REVENUE_ANALYSIS | `get_kpi_overview`, `execute_sql_query` | "Doanh thu từ tiền phòng bao nhiêu?" |
| EXPENSE_ANALYSIS | `get_kpi_overview`, `execute_sql_query` | "Chi phí điện nước tháng này?" |
| DEBT_ANALYSIS | `execute_sql_query` | "Phòng nào nợ nhiều nhất?" |
| OCCUPANCY_ANALYSIS | `execute_sql_query` | "Tỉ lệ lấp đầy hiện tại?" |
| MARKETING | `generate_marketing_post` | "Viết bài đăng tìm khách phòng 401" |
| CALCULATION | `execute_dynamic_python_script` | "Tính chi phí cơ hội phòng trống" |

---

## 4. SUGGESTION & PROACTIVE ANALYSIS ENGINE

### 4.1 Suggested Questions Service (LLM + Fallback)

```mermaid
flowchart TB
    REQ["GET /copilot/suggestions"] --> GET_KPI["Get KPIObject for period"]
    GET_KPI --> HAS_KPI{"KPI exists?"}

    HAS_KPI -->|"No"| FALLBACK_MIXED["Return default mixed questions"]
    HAS_KPI -->|"Yes"| LLM_ATTEMPT["Try Gemini LLM with SUGGESTION_PROMPT"]

    LLM_ATTEMPT --> LLM_SUCCESS{"Valid JSON array<br/>with ≥ 3 items?"}

    LLM_SUCCESS -->|"Yes ✅"| RETURN_LLM["Return LLM-generated questions (max 8)"]
    LLM_SUCCESS -->|"Exception/Invalid"| RULE_FALLBACK["Rule-based fallback"]

    RULE_FALLBACK --> QUESTIONS["Select questions based on KPI anomalies:"]
    QUESTIONS --> Q1["if revenue change > 5% → 'Vì sao tăng/giảm X%?'"]
    QUESTIONS --> Q2["if overdue_count > 0 → 'Nếu thu hồi hết Yđ công nợ...'"]
    QUESTIONS --> Q3["if occupancy change < -1% → 'Tỉ lệ lấp đầy giảm...'"]
    QUESTIONS --> Q4["if maintenance > 30% → 'Chi phí sửa chữa...'"]
    QUESTIONS --> Q5["if collection_rate < 80% → 'Tỷ lệ thu tiền đang thấp...'"]
    QUESTIONS --> DEFAULTS["Add 4 default questions"]
    DEFAULTS --> RETURN_RULE["Return rule-based questions (max 8)"]
```

**LLM Prompt for Suggestion Generation:**

```python
SUGGESTION_PROMPT = """Bạn là AI Financial Copilot. Dựa vào KPI dưới đây, hãy đề xuất 5-8 câu hỏi phân tích:

KPI hiện tại:
- Doanh thu: {revenue} ({revenue_growth})
- Chi phí: {expense} ({expense_growth})
- Lợi nhuận ròng: {profit}
- Công nợ: {debt} ({overdue_count} hóa đơn quá hạn)
- Tỷ lệ thu tiền: {collection_rate}%
- Tỉ lệ lấp đầy: {occupancy_rate}% ({occupied_rooms}/{total_rooms} phòng)

Yêu cầu:
1. Câu hỏi phải đi sâu vào biến động
2. Đa dạng: so sánh, nguyên nhân, dự báo
3. Ưu tiên các chỉ số bất thường
4. Trả về JSON array: ["câu hỏi 1", "câu hỏi 2", ...]"""
```

---



## 5. API REFERENCE & ENDPOINT MAP

### 5.1 Complete API Topology

```mermaid
flowchart LR
    subgraph Gateway["🚪 API Gateway"]
        BASE["Base: /api/v1/advisor"]
        AUTH["Deps: landlord_id (Query), period (default: current month)"]
    end

    subgraph KPI["📊 KPI Analytics (6 endpoints)"]
        KO["GET /kpi/overview — Full KPIObject + cached AI report"]
        KR["GET /kpi/revenue — Revenue breakdown + 12m history"]
        KE["GET /kpi/expense — Expense breakdown + 12m history"]
        KD["GET /kpi/debt — Debt aging + per-room detail + warnings"]
        KOC["GET /kpi/occupancy — Occupancy rate + 12m trend"]
        KEX["GET /kpi/export?format=json|excel — Full export"]
    end

    subgraph AI["🤖 AI Copilot (12 endpoints)"]
        CA["POST /copilot/ask<br/>Multi-turn Agent Loop"]
        CR["POST /copilot/report<br/>AI Financial Report (cached)"]
        CRF["POST /copilot/report/refresh<br/>Force regenerate"]
        CRX["GET /copilot/report/export-docx<br/>Word (.docx) download"]
        CS["POST /copilot/session<br/>Create session"]
        CSH["GET /copilot/session/{id}<br/>Session history"]
        CSU["GET /copilot/suggestions<br/>Suggested questions"]
        CSA["GET /copilot/analysis<br/>Proactive KPI analysis"]
        EVAL["GET /copilot/eval<br/>AI + Model + Cache stats"]
        EVAL_LOG["GET /copilot/eval/logs<br/>Recent eval logs"]
        SQL_STATS["GET /copilot/sql-cache/stats<br/>SQL cache statistics"]
        ZALO["POST /copilot/send-zalo<br/>Zalo dispatch (stub)"]
    end

    subgraph SYS["⚙️ System"]
        H["GET /health — Health check"]
        UI["GET /ui — Web dashboard"]
    end

    Gateway --> KPI & AI & SYS
    AI --> RATE_LIMIT["Rate Limited: 30/60s"]
```

### 5.2 Core AI Endpoint Specifications

| Method | Path | Input | Output | Rate Limited | Cache |
|--------|------|-------|--------|--------------|-------|
| `POST` | `/copilot/ask` | `{question, session_id?}` | `{reply, session_id, suggestions, type}` | Yes | Session + SQL |
| `POST` | `/copilot/report` | `landlord_id, period, force?` | `{report, from_cache, cache_version}` | Yes | AI Report (versioned) |
| `POST` | `/copilot/report/refresh` | `landlord_id, period` | `{report, cache_version}` | Yes | Invalidates + regen |
| `GET` | `/copilot/report/export-docx` | `landlord_id, period` | Word `.docx` file | Yes | AI Report |
| `POST` | `/copilot/session` | `landlord_id` | `{session_id}` | No | Session Store |
| `GET` | `/copilot/session/{id}` | `session_id` | `{history}` | No | Session + DB |
| `GET` | `/copilot/suggestions` | `landlord_id, period` | `{questions[]}` | Yes | Analysis (1h) |
| `GET` | `/copilot/analysis` | `landlord_id, period` | `{analyses[]}` | No | Analysis (1h) |
| `GET` | `/copilot/eval` | — | `{ai_stats, model_stats, sql_cache}` | No | No |

---

## 6. DEPLOYMENT ARCHITECTURE

### 6.1 Docker Compose Topology

```mermaid
graph TB
    subgraph Internet["🌐 Internet"]
        USER["👤 User Browser"]
        GEMINI["☁️ Google Gemini API"]
    end

    subgraph Docker_Host["🐳 Docker Host"]
        subgraph Network["🌐 Bridge Network"]
            APP["App Container<br/>Port: 8000 → Host: 8080<br/>uvicorn main:app"]
            DB["MySQL Container<br/>mysql:8.0<br/>Port: 3306"]
        end

        subgraph Volumes["💾 Volumes"]
            V_DB["mysql_data → /var/lib/mysql"]
        end

        subgraph ENV["🔐 Environment"]
            E_DB["DATABASE_URL=mysql://root:password@mysql:3306/hdbhms"]
            E_GEMINI["GEMINI_API_KEY=AIzaSy..."]
            E_MODEL["GEMINI_MODEL=gemini-3.5-flash-lite"]
            E_FALLBACK["GEMINI_FALLBACK_MODEL=gemini-3.1-flash-lite"]
            E_RATE["RATE_LIMIT_REQUESTS=30, RATE_LIMIT_WINDOW=60"]
            E_CACHE["CACHE_TYPE=memory"]
        end
    end

    USER -->|"HTTP :8080"| APP
    APP -->|"MySQL :3306"| DB
    APP -->|"HTTPS"| GEMINI
    DB --> V_DB
    APP -.-> ENV
    DB -.-> ENV
```

### 6.2 Environment Configuration

```ini
# === Database ===
DATABASE_URL=mysql://root:password@mysql:3306/hdbhms

# === Google Gemini AI ===
GEMINI_API_KEY=AIzaSyYourApiKeyHere
GEMINI_MODEL=gemini-3.5-flash-lite
GEMINI_FALLBACK_MODEL=gemini-3.1-flash-lite
GEMINI_TEMPERATURE=0.0
GEMINI_TIMEOUT=120.0

# === FastAPI Server ===
API_HOST=0.0.0.0
API_PORT=8000
API_WORKERS=1
LOG_LEVEL=INFO
ENVIRONMENT=production

# === Rate Limiting ===
RATE_LIMIT_ENABLED=True
RATE_LIMIT_REQUESTS=30
RATE_LIMIT_WINDOW=60

# === Caching ===
CACHE_TYPE=memory
REDIS_URL=
```

