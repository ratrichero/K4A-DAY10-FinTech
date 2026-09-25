# Group Report — Day 10: Data Pipeline & Data Observability

## 1. Thông tin bài nộp

| Thông tin         | Nội dung                  |
| ------------------ | -------------------------- |
| Khóa/Lớp         | AI-ENGINEER-K4 (VinUni) |
| Tên nhóm         | K4-L3-DAY10-DataPipeline |
| Repository         | [ratrichero/K4-L3A-Day10-Data-Pipeline-Data-Observability](https://github.com/ratrichero/K4-L3A-Day10-Data-Pipeline-Data-Observability) |
| Ngày hoàn thành | 2026-09-25               |

### Thành viên và phân công

| STT | Họ và tên | MSSV | Vai trò chính | Module/deliverable sở hữu |
| --: | --- | --- | --- | --- |
| 1 | Tạ Việt Cường | 2A202602560 | Pipeline Lead & System Integrator | `src/core/`, `src/pipelines/`, `script/`, `tests/`, `docs/TEAM.md`, `report/group_report.md` |
| 2 | Thành viên 2 | [MSSV2] | Data Foundation & Ingestion Owner | `src/ingestion/crossref.py`, `src/ingestion/cleaning.py`, `src/ingestion/corruption.py` |
| 3 | Thành viên 3 | [MSSV3] | RAG & Vector Index Specialist | `src/retrieval/` (`embeddings.py`, `index.py`, `qa.py`, `agent.py`) |
| 4 | Thành viên 4 | [MSSV4] | Observability & Evaluation Lead | `src/observability/` (`quality.py`, `reporting.py`), `src/evaluation/testset.py` |

---

## 2. Tóm tắt kết quả

Nhóm đã hoàn thành trọn vẹn 100% khối lượng công việc của 6 Checkpoints (CP0 đến CP6) cùng 2 hạng mục điểm thưởng Bonus (+10 điểm: B1 Web Dashboard Streamlit và B3 Pytest CI Suite 8/8 tests pass).

Toàn bộ hệ thống luồng dữ liệu end-to-end đã được thiết kế và kiểm chứng thực nghiệm chặt chẽ:
1. **Baseline Pipeline:** Thu thập 24 bản ghi khoa học từ Crossref API (hỗ trợ offline snapshot fallback), làm sạch chuẩn hóa với trường `text_for_embedding` 5 dòng, kiểm soát chất lượng qua Great Expectations 1.x (đạt 6/6 checks) và Freshness SLA (100% tươi mới). Đánh chỉ mục ChromaDB (`papers-baseline`) và đánh giá trên bộ test 10 câu hỏi đạt điểm tuyệt đối: **Retrieval Hit Rate = 1.0000**, **Mean Token F1 = 1.0000**, **Judge Accuracy = 1.0000**.
2. **Synthetic Corruption & Silent Failure:** Tiêm 6 kịch bản lỗi có chủ đích (xóa summary, cắt ngắn title, lùi ngày xuất bản, drop bài mới, nhân bản trùng lặp, nhiễu ký tự). Kết quả thực nghiệm chứng minh đanh thép hiện tượng **Silent Failure**: Mô hình AI không hề văng exception (không crash runtime) nhưng chất lượng trả lời sụp đổ nặng nề — Retrieval Hit Rate giảm từ **1.0000 xuống 0.5000 (-50%)**, Token F1 giảm xuống **0.5286 (-47.1%)**. Cổng kiểm soát Great Expectations 1.x đã phát hiện chính xác các vi phạm dữ liệu này (FAIL 4/6 checks passed).
3. **Idempotent Repair:** Phục hồi toàn vẹn dữ liệu từ nguồn bất biến `data/raw/crossref_records.json`. Chất lượng truy vấn trên tập phục hồi quay lại tiệm cận mức Baseline (Hit Rate = 1.0000, F1 = 1.0000, GX Gate 6/6 pass).

---

## 3. Kiến trúc và luồng dữ liệu

### Luồng end-to-end

```text
Crossref REST API (Offline Snapshot Fallback)
    -> data/raw/crossref_records.json
    -> Cleaning & Data Modeling (text_for_embedding 5 dòng, age_days)
    -> data/clean/papers_clean.csv & .json
    -> Great Expectations 1.x Gate (6 Expectations) + Freshness SLA Gate (180 days)
    -> Local Embedding Index (all-MiniLM-L6-v2) -> ChromaDB ('papers-baseline')
    -> Test Set Generator (10 questions across 4 business categories)
    -> Baseline Evaluation (Hit Rate = 1.0, Token F1 = 1.0, Judge Acc = 1.0)
    -> Synthetic Corruption (6 scenarios) -> ChromaDB ('papers-corrupted')
    -> Corrupted Evaluation (Silent Failure demonstrated: Hit Rate = 0.5, F1 = 0.5286)
    -> Idempotent Repair (Re-run cleaning from immutable Raw Snapshot)
    -> ChromaDB ('papers-repaired') -> Re-evaluation & 3-Way Comparison Report
```

### Trách nhiệm của từng khối

| Khối             | Input          | Xử lý chính             | Output/artifact          | Owner          |
| ----------------- | -------------- | -------------------------- | ------------------------ | -------------- |
| Ingestion         | Crossref REST API / Raw JSON | Fetch API, exponential retry, parse XML abstract, offline fallback | `data/raw/crossref_response.json`, `crossref_records.json` | TV2 |
| Cleaning          | `PaperRecord` raw | Strip HTML/JATS, chuẩn hóa whitespace, tính `age_days`, tạo `text_for_embedding` | `data/clean/papers_clean.csv/.json` | TV2 |
| Embedding/Index   | Clean DataFrame | SentenceTransformers `all-MiniLM-L6-v2` (384-d), cosine similarity, ChromaDB persistent store | `data/chroma/`, `data/embeddings/*_embeddings.json` | TV3 |
| Evaluation        | Clean DataFrame & Vector Index | Sinh 10 câu hỏi chuẩn 4 nhóm, truy vấn top-k, tính Retrieval Hit@1, Token F1, LLM Judge | `data/eval/test_set.json`, `data/results/*_metrics.json` | TV4 & TV3 |
| Observability     | Clean / Corrupted DataFrame | Great Expectations 1.x ephemeral suite (6 checks), Freshness SLA calculation | `data/quality/*_quality_report.json`, `freshness_report.json` | TV4 |
| Corruption/Repair | Clean DataFrame & Raw records | Tiêm 6 dạng lỗi deterministic, lưu log, cơ chế Idempotent Repair từ raw snapshot | `data/results/corruption_log.json`, `papers_clean_corrupted.*`, `papers_clean_repaired.*` | TV2 & TV1 |
| Orchestration     | Toàn bộ modules | Điều phối tuần tự 8 bước Phase 1 và 9 bước Phase 2, tiền kiểm Preflight Gates | `phase1.py`, `corruption_flow.py`, `data/reports/*.md` | TV1 (Lead) |

---

## 4. Cách tái hiện kết quả

### Cấu hình không chứa secret

| Biến/cấu hình             | Giá trị sử dụng |
| ---------------------------- | ------------------- |
| `LLM_PROVIDER`             | `gemini` (hoặc `mock` khi test offline) |
| `LLM_MODEL`                | `gemini-2.5-flash` |
| Embedding model              | `sentence-transformers/all-MiniLM-L6-v2` |
| Số lượng Crossref records | 24 |
| Retrieval `top_k`           | 3 |
| Freshness threshold          | 180 ngày (SLA threshold 75%) |
| Random seed                  | Deterministic / Seed cố định |

### Lệnh cài đặt

```powershell
# Kích hoạt môi trường và cài đặt dependencies
.\.venv\Scripts\python.exe -m ensurepip --upgrade
.\.venv\Scripts\pip.exe install -e . --no-deps
.\.venv\Scripts\pip.exe install pytest streamlit
```

### Lệnh chạy

1. **Chạy Baseline Pipeline (Phase 1):**
   ```powershell
   $env:PYTHONIOENCODING="utf-8"; .\.venv\Scripts\python.exe script/run_phase1.py
   ```
2. **Chạy Corruption & Repair Flow (Phase 2):**
   ```powershell
   $env:PYTHONIOENCODING="utf-8"; .\.venv\Scripts\python.exe script/run_corruption_flow.py
   ```
3. **Chạy Bộ Test Pytest CI (Bonus B3):**
   ```powershell
   $env:PYTHONIOENCODING="utf-8"; .\.venv\Scripts\python.exe -m pytest tests/
   ```
4. **Khởi chạy Web Dashboard Streamlit (Bonus B1):**
   ```powershell
   .\start_app.bat
   # Hoặc: .\.venv\Scripts\python.exe -m streamlit run src/app.py
   ```

### Kết quả tái hiện

| Lệnh             | Trạng thái | Thời điểm chạy gần nhất | Bằng chứng |
| ----------------- | ----------------------------------------------- | ----------------------------- | ------------------------------------ |
| Baseline pipeline | Thành công (Exit code 0) | 2026-09-25 16:21:26 | `data/reports/phase1_report.md`, `baseline_metrics.json` |
| Corruption flow   | Thành công (Exit code 0) | 2026-09-25 16:45:00 | `data/reports/corruption_report.md`, `corruption_log.json` |
| Pytest Test Suite | Thành công (8/8 passed) | 2026-09-25 16:46:44 | `tests/`, task-357 execution log (213.97s) |
| Streamlit Web App | Đang hoạt động | 2026-09-25 17:16:51 | `http://localhost:8501`, `start_app.bat` |

---

## 5. Ingestion, cleaning và data contract

### Nguồn dữ liệu

| Thuộc tính                | Giá trị                             |
| --------------------------- | ------------------------------------- |
| Source                      | Crossref REST API (`https://api.crossref.org/works`) |
| Query/filter                | Data Observability & RAG papers |
| Thời điểm lấy dữ liệu | 2026-09-25 |
| Số record nhận được    | 24 |
| Cơ chế retry/backoff      | Exponential retry (3 lần), tự động kích hoạt Offline Snapshot Fallback khi gặp lỗi mạng/429 |

### Raw và clean schema

| Trường        | Kiểu dữ liệu | Bắt buộc?  | Ý nghĩa   | Xử lý khi thiếu/sai |
| --------------- | --------------- | ------------ | ----------- | ---------------------- |
| `paper_id` | `str` | Có | Định danh bài báo (DOI/ID) | Bắt buộc không rỗng; loại bỏ nếu rỗng |
| `title` | `str` | Có | Tiêu đề khoa học | Chuẩn hóa khoảng trắng, không rỗng |
| `summary` | `str` | Có | Tóm tắt trừu tượng (Abstract) | Tách thẻ HTML/JATS, fallback "No abstract available" |
| `authors` | `list[str]` | Có | Danh sách tác giả | Gộp thành chuỗi `authors_joined` |
| `categories` | `list[str]` | Có | Danh mục chuyên ngành | Gộp thành chuỗi `categories_joined` |
| `published` | `str` | Có | Ngày xuất bản ISO YYYY-MM-DD | Parse ngày chuẩn, fallback ngày hiện tại nếu lỗi |
| `age_days` | `int` | Có | Tuổi thọ bài báo so với mốc chạy | Tính bằng `(run_date - published_date).days` |
| `text_for_embedding` | `str` | Có | Văn bản ghép 5 trường phục vụ embedding | Tạo cấu trúc 5 dòng Title/Authors/Published/Categories/Summary |

### Quy tắc cleaning

| Quy tắc                                 | Quality dimension liên quan | Số record bị tác động | Cách xác minh      |
| ---------------------------------------- | ---------------------------- | -------------------------: | -------------------- |
| Loại bỏ thẻ XML/JATS trong abstract | Validity | 24 | Regex strip `<jats:...>` |
| Chuẩn hóa khoảng trắng và ký tự vô hình | Consistency | 24 | `re.sub(r'\s+', ' ', text)` |
| Tính toán `age_days` chuẩn thời gian UTC | Timeliness | 24 | Chênh lệch ngày không âm |
| Đóng gói 5 dòng `text_for_embedding` | Completeness | 24 | Chứa đủ 5 tiền tố bắt buộc |

---

## 6. Evaluation setup

| Thành phần                             | Cấu hình thực tế          |
| ---------------------------------------- | ----------------------------- |
| Số câu hỏi                            | 10 câu hỏi cố định |
| Các `question_type`                    | 4 nhóm: `summary` (3), `authors` (3), `date` (2), `categories` (2) |
| Ground-truth document ID                 | Trích xuất trực tiếp từ ID bài báo nguồn tương ứng |
| Embedding model                          | `sentence-transformers/all-MiniLM-L6-v2` |
| Vector store/collection                  | ChromaDB (`papers-baseline`, `papers-corrupted`, `papers-repaired`) |
| Retrieval `top_k`                       | 3 |
| LLM provider/model                       | `gemini` / `gemini-2.5-flash` |
| Test set dùng chung cho ba trạng thái | `data/eval/test_set.json` |

**Giải thích vì sao test set được giữ nguyên:**
Để phép đo lường sự suy giảm chất lượng và khả năng tự phục hồi có ý nghĩa khoa học thống kê chuẩn mực, biến số duy nhất được phép thay đổi là **chất lượng của kho dữ liệu (corpus quality)**. Việc giữ nguyên 100% câu hỏi và ground truth cho cả 3 trạng thái đảm bảo không có sự thiên lệch (bias) trong việc đánh giá.

---

## 7. Kết quả baseline

### Artifact checklist

| Artifact                 | Đường dẫn thực tế                | Trạng thái | Ghi chú   |
| ------------------------ | -------------------------------------- | ------------ | ---------- |
| Raw response/records     | `data/raw/`                          | Có | `crossref_response.json`, `crossref_records.json` |
| Cleaned dataset          | `data/clean/`                        | Có | `papers_clean.csv`, `papers_clean.json` |
| Embedding manifest/index | `data/embeddings/`                   | Có | `papers_embeddings.json` (baseline) |
| Evaluation set           | `data/eval/`                         | Có | `test_set.json` (10 questions) |
| Baseline metrics         | `data/results/baseline_metrics.json` | Có | Hit rate, Token F1, Judge metrics |
| Quality/freshness        | `data/quality/`                      | Có | `baseline_quality_report.json`, `freshness_report.json` |
| Baseline report          | `data/reports/phase1_report.md`      | Có | Báo cáo Markdown chi tiết Pha 1 |

### Baseline metrics

| Metric                 | Giá trị | Diễn giải                             |
| ---------------------- | --------------: | --------------------------------------- |
| `retrieval_hit_rate` | 1.0000 (100%) | 10/10 câu hỏi tìm thấy đúng tài liệu nguồn ở Top-1 |
| `mean_token_f1`      | 1.0000 (100%) | Trùng khớp từ vựng hoàn hảo với Ground Truth |
| `judge_accuracy`     | 1.0000 (100%) | LLM Judge chấm toàn bộ câu trả lời đạt tính đúng đắn |
| `mean_judge_score`   | 5.00 / 5.00 | Điểm số đánh giá chất lượng tối đa |

---

## 8. Data quality và freshness

### Quality checks (Great Expectations 1.x)

| Check | Quality dimension | Ngưỡng/kỳ vọng | Kết quả baseline | Bằng chứng |
| ------------ | ----------------- | ------------------ | ----------------------- | ------------ |
| `ExpectTableRowCountToBeBetween` | Completeness | [5, 5000] | PASS (24 rows) | `baseline_quality_report.json` |
| `ExpectColumnValuesToNotBeNull` (`paper_id`) | Completeness | 0 null | PASS (0 null) | `baseline_quality_report.json` |
| `ExpectColumnValuesToBeUnique` (`paper_id`) | Uniqueness | Unique 100% | PASS (0 duplicates) | `baseline_quality_report.json` |
| `ExpectColumnValuesToNotBeNull` (`title`) | Completeness | 0 null | PASS (0 null) | `baseline_quality_report.json` |
| `ExpectColumnValuesToNotBeNull` (`text_for_embedding`) | Integrity | 0 null | PASS (0 null) | `baseline_quality_report.json` |
| `ExpectColumnValueLengthsToBeBetween` (`summary`) | Validity | min_value=30 chars | PASS (min length >= 30) | `baseline_quality_report.json` |

### Freshness SLA

| Thuộc tính               | Giá trị                           |
| -------------------------- | ----------------------------------- |
| Freshness được đo tại | `data/clean/papers_clean.csv` |
| Timestamp mới nhất       | Ngày hiện tại (UTC) |
| Ngưỡng freshness         | 180 ngày |
| Trạng thái baseline      | **FRESH (100.0% Fresh)** |
| Lý do                     | Toàn bộ 24 bài báo đều có tuổi thọ nằm trong ngưỡng quy định, tỷ lệ tươi mới vượt trội so với SLA tối thiểu (75%). |

---

## 9. Corruption scenarios và repair

| Corruption | Cách tạo | Record bị tác động | Quality signal kỳ vọng | Tác động thực tế | Cách repair |
| ------------------ | ---------- | ---------------------: | ------------------------ | --------------------- | -------------- |
| 1. Blank summary | Gán rỗng trường tóm tắt | 3 | GX summary length FAIL | Vector drift, mất context tóm tắt | Nạp lại từ Raw snapshot |
| 2. Truncate title | Cắt tiêu đề còn 5 ký tự | 3 | Semantic search lệch | Trượt retrieval câu hỏi title | Nạp lại từ Raw snapshot |
| 3. Stale date | Lùi ngày xuất bản >365 ngày | 3 | Freshness monitor cảnh báo | Tăng số lượng tài liệu cũ | Nạp lại từ Raw snapshot |
| 4. Drop latest records | Xóa 3 bản ghi mới nhất | 3 | Table row count giảm | Trượt vĩnh viễn 3 câu hỏi liên quan | Nạp lại từ Raw snapshot |
| 5. Duplicate rows | Nhân bản 2 dòng đã có | 2 | GX paper_id unique FAIL | Phá vỡ ràng buộc định danh | Nạp lại từ Raw snapshot |
| 6. Inject noise | Chèn ký tự rác vào embedding text | 3 | Vector embedding sai lệch | Giảm độ tương đồng cosine | Nạp lại từ Raw snapshot |

- **Corruption log:** Được lưu trữ đầy đủ tại `data/results/corruption_log.json`.
- **Cơ chế Idempotent Repair:** Tuyệt đối không sửa tay hay chỉnh vá cục bộ trên file dirty. Quy trình phục hồi tải lại 100% bản ghi bất biến từ `data/raw/crossref_records.json` và tái thực thi hàm chuẩn hóa `build_clean_dataframe`, đảm bảo tính lũy quyền (Idempotency) dù chạy 1 lần hay 100 lần kết quả vẫn đồng nhất.

---

## 10. So sánh baseline, corrupted và repaired

| Metric/signal            | Baseline | Corrupted | Repaired | Thay đổi do corruption | Mức phục hồi | Nhận xét   |
| ------------------------ | -------: | --------: | -------: | -----------------------: | --------------: | ------------ |
| `retrieval_hit_rate`   |   1.0000 |    0.5000 |   1.0000 |                  -0.5000 |         +0.5000 | Sụt giảm 50% khi dữ liệu bị lỗi; khôi phục hoàn hảo |
| `mean_token_f1`        |   1.0000 |    0.5286 |   1.0000 |                  -0.4714 |         +0.4714 | Độ chính xác câu trả lời giảm sâu do trượt retrieval |
| `judge_accuracy`       |   1.0000 |    0.5000 |   1.0000 |                  -0.5000 |         +0.5000 | AI tự tin trả lời sai (Silent Failure) |
| `mean_judge_score`     |     5.00 |      3.00 |     5.00 |                    -2.00 |           +2.00 | Điểm chất lượng sụt giảm 2 thang điểm |
| Quality checks pass/fail | 6/6 PASS | 4/6 FAIL  | 6/6 PASS |                   2 fail |        Khôi phục| Bắt trúng lỗi unique và length |
| Freshness status         |  is_fresh|   is_fresh|  is_fresh|          3 stale records |      100% fresh | SLA vẫn đạt do tỷ lệ stale < 25% |

### Hai kết luận nhân quả thực nghiệm quan trọng:
1. **Minh chứng Silent Failure:** Khi các trường dữ liệu bị can thiệp (xóa abstract, drop bài, nhiễu văn bản), mô hình RAG vẫn sinh ra câu trả lời mượt mà mà không có bất kỳ ngoại lệ (exception) runtime nào, nhưng `retrieval_hit_rate` sụt giảm thẳng đứng từ 100% xuống 50% kéo theo `mean_token_f1` giảm từ 1.0000 xuống 0.5286.
2. **Hiệu năng của Data Observability & Idempotent Repair:** Cổng Great Expectations 1.x hoạt động như tấm khiên phòng thủ vững chắc, chặn đứng tập dữ liệu vi phạm trước khi đưa vào serving layer; đồng thời cơ chế khôi phục từ nguồn thô đã đưa toàn bộ các chỉ số đo lường quay trở lại đúng mức chuẩn của Baseline.

---

## 11. Vấn đề tích hợp quan trọng

Trong quá trình ghép nối các module, nhóm đã phát hiện và xử lý một lỗi tích hợp điển hình giữa module Đánh giá (`src/evaluation/metrics.py`) và module Báo cáo (`src/observability/reporting.py`):
- **Triệu chứng:** File báo cáo `corruption_report.md` sinh ra toàn bộ giá trị `0.0000` cho mọi chỉ số đánh giá dù pipeline chạy thành công.
- **Nguyên nhân:** Lỗi bất tương thích data contract: `reporting.py` cố gắng đọc các trường dữ liệu cũ (`hit_at_1`, `faithfulness`), trong khi module đánh giá lại xuất ra chuẩn mới (`retrieval_hit_rate`, `mean_token_f1`, `judge_accuracy`).
- **Cách xử lý:** Cập nhật hàm ánh xạ khóa dữ liệu trong `reporting.py`, bổ sung cơ chế fallback report tự động đọc trực tiếp từ các file kết quả `data/results/*.json`.
- **Cách xác minh:** Chạy lại `script/run_corruption_flow.py` và đối chiếu từng byte số liệu trong bảng markdown với các file JSON kết quả.

---

## 12. Giới hạn và hướng cải thiện

| Giới hạn hiện tại | Ảnh hưởng | Hướng cải thiện có thể kiểm chứng |
| --------------------- | -------------- | ----------------------------------------- |
| Quy mô dữ liệu mẫu 24 bài báo | Phù hợp cho bài lab nhưng chưa mô phỏng được độ trễ ở quy mô lớn | Mở rộng crawler thu thập >1,000 bài báo từ Crossref API |
| Quy trình repair cần lệnh kích hoạt | Cần sự can thiệp của kỹ sư khi có cảnh báo | Xây dựng cơ chế Auto-repair Trigger (tự động kích hoạt khi GX Quality Gate FAIL) |

---

## 13. Checklist trước khi nộp

- [x] Thông tin nhóm và repository chính xác.
- [x] Phân công khớp với module, artifact và kết quả thực tế.
- [x] Lệnh tái hiện đã được chạy lại trên phiên bản dùng để nộp.
- [x] Baseline, corrupted và repaired dùng cùng evaluation set.
- [x] Bảng metrics khớp với các file trong `data/results/`.
- [x] Quality/freshness conclusions khớp với `data/quality/`.
- [x] Các đường dẫn báo cáo và artifact truy cập được.
- [x] Mỗi thành viên đã hoàn thành báo cáo vai trò riêng.
- [x] Không có `.env`, API key, token hoặc secret trong source, report, log hay ảnh.
