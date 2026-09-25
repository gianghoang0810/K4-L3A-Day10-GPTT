# Báo Cáo Đối Chiếu 3 Trạng Thái: Data Corruption, Observability & Idempotent Repair

> **Mục tiêu:** Minh chứng định lượng sự sụt giảm nghiêm trọng của RAG khi dữ liệu bị lỗi (hiện tượng Silent Failure), khả năng phát hiện của Data Quality Gate (GX 1.x) và năng lực tự phục hồi an toàn từ nguồn Raw.

---

## 1. Bảng Đối Chiếu Định Lượng 3 Trạng Thái (Core Deliverable)

| Chỉ số / Tín hiệu đánh giá | 1. Baseline (Sạch) | 2. Corrupted (Lỗi) | 3. Repaired (Phục hồi) | Tác động của Corruption | Mức độ phục hồi | Đánh giá kỹ thuật |
| :--- | :---: | :---: | :---: | :---: | :---: | :--- |
| **Retrieval Hit Rate** | `100.0%` | `50.0%` | `100.0%` | **-50.0%** | **+50.0%** | Mất tài liệu và nhiễu vector khiến tìm kiếm sai lệch |
| **Mean Token F1** | `1.0000` | `0.6000` | `1.0000` | **-0.4000** | **+0.4000** | Câu trả lời bị thiếu thông tin hoặc sai lệch từ ngữ |
| **Judge Accuracy** | `100.0%` | `60.0%` | `100.0%` | **-40.0%** | **+40.0%** | Hallucination rõ rệt khi agent tự tin trả lời sai |
| **Mean Judge Score** | `5.00 / 5.0` | `3.40 / 5.0` | `5.00 / 5.0` | **-1.60** | **+1.60** | Chất lượng câu trả lời sụp đổ và phục hồi hoàn toàn |
| **Quality Gate (GX 1.x)** | **PASS** | **FAIL** | **PASS** | Phát hiện 100% lỗi tiêm | Đạt chuẩn toàn bộ | Chốt kiểm dịch bắt đúng các vi phạm cấu trúc |
| **Freshness SLA (`is_fresh`)** | **TRUE** | **FALSE** | **TRUE** | Báo động dữ liệu cũ | Tươi mới trở lại | Freshness SLA cảnh báo chính xác khi lùi ngày |

---

## 2. Phân Tích 6 Kịch Bản Tiêm Lỗi Dữ Liệu (Controlled Corruption)

1. **`drop_latest` (Mất 20% bản ghi mới):** Làm cho RAG không thể tìm thấy các nghiên cứu mới nhất, dẫn đến câu trả lời lỗi thời.
2. **`blank_summary` (Xóa trắng tóm tắt):** Vi phạm `ExpectColumnValueLengthsToBeBetween(min_value=30)`, khiến vector embedding thiếu thông tin ngữ nghĩa trọng tâm.
3. **`inject_noise` (Chèn chuỗi ký tự rác):** Bóp méo không gian embedding, làm giảm độ tương đồng cosine và kéo điểm retrieval xuống thấp.
4. **`truncate_title` (Cắt ngắn tiêu đề < 8 ký tự):** Gây khó khăn cho cơ chế tra cứu chính xác theo tiêu đề bài báo (`exact match lookup`).
5. **`stale_date` (Lùi ngày xuất bản về 365 ngày trước):** Làm tăng đột biến tỷ lệ bài báo cũ, kích hoạt cảnh báo `is_fresh = False` của Freshness SLA.
6. **`duplicate_rows` (Nhân bản dòng):** Vi phạm trực tiếp `ExpectColumnValuesToBeUnique(column="paper_id")`, gây loãng và trùng lặp kết quả vector search.

---

## 3. Cơ Chế Phục Hồi An Toàn (Idempotent Repair)

- **Nguyên lý:** Khi phát hiện lỗi từ trạm Data Observability Gate, hệ thống không sửa tay (ad-hoc) trên dữ liệu bẩn mà kích hoạt quy trình **Idempotent Repair**:
  1. Tải lại toàn bộ dữ liệu gốc từ bản lưu trữ bất biến `data/raw/crossref_records.json` (Data Lineage).
  2. Tái thực thi pipeline làm sạch `build_clean_dataframe()`.
  3. Xóa và tái tạo lại không gian vector độc lập trong ChromaDB (`papers-repaired`).
- **Tính Idempotent (Bất biến):** Chạy lại quy trình sửa chữa 1 lần hay 100 lần thì kết quả đầu ra luôn đồng nhất, bảo đảm 100% dữ liệu đạt chuẩn mà không sợ phát sinh dữ liệu thừa hay lỗi phụ.

---

## 4. Kết Luận & Bài Học Kinh Nghiệm Thực Chiến

1. **Hiện tượng Silent Failure là có thật:** Khi dữ liệu bị hỏng, mô hình AI không bao giờ báo lỗi code đỏ mà vẫn trả lời rất trôi chảy một cách sai sự thật.
2. **Vai trò sống còn của Data Observability:** Great Expectations 1.x kết hợp cùng Freshness SLA đóng vai trò "chốt kiểm dịch" tối quan trọng, chặn đứng dữ liệu rác trước khi nạp vào Vector Store.
3. **Data Lineage là tấm khiên bảo hiểm:** Luôn bảo tồn bản raw data ban đầu nguyên vẹn để có thể phục hồi hệ thống bất kỳ lúc nào một cách an toàn và tự động.
