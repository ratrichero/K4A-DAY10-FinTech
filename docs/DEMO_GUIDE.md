# HƯỚNG DẪN BẢO VỆ LIVE DEMO & Q&A TRÊN BẢNG (CHECKPOINT 6)
**Dự án:** Data Pipeline & Data Observability for RAG  
**Nhóm:** Nhóm Dự Án VinUni AI-Engineer K4  
**Thời lượng trình diễn:** 3 - 5 phút trước Giảng viên và Hội đồng

---

## 🎯 1. KỊCH BẢN THUYẾT TRÌNH TRỰC DIỆN (3 - 5 PHÚT)

### Phút 0:00 - 1:00: Mở đầu & Giới thiệu Vấn đề (Silent Failure)
- *"Kính thưa Thầy và các bạn, trọng tâm của bài Lab 10 hôm nay không chỉ là xây dựng RAG Pipeline, mà là chứng minh bằng số liệu thực nghiệm: **Khi dữ liệu xấu, AI dù giỏi đến đâu cũng sẽ trả lời sai mà không hề báo lỗi (Silent Failure)**."*
- *"Chúng em giải quyết bài toán này bằng bộ đôi giải pháp: **Cổng kiểm soát chất lượng tự động với Great Expectations 1.x** và **Cơ chế tự phục hồi an toàn Idempotent Repair**."*

### Phút 1:00 - 2:30: Trình chiếu Bảng Đối Chiếu 3 Trạng Thái (Thực Nghiệm Thực Tế)
Mở file `data/reports/corruption_report.md` hoặc show trực tiếp terminal:

| Trạng thái | Data Quality Gate (GX 1.x) | Retrieval Hit Rate | Mean Token F1 | Judge Accuracy |
| :--- | :---: | :---: | :---: | :---: |
| **1. Baseline (Chuẩn)** | ✅ PASS (6/6 checks) | **1.0000 (100%)** | **1.0000** | **1.0000** |
| **2. Corrupted (Nhiễm bẩn)** | ❌ FAIL (4/6 checks) | **0.5000 (50%)** | **0.5286** | **0.5000** |
| **3. Repaired (Phục hồi)** | ✅ PASS (6/6 checks) | **1.0000 (100%)** | **1.0000** | **1.0000** |

- **Điểm nhấn thuyết minh:**
  1. Khi bị tiêm 6 dạng lỗi dữ liệu (xóa tóm tắt, cắt ngắn title, lùi ngày xuất bản), **Retrieval Hit Rate sụt giảm nghiêm trọng từ 100% xuống 50%**, Token F1 giảm từ 1.0 xuống 0.52.
  2. Mô hình AI vẫn tạo câu trả lời (không hề văng exception), nhưng nội dung trả lời bị sai lệch hoàn toàn.
  3. Great Expectations 1.x đã phát hiện chính xác các vi phạm dữ liệu này.

### Phút 2:30 - 3:30: Demo Live Tương Tác Bằng Lệnh CLI
Chạy lệnh trực tiếp trên terminal máy chiếu:
```bash
python script/demo_live.py
```
- Nhập chọn câu hỏi mẫu `[1]`:
  - Show kết quả từ **Baseline Index**: Trả lời chính xác tóm tắt bài báo.
  - Show kết quả từ **Corrupted Index**: Mô hình retrieve sai hoặc trả lời sai nội dung.
  - Show kết quả từ **Repaired Index**: Mô hình khôi phục hoàn hảo phong độ.

### Phút 3:30 - 4:00: Kết luận
- *"Thông điệp của nhóm: Trong môi trường AI Production, Data Observability là tấm khiên phòng thủ đầu tiên. Không có dữ liệu sạch thì không thể có AI đáng tin cậy."*

---

## ❓ 2. BỘ CÂU HỎI PHẢN BIỆN Q&A DỰ KIẾN TỪ GIẢNG VIÊN

### Câu hỏi 1: Tại sao cơ chế phục hồi (Repair) bắt buộc phải là Idempotent và lấy từ Raw Snapshot thay vì sửa trực tiếp trên file Cleaned?
> **Trả lời:**
> Sửa trực tiếp trên file Cleaned đã bị biến đổi tiềm ẩn rủi ro phá hủy trạng thái gốc và tạo ra lỗi dây chuyền (Dirty State). 
> **Tính chất Idempotent** đảm bảo rằng dù chạy lệnh khôi phục 1 lần hay 100 lần từ nguồn dữ liệu thô bất biến ban đầu (`data/raw/crossref_records.json`), kết quả đầu ra luôn tạo ra cùng một tập `clean_df` chuẩn xác mà không sinh thêm tác dụng phụ. Đây là chuẩn mực vàng của Data Engineering hiện đại.

### Câu hỏi 2: Cú pháp Great Expectations 1.x trong dự án khác gì so với phiên bản cũ?
> **Trả lời:**
> Trong phiên bản 1.x, Great Expectations chuyển đổi hoàn toàn sang mô hình cấu trúc hướng đối tượng mới:
> 1. Sử dụng `gx.get_context(mode="ephemeral")` thay cho `DataContext` cồng kềnh với thư mục `.ge/`.
> 2. Phân tách rõ ràng giữa `Data Source` $\rightarrow$ `Data Asset` $\rightarrow$ `Batch Definition` $\rightarrow$ `Batch`.
> 3. Tận dụng `great_expectations.expectations as gxe` với các lớp Expectation trực tiếp (ví dụ: `gxe.ExpectColumnValuesToNotBeNull`) thay vì gọi qua chuỗi string như phiên bản cũ.

### Câu hỏi 3: Chỉ số Token F1 và Retrieval Hit Rate phản ánh điều gì trong RAG?
> **Trả lời:**
> - **Retrieval Hit@1**: Đo lường tỷ lệ tài liệu đúng (Ground Truth ID) nằm ngay tại vị trí số 1 trong danh sách tài liệu mà ChromaDB trả về. Khi dữ liệu sạch, Hit@1 đạt 100%. Khi bị corrupt tiêu đề và nội dung, Hit@1 rơi xuống 50%.
> - **Token F1**: Đánh giá sự tương đồng giữa câu trả lời sinh ra và câu trả lời chuẩn (Ground Truth) dựa trên độ phủ từ (harmonic mean giữa Precision và Recall). Token F1 của nhóm giảm từ 1.0 xuống 0.5286 là bằng chứng toán học đanh thép về Silent Failure.

---

## 🚀 3. CÁC LỆNH CHUẨN BỊ TRƯỚC GIỜ LÊN BẢNG
1. **Kiểm tra bộ test tự động (Pytest):**
   ```bash
   python -m pytest tests/
   ```
2. **Khởi chạy bảng demo tương tác:**
   ```bash
   python script/demo_live.py
   ```
