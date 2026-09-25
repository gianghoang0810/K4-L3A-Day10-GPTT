# Danh Sách Thành Viên & Báo Cáo Phân Công Nhóm

- **Tên Nhóm:** `GPTT`
- **Mã Nhóm / Lớp:** `K4-L3-DAY10`
- **Tên Repository Nộp Bài:** `K4-L3A-Day10-GPTT`

---

## 1. Thành viên

| STT | Họ và tên | MSSV | Email | Vai trò & Phân công công việc | Báo cáo cá nhân |
|---:|---|---|---|---|---|
| 1 | Từ Hoàng Giang | 2A202602363 | gianga1k49kc@gmail.com | Trưởng nhóm / Pipeline Orchestration, Ingestion & Data Recovery (`src/core/`, `src/ingestion/`, `src/pipelines/`) | `report/2A202602363_TuHoangGiang.md` |
| 2 | Nguyễn Hồng Phi | 2A202602750 | phinguyenhong@gmail.com | RAG, Vector Database, Data Observability & Evaluation (`src/retrieval/`, `src/observability/`, `src/evaluation/`, `tests/`) | `report/2A202602750_NguyenHongPhi.md` |

---

## 2. Phần Tự Khai Cá Nhân

### 2.1. Từ Hoàng Giang (2A202602363)
- **Vai trò:** Trưởng nhóm, Phụ trách Pipeline Orchestration, Ingestion & Data Recovery.
- **Công việc chi tiết đã hoàn thành:**
  - Thiết lập cấu hình hệ thống tập trung `src/core/config.py` và đường dẫn artifacts `src/core/utils.py`.
  - Xây dựng module Ingestion thu thập dữ liệu Crossref API với cơ chế retry/backoff và Fallback offline tự động trong `src/ingestion/crossref.py`.
  - Chuẩn hóa schema, tính toán trường `age_days` (UTC-safe) và cấu trúc 5 phần `text_for_embedding` trong `src/ingestion/cleaning.py`.
  - Xây dựng module tiêm 6 kịch bản lỗi synthetic corruption (`src/ingestion/corruption.py`) và luồng tự phục hồi Idempotent Repair từ snapshot Raw gốc (`src/pipelines/corruption_flow.py`).
  - Kết nối và tự động hóa toàn bộ luồng thực thi trong `src/pipelines/phase1.py` và `src/pipelines/corruption_flow.py`.
  - Xây dựng tính năng Bonus B2: Pipeline tự phục hồi Anomaly Detection & Self-Healing (`src/pipelines/auto_heal.py`, `script/run_auto_heal.py`).
  - Đảm bảo an toàn bảo mật (.env gitignored) và giải quyết tương thích encoding UTF-8 trên Windows console.
- **Điều học được / Đóng góp chính:**
  - Hiểu sâu sắc về thiết kế Idempotent Data Pipeline, nguyên tắc Data Lineage (bảo toàn raw snapshot bất biến) và quản lý trạng thái luồng dữ liệu đa tầng trong hệ thống MLOps.

### 2.2. Nguyễn Hồng Phi (2A202602750)
- **Vai trò:** Phụ trách RAG, Vector Database, Data Observability & Benchmark Evaluation.
- **Công việc chi tiết đã hoàn thành:**
  - Quản lý mô hình embedding `sentence-transformers/all-MiniLM-L6-v2` và nạp 3 collection ChromaDB độc lập (`papers-baseline`, `papers-corrupted`, `papers-repaired`) trong `src/retrieval/index.py`.
  - Xây dựng QA Agent truy vấn ngữ cảnh chính xác và sinh câu trả lời trong `src/retrieval/qa.py`.
  - Thiết lập Data Quality Gate theo chuẩn mới **Great Expectations 1.x (ephemeral mode)** với 6 checks bắt buộc và giám sát Freshness SLA trong `src/observability/quality.py`.
  - Xây dựng bộ 10 câu hỏi đánh giá chuẩn phủ đều 5 dạng câu hỏi (`summary`, `authors`, `date`, `category`, `multi_hop`) trong `src/evaluation/testset.py`.
  - Đo lường và phân tích hiện tượng Silent Failure (Hit Rate giảm từ 100% -> 60%, F1 giảm từ 1.0000 -> 0.5741) khi dữ liệu bị ô nhiễm.
  - Xây dựng tính năng Bonus B3: Bộ kiểm thử tự động Pytest với 6 unit tests (`tests/test_cleaning.py`, `tests/test_quality.py`, `tests/test_corruption_and_repair.py`) đạt PASS 100%.
  - Xây dựng tính năng Bonus B1: Giao diện trực quan Dashboard Dark-Mode Glassmorphism (`report/dashboard.html`) với biểu đồ đối chiếu 3 trạng thái và Radar Chart 6 chiều chất lượng.
- **Điều học được / Đóng góp chính:**
  - Cách thiết lập hệ thống Data Observability chặn đứng hiện tượng Silent Failure trước khi dữ liệu bị ô nhiễm lọt vào serving layer của RAG, cùng kỹ thuật cô lập không gian vector tránh rò rỉ dữ liệu.
