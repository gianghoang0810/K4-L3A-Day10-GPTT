# Member Role Report — Day 10: Data Pipeline & Data Observability

## 1. Thông tin cá nhân

| Thông tin         | Nội dung                  |
| ------------------ | -------------------------- |
| Họ và tên          | Từ Hoàng Giang             |
| MSSV               | 2A202602363                |
| Khóa/Lớp           | AI-ENGINEER-K4 — VinUni    |
| Tên nhóm           | GPTT                       |
| Vai trò chính      | Trưởng nhóm / Pipeline Orchestration, Ingestion & Data Recovery |
| Repository         | https://github.com/gianghoang0810/K4-L3A-Day10-GPTT |
| Ngày hoàn thành    | 2026-09-25                 |

## 2. Vai trò và phạm vi công việc

### Phần việc sở hữu

| Module/deliverable | File/hàm phụ trách | Input nhận vào | Output bàn giao | Trạng thái |
| ------------------ | ------------------ | -------------- | --------------- | ---------- |
| Pipeline Orchestration | `src/pipelines/phase1.py`, `src/pipelines/corruption_flow.py` | Config, Clean DF, Raw records | Báo cáo Phase 1, Báo cáo Corruption & 3-state metrics | Hoàn thành |
| Data Ingestion & Snapshot | `src/ingestion/crossref.py` (`fetch_crossref_papers`, `load_raw_records`) | Crossref REST API / Snapshot JSON | `crossref_response.json`, `crossref_records.json` | Hoàn thành |
| Data Cleaning & Modeling | `src/ingestion/cleaning.py` (`build_clean_dataframe`) | Raw records list, Current UTC time | `papers_clean.csv`, `papers_clean.json` (24 rows, `age_days`, 5-part `text_for_embedding`) | Hoàn thành |
| Synthetic Corruption & Repair | `src/ingestion/corruption.py`, `src/pipelines/corruption_flow.py` | Clean DataFrame, Raw records | 6 corruption types, `papers_clean_corrupted.*`, `papers_clean_repaired.*` | Hoàn thành |
| Auto-Heal Self-Healing (Bonus B2) | `src/pipelines/auto_heal.py`, `script/run_auto_heal.py` | Candidate DataFrame, Quality Gate | Tự động phát hiện lỗi và rollback/repair về baseline sạch | Hoàn thành |
| Core Architecture & Config | `src/core/config.py`, `src/core/utils.py` | `.env`, System environment | Dataclasses cấu hình đường dẫn, helpers I/O, UTF-8 logging | Hoàn thành |

### Việc hỗ trợ ngoài phạm vi chính

| Hoạt động | Thành viên/module được hỗ trợ | Kết quả |
| --------- | ----------------------------- | ------- |
| Tích hợp ChromaDB & Embedding API | Nguyễn Hồng Phi (`retrieval/index.py`) | Bổ sung phương thức `build_from_clean()` và `semantic_search()` tương thích hoàn toàn với acceptance check commands của lab |
| Debug Great Expectations 1.x | Nguyễn Hồng Phi (`observability/quality.py`) | Chuyển đổi thành công sang kiến trúc Ephemeral Data Source của GX 1.x, tương thích với phiên bản mới nhất `great_expectations>=1.0.0` |
| Quản trị môi trường UV & Dependencies | Nhóm GPTT | Cấu hình cài đặt PyTorch CPU dung lượng tối ưu (117MB) thay vì CUDA (2.6GB), đảm bảo dự án chạy nhẹ nhàng |

## 3. Kết quả theo vai trò

| Nhiệm vụ đã thực hiện | File/hàm/artifact liên quan | Kết quả bàn giao | Cách xác minh |
| --------------------- | --------------------------- | ---------------- | ------------- |
| Xây dựng Ingestion Dual-Mode | `src/ingestion/crossref.py` | Thu thập 24 bản ghi với retry/backoff và tự động fallback offline | `python script/run_phase1.py` |
| Chuẩn hóa và làm sạch dữ liệu | `src/ingestion/cleaning.py` | Làm sạch text, deduplicate, tính `age_days` (UTC-safe), tạo 5-part `text_for_embedding` | `data/clean/papers_clean.json` |
| Tiêm 6 kịch bản lỗi thực tế | `src/ingestion/corruption.py` | Tiêm đồng thời 6 dạng lỗi (drop, blank, noise, truncate, stale, dup) | `data/results/corruption_log.json` |
| Tự động phục hồi Idempotent Repair | `src/pipelines/corruption_flow.py` | Tái tạo dữ liệu sạch 100% từ raw snapshot bất biến | `data/clean/papers_clean_repaired.json` |
| Điều phối Phase 1 & Phase 2 | `src/pipelines/*.py` | Xuất bảng đối chiếu 3 trạng thái Baseline vs Corrupted vs Repaired | `data/reports/corruption_report.md` |
| Bonus B2: Auto-Heal Self-Healing Pipeline | `src/pipelines/auto_heal.py` | Tự động phát hiện vi phạm quality gate và tự động rollback/repair | `python script/run_auto_heal.py` |

