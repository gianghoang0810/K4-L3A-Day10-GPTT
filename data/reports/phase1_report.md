# Báo Cáo Pha 1: Baseline Data Pipeline & Observability

> **Mã báo cáo:** PHASE1-BASELINE-REPORT  
> **Trạng thái:** Hoàn thành tốt (Pass toàn bộ kiểm định chất lượng)

---

## 1. Nguồn Dữ Liệu & Data Lineage (Ingestion)

- **Nguồn:** Crossref REST API
- **Số lượng bản ghi thu thập:** `24` bài báo
- **Bảo toàn nguồn cội (Raw Preservation):**
  - File JSON API thô: `D:\VinAI\DAY_10\K4-L3A-Day10-GPTT\data\raw\crossref_response.json`
  - File records bóc tách: `D:\VinAI\DAY_10\K4-L3A-Day10-GPTT\data\raw\crossref_records.json`

---

## 2. Tiền Xử Lý & Làm Sạch (Cleaning)

- **Số dòng dữ liệu sạch hợp lệ:** `24`
- **Các trường làm sạch:** Khử trùng lặp DOI `paper_id`, loại bỏ thẻ HTML/XML rác trong `summary`, chuẩn hóa tác giả và tính toán `age_days`.
- **Cấu trúc ngữ cảnh vector (`text_for_embedding`):** Đầy đủ 5 phần (Title, Authors, Published, Categories, Summary).

---

## 3. Trạm Kiểm Soát Chất Lượng (Data Quality Gate - Great Expectations 1.x)

- **Trạng thái tổng thể:** **SUCCESS (100% PASS)**
- **Tổng số Expectations kiểm thử:** `6`
- **Số Expectations đạt chuẩn:** `6`

| Expectation Name | Result |
| :--- | :---: |
| `expect_table_row_count_to_be_between` | **PASSED** |
| `expect_column_values_to_not_be_null` | **PASSED** |
| `expect_column_values_to_be_unique` | **PASSED** |
| `expect_column_values_to_not_be_null` | **PASSED** |
| `expect_column_values_to_not_be_null` | **PASSED** |
| `expect_column_value_lengths_to_be_between` | **PASSED** |

---

## 4. Giám Sát Độ Tươi (Freshness SLA Monitoring)

- **Ngày xuất bản mới nhất:** `2026-07-22`
- **Ngày xuất bản cũ nhất:** `2026-03-28`
- **Số bản ghi quá hạn (> 180 ngày):** `1 / 24`
- **Tỷ lệ bản ghi quá hạn:** `4.2%` (Ngưỡng cho phép: <= 25%)
- **Trạng thái Freshness:** **FRESH (Đạt SLA)**

---

## 5. Kết Quả Đánh Giá RAG Agent (Baseline Benchmarks)

Đánh giá trên bộ testset chuẩn 10 câu hỏi độc lập qua 4 nhóm nghiệp vụ (`summary`, `authors`, `date`, `categories`):

| Chỉ số đánh giá | Giá trị Baseline | Diễn giải |
| :--- | :---: | :--- |
| **Retrieval Hit Rate** | **100.0%** | Tỷ lệ tìm đúng tài liệu chứa đáp án trong top_k |
| **Mean Token F1** | **1.0000** | Độ trùng khớp từ vựng giữa câu trả lời và ground truth |
| **Judge Accuracy** | **100.0%** | Tỷ lệ câu trả lời được LLM/Heuristic Judge xác nhận đúng |
| **Mean Judge Score** | **5.00 / 5.0** | Điểm số chất lượng trung bình của câu trả lời |

*Kết luận:* Dữ liệu sạch ban đầu giúp hệ thống RAG đạt độ chính xác cao, truy xuất tài liệu ổn định và trả lời đầy đủ thông tin sự thật.
