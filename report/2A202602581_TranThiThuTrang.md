# Member Role Report — Day 10: Data Pipeline & Data Observability

## 1. Thông tin cá nhân

| Thông tin | Nội dung |
| --- | --- |
| Họ và tên | Trần Thị Thu Trang |
| MSSV | 2A202602581 |
| Khóa/Lớp | K4 |
| Tên nhóm | FinTech (K4-L3) |
| Vai trò chính | Observability & Evaluation Lead (Thành viên 4) |
| Repository | https://github.com/ratrichero/K4A-DAY10-FinTech.git |
| Ngày hoàn thành | 2026-09-25 |

## 2. Vai trò và phạm vi công việc

### Phần việc sở hữu

| Module/deliverable | File/hàm phụ trách | Input nhận vào | Output bàn giao | Trạng thái |
| --- | --- | --- | --- | --- |
| Data Quality Gate (GX 1.x) | `src/observability/quality.py::run_data_quality_checks` | `pandas.DataFrame` đúng Data Contract (`papers_clean`) | `data/quality/*_quality_report.json` | Hoàn thành (Nghiệm thu cả 3 trạng thái Baseline, Corrupted, Repaired) |
| Freshness SLA | `src/observability/quality.py::build_freshness_report` | Cùng DataFrame trên, cột `age_days` | `data/quality/*freshness_report.json` | Hoàn thành (Theo dõi SLA 180 ngày xuyên suốt 3 trạng thái) |
| Benchmark test set | `src/evaluation/testset.py::build_test_set` | DataFrame clean | `data/eval/test_set.json` (10 câu, 4 loại) | Hoàn thành |
| Báo cáo markdown | `src/observability/reporting.py::generate_phase1_report`, `generate_corruption_report` | `metrics`, `quality`, `freshness` dict | `data/reports/phase1_report.md`, `corruption_report.md` | Hoàn thành (Tạo tự động 2 báo cáo markdown chứa đầy đủ số liệu định lượng) |

### Việc hỗ trợ ngoài phạm vi chính

| Hoạt động | Thành viên/module được hỗ trợ | Kết quả |
| --- | --- | --- |
| Chuẩn hóa Data Contract & Schema Mapping | TV1 (Lead), TV2 (Data Foundation), TV3 (RAG) | Thống nhất cấu trúc 16 trường chuẩn và ánh xạ chính xác các khóa metric trong `reporting.py` (`retrieval_hit_rate`, `mean_token_f1`, `judge_accuracy`). |
| Tích hợp kiểm tra tự động | TV1 (Lead) | Cung cấp logic kiểm tra chất lượng cho bộ unit test tự động `tests/test_quality_gate.py` trong pytest CI suite. |

## 3. Kết quả theo vai trò

| Nhiệm vụ đã thực hiện | File/hàm/artifact liên quan | Kết quả bàn giao | Cách xác minh |
| --- | --- | --- | --- |
| Cài đặt 6 expectation GX 1.x (ephemeral context) | `src/observability/quality.py` | `data/quality/baseline_quality_report.json` — `success: true`, 6/6 expectation PASS | `python -c "from core.config import load_settings; from observability.quality import run_data_quality_checks; import pandas as pd; s=load_settings(); df=pd.read_json(s.paths.clean_json); res=run_data_quality_checks(df, s, 'baseline'); print(res['success'])"` |
| Freshness SLA (`age_days > 180` → cảnh báo nếu > 25%) | `src/observability/quality.py` | `data/quality/freshness_report.json` — stale_ratio 0.0% (0/24), `is_fresh: true` (100% fresh) | `python -c "from core.config import load_settings; from observability.quality import build_freshness_report; import pandas as pd; s=load_settings(); df=pd.read_json(s.paths.clean_json); print(build_freshness_report(df, s, s.paths.freshness_report))"` |
| Sinh 10 câu hỏi benchmark, phủ đều 4 loại | `src/evaluation/testset.py` | `data/eval/test_set.json` — phân bố 3 summary / 3 authors / 2 date / 2 categories, đúng 5 field bắt buộc | Tự viết bộ kiểm tra invariant (id không trùng, không rỗng, `ground_truth_doc_ids` trỏ đúng `paper_id` có thật) — tất cả PASS |
| Sinh báo cáo markdown baseline & so sánh 3 trạng thái | `src/observability/reporting.py` | `data/reports/phase1_report.md` và `data/reports/corruption_report.md` | Chạy pipeline và kiểm tra trực tiếp 2 file báo cáo markdown trong `data/reports/` khớp số liệu JSON |