Output cụ thể: `data/reports/corruption_report.md` và `data/results/repaired_metrics.json` chứng minh tỷ lệ Hit Rate phục hồi từ 60% lên 100%, F1 phục hồi từ 0.5741 lên 1.0000.

## 4. Giải thích phần kỹ thuật đã thực hiện

### Vấn đề cần giải quyết
Xây dựng một pipeline dữ liệu end-to-end có khả năng:
1. Thu thập dữ liệu nghiên cứu ổn định ngay cả khi API bên thứ ba gặp sự cố hoặc rate limit.
2. Chuẩn hóa dữ liệu thô thành cấu trúc vector-ready mà không làm mất mát ngữ cảnh.
3. Mô phỏng các sự cố dữ liệu thực tế (data corruption) để chứng minh hiện tượng suy giảm ngầm (Silent Failure) của RAG Agent.
4. Tự động phục hồi (Idempotent Repair) bảo toàn tính toàn vẹn của dữ liệu mà không gây ô nhiễm trạng thái.

### Cách triển khai
1. **Dual-Mode Ingestion:** Triển khai hàm `fetch_crossref_papers` với cơ chế thử lại (exponential backoff). Nếu API thất bại hoặc trả về lỗi, hệ thống tự động tải từ snapshot cục bộ `data/raw/crossref_response.json`, sau đó trích xuất thành danh sách phẳng `crossref_records.json`.
2. **Data Cleaning & Text for Embedding:**
   - Chuẩn hóa văn bản loại bỏ khoảng trắng thừa, ký tự điều khiển.
   - Tính toán `age_days` an toàn bằng `(now_utc - published_utc).days`.
   - Ghép 5 trường thông tin thành một chuỗi ngữ cảnh toàn vẹn: `Title: ... | Abstract: ... | Authors: ... | Categories: ... | Published: ...`.
3. **Synthetic Corruption:** Thiết kế 6 hàm tiêm lỗi có thể cấu hình ngẫu nhiên hoặc kiểm soát hạt giống (seed):
   - Kịch bản 1: Drop 2 dòng ngẫu nhiên.
   - Kịch bản 2: Xóa trắng summary thành rỗng.
   - Kịch bản 3: Chèn text rác (random noise) phá vỡ vector embedding.
   - Kịch bản 4: Cắt cụt tóm tắt chỉ còn dưới 20 ký tự.
   - Kịch bản 5: Đẩy lùi ngày xuất bản thêm 300 ngày làm tăng `age_days`, vi phạm Freshness SLA.
   - Kịch bản 6: Nhân bản dòng trùng lặp nhưng đổi `paper_id`.
4. **Idempotent Repair:** Khi phát hiện vi phạm, không chắp vá trực tiếp trên dataframe bị lỗi (anti-pattern). Hệ thống đọc lại snapshot bất biến `data/raw/crossref_records.json`, chạy lại pipeline làm sạch và tái nạp vector database.

### Input, output và contract

| Thành phần | Chi tiết |
| ---------- | -------- |
| Input | Snapshot JSON hoặc live HTTP response từ Crossref API |
| Output | DataFrame sạch (`papers_clean.csv`, `papers_clean.json`), file corrupted, file repaired, log tiêm lỗi |
| Contract | Schema clean bắt buộc có 8 cột: `paper_id`, `title`, `summary`, `authors`, `published_date`, `categories`, `age_days`, `text_for_embedding` |
| Xử lý ngoại lệ | Fallback offline khi lỗi mạng, validate schema trước khi trả về |

### Cách xác minh

```bash
# Kiểm tra Ingestion & Cleaning
python script/run_phase1.py

# Kiểm tra Corruption & Idempotent Repair
python script/run_corruption_flow.py

# Kiểm tra Auto-heal Pipeline (Bonus)
python script/run_auto_heal.py
```

- **Kết quả thực tế:** Tất cả các lệnh kết thúc với Exit code 0, không có warning hay lỗi ngoại lệ nào.

## 5. Một quyết định kỹ thuật quan trọng

- **Bối cảnh:** Lựa chọn chiến lược sửa chữa dữ liệu khi phát hiện vi phạm Data Quality: Sửa cục bộ (In-place patching) hay Tái tạo toàn bộ từ nguồn gốc (Idempotent replay).
- **Các phương án đã cân nhắc:**
  - *Phương án A (In-place Patching):* Viết các hàm điều kiện để dò tìm các bản ghi bị null, rác hoặc trùng lặp trên dataframe hiện tại và tìm cách khôi phục riêng các ô đó.
  - *Phương án B (Idempotent Replay from Raw Snapshot):* Coi tập dữ liệu bị lỗi là không thể cứu vãn; kích hoạt luồng làm sạch từ đầu dựa trên snapshot raw data gốc `data/raw/crossref_records.json`.
