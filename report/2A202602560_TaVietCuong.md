# Member Role Report — Day 10: Data Pipeline & Data Observability

## 1. Thông tin cá nhân

| Thông tin         | Nội dung                                          |
| ------------------ | ------------------------------------------------- |
| Họ và tên       | Tạ Việt Cường                                   |
| MSSV               | 2A202602560                                     |
| Khóa/Lớp         | K4                                              |
| Tên nhóm         | FinTech (K4-L3) |
| Vai trò chính    | Pipeline Lead & System Integrator (Thành viên 1) |
| Repository         | [ratrichero/K4A-DAY10-FinTech](https://github.com/ratrichero/K4A-DAY10-FinTech) (nhánh làm việc: `cuongtv`) |
| Ngày hoàn thành | 2026-09-25                                     |

## 2. Vai trò và phạm vi công việc

### Phần việc sở hữu

| Module/deliverable | File/hàm phụ trách | Input nhận vào | Output bàn giao | Trạng thái |
| --- | --- | --- | --- | --- |
| Cấu hình hệ thống | `src/core/config.py` (`load_settings`, `Settings`, `Paths`) | `.env`, cấu trúc thư mục dự án | `Settings` dùng chung cho mọi module | Hoàn thành |
| Baseline orchestration | `src/pipelines/phase1.py`, `script/run_phase1.py` | Raw records, các module con | `baseline_metrics.json`, `phase1_report.md`, collection `papers-baseline` | Hoàn thành |
| Corruption & repair orchestration | `src/pipelines/corruption_flow.py`, `script/run_corruption_flow.py` | Artifacts của Phase 1 (clean CSV, baseline metrics, test set) | `corrupted_metrics.json`, `repaired_metrics.json`, `corruption_report.md`, 2 collection ChromaDB | Hoàn thành |
| Corruption suite (viết thay TV2 theo Anti-Blocking Protocol, chờ TV2 review) | `src/ingestion/corruption.py` (`corrupt_clean_dataframe`) | `papers_clean.csv` | `papers_clean_corrupted.csv/.json`, `corruption_log.json` | Hoàn thành (pending review) |
| Nhật ký thực thi | `mydoc/excute.md` | Kết quả chạy từng Phase | Traceability log Phase 0 → Phase 3 | Hoàn thành |

Chú thích phạm vi: tôi là owner chính của khối **orchestration/integration**. Các module `crossref.py`, `cleaning.py` (TV2), `index.py`, `embeddings.py`, `qa.py` (TV3), `testset.py` (TV4) do thành viên khác sở hữu; tôi có fix tích hợp trên `quality.py`/`reporting.py`/`llm.py` khi chúng chặn pipeline (ghi rõ ở mục 6).

### Việc hỗ trợ ngoài phạm vi chính

| Hoạt động | Thành viên/module được hỗ trợ | Kết quả |
| --- | --- | --- |
| Fix tích hợp `src/observability/quality.py` + `src/core/config.py` | TV4 — quality gate gọi field không tồn tại trong `Settings` | GX gate chạy được cho cả 3 trạng thái, mỗi trạng thái có file report riêng |
| Fix mapping key metrics `src/observability/reporting.py` | TV4 — báo cáo sinh ra toàn 0.0000 do đọc sai key | `phase1_report.md` và `corruption_report.md` hiển thị số liệu khớp `data/results/*.json` |
| Thêm `timeout=60, max_retries=2` cho LLM client `src/retrieval/llm.py` | TV3 — pipeline bị treo >600s khi LLM API chậm | LLM fail nhanh rồi fallback heuristic judge, pipeline không treo |
| Implement `corrupt_clean_dataframe` tạm | TV2 — module còn stub `NotImplementedError` | Phase 2 chạy end-to-end được trong khi TV2 làm phần khác |

## 3. Kết quả theo vai trò

| Nhiệm vụ đã thực hiện | File/hàm/artifact liên quan | Kết quả bàn giao | Cách xác minh |
| --- | --- | --- | --- |
| Thiết kế preflight gate cho Phase 2 | `corruption_flow.py` (`_missing_baseline_artifacts`) | Phase 2 từ chối chạy (Exit Code 2) nếu thiếu artifact Phase 1, in hướng dẫn chạy `run_phase1.py` trước | Xóa/đổi tên artifact → chạy script → thấy thông báo `[PREFLIGHT] missing` |
| Pipeline corruption→repair 9 bước | `src/pipelines/corruption_flow.py` | End-to-end Exit Code 0, sinh đủ 14+ artifacts, 3 collection ChromaDB tách biệt | `python script/run_corruption_flow.py` |
| 6 kịch bản corruption deterministic | `src/ingestion/corruption.py` | `data/results/corruption_log.json` ghi đủ 6 kịch bản + paper_id bị ảnh hưởng, corpus 24→21 dòng | Đọc `corruption_log.json`; chạy lại 2 lần log khớp nhau |
| Fallback report khi reporting chưa xong | `_write_fallback_comparison_report` | Bảng 3 cột luôn được sinh kể cả khi `generate_corruption_report` chưa implement | Tạm mock lỗi → report fallback vẫn xuất hiện |
| Chạy nghiệm thu 2 pipeline + pytest | `script/*.py`, `tests/` | Exit Code 0 cho cả 2 pipeline; pytest 16/16 passed | Xem log trong `mydoc/excute.md` |

Output cụ thể nhất phần tôi tạo ra: **`data/reports/corruption_report.md`** — bảng đối chiếu 3 trạng thái với số liệu thật, cùng cơ chế đảm bảo nó luôn đúng (đọc key metrics từ `evaluate_pipeline`, fallback khi reporting stub).

## 4. Giải thích phần kỹ thuật đã thực hiện

### Vấn đề cần giải quyết

Ghép 3 module của 3 thành viên (được viết song song theo data contract đóng băng) thành 2 pipeline chạy end-to-end, đồng thời chứng minh bằng số liệu: dữ liệu bẩn làm RAG sụt giảm mà không báo lỗi (Silent Failure), và repair từ raw snapshot khôi phục hoàn toàn.

### Cách triển khai

`corruption_flow.py` gồm 9 bước, khớp pseudo-code trong `mydoc/plan.md`:

1. **Preflight gate:** kiểm tra sự tồn tại của 3 artifact Phase 1 (`papers_clean.csv`, `baseline_metrics.json`, `test_set.json`). Thiếu → thoát Exit Code 2 kèm hướng dẫn. Thiết kế này giúp Phase 2 chỉ phụ thuộc *artifact* (không import code `phase1.py`), nên 2 thread làm việc song song không dẫm file của nhau.
2. Tiêm 6 corruption qua `corrupt_clean_dataframe`, lưu CSV/JSON + log.
3. Dựng index ChromaDB collection `papers-corrupted` (tách biệt baseline, đảm bảo phép so sánh công bằng).
4. Chạy GX gate + freshness trên dữ liệu lỗi (kỳ vọng `success=False`).
5. Evaluate corrupted trên **cùng** `test_set.json` của baseline (điều kiện bắt buộc để so sánh có ý nghĩa).
6. **Idempotent repair:** đọc lại `data/raw/crossref_records.json` → chạy lại `build_clean_dataframe` → ghi `papers_clean_repaired.*`. Không sửa tay bất kỳ dòng nào.
7. Dựng collection `papers-repaired` + GX + freshness.
8. Evaluate repaired trên cùng test set.
9. Sinh `corruption_report.md` (qua `generate_corruption_report`; nếu stub thì dùng fallback report tự sinh từ metrics).

Summary cuối cùng in console so sánh hit rate 3 trạng thái và kiểm tra idempotent bằng cách so danh sách `paper_id` của repaired với clean corpus gốc.

### Input, output và contract

| Thành phần | Mô tả |
| --- | --- |
| Input | `data/clean/papers_clean.csv/.json` (16 cột chuẩn contract), `data/results/baseline_metrics.json` (keys: `retrieval_hit_rate`, `mean_token_f1`, `judge_accuracy`, `mean_judge_score`), `data/eval/test_set.json` (10 items) |
| Output | `data/results/{corrupted,repaired}_metrics.json`, `corruption_log.json`, `data/reports/corruption_report.md`, collection `papers-corrupted`/`papers-repaired` |
| Module phụ thuộc | `ingestion.corruption`, `ingestion.cleaning`, `ingestion.crossref` (repair), `retrieval.index`, `evaluation.metrics`, `observability.quality`, `observability.reporting` |
| Module sử dụng output | Báo cáo nhóm, live demo (`script/demo_live.py`), giảng viên chấm bài |
| Điều kiện lỗi cần xử lý | Thiếu artifact Phase 1 (Exit Code 2 có hướng dẫn); thiếu raw snapshot khi repair (RuntimeError rõ ràng); reporting stub (fallback report); LLM API chậm (timeout + fallback heuristic judge) |

### Cách xác minh

```bash
PYTHONIOENCODING=utf-8 LLM_PROVIDER=mock .venv/Scripts/python.exe script/run_corruption_flow.py
```

- **Kết quả mong đợi:** GX corrupted FAIL, hit rate corrupted giảm sâu, repaired khôi phục ~100%, console in `idempotent repair vs clean corpus: IDENTICAL`.
- **Kết quả thực tế:** `GX success=False (4/6)` → `hit rate=50.00%` → `hit rate=100.00%` → `IDENTICAL (24 rows)`, Exit Code 0.
- **Artifact/log:** `data/reports/corruption_report.md`, `data/results/corruption_log.json`, nhật ký đầy đủ trong `mydoc/excute.md`.

## 5. Một quyết định kỹ thuật quan trọng

- **Bối cảnh:** Phase 2 cần đảm bảo kết quả chạy lại giống hệt nhau (idempotent, phục vụ demo và chấm bài), trong khi corruption thường được viết bằng random nên log và metrics lệch nhau giữa các lần chạy.
- **Các phương án đã cân nhắc:** (1) dùng random + seed cố định; (2) chọn vị trí dòng **deterministic** theo quy luật (mọi dòng thứ 4 blank summary, 3 dòng cuối truncate title, v.v.).
- **Phương án đã chọn:** phương án (2) — không dùng RNG hoàn toàn.
- **Lý do:** với 24 dòng dữ liệu, quy luật vị trí đơn giản, dễ giải thích khi bảo vệ; `corruption_log.json` luôn khớp giữa các lần chạy nên nhóm chứng minh được idempotency mà không cần quản lý seed; rủi ro "dữ liệu thật lệch pattern" là thấp vì corpus nhỏ và cố định.
- **Bằng chứng quyết định phù hợp:** chạy `run_corruption_flow.py` 2 lần độc lập cho metrics trùng khớp 100% (baseline/corrupted/repaired đều 1.0/0.5/1.0), log 6 kịch bản giống hệt nhau.

## 6. Một lỗi hoặc blocker đã xử lý

- **Triệu chứng/lỗi nguyên văn:** (a) `AttributeError` tiềm ẩn do `src/observability/quality.py` gọi `settings.paths.data_dir` và `settings.stale_after_days` — hai attribute không tồn tại trong `Settings`; (b) `corruption_report.md` sinh ra **toàn bộ chỉ số 0.0000** dù metrics thật là 1.0/0.5/1.0.
- **Lệnh hoặc bước tái hiện:** chạy `python script/run_corruption_flow.py` trước khi fix → crash ở bước quality gate; sau khi pipeline chạy được, mở `corruption_report.md` thấy bảng 3 cột toàn 0.0000.
- **Nguyên nhân gốc:** (a) module quality viết theo interface `Settings` phác thảo, chưa đối chiếu với `config.py` thật; (b) `reporting.py` đọc các key cũ (`hit_at_1`, `mrr`, `faithfulness`…) trong khi `evaluate_pipeline` trả về `retrieval_hit_rate`, `mean_token_f1`, `judge_accuracy` — lỗi tích hợp điển hình giữa 2 module của 2 người khác nhau, không crash mà âm thầm cho số sai (nguy hiểm hơn).
- **Cách xử lý:** (a) thêm `freshness_sla_percent` vào `Settings`, sửa quality.py dùng `paths.quality_dir`/`freshness_threshold_days`, thêm tham số `report_name` để corrupted/repaired ghi file freshness riêng không ghi đè; (b) thêm helper `_metric()` đọc key đúng với fallback, đồng thời regenerate `phase1_report.md` từ artifacts thật.
- **Cách xác minh sau khi sửa:** chạy lại 2 pipeline Exit Code 0; `phase1_report.md` chỉ còn 4 chỉ số khớp từng byte với `baseline_metrics.json`; `corruption_report.md` hiển thị 1.0000/0.5000/1.0000.
- **Điều học được:** lỗi tích hợp nguy hiểm nhất không phải exception mà là **sai số liệu âm thầm** khi 2 module hiểu khác nhau về contract output — phải đối chiếu báo cáo với artifact gốc trước khi nộp.

## 7. Hiểu biết về luồng end-to-end

1. **Crossref → vector index:** `fetch_source_records` gọi Crossref API (lỗi mạng/429 thì fallback đọc `data/raw/crossref_response.json`), parse thành 24 `PaperRecord`; `build_clean_dataframe` khử trùng lặp theo `paper_id`, tính `age_days`, ghép `text_for_embedding` 5 dòng; `LocalEmbeddingIndex.build` embed bằng `all-MiniLM-L6-v2` (vector 384 chiều, cosine) vào collection ChromaDB persistent.
2. **Evaluation set:** `build_test_set` sinh 10 câu hỏi 4 nhóm (`summary`/`authors`/`date`/`categories`) kèm `ground_truth_doc_ids`; khi evaluate, câu trả lời của agent được so với ground truth (token F1), và top-k doc retrieved được so với `ground_truth_doc_ids` để tính hit rate.
3. **Quality checks vs freshness:** GX kiểm tra **cấu trúc/tính hợp lệ tại một thời điểm** (không null, unique, độ dài summary ≥ 30); freshness giám sát **chất lượng theo thời gian** (tỷ lệ bài có `age_days > 180`; vượt 25% → `is_fresh = False`). Một dataset có thể pass GX nhưng fail freshness và ngược lại.
4. **Cùng test set cho 3 trạng thái:** nếu đổi bộ câu hỏi giữa baseline/corrupted/repaired thì chênh lệch metrics không còn do corruption gây ra nữa — phép so sánh chỉ có ý nghĩa khi mọi biến khác được giữ cố định, chỉ thay đổi quality của corpus.
5. **Repair thành công khi:** (1) `papers_clean_repaired` khớp clean corpus gốc theo danh sách `paper_id` (console in `IDENTICAL`); (2) GX repaired `success=True`; (3) metrics repaired ≈ baseline (ở đây 1.0/1.0) — đều đối chiếu được qua artifacts, không phải lời khai.

## 8. Phân tích kết quả

### Metrics chính

| Metric/signal | Baseline | Corrupted | Repaired | Nhận xét của cá nhân |
| --- | ---: | ---: | ---: | --- |
| `retrieval_hit_rate` | 1.0000 | 0.5000 | 1.0000 | Corpus mất 3 bài mới nhất + nhiễu vector làm 5/10 câu trượt ground-truth doc |
| `mean_token_f1` | 1.0000 | 0.5286 | 1.0000 | Trượt retrieval kéo câu trả lời lấy nhầm context → F1 sụp theo |
| `judge_accuracy` | 1.0000 | 0.5000 | 1.0000 | Agent vẫn trả lời "tự tin" (không exception) — đúng hiện tượng Silent Failure |
| `mean_judge_score` | 5.0 | 3.0 | 5.0 | Điểm judge giảm 2/5 khi dữ liệu bẩn |
| Quality checks (GX) | 6/6 PASS | 4/6 FAIL | 6/6 PASS | Fail đúng 2 expectation: `paper_id` unique (duplicate rows) và summary length (blank/noise) |
| Freshness status | is_fresh=True (100%) | is_fresh=True (stale 3/21) | is_fresh=True | `stale_date` làm 3 dòng vượt 180 ngày nhưng chưa đủ 25% để fail SLA — minh họa được "mỗi gate bắt một loại lỗi" |

### Kết luận từ số liệu

1. `duplicate_rows + blank_summary + inject_noise` (thay đổi dữ liệu) → GX gate FAIL 2 vi phạm + vector drift (tài liệu không còn unique/nhiễu ký tự vô nghĩa) → `retrieval_hit_rate` tụt 1.0 → 0.5, F1 tụt xuống 0.5286.
2. `repair từ raw snapshot` (rebuild lại corpus sạch bằng `build_clean_dataframe`, không sửa tay) → GX 6/6 PASS trở lại + corpus khớp gốc theo `paper_id` → metrics hồi phục tuyệt đối về 1.0/1.0.

**Corruption ảnh hưởng rõ nhất:** tổ hợp *drop latest records + duplicate rows* — vì nó vừa làm mất tài liệu ground-truth (trượt retrieval vĩnh viễn trong corrupted index) vừa phá ràng buộc unique mà GX bắt được. Ngược lại *stale_date* không làm RAG sai câu trả lời trong bộ test này (không câu hỏi nào phụ thuộc độ tuổi) — cho thấy corruption "nhìn thấy được" ở quality gate chưa chắc ảnh hưởng agent và ngược lại.

**Khác kỳ vọng:** freshness của corrupted vẫn `is_fresh=True` dù đã có 3 dòng stale — dự kiến ban đầu là gate sẽ đỏ; kiểm tra lại số liệu: 3/21 ≈ 14% < ngưỡng 25%, nên SLA vẫn đạt. Đây là hành vi đúng theo spec, không phải lỗi.

## 9. Điều học được và hướng cải thiện

### Ba điều quan trọng nhất

1. **Data contract đóng băng + artifact-based dependency** cho phép 3-4 người code song song mà không chờ nhau: Phase 2 của tôi chỉ "cắm" vào 3 file artifact của Phase 1, không đụng code.
2. **Observability phải đối chiếu ngược với artifact:** báo cáo sinh tự động vẫn có thể sai (case 0.0000) — tin số liệu từ `data/results/*.json` và luôn diff report với metrics gốc.
3. **Silent Failure nguy hiểm hơn crash:** hệ thống không văng exception nào nhưng nửa số câu trả lời sai — chỉ có quality gate + evaluation metric phát hiện được.

### Nếu có thêm thời gian

Thêm cơ chế **auto-repair trigger** (Bonus B2): sau bước GX gate, nếu `success=False` thì tự động gọi luồng repair và re-validate thay vì chỉ báo động — đo cải thiện bằng: corrupted pipeline không còn cần bước manual, thời gian từ phát hiện lỗi đến corpus sạch giảm về 0 thao tác người. Có thể kiểm chứng bằng test pytest chạy 2 lần liên tiếp pipeline trong 1 process.

## 10. Cam kết của thành viên

Đánh dấu sau khi tự kiểm tra:

- [x] Nội dung báo cáo phản ánh đúng phần việc và mức hiểu của tôi.
- [x] Tôi có thể giải thích luồng end-to-end, không chỉ module mình phụ trách.
- [x] Mọi kết luận về kết quả đều có artifact hoặc metric để đối chiếu.
- [x] Tôi không ghi "đã chạy thành công" cho phần chưa được kiểm chứng.
- [x] Báo cáo không chứa `.env`, API key, token hoặc secret.
- [x] Báo cáo này không phải bản sao nguyên văn của báo cáo nhóm hoặc báo cáo thành viên khác.

**Họ và tên:** Tạ Việt Cường  
**Ngày xác nhận:** 2026-09-25