**Output cụ thể:** Toàn bộ các artifacts thực tế đã tồn tại đầy đủ trong thư mục `data/quality/`, `data/eval/`, và `data/reports/`, được sinh ra từ quy trình chạy pipeline tự động end-to-end trên tập dữ liệu chuẩn 24 bản ghi của bài lab.

## 4. Giải thích phần kỹ thuật đã thực hiện

### Vấn đề cần giải quyết

Phần việc của tôi giải quyết bài toán "Silent Failure" ở đúng lớp mà đề bài nhấn mạnh: Agent/RAG không tự báo lỗi khi dữ liệu bẩn, nên cần một **chốt kiểm dịch dữ liệu độc lập** (Data Quality Gate + Freshness SLA) chặn đứng trước khi dữ liệu vào Vector Store, và một **bộ đề thi benchmark cố định** để đo lường khách quan mức độ suy giảm/hồi phục của hệ thống RAG qua từng trạng thái dữ liệu.

### Cách triển khai

- `run_data_quality_checks`: dùng đúng API ephemeral của Great Expectations 1.x (`gx.get_context(mode="ephemeral")` → `add_pandas` → `add_dataframe_asset` → `add_batch_definition_whole_dataframe` → `get_batch`), sau đó thiết lập ExpectationSuite chứa 6 kiểm tra chất lượng (row count 5-5000, không null `paper_id`, `title`, `text_for_embedding`, duy nhất `paper_id`, và độ dài `summary` >= 30 ký tự) và gom kết quả xác thực an toàn.
- `build_freshness_report`: tính `stale_ratio` dựa trên `settings.freshness_threshold_days` (180 ngày) và xác thực SLA (tỷ lệ bài cũ ≤ 25%).
- `build_test_set`: chọn dòng theo thứ tự sort cố định (`sort_values("paper_id")`) thay vì random, để test set **tái lập được** — đúng vai trò "ground truth bất di bất dịch" mà `nhiemvu.md` yêu cầu; gán loại câu hỏi theo round-robin qua 4 loại để tự động phủ đều mà không cần hardcode tỉ lệ.
- `reporting.py`: xây dựng 2 hàm sinh báo cáo tự động (`generate_phase1_report`, `generate_corruption_report`), tính toán chính xác mức độ biến thiên delta giữa các trạng thái và xuất bảng đối chuẩn markdown trực quan.

### Input, output và contract

| Thành phần | Mô tả |
| --- | --- |
| Input | `papers_clean.csv/json` (contract: `paper_id, title, summary, authors, categories, published, age_days, authors_joined, categories_joined, summary_chars, text_for_embedding`) do TV2 (`cleaning.py`) tạo ra |
| Output | `data/quality/*.json`, `data/eval/test_set.json`, `data/reports/*.md` |
| Module phụ thuộc | `src/ingestion/cleaning.py` (TV2), `src/ingestion/corruption.py` (TV2), `src/core/config.py`/`core/utils.py` (TV1) |
| Module sử dụng output | `src/evaluation/metrics.py::evaluate_pipeline` (đọc `test_set.json`), `src/pipelines/phase1.py`, `corruption_flow.py` (TV1, gọi `quality.py`/`reporting.py`) |
| Điều kiện lỗi cần xử lý | `build_test_set` raise `ValueError` nếu DataFrame có ít hơn 5 dòng, tránh sinh test set rỗng/vô nghĩa |

### Cách xác minh

```bash
python -c "from core.config import load_settings; from observability.quality import run_data_quality_checks; import pandas as pd; s=load_settings(); df=pd.read_json(s.paths.clean_json); res=run_data_quality_checks(df, s, 'baseline'); print('success =', res['success'])"
python -c "from core.config import load_settings; from evaluation.testset import build_test_set; import pandas as pd; s=load_settings(); df=pd.read_json(s.paths.clean_json); ts=build_test_set(df, s.paths.eval_testset); print(len(ts), 'cau hoi')"
```

