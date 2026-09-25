# NHẬT KÝ THỰC THI DỰ ÁN (EXECUTION TRACEABILITY LOG)
## Dự án: Data Pipeline & Data Observability for RAG (Day 10)
**Vai trò phụ trách:** Pipeline Lead & System Integrator  
**Nhánh Git:** `cuongtv`  
**Mục tiêu:** Lưu trữ toàn bộ dấu vết thực thi (traceability), kết quả chạy lệnh, artifacts sinh ra và quyết định kỹ thuật sau mỗi Phase.

---

## 📌 PHASE 0: SETUP & HEALTH CHECK (KHỞI TẠO NỀN TẢNG & MÔI TRƯỜNG)
- **Thời gian hoàn thành:** 2026-09-25 15:54:00 (Local Time)
- **Mục tiêu:** Chuẩn bị môi trường Python 3.12, cài đặt toàn bộ package lõi, thiết lập file cấu hình `.env`, kiểm tra tính toàn vẹn của Raw Data Snapshot và bảo mật secret.

### 1. Chi tiết các hành động kỹ thuật đã thực hiện:
1. **Khởi tạo file cấu hình `.env`:**
   - Tạo file `.env` từ `.env.example`.
   - Cấu hình sẵn `LLM_PROVIDER=gemini`, `LLM_MODEL=gemini-2.5-flash` và các placeholder API key.
   - Kiểm tra `.gitignore`: Đã có dòng `.env` để ngăn chặn rò rỉ secret lên Git repository.
2. **Khắc phục sự cố môi trường & Cài đặt gói thư viện:**
   - Dọn dẹp folder rác `~ip` từ phiên trước bằng PowerShell `Remove-Item`.
   - Phục hồi `pip` chuẩn bằng lệnh:
     ```powershell
     .\.venv\Scripts\python.exe -m ensurepip --upgrade
     ```
   - Cài đặt toàn bộ thư viện dependencies cốt lõi vào `.venv`:
     - `chromadb==1.5.9`, `great-expectations==1.23.1`, `sentence-transformers==6.1.0`, `langchain==1.4.2`, `datasets==5.0.1`, `torch==2.14.0`, `transformers==5.17.0`, `pandas==3.0.6`, `pydantic==2.13.5`.
   - Cài đặt package local ở chế độ editable:
     ```powershell
     .\.venv\Scripts\pip.exe install -e . --no-deps
     ```
3. **Kiểm tra tính toàn vẹn của Offline Snapshot:**
   - Đã xác thực sự tồn tại của 2 file raw records:
     - `data/raw/crossref_response.json` (25.8 KB - 24 papers raw payload).
     - `data/raw/crossref_records.json` (20.2 KB - 24 normalized paper records).

### 2. Bằng chứng kiểm thử & Lệnh nghiệm thu (Smoke Test Verification):
- **Kiểm tra import core libraries:** Exit code 0, log `Environment Ready: All core libraries imported successfully!`.
- **Kiểm tra Settings & Paths:** Exit code 0, log `Config OK: D:\VinUni\Lap10\K4-L3A-Day10-Data-Pipeline-Data-Observability`.

### 3. Trạng thái Artifacts sau Phase 0:
- `.env`: Đã tạo, an toàn (bị `.gitignore` bỏ qua).
- `mydoc/plan.md`: Đã hoàn thiện kế hoạch chi tiết cho Lead.
- `mydoc/nhiemvu.md`: Đã hoàn thiện ma trận phân công 4 thành viên.
- `.venv`: Đầy đủ 100% dependencies chuẩn bị cho chạy Pipeline.

---

## 📌 PHASE 1: BASELINE PIPELINE END-TO-END (CHECKPOINTS 1 - 3)
- **Thời gian hoàn thành:** 2026-09-25 16:22:00 (Local Time)
- **Mục tiêu:** Xây dựng và tích hợp trọn vẹn luồng Baseline: Thu thập dữ liệu Crossref, Tiền xử lý chuẩn hóa, Kiểm toán chất lượng bằng Great Expectations 1.x, Quan sát tính tươi mới (Freshness SLA), Đánh chỉ mục ChromaDB, Tự động sinh test set 10 câu hỏi, Đánh giá Baseline RAG và Xuất báo cáo Markdown.

