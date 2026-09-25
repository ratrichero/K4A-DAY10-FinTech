# BÁO CÁO THỬ NGHIỆM GÂY LỖI & PHỤC HỒI DỮ LIỆU (SYNTHETIC CORRUPTION & REPAIR REPORT)
**Mục tiêu:** Chứng minh thực nghiệm hiện tượng Silent Failure (RAG trả lời sai do dữ liệu bẩn) và hiệu quả của cơ chế Idempotent Repair.

---

## 1. SO SÁNH HIỆU SUẤT TRUY VẤN RAG (3-WAY COMPARISON)

| Chỉ số | 1. Baseline | 2. Corrupted | 3. Repaired | Biến thiên (Corrupted vs Baseline) |
| :--- | :---: | :---: | :---: | :---: |
| **Retrieval Hit Rate** | 1.0000 | 0.5000 | 1.0000 | -0.5000 |
| **Mean Token F1** | 1.0000 | 0.5286 | 1.0000 | -0.4714 |
| **Judge Accuracy** | 1.0000 | 0.5000 | 1.0000 | -0.5000 |
| **Mean Judge Score** | 5.0000 | 3.0000 | 5.0000 | -2.0000 |

---

## 2. QUAN SÁT TẠI CỔNG CHẤT LƯỢNG (DATA QUALITY GATES)
- **Tập Corrupted:** Trạng thái ❌ BỊ CHẶN (FAIL) - Phát hiện 2 lỗi vi phạm chất lượng dữ liệu (4/6 kiểm tra đạt).
- **Tập Repaired:** Trạng thái ✅ ĐẠT - Toàn bộ các vi phạm đã được khôi phục chuẩn xác.

---

## 3. KẾT LUẬN THỰC NGHIỆM
1. **Silent Failure được xác nhận:** Khi dữ liệu bị nhiễm bẩn (title rỗng, summary bị cắt xén, ngày tháng bị đảo lộn), mô hình AI vẫn sinh câu trả lời mà không báo lỗi runtime, nhưng độ chính xác (Hit@1 và Token F1) sụt giảm nghiêm trọng.
2. **Cổng kiểm soát Great Expectations hoạt động hiệu quả:** Đã bắt trúng toàn bộ các điểm bất thường trước khi nạp vào vector store.
3. **Cơ chế Idempotent Repair thành công:** Sau khi phục hồi, các chỉ số đánh giá đã quay trở lại tiệm cận mức Baseline ban đầu.