- **Phương án đã chọn:** Phương án B (Idempotent Replay).
- **Lý do:**
  1. *Nguyên lý Data Lineage:* Trong hệ thống MLOps, dữ liệu raw là "nguồn chân lý duy nhất" (single source of truth) và bất biến (immutable).
  2. *Tránh tích lũy lỗi ngầm (Error Compounding):* Sửa cục bộ dễ bỏ sót các trường hợp biên hoặc gây ra tình trạng dữ liệu nửa sạch nửa bẩn.
  3. *Tính nhất quán (Idempotency):* Chạy lại luồng repair 1 lần hay 100 lần đều cho ra cùng một kết quả hoàn hảo.
- **Bằng chứng:** Sau khi thực hiện repair theo phương án B, 100% (24/24) bản ghi vượt qua cả 6 checks của Great Expectations 1.x và RAG Hit Rate được khôi phục trọn vẹn từ 60% lên 100%.

## 6. Một lỗi hoặc blocker đã xử lý

- **Triệu chứng:** Khi chạy các lệnh kiểm tra Acceptance test trên Windows PowerShell:
  `UnicodeEncodeError: 'charmap' codec can't encode character '\u1ec7' in position 4: character maps to <undefined>`.
- **Lệnh tái hiện:**
  `python -c "print('Tín hiệu hoàn thành')"` trên terminal Windows mặc định.
- **Nguyên nhân gốc:** Windows PowerShell sử dụng bảng mã mặc định `cp1252` thay vì `UTF-8`. Khi Python cố gắng in các ký tự tiếng Việt có dấu ra stdout, bảng mã không tìm thấy ký tự tương ứng và ném ngoại lệ.
- **Cách xử lý:**
  1. Bổ sung `sys.stdout.reconfigure(encoding='utf-8')` trong các module Python.
  2. Hướng dẫn và cấu hình cờ `-X utf8` (`python -X utf8 -c "..."`) cho các câu lệnh kiểm tra trên môi trường Windows.
- **Cách xác minh sau khi sửa:** Tất cả các câu lệnh kiểm tra chấp nhận đều chạy thành công trên Windows PowerShell mà không còn lỗi encoding.
- **Điều học được:** Môi trường phát triển trên Windows luôn tiềm ẩn vấn đề mã hóa I/O. Thiết kế hệ thống dữ liệu phải luôn chủ động kiểm soát UTF-8 ở cả tầng tệp tin và tầng console stream.

## 7. Hiểu biết về luồng end-to-end

1. **Dữ liệu đi từ Crossref đến vector index:** Crossref API trả về metadata thô (JSON) -> Ingestion module lưu raw snapshot -> Cleaning module làm sạch text, tính `age_days`, format `text_for_embedding` gồm 5 phần -> Quality Gate kiểm tra tính hợp lệ -> Embedding module dùng `all-MiniLM-L6-v2` chuyển đổi text thành vector 384 chiều -> Nạp vào ChromaDB collection.
2. **Evaluation set và ground-truth document IDs:** Dùng 10 câu hỏi chuẩn hóa thuộc 5 dạng câu hỏi (`summary`, `authors`, `date`, `category`, `multi_hop`). Mỗi câu hỏi gắn kèm `ground_truth_doc_ids` (DOI của bài báo). Khi RAG Agent truy xuất top-3 tài liệu, nếu DOI này nằm trong kết quả trả về thì tính Hit = 1, ngược lại Hit = 0. Sau đó Agent sinh câu trả lời và so sánh token với ground-truth answer để tính F1 score.
3. **Quality checks khác freshness monitoring:** Quality checks (Great Expectations) kiểm tra các chiều chất lượng tĩnh của dữ liệu (Completeness, Uniqueness, Validity, Schema). Trong khi đó, Freshness SLA kiểm tra chiều Timeliness (tính thời sự) bằng cách đo khoảng cách thời gian giữa ngày chạy pipeline và ngày xuất bản của dữ liệu.
4. **Vì sao phải dùng cùng test set cho baseline, corrupted và repaired:** Để đảm bảo nguyên tắc biến kiểm soát (controlled experiment). Nếu thay đổi test set giữa các lần đo, sự thay đổi điểm số sẽ bị ảnh hưởng bởi độ khó của câu hỏi thay vì chất lượng thực tế của dữ liệu.
5. **Repair được xem là thành công dựa trên:** 
   - Vượt qua 100% Quality Gate (6/6 checks của Great Expectations 1.x).
   - Đạt tiêu chuẩn Freshness SLA (< 25% stale papers > 180 ngày).
   - Chỉ số Retrieval Hit Rate và Token F1 trên tập dữ liệu phục hồi phải quay trở lại tương đương hoặc bằng mức Baseline ban đầu (100% Hit Rate, F1 = 1.0000).

---

**Xác nhận cam kết:**
Tôi xác nhận các phần việc được báo cáo ở trên phản ánh đúng đóng góp thực tế của tôi trong nhóm GPTT.

**Họ và tên:** Từ Hoàng Giang  
**MSSV:** 2A202602363  
**Chữ ký xác thực:** *Từ Hoàng Giang*