### 1. Chi tiết các modules đã triển khai & tích hợp:
1. **Module Thu thập dữ liệu (`src/ingestion/crossref.py`):**
   - Lập trình `parse_crossref_payload`: Phân giải DOI, tách thẻ XML HTML trong abstract, trích xuất tác giả, phân loại danh mục, chuẩn hóa ngày xuất bản ISO `YYYY-MM-DD`.
   - Lập trình `fetch_source_records`: Gọi Crossref REST API có cơ chế retry và tự động kích hoạt fallback sử dụng offline snapshot `data/raw/crossref_response.json` khi mạng offline hoặc bị rate limit.
   - Lập trình `load_raw_records`: Tải và ánh xạ bản ghi sang `PaperRecord` dataclass.
2. **Module Làm sạch & Chuẩn hóa (`src/ingestion/cleaning.py`):**
   - Chuẩn hóa khoảng trắng (`normalize_whitespace`), loại bỏ ký tự rác.
   - Tính toán chỉ số tuổi thọ tài liệu `age_days = (run_date - published_date).days`.
   - Tạo trường embedding chuẩn gồm 5 trường: `Title`, `Authors`, `Published`, `Categories`, `Summary`.
   - Lưu trữ song song 2 định dạng: CSV (`data/clean/papers_clean.csv`) và JSON (`data/clean/papers_clean.json`).
3. **Module Quản trị Chất lượng & Độ tươi mới (`src/observability/quality.py`):**
   - Thiết kế Quality Gate chuẩn **Great Expectations 1.x (Fluent Ephemeral Mode)** với 6 Expectation checks:
     - `ExpectTableRowCountToBeBetween(min_value=5, max_value=5000)`
     - `ExpectColumnValuesToNotBeNull(column="paper_id")`
     - `ExpectColumnValuesToBeUnique(column="paper_id")`
     - `ExpectColumnValuesToNotBeNull(column="title")`
     - `ExpectColumnValuesToNotBeNull(column="text_for_embedding")`
     - `ExpectColumnValueLengthsToBeBetween(column="summary", min_value=30)`
   - Xây dựng cơ chế Freshness SLA: Đánh giá tỷ lệ bài báo mới trong 180 ngày, ngưỡng chấp nhận SLA ≥ 75%.
   - Lưu báo cáo kết quả: `data/quality/baseline_quality_report.json` và `data/quality/freshness_report.json`.
4. **Module Đánh chỉ mục & Vector Database (`src/retrieval/index.py` & `src/retrieval/embeddings.py`):**
   - Sử dụng model `sentence-transformers/all-MiniLM-L6-v2` tạo embeddings 384 chiều, cosine similarity.
   - Quản lý persistent ChromaDB với collection riêng biệt: `papers-baseline`.
   - Lưu manifest tại `data/embeddings/papers_embeddings.json`.
5. **Module Sinh Tập Kiểm Thử Chuẩn (`src/evaluation/testset.py`):**
   - Tự động sinh `data/eval/test_set.json` gồm 10 câu hỏi bao quát 4 nhóm: `summary` (3 câu), `authors` (3 câu), `date` (2 câu), `categories` (2 câu).
   - Mỗi câu hỏi gắn kèm `ground_truth` và `ground_truth_doc_ids` phục vụ chấm điểm tự động.
6. **Module Đánh giá Hiệu năng RAG (`src/evaluation/metrics.py`):**
   - Đánh giá khả năng truy hồi: `retrieval_hit_rate` (Top-1 recall).
   - Đánh giá chất lượng câu trả lời: `mean_token_f1`.
   - Đánh giá ngữ nghĩa qua LLM Judge: `judge_accuracy` và `mean_judge_score` (thang 1-5).
