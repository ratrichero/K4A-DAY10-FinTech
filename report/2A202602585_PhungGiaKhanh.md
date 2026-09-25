# Báo cáo cá nhân — Thành viên 3: RAG & Agent Specialist

## 1. Thông tin cá nhân

| Thông tin | Nội dung |
|---|---|
| Họ và tên | Phùng Gia Khánh |
| MSSV | 2A202602585 |
| Khóa/Lớp | K4 |
| Tên nhóm | FinTech |
| Vai trò chính | RAG & Agent Specialist |
| Repository | `K4A-DAY10-FinTech` |
| Ngày hoàn thành | 2026-09-25 |

## 2. Vai trò và phạm vi công việc

| Module/deliverable | File phụ trách | Input | Output | Trạng thái |
|---|---|---|---|---|
| Embedding | `src/retrieval/embeddings.py` | `text_for_embedding` | Vector MiniLM chuẩn hóa | Hoàn thành |
| Vector index | `src/retrieval/index.py` | Cleaned DataFrame | Chroma collection và manifest | Hoàn thành |
| QA | `src/retrieval/qa.py` | Question và index | `AnswerResult` | Hoàn thành |
| Agent/LLM | `src/retrieval/agent.py`, `llm.py` | Settings và index | Agent có retrieval tools | Hoàn thành |
| Kiểm thử | `tests/test_retrieval.py` | Fixture độc lập | 8 test cases | Hoàn thành |
| Handoff | `docs/MEMBER3_HANDOFF.md` | Public contract | Hướng dẫn tích hợp | Hoàn thành |

## 3. Kết quả và cách xác minh

Đã bổ sung validation cho schema đầu vào, build/load/search/lookup, ba collection độc lập, cơ chế rebuild idempotent, QA Anh–Việt và mock agent chạy không cần API key.

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

Kết quả thực tế:

```text
Ran 8 tests
OK

MiniLM smoke test:
rows 24
collection papers-baseline
indexed 24
top_k 4
```

## 4. Input, output và contract

| Thành phần | Mô tả |
|---|---|
| Input | DataFrame có `paper_id`, `title`, `published`, `authors_joined`, `categories_joined`, `summary`, `abs_url`, `pdf_url`, `text_for_embedding` |
| Output | Chroma collection, JSON manifest, `SearchResult`, `AnswerResult` |
| Module phụ thuộc | `core.config`, `core.utils`, cleaned data từ ingestion |
| Module sử dụng output | `evaluation.metrics`, `pipelines.phase1`, `pipelines.corruption_flow` |
| Điều kiện lỗi | Thiếu cột, ID/title/content rỗng, query rỗng, `top_k <= 0`, backend manifest không hợp lệ |

## 5. Quyết định kỹ thuật quan trọng

- **Bối cảnh:** Corruption flow cần mô phỏng duplicate rows nhưng Chroma yêu cầu ID bản ghi duy nhất.
- **Phương án cân nhắc:** Loại duplicate trước khi index; dùng `paper_id` trực tiếp; hoặc tạo record ID gồm `paper_id` và vị trí dòng.
- **Phương án chọn:** Dùng `record_id = <paper_id>::<row_index>`.
- **Lý do:** Vẫn giữ `paper_id` nghiệp vụ trong metadata để evaluation đối chiếu, đồng thời index được duplicate rows nhằm đo tác động thực tế của corruption.
- **Bằng chứng:** Test `test_duplicate_paper_ids_remain_indexable_for_corruption_flow` xác nhận hai dòng trùng paper ID đều được index.

## 6. Lỗi đã xử lý

- **Triệu chứng:** Test ChromaDB hoàn tất logic nhưng Windows báo `WinError 32` khi xóa thư mục tạm.
- **Nguyên nhân gốc:** `LocalEmbeddingIndex.build()` tạo PersistentClient tạm nhưng không đóng; SQLite/HNSW giữ file handle.
- **Cách xử lý:** Đóng build client bằng `finally`, bổ sung `close()` và context-manager protocol cho `LocalEmbeddingIndex`.
- **Xác minh:** Toàn bộ 8 test kết thúc thành công, không còn file-lock exception.
- **Bài học:** Với persistent vector store, quản lý vòng đời resource là một phần của data contract, không chỉ là chi tiết của test.

## 7. Hiểu biết về luồng end-to-end

Crossref records được làm sạch thành DataFrame có `text_for_embedding`. Retrieval module biến trường này thành vector MiniLM và lưu cùng metadata vào ChromaDB. Evaluation dùng cùng test set và ground-truth IDs để kiểm tra tài liệu đúng có xuất hiện trong top-k hay không, sau đó đo chất lượng câu trả lời. Quality/freshness kiểm tra dữ liệu trước hoặc song song với bước indexing. Baseline, corrupted và repaired phải dùng cùng test set để chênh lệch metric phản ánh thay đổi dữ liệu. Repair thành công khi quality signal và retrieval/answer metrics phục hồi so với baseline.

## 8. Giới hạn kết quả hiện tại

Các metric end-to-end `retrieval_hit_rate`, `mean_token_f1`, `judge_accuracy` và `mean_judge_score` chưa được ghi vào báo cáo này vì `phase1.py` và `corruption_flow.py` vẫn thuộc phạm vi tích hợp của thành viên khác và chưa hoàn thiện. Báo cáo không tuyên bố các metric chưa được chạy.

## 9. Cam kết

- [x] Phạm vi ownership khớp với phần code trực tiếp thực hiện.
- [x] Kết luận kỹ thuật có test để đối chiếu.
- [x] Không chứa `.env`, API key, token hoặc secret.
- [x] Không nhận là đã hoàn thành các pipeline/metric chưa được tích hợp.
- [x] Đã điền MSSV và đổi tên file theo quy ước `<MSSV>_PhungGiaKhanh.md` trước khi nộp.
