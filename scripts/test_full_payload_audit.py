"""
Test Full Communication & Payload Audit Logging
Triggers questions and prints the complete JSON log payloads recorded in `static/logs/full_server_audit.jsonl`.
"""
import asyncio
import json
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8')

async def test_full_payload_audit():
    from src.harness.agent_loop import HarnessAgentLoop
    from src.harness.payload_logger import PayloadAuditLogger

    print("==========================================================")
    print("🚀 GỬI CÂU HỎI VÀ KIỂM TRA CHỈ SỐ LOG PAYLOAD TOÀN BỘ SERVER")
    print("==========================================================")

    res = await HarnessAgentLoop.run(
        question="Phân tích tình hình tài chính và liệt kê danh sách các phòng đang nợ tiền trong kỳ 2026-06?",
        landlord_id=1,
        period="2026-06"
    )

    print("\n----------------------------------------------------------")
    print("📋 DỮ LIỆU AUDIT PAYLOAD ĐÃ LOG LƯU VÀO FILE static/logs/full_server_audit.jsonl:")
    print("----------------------------------------------------------")
    logs = PayloadAuditLogger.read_all_logs(limit=1)
    if logs:
        print(json.dumps(logs[-1], ensure_ascii=False, indent=2))
    else:
        print("Chưa có log entry.")

if __name__ == "__main__":
    asyncio.run(test_full_payload_audit())