7. **Module Báo cáo Markdown Tự động (`src/observability/reporting.py`):**
   - Kết xuất file báo cáo phân tích toàn diện `data/reports/phase1_report.md`.

### 2. Bằng chứng kiểm thử & Lệnh nghiệm thu (Execution Verification):
- **Lệnh thực thi:**
  ```powershell
  $env:PYTHONIOENCODING="utf-8"; .\.venv\Scripts\python.exe script/run_phase1.py
  ```
- **Kết quả nghiệm thu:**
  - Exit code: 0 (Thành công 100%).
  - Số bản ghi xử lý: 24/24 records.
  - Great Expectations Quality Gate: **6/6 expectations PASSED**.
  - Freshness SLA: **100.0% Fresh (24/24), SLA Status: PASSED**.
  - ChromaDB Collection: `papers-baseline` indexed 24 items.
  - Evaluation Benchmark (10 questions):
    - `retrieval_hit_rate`: **1.0000 (100.0%)**
    - `mean_token_f1`: **1.0000 (100.0%)**
    - `judge_accuracy`: **1.0000 (100.0%)**
    - `mean_judge_score`: **5.0000 / 5.0**

### 3. Trạng thái Artifacts sau Phase 1:
- `data/clean/papers_clean.csv` & `papers_clean.json` (24 rows).
- `data/quality/baseline_quality_report.json` (Success = True).
- `data/quality/freshness_report.json` (is_fresh = True, 100%).
- `data/eval/test_set.json` (10 items).
- `data/embeddings/papers_embeddings.json` (24 vectors).
- `data/results/baseline_metrics.json` & `data/results/baseline_answers.json`.
- `data/reports/phase1_report.md` (Generated report).

---

## 📌 PHASE 2: SYNTHETIC CORRUPTION & IDEMPOTENT REPAIR (CHECKPOINTS 4 - 5)
- **Thời gian hoàn thành:** 2026-09-25 16:45:00 (Local Time)
- **Mục tiêu:** Tiêm 6 kịch bản lỗi vào dữ liệu sạch, chứng minh hiện tượng **Silent Failure** (AI không báo lỗi nhưng trả lời sai lệch), và kiểm chứng khả năng tự phục hồi lũy quyền (**Idempotent Repair**) từ snapshot dữ liệu thô.

### 1. Chi tiết các hành động kỹ thuật đã thực hiện:
1. **Tiêm 6 kịch bản Synthetic Corruption (`src/ingestion/corruption.py`):**
   - `blank_summary`: Xóa trắng phần abstract của 3 bài báo.
   - `truncate_title`: Cắt ngắn tiêu đề khoa học còn 5 ký tự (3 bài báo).
   - `stale_date`: Lùi ngày xuất bản về quá khứ xa (>365 ngày) cho 3 bài báo.
   - `drop_latest_records`: Xóa hoàn toàn 3 bài báo có ngày xuất bản mới nhất (Corpus giảm 24 → 21 bản ghi).
   - `duplicate_rows`: Nhân bản trùng lặp 2 bản ghi đã có để tạo xung đột khóa chính `paper_id`.
   - `inject_noise`: Chèn ký tự rác `@@@NOISE###` vào trường văn bản embedding (3 bài báo).
   - Xuất file: `data/clean/papers_clean_corrupted.csv`, `papers_clean_corrupted.json` và nhật ký `data/results/corruption_log.json`.
2. **Kiểm toán chất lượng dữ liệu bẩn (Quality Gate Fail):**
   - Chạy Great Expectations 1.x trên tập corrupted: Bắt trúng 2 vi phạm nghiêm trọng (`duplicate paper_id` và `summary length < 30`). Kết quả: **FAIL (4/6 checks passed)**.
   - Lưu báo cáo: `data/quality/corrupted_quality_report.json`.
