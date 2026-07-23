"""
Benchmark Test Suite for Super Complex Real-World Property Queries
Runs 5 complex multi-table SQL queries against `database/test_data_final.db`
"""
import sys
import os
import sqlite3
import json

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8')

DB_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "database", "test_data_final.db"))


class SQLiteTestRunner:
    @staticmethod
    def query(sql: str) -> list:
        if not os.path.exists(DB_PATH):
            return [{"error": "DB file not found"}]
        
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        try:
            cursor.execute(sql)
            rows = cursor.fetchall()
            conn.close()
            return [dict(r) for r in rows]
        except Exception as e:
            conn.close()
            return [{"error": str(e)}]


COMPLEX_BENCHMARK_CASES = [
    {
        "id": "CASE_01",
        "category": "Ma Trận Phòng & Định Giá",
        "question": "Cho biết ma trận trạng thái tất cả các phòng hiện tại (VACANT, OCCUPIED), diện tích m2 và giá thuê niêm yết?",
        "sql": """
            SELECT r.room_number, r.status, r.base_price, r.area_sqm 
            FROM rooms r 
            ORDER BY r.room_number;
        """
    },
    {
        "id": "CASE_02",
        "category": "Multi-Join Hợp Đồng & Khách Thêu",
        "question": "Danh sách hợp đồng đang hoạt động kèm thông tin phòng, họ tên khách thuê, SĐT và thời hạn hợp đồng?",
        "sql": """
            SELECT r.room_number, t.full_name, t.phone, c.contract_number, c.start_date, c.end_date, c.rent_price
            FROM contracts c
            JOIN rooms r ON c.room_id = r.id
            JOIN tenants t ON c.tenant_id = t.id
            WHERE c.status = 'ACTIVE';
        """
    },
    {
        "id": "CASE_03",
        "category": "Chi Tiết Doanh Thu & Khoản Mục Hóa Đơn",
        "question": "Thống kê chi tiết tiền nhà, tiền dịch vụ và tổng tiền của từng hóa đơn theo phòng?",
        "sql": """
            SELECT r.room_number, b.invoice_number, b.rent_amount, b.service_amount, b.total_amount, b.paid_amount, b.status
            FROM bills b
            JOIN rooms r ON b.room_id = r.id
            ORDER BY r.room_number;
        """
    },
    {
        "id": "CASE_04",
        "category": "Multi-Join Hóa Đơn Nợ & Khách Nợ",
        "question": "Liệt kê các hóa đơn chưa thanh toán hoặc nợ tiền, kèm tên khách thuê, phòng và số tiền còn nợ?",
        "sql": """
            SELECT r.room_number, t.full_name, b.invoice_number, b.total_amount, b.remaining_amount, b.due_date
            FROM bills b
            JOIN rooms r ON b.room_id = r.id
            JOIN tenants t ON b.tenant_id = t.id
            WHERE b.remaining_amount > 0 OR b.status IN ('UNPAID', 'OVERDUE', 'PARTIALLY_PAID');
        """
    },
    {
        "id": "CASE_05",
        "category": "Gom Nhóm & Tính Tỉ Lệ Nợ/Doanh Thu Theo Phòng",
        "question": "Tổng hợp doanh thu đã thu vs công nợ theo từng phòng, sắp xếp theo phòng nợ nhiều nhất?",
        "sql": """
            SELECT r.room_number, 
                   SUM(b.total_amount) AS total_billed, 
                   SUM(b.paid_amount) AS total_paid, 
                   SUM(b.remaining_amount) AS total_debt
            FROM bills b
            JOIN rooms r ON b.room_id = r.id
            GROUP BY r.room_number
            ORDER BY total_debt DESC;
        """
    }
]


def run_benchmark():
    print("==========================================================")
    print("🚀 BẮT ĐẦU BENCHMARK 5 CÂU HỎI THỰC TẾ SIÊU PHỨC TẠP")
    print(f"CSDL Thực tế: {DB_PATH}")
    print("==========================================================")
    
    success_count = 0
    total_rows_retrieved = 0
    
    for c in COMPLEX_BENCHMARK_CASES:
        print(f"\n📌 [{c['id']}] {c['category']}")
        print(f"❓ Câu hỏi: {c['question']}")
        
        rows = SQLiteTestRunner.query(c["sql"])
        if rows and "error" not in rows[0]:
            success_count += 1
            total_rows_retrieved += len(rows)
            print(f"✅ Executed Successfully! Output ({len(rows)} rows):")
            print(f"   Sample Row: {json.dumps(rows[0], ensure_ascii=False)}")
        else:
            err = rows[0].get("error") if rows else "No rows returned"
            print(f"❌ SQL Execution Error: {err}")

    print("\n==========================================================")
    print(f"📊 KẾT QUẢ BENCHMARK CHÍNH THỨC:")
    print(f"   - Tỉ lệ thực thi SQL thành công: {success_count}/{len(COMPLEX_BENCHMARK_CASES)} ({success_count/len(COMPLEX_BENCHMARK_CASES)*100:.1f}%)")
    print(f"   - Tổng số dòng dữ liệu truy vấn thực tế: {total_rows_retrieved}")
    print("==========================================================")


if __name__ == "__main__":
    run_benchmark()