- **Kết quả mong đợi:** `success = True` trên dữ liệu sạch; `10 cau hoi` với phân bố phủ đều 4 loại.
- **Kết quả thực tế:** Đúng như mong đợi trên tập dữ liệu clean chuẩn 24 bản ghi của Crossref.
- **Artifact/log:** `data/quality/baseline_quality_report.json`, `data/quality/freshness_report.json`, `data/eval/test_set.json` — không chứa secret.

## 5. Một quyết định kỹ thuật quan trọng

- **Bối cảnh:** Tại thời điểm cần code và verify `quality.py`/`testset.py`, các module thượng tầng đang được phát triển song song.
- **Các phương án đã cân nhắc:**
  1. Chờ TV2 hoàn thành `cleaning.py` rồi mới bắt đầu code/test.
  2. Tự dựng một DataFrame tạm, đúng 100% Data Contract đã chốt trong `nhiemvu.md`, lấy dữ liệu từ snapshot `data/raw/crossref_records.json` có sẵn, để code và verify độc lập.
- **Phương án đã chọn:** Phương án 2.
- **Lý do:** Đúng nguyên tắc "Song mã cùng chạy — Không dẫm chân, Không chờ đợi" mà `nhiemvu.md` đặt ra làm nguyên tắc vàng của nhóm; đồng thời Data Contract đã đóng băng nên DataFrame tạm dựng đúng contract có giá trị test tương đương dữ liệu thật, chỉ khác nội dung, không khác schema.
- **Bằng chứng quyết định phù hợp:** Toàn bộ smoke-test (GX 6 expectation, freshness, 10 câu hỏi test) đều chạy đúng logic và cho `success/is_fresh` hợp lý; khi cố ý đưa dữ liệu lỗi vào (trùng `paper_id`, `summary` rỗng), GX bắt đúng loại lỗi — chứng minh code đã sẵn sàng nhận dữ liệu thật mà không cần sửa lại khi tích hợp toàn hệ thống.

## 6. Một lỗi hoặc blocker đã xử lý

- **Triệu chứng/lỗi nguyên văn:**
  ```
  AttributeError: 'str' object has no attribute 'resolve'
  ```
  xảy ra khi gọi `load_settings(project_dir=...)` trong script test.
- **Lệnh hoặc bước tái hiện:** `load_settings(project_dir=r"C:\...\K4-L3A-Day10-...")` — truyền một chuỗi thay vì `pathlib.Path`.
- **Nguyên nhân gốc:** `src/core/config.py::load_settings` gọi `.resolve()` trực tiếp lên `project_dir`, kỳ vọng tham số là `Path`, nhưng script test truyền vào `str` (raw string Windows path).
- **Cách xử lý:** Sửa script test để bọc `Path(...)` quanh đường dẫn trước khi truyền vào `load_settings` — không sửa `core/config.py` vì đó không phải file tôi sở hữu và hành vi hiện tại (yêu cầu `Path`) là hợp lý theo type hint đã khai báo.
- **Cách xác minh sau khi sửa:** Chạy lại script, `load_settings` trả về `Settings` hợp lệ, các bước tiếp theo (`run_data_quality_checks`, `build_freshness_report`) chạy thành công.
- **Điều học được:** Luôn đối chiếu type hint của hàm thuộc module người khác sở hữu trước khi gọi trong script test, thay vì đoán kiểu dữ liệu.

**Giải tỏa Blocker tích hợp:**
- Blocker phụ thuộc trước đó về việc thiếu dữ liệu thực tế và pipeline end-to-end đã được giải quyết triệt để sau khi TV1 (Pipeline Lead) và TV2 (Data Foundation) hoàn thiện `src/pipelines/phase1.py` và `src/pipelines/corruption_flow.py`.
- Toàn bộ trạm kiểm soát chất lượng Great Expectations 1.x và module báo cáo Markdown đã chạy thông suốt trên cả 3 tập dữ liệu (Baseline, Corrupted, Repaired), sinh ra đầy đủ các báo cáo JSON và Markdown chính thức.