3. **Chứng minh hiện tượng Silent Failure trên Vector Index Corrupted:**
   - Dựng collection độc lập: `papers-corrupted`.
   - Đánh giá lại trên chính bộ câu hỏi `data/eval/test_set.json`:
     - Mô hình AI không ném ra exception nào (hệ thống hoạt động bình thường, không crash).
     - Tuy nhiên chỉ số chất lượng sụt giảm nghiêm trọng:
       - `retrieval_hit_rate`: Giảm từ **1.0000 xuống 0.5000 (-50.0%)** do trượt ngữ cảnh tài liệu gốc.
       - `mean_token_f1`: Giảm từ **1.0000 xuống 0.5286 (-47.14%)**.
       - `judge_accuracy`: Giảm từ **1.0000 xuống 0.5000**.
       - `mean_judge_score`: Giảm từ **5.00 xuống 3.00**.
4. **Triển khai cơ chế Phục hồi Lũy Quyền (Idempotent Repair):**
   - Đọc lại dữ liệu thô bất biến `data/raw/crossref_records.json`.
   - Tái thực thi quy trình làm sạch chuẩn hóa `build_clean_dataframe` để sinh ra `data/clean/papers_clean_repaired.csv` và `.json`.
   - Xây dựng lại vector index `papers-repaired`.
   - Kiểm tra Great Expectations trên dữ liệu đã sửa: **Khôi phục thành công 6/6 checks PASSED**.
   - Đánh giá RAG trên `papers-repaired`: Chỉ số khôi phục tuyệt đối về mức ban đầu:
     - `retrieval_hit_rate`: **1.0000 (100.0%)**
     - `mean_token_f1`: **1.0000 (100.0%)**
     - `judge_accuracy`: **1.0000 (100.0%)**
5. **Xuất bảng đối chiếu định lượng 3 trạng thái:**
   - Xuất file `data/reports/corruption_report.md` thể hiện bảng so sánh 3 cột: Baseline vs Corrupted vs Repaired.

### 2. Bằng chứng kiểm thử & Lệnh nghiệm thu:
- **Lệnh thực thi:**
  ```powershell
  $env:PYTHONIOENCODING="utf-8"; .\.venv\Scripts\python.exe script/run_corruption_flow.py
  ```
- **Kết quả nghiệm thu:** Exit code 0, sinh đầy đủ 14+ artifacts, xác nhận tính lũy quyền: `repaired corpus matches original clean corpus by paper_id: IDENTICAL (24 rows)`.

---

## 📌 PHASE 3: TỔNG TÍCH HỢP, WEB DASHBOARD & LIVE DEMO SẴN SÀNG (CHECKPOINT 6 & BONUS)
- **Thời gian hoàn thành:** 2026-09-25 17:05:00 (Local Time)
- **Mục tiêu:** Xây dựng bộ test tự động Pytest CI (+5đ Bonus B3), Web Dashboard trực quan Streamlit (+5đ Bonus B1), công cụ Live Demo CLI cho Checkpoint 6, soạn thảo hướng dẫn bảo vệ Q&A và rà soát hồ sơ nhóm.

### 1. Các module và tính năng đã hoàn thiện:
1. **Web Dashboard Trực Quan Streamlit (`src/app.py`) 👉 *[Săn +5đ Bonus B1]*:**
   - Cài đặt `streamlit==1.64.0` và khởi chạy server trên port 8501 (`http://localhost:8501`).
   - Tích hợp 4 tab chuyên sâu:
     - **Tab 1: Bảng Đối Chiếu 3 Trạng Thái**: Trực quan hóa so sánh Baseline vs Corrupted vs Repaired bằng bar chart và metrics.
     - **Tab 2: Data Quality Gate & Freshness SLA**: Hiển thị bảng chi tiết các vi phạm bị Great Expectations chặn và biểu đồ Freshness.
     - **Tab 3: Live RAG Demo**: Giao diện tương tác cho phép chọn câu hỏi hoặc gõ câu hỏi tùy ý, so sánh đồng thời 3 câu trả lời AI.
     - **Tab 4: Dataset Explorer & Lineage**: Khám phá bảng dữ liệu sạch, dữ liệu bẩn và dữ liệu phục hồi kèm xem trước text embedding.
