# Thành viên 3 — RAG & Agent handoff

## Phạm vi sở hữu

Thành viên 3 sở hữu package `src/retrieval/`:

- `embeddings.py`: sinh vector chuẩn hóa bằng `sentence-transformers/all-MiniLM-L6-v2`.
- `index.py`: build, load, search và exact lookup trên ChromaDB.
- `qa.py`: trả lời bốn nhóm câu hỏi summary, authors, publication date và categories.
- `llm.py`: khởi tạo LLM theo provider, gồm provider `mock` chạy offline.
- `agent.py`: cung cấp semantic-search và exact-lookup tools cho agent.

Không thuộc phạm vi sở hữu: ingestion/cleaning, evaluation/test-set, observability và pipeline orchestration.

## Input contract

`LocalEmbeddingIndex.build()` nhận một `pandas.DataFrame` có các cột:

```text
paper_id
title
published
authors_joined
categories_joined
summary
abs_url
pdf_url
text_for_embedding
```

`paper_id`, `title` và `text_for_embedding` phải là chuỗi không rỗng. Các trường metadata còn lại được chuẩn hóa thành chuỗi an toàn trước khi ghi vào ChromaDB.

## Public API bàn giao

```python
from retrieval.index import LocalEmbeddingIndex
from retrieval.qa import answer_question

index = LocalEmbeddingIndex.build(
    clean_df,
    settings,
    settings.paths.embeddings_json,
)

results = index.search("semantic retrieval", top_k=4)
exact = index.lookup("10.1000/example")
answer = answer_question("Who authored 'Example paper'?", settings, index)

index.close()
```

Có thể dùng index như context manager để bảo đảm ChromaDB giải phóng file handle:

```python
with LocalEmbeddingIndex.load(settings) as index:
    results = index.search("semantic retrieval")
```

## Collection contract

Tên collection được suy ra từ đường dẫn manifest:

| Manifest | Collection |
|---|---|
| `settings.paths.embeddings_json` | `papers-baseline` |
| `settings.paths.corrupted_embeddings_json` | `papers-corrupted` |
| `settings.paths.repaired_embeddings_json` | `papers-repaired` |

Mỗi lần build, chỉ collection đích bị tạo lại. Hai collection còn lại được giữ nguyên. Duplicate `paper_id` vẫn được index bằng `record_id` có hậu tố vị trí để phục vụ corruption scenario.

## Output contract

Manifest embedding gồm:

- `backend`
- `embedding_model`
- `persist_path`
- `collection_name`
- `document_count`
- `documents`

`search()` trả về danh sách `SearchResult`; score cosine được chuẩn hóa về khoảng `0.0–1.0`.

`answer_question()` trả về `AnswerResult` với câu trả lời, document IDs, titles và contexts đã retrieve. Nếu corpus không có kết quả, hàm trả `I don't know from the indexed corpus.`.

## Xác minh độc lập

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

Kết quả gần nhất: `Ran 8 tests ... OK`.

Smoke test với model thật `sentence-transformers/all-MiniLM-L6-v2` trên cleaned dataset:

```text
rows 24
columns_ok True
collection papers-baseline
indexed 24
top_k 4
```

Các trường hợp đã kiểm tra:

- build/load round-trip;
- semantic search và exact lookup;
- rebuild idempotent;
- collection baseline/corrupted độc lập;
- duplicate-paper corruption;
- empty collection và input validation;
- QA tiếng Anh và tiếng Việt;
- mock LLM và agent offline.
- MiniLM thật và ChromaDB trên đủ 24 tài liệu.

## Hướng dẫn tích hợp

1. Thành viên Data Foundation bàn giao cleaned DataFrame theo đúng input contract.
2. Thành viên Pipeline gọi `LocalEmbeddingIndex.build()` cho từng trạng thái.
3. Thành viên Evaluation gọi `answer_question()` hoặc `evaluate_pipeline()` trên cùng test set.
4. Pipeline phải gọi `index.close()` hoặc dùng context manager khi hoàn thành để tránh khóa file ChromaDB trên Windows.
5. Không commit `.env`, API key hoặc model cache.