## 7. Hiểu biết về luồng end-to-end

1. **Dữ liệu đi từ Crossref đến vector index như thế nào?** Crossref API (hoặc snapshot offline `data/raw/crossref_response.json`) → `crossref.py` bóc tách thành `PaperRecord` (DOI, title, summary đã lọc HTML tag, authors, categories, published) → `cleaning.py` chuẩn hóa, khử trùng lặp theo `paper_id`, tính `age_days`, ghép `text_for_embedding` → `papers_clean.csv/json` → `retrieval/index.py` dùng MiniLM embed và nạp vào ChromaDB theo từng collection (`papers-baseline`, `papers-corrupted`, `papers-repaired`).
2. **Evaluation set và ground-truth document IDs dùng để đo retrieval/answer quality ra sao?** `test_set.json` (10 câu, do tôi sinh) giữ `ground_truth_doc_ids` là `paper_id` đúng của bài báo được hỏi; `evaluation/metrics.py::evaluate_pipeline` so khớp `retrieved_doc_ids` của Agent với `ground_truth_doc_ids` để tính `retrieval_hit_rate`, và so khớp văn bản trả lời với `ground_truth` để tính `token_f1`.
3. **Quality checks khác freshness monitoring ở điểm nào?** Quality checks (GX) kiểm tra tính toàn vẹn cấu trúc/nội dung tại một thời điểm snapshot (đủ dòng, không null, không trùng, đủ độ dài) — trả lời câu hỏi "dữ liệu có sạch không". Freshness monitoring kiểm tra tính thời sự của dữ liệu theo thời gian (`age_days`) — trả lời câu hỏi "dữ liệu có còn mới không", một dữ liệu có thể hoàn toàn sạch về cấu trúc nhưng vẫn cũ/lỗi thời.
4. **Vì sao phải dùng cùng test set cho baseline, corrupted và repaired?** Để phép so sánh có ý nghĩa thống kê — nếu đổi câu hỏi giữa các trạng thái, sự sụt giảm/phục hồi của Hit Rate hay Token F1 có thể do đổi độ khó câu hỏi chứ không phải do chất lượng dữ liệu, làm mất giá trị chứng minh của thí nghiệm.
5. **Repair được xem là thành công dựa trên artifact và metric nào?** Dựa trên: (a) `repaired_quality_report`/`freshness` trả về `success=True`/`is_fresh` tương đương baseline (6/6 checks PASS); (b) `repaired_metrics.json` có `retrieval_hit_rate` (1.0000), `mean_token_f1` (1.0000) hồi phục hoàn toàn về mức baseline (so với mức sụt giảm nghiêm trọng ở `corrupted_metrics.json`) — tức là quy trình nạp lại từ `data/raw/crossref_records.json` gốc và chạy lại `cleaning.py` một cách idempotent, không cần sửa tay.

## 8. Phân tích kết quả

### Bảng metrics đối chuẩn 3 trạng thái thực nghiệm

| Metric / Tín hiệu kiểm soát | 1. Baseline | 2. Corrupted | 3. Repaired | Thay đổi do Corruption | Mức phục hồi sau Repair | Nhận xét cá nhân |
| :--- | :---: | :---: | :---: | :---: | :---: | :--- |
| `retrieval_hit_rate` | **1.0000** | **0.5000** | **1.0000** | -0.5000 (-50.0%) | +0.5000 (+100.0%) | Sụt giảm 50% khi dữ liệu bị lỗi; khôi phục hoàn hảo sau Idempotent Repair. |
| `mean_token_f1` | **1.0000** | **0.5286** | **1.0000** | -0.4714 (-47.14%) | +0.4714 (+89.18%) | Độ chính xác câu trả lời giảm sâu do trượt ngữ cảnh; khôi phục 100%. |
| `judge_accuracy` | **1.0000** | **0.5000** | **1.0000** | -0.5000 (-50.0%) | +0.5000 (+100.0%) | Minh chứng Silent Failure: AI tự tin trả lời sai lệch nhưng không báo lỗi. |
| `mean_judge_score` | **5.00** | **3.00** | **5.00** | -2.00 | +2.00 | Điểm chất lượng sụt giảm 2 điểm trên thang điểm 5. |
| Quality checks (GX 1.x) | **6/6 PASS** | **4/6 PASS (2 FAIL)** | **6/6 PASS** | 2 checks vi phạm | Phục hồi 6/6 PASS | Bắt trúng lỗi `duplicate paper_id` (19.05% dup) và `summary < 30 ký tự`. |
| Freshness SLA (180 days) | **FRESH (100%)** | **FRESH (85.71%)** | **FRESH (100%)** | 3 stale records (14.29%) | Phục hồi 100% fresh | Bắt trúng 3 bài báo bị lùi ngày; SLA vẫn đạt (stale 14.29% < ngưỡng 25%). |

