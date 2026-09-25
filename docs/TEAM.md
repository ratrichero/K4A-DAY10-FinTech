# Danh Sách Thành Viên & Báo Cáo Phân Công Nhóm

- **Tên Nhóm:** `FinTech`
- **Mã Nhóm / Lớp:** `K4-L3`
- **Tên Repository Nộp Bài:** `K4A-DAY10-FinTech`
- **GitHub URL:** `https://github.com/ratrichero/K4A-DAY10-FinTech`

---

## # Thành viên

| STT | Họ và tên | MSSV | Email | Vai trò & Phân công công việc | Báo cáo cá nhân |
|---:|---|---|---|---|---|
| 1 | Tạ Việt Cường | 2A202602560 | ratrichero@gmail.com | Trưởng nhóm / Pipeline Integrator (`core/`, `phase1.py`, `corruption_flow.py`, `tests/`) | [`report/2A202602560_TaVietCuong.md`](../report/2A202602560_TaVietCuong.md) |
| 2 | Vũ Minh Hoàng | 2A202602371 | minhhoangvu111@gmail.com | Data Foundation & Recovery (`crossref.py`, `cleaning.py`, raw data) | [`report/2A202602371_VuMinhHoang.md`](../report/2A202602371_VuMinhHoang.md) |
| 3 | Phùng Gia Khánh | 2A202602585 | phunggiakhanh030405@gmail.com | RAG & Vector Index (`retrieval/index.py`, `embeddings.py`, ChromaDB) | [`report/2A202602585_PhungGiaKhanh.md`](../report/2A202602585_PhungGiaKhanh.md) |
| 4 | Trần Thị Thu Trang | 2A202602581 | trangdhsp@gmail.com | Observability & Evaluation (`quality.py` GX 1.x, `testset.py`, reporting) | [`report/2A202602581_TranThiThuTrang.md`](../report/2A202602581_TranThiThuTrang.md) |

---

## # Cá nhân

### ## TaVietCuong-2A202602560
- **Vai trò:** Trưởng nhóm & Điều phối Pipeline (Pipeline Lead & System Integrator).
- **Công việc chi tiết đã hoàn thành:**
  - Thiết lập cấu hình hệ thống `core/config.py` và đường dẫn artifacts `core/utils.py`.
  - Kết nối luồng thực thi trong `src/pipelines/phase1.py` và `src/pipelines/corruption_flow.py`.
  - Viết bộ tự động hóa kiểm thử `tests/` với 8 bài unit test pytest đạt tỷ lệ pass 100% (Bonus B3: +5đ).
  - Xây dựng ứng dụng Web Demo Studio tương tác bằng Streamlit tại `src/app.py` và bộ launcher `start_app.bat` (Bonus B1: +5đ).
  - Soạn thảo báo cáo nhóm `report/group_report.md` và tài liệu hướng dẫn bảo vệ `docs/DEMO_GUIDE.md`.
- **Điều học được / Đóng góp chính:**
  - Hiểu sâu sắc về thiết kế Idempotent Pipeline, cơ chế kiểm soát chất lượng Great Expectations 1.x và ngăn chặn hiện tượng Silent Failure trong các hệ thống RAG thực tế.

### ## VuMinhHoang-2A202602371
- **Vai trò:** Phụ trách Ingestion, Làm sạch & Phục hồi dữ liệu.
- **Công việc chi tiết đã hoàn thành:**
  - Xây dựng module thu thập Crossref API với cơ chế Fallback offline trong `src/ingestion/crossref.py`.
  - Chuẩn hóa schema, tính toán trường `age_days` và `text_for_embedding` trong `src/ingestion/cleaning.py`.
  - Thực thi cơ chế Idempotent Repair phục hồi dữ liệu từ raw snapshot.
- **Điều học được / Đóng góp chính:**
  - Kỹ thuật truy vết nguồn gốc dữ liệu (Data Lineage) và bảo toàn raw snapshot trước khi biến đổi.

### ## Phùng Gia Khánh — 2A202602585
- **Vai trò:** Phụ trách RAG, Vector Database & Embedding.
- **Công việc chi tiết đã hoàn thành:**
  - Quản lý mô hình embedding `sentence-transformers/all-MiniLM-L6-v2`.
  - Nạp và quản lý 3 collection riêng biệt trong ChromaDB (`papers-baseline`, `papers-corrupted`, `papers-repaired`).
  - Xây dựng QA Agent truy vấn ngữ cảnh chính xác theo tài liệu.
- **Điều học được / Đóng góp chính:**
  - Cách cô lập các không gian vector để so sánh khách quan giữa dữ liệu sạch và dữ liệu bị lỗi.

### ## TranThiThuTrang-2A202602581
- **Vai trò:** Phụ trách Data Observability & Benchmark Evaluation.
- **Công việc chi tiết đã hoàn thành:**
  - Thiết lập Quality Gate theo chuẩn mới **Great Expectations 1.x** và giám sát Freshness SLA trong `src/observability/quality.py`.
  - Xây dựng bộ câu hỏi đánh giá chuẩn trong `src/evaluation/testset.py`.
  - Đo lường và xuất bảng đối chiếu 3 trạng thái vào `data/reports/corruption_report.md`.
- **Điều học được / Đóng góp chính:**
  - Cách thiết lập hệ thống cảnh báo sớm chặn đứng hiện tượng Silent Failure trước khi dữ liệu vào serving layer.
