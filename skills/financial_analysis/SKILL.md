---
name: financial_analysis
description: Tri thức chuyên sâu về phân tích tài chính nhà trọ, đánh giá sức khỏe KPI, phân tích lợi nhuận và thu hồi công nợ.
---

# QUÁ TRÌNH PHÂN TÍCH TÀI CHÍNH NHÀ TRỌ

## 1. ĐÁNH GIÁ ĐIỂM SỨC KHỎE (HEALTH SCORE 0-100)
- **>= 80 (EXCELLENT):** Lợi nhuận ròng dương, lấp đầy >= 90%, công nợ < 5% tổng doanh thu.
- **60-79 (GOOD):** Hoạt động ổn định, lấp đầy 75-89%, công nợ 5-15%.
- **40-59 (WARNING):** Tỷ lệ chi phí/doanh thu > 70%, công nợ quá hạn tăng, phòng trống > 25%.
- **< 40 (CRITICAL):** Dòng tiền âm, công nợ xấu > 20%, lấp đầy < 60%. Cần can thiệp khẩn cấp!

## 2. NGUYÊN TẮC PHÂN TÍCH DOANH THU & CHI PHÍ
- Doanh thu bao gồm 5 nguồn: Tiền phòng (ROOM_RENT), Điện (ELECTRICITY), Nước (WATER), Phí dịch vụ (SERVICE_FEE), Phụ thu (OTHER).
- Tiền phòng thường chiếm 70-85% tổng doanh thu. Nếu tỉ lệ dịch vụ quá cao (> 30%), cần kiểm tra đơn giá điện nước.
- Chi phí vận hành bao gồm: Chi phí bảo trì sửa chữa, điện nước đầu vào, thuế, phí quản lý.

## 3. CHIẾN LƯỢC XỬ LÝ CÔNG NỢ
- Ưu tiên 1: Các phòng nợ > 60 ngày hoặc tiền nợ > 2 tháng tiền nhà.
- Đề xuất giải pháp: Gửi thông báo nhắc nợ -> Áp dụng phạt chậm nộp -> Tạm ngưng dịch vụ -> Thanh lý hợp đồng.