### Kết luận nhân quả thực nghiệm quan trọng:
1. **Xác nhận hiện tượng Silent Failure:** Khi các trường dữ liệu bị can thiệp (xóa abstract, cắt ngắn title, chèn ký tự rác), mô hình RAG vẫn sinh ra câu trả lời bình thường mà không hề có ngoại lệ runtime, nhưng `retrieval_hit_rate` sụt giảm thẳng đứng từ 100% xuống 50%, kéo theo `mean_token_f1` giảm từ 1.0000 xuống 0.5286.
2. **Sức mạnh phòng thủ của Great Expectations 1.x:** Trạm kiểm soát chất lượng đã chặn đứng tập dữ liệu lỗi (FAIL 4/6 checks passed), ngăn chặn dữ liệu rác tiến sâu vào serving layer.
3. **Tính lũy quyền của Idempotent Repair:** Cơ chế tái thực thi pipeline chuẩn hóa từ snapshot bất biến `data/raw/crossref_records.json` đã đưa toàn bộ chất lượng dữ liệu và hiệu năng truy vấn quay trở lại mức Gold Baseline ban đầu.

## 9. Điều học được và hướng cải thiện

### Ba điều quan trọng nhất

1. Great Expectations 1.x có API ephemeral khác hẳn cú pháp cũ (`add_pandas` → `add_dataframe_asset` → `add_batch_definition_whole_dataframe` → `batch.validate(expectation)`), và việc thiết lập ExpectationSuite đồng bộ với BatchDefinition là chìa khóa để triển khai cổng kiểm dịch gọn nhẹ, không phụ thuộc file cấu hình cồng kềnh.
2. Một bộ evaluation set chỉ có giá trị khoa học nếu nó **deterministic và bất biến** giữa các lần chạy/các trạng thái dữ liệu — nếu không, mọi kết luận về "sụt giảm" hay "phục hồi" đều mất ý nghĩa so sánh.
3. Sự kết hợp giữa Data Observability và Data Contract chặt chẽ giúp nhóm phát hiện sớm các bất tương thích về kiểu dữ liệu và cấu trúc trước khi tích hợp vào production pipeline.

### Nếu có thêm thời gian

Tôi sẽ xây dựng thêm các quy tắc kiểm tra nâng cao (ví dụ: phát hiện độ trôi dạt phân phối nhãn danh mục bài báo Drift Detection) và xây dựng webhook gửi cảnh báo Slack/Discord tự động khi Freshness SLA vi phạm ngưỡng cho phép.

## 10. Cam kết của thành viên

- [x] Nội dung báo cáo phản ánh đúng phần việc và mức hiểu của tôi.
- [x] Tôi có thể giải thích luồng end-to-end, không chỉ module mình phụ trách.
- [x] Mọi kết luận về kết quả đều có artifact hoặc metric để đối chiếu.
- [x] Tôi không ghi "đã chạy thành công" cho phần chưa được kiểm chứng.
- [x] Báo cáo không chứa `.env`, API key, token hoặc secret.
- [x] Báo cáo này không phải bản sao nguyên văn của báo cáo nhóm hoặc báo cáo thành viên khác.

**Họ và tên:** Trần Thị Thu Trang  
**MSSV:** 2A202602581  
**Ngày xác nhận:** 2026-09-25
