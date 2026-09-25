# BÁO CÁO PIPELINE GIAI ĐOẠN 1: BASELINE RAG & DATA OBSERVABILITY
**Ngày thực thi:** 2026-09-25 09:19:29 UTC  
**Môi trường:** ChromaDB Vector Index + Great Expectations 1.x + SentenceTransformers

---

## 1. TỔNG QUAN NGUỒN DỮ LIỆU (DATA INGESTION)
- **Nguồn dữ liệu:** Crossref API (`agentic retrieval augmented generation large language model`)
- **Tổng số bản ghi raw tải về:** 24
- **Số bản ghi sau tiền xử lý làm sạch (Cleaned):** 24
- **Định dạng Text embedding:** 5 trường chuẩn hóa (`Title`, `Authors`, `Published`, `Categories`, `Summary`).

---

## 2. KẾT QUẢ KIỂM SOÁT CHẤT LƯỢNG (DATA QUALITY GATE - GREAT EXPECTATIONS)
- **Trạng thái cổng chất lượng:** ✅ ĐẠT (PASS)
- **Tổng số kiểm tra:** 6 (6 đạt, 0 lỗi)

| Kiểm tra (Expectation) | Cột | Kết quả |
| :--- | :--- | :---: |
| `expect_table_row_count_to_be_between` | `table` | ✅ Đạt |
| `expect_column_values_to_not_be_null` | `paper_id` | ✅ Đạt |
| `expect_column_values_to_be_unique` | `paper_id` | ✅ Đạt |
| `expect_column_values_to_not_be_null` | `title` | ✅ Đạt |
| `expect_column_values_to_not_be_null` | `text_for_embedding` | ✅ Đạt |
| `expect_column_value_lengths_to_be_between` | `summary` | ✅ Đạt |


---

## 3. QUAN SÁT TÍNH TƯƠI MỚI DỮ LIỆU (DATA FRESHNESS OBSERVABILITY)
- **Tổng số tài liệu:** 24
- **Số tài liệu cũ (Stale rows > 180 ngày):** 0
- **Tỷ lệ tài liệu tươi mới:** 100.0%
- **Đạt SLA tươi mới (>= 75.0%):** ✅ ĐẠT
- **Khoảng thời gian xuất bản:** từ `2026-04-01` đến `2026-09-15`

---

## 4. HIỆU SUẤT TRUY VẤN VÀ ĐÁNH GIÁ RAG (BASELINE RETRIEVAL & EVALUATION)
Đánh giá trên bộ câu hỏi kiểm thử chuẩn (10 câu hỏi thuộc 4 nhóm nghiệp vụ):

| Chỉ số đánh giá | Giá trị Baseline |
| :--- | :---: |
| **Retrieval Hit Rate** | 1.0000 |
| **Mean Token F1** | 1.0000 |
| **Judge Accuracy** | 1.0000 |
| **Mean Judge Score** | 5.0000 |


---

## 5. KẾT LUẬN & SẴN SÀNG CHO GIAI ĐOẠN CORRUPTION
Dữ liệu Baseline đã vượt qua toàn bộ các bài kiểm tra chất lượng của Great Expectations và đạt chỉ số truy vấn cao trên ChromaDB. Hệ thống đã sẵn sàng làm chuẩn đối chuẩn (Gold Baseline) cho thử nghiệm gây lỗi nhân tạo (Phase 2 - Synthetic Corruption).