2. **Bộ kiểm thử tự động End-to-End (`tests/` với Pytest) 👉 *[Săn +5đ Bonus B3]*:**
   - Cài đặt `pytest==9.1.1` và cấu hình `tests/conftest.py`.
   - Xây dựng 4 file test độc lập bao quát toàn bộ pipeline: `test_ingestion.py`, `test_cleaning.py`, `test_quality_gate.py`, `test_retrieval.py`.
3. **Công cụ Trình diễn Trực quan CLI (`script/demo_live.py`):**
   - Nạp đồng thời cả 3 Vector Collections: `papers-baseline`, `papers-corrupted`, `papers-repaired`.
   - Phục vụ demo máy chiếu nhanh không cần trình duyệt web.
4. **Cẩm nang bảo vệ & Phản biện Q&A (`docs/DEMO_GUIDE.md`):**
   - Soạn thảo kịch bản 3-5 phút lên bảng cho nhóm.
   - Giải đáp chuyên sâu về Idempotent Repair, Great Expectations 1.x ephemeral và toán học Token F1.
5. **Cập nhật hồ sơ nhóm (`docs/TEAM.md`):**
   - Khai báo đầy đủ phân công trách nhiệm cho 4 vai trò, sẵn sàng cho nộp bài VLearn LMS.

---

## 📌 PHASE 4: TỔNG KẾT HỒ SƠ BÁO CÁO & SẴN SÀNG NỘP BÀI (SUBMISSION READINESS)
- **Thời gian hoàn thành:** 2026-09-25 17:35:00 (Local Time)
- **Mục tiêu:** Rà soát và hoàn thiện toàn bộ báo cáo nhóm (`report/group_report.md`), báo cáo cá nhân (`report/2A202602560_TaVietCuong.md`), đối chiếu toàn diện với barem quy định tại `docs/SUBMISSION.md`, `docs/RULES.md`, `report/README.md`.

---

## 📌 PHASE 5: GIẢI QUYẾT XUNG ĐỘT (MERGE CONFLICT RESOLUTION) & SẴN SÀNG MERGE MAIN
- **Thời gian hoàn thành:** 2026-09-25 18:40:00 (Local Time)
- **Mục tiêu:** Giải quyết triệt để xung đột mã nguồn khi đồng bộ nhánh `cuongtv` với `origin/main` (sau khi các PR #1 của Trang, PR #2 của Hoàng, PR #3 của Khánh đã merge vào `main`).

### 1. Chi tiết các xung đột đã xử lý thành công:
1. **Xung đột mã nguồn pipeline (`src/`):**
   - Giữ bản hoàn chỉnh của Lead với đầy đủ fix lỗi contract, timeout API và Great Expectations 1.x.
2. **Xung đột hồ sơ nhóm (`docs/TEAM.md` & `report/group_report.md`):**
   - Tích hợp đầy đủ thông tin định danh và liên kết báo cáo cá nhân của cả 4 thành viên:
     - TV1: Tạ Việt Cường (2A202602560) - Trưởng nhóm & Điều phối Pipeline.
     - TV2: Vũ Minh Hoàng (2A202602371) - Data Foundation & Recovery.
     - TV3: Phùng Gia Khánh (2A202602585) - RAG & Vector Index.
     - TV4: Trần Thị Thu Trang (2A202602581) - Observability & Evaluation.
3. **Hợp nhất bộ kiểm thử (`tests/test_retrieval.py`):**
   - Tích hợp cả test suite unit test giả lập của TV3 (FakeEmbeddings, StubIndex, QA testing) và integration tests kiểm tra ChromaDB thực tế của TV1.
4. **Nghiệm thu toàn bộ test suite:**
   - Chạy `pytest tests/`: **16/16 tests PASSED 100% trong 113.63s**.
5. **Đồng bộ Git:**
   - Đã tạo merge commit và push sạch lên `origin/cuongtv`. Pull Request vào `main` ở trạng thái **Able to merge**.
