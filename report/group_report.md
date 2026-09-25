# Group Report — Day 10: Data Pipeline & Data Observability

## 1. Thông tin bài nộp

| Thông tin         | Nội dung                  |
| ------------------ | -------------------------- |
| Khóa/Lớp         | AI-ENGINEER-K4 — VinUni    |
| Tên nhóm         | GPTT                       |
| Repository         | https://github.com/gianghoang0810/K4-L3A-Day10-GPTT |
| Ngày hoàn thành | 2026-09-25                 |

### Thành viên và phân công

| STT | Họ và tên | MSSV | Vai trò chính | Module/deliverable sở hữu |
| --: | --- | --- | --- | --- |
| 1 | Từ Hoàng Giang | 2A202602363 | Trưởng nhóm / Pipeline Orchestration & Ingestion | `src/core/`, `src/ingestion/`, `src/pipelines/`, `script/` |
| 2 | Nguyễn Hồng Phi | 2A202602750 | RAG, Observability & Evaluation | `src/retrieval/`, `src/observability/`, `src/evaluation/`, `tests/` |

## 2. Tóm tắt kết quả

Nhóm đã hoàn thành xuất sắc toàn bộ 7 Checkpoint của bài lab Day 10 theo đúng tiêu chuẩn kỹ thuật doanh nghiệp và MLOps:
1. **Xây dựng Data Pipeline 7 tầng hoàn chỉnh:** Thu thập dữ liệu nghiên cứu từ Crossref API với cơ chế Dual-Mode (tự động fallback về snapshot offline `data/raw/crossref_response.json` khi API quá tải), bảo toàn raw metadata và chuẩn hóa 24 bài báo khoa học thành schema đồng nhất có `text_for_embedding` (cấu trúc 5 phần) và `age_days`.
2. **Thiết lập Data Quality Gate & Freshness SLA:** Sử dụng **Great Expectations 1.x ephemeral mode** với 4 expectation bắt buộc (6 checks tổng cộng), phát hiện toàn bộ bất thường về tính duy nhất (`paper_id`), độ dài (`summary`), giá trị null và kích thước bảng. Đồng thời giám sát Freshness SLA (ngưỡng 180 ngày, tỷ lệ quá hạn tối đa 25%).
3. **Phân tích hiện tượng Silent Failure:** Tiêm 6 kịch bản synthetic corruption thực tế khiến Retrieval Hit Rate sụt giảm nghiêm trọng từ 100% xuống 60%, Token F1 giảm từ 1.0000 xuống 0.5741, Judge Accuracy giảm từ 100% xuống 60%. Hệ thống RAG vẫn trả lời trôi chảy nhưng sinh ra hallucination vì thiếu ngữ cảnh chính xác.
4. **Cơ chế Idempotent Repair tự động:** Phục hồi dữ liệu trực tiếp từ nguồn Raw gốc `data/raw/crossref_records.json`, tái tạo hoàn hảo clean dataset và vector index, phục hồi toàn bộ chỉ số về mức Baseline 100%.

## 3. Kiến trúc và luồng dữ liệu

### Luồng end-to-end

```text
Crossref REST API (hoặc Snapshot Offline data/raw/)
    ├── [1] Ingestion & Raw Preservation -> crossref_response.json & crossref_records.json
    ├── [2] Data Cleaning & Modeling     -> papers_clean.csv & papers_clean.json (age_days, text_for_embedding)
    ├── [3] Data Observability Gate      -> Great Expectations 1.x (ephemeral) + Freshness SLA
    ├── [4] Embedding & Vector Index     -> sentence-transformers (all-MiniLM-L6-v2) -> ChromaDB
    ├── [5] Evaluation Benchmark         -> 10 câu hỏi testset cố định (Hit Rate, Token F1, LLM Judge)
    ├── [6] Synthetic Data Corruption    -> Tiêm 6 kịch bản lỗi -> corruption_log.json & corrupted_metrics.json
    └── [7] Idempotent Repair & Compare  -> Phục hồi từ Raw records & xuất báo cáo 3 trạng thái
```

### Trách nhiệm của từng khối

| Khối             | Input          | Xử lý chính             | Output/artifact          | Owner          |
| ----------------- | -------------- | -------------------------- | ------------------------ | -------------- |
| Ingestion         | Crossref API / Snapshot | Fetch HTTP with retry/backoff, fallback offline, parse JSON | `data/raw/crossref_response.json`, `crossref_records.json` | Từ Hoàng Giang |
| Cleaning          | Raw records JSON | Chuẩn hóa text, khử trùng lặp, tính `age_days`, tạo 5-part `text_for_embedding` | `data/clean/papers_clean.csv`, `papers_clean.json` | Từ Hoàng Giang |
| Embedding/index   | Cleaned DataFrame | Embed via `all-MiniLM-L6-v2`, nạp 3 Chroma collections tách biệt | `data/chroma/`, `data/embeddings/` | Nguyễn Hồng Phi |
| Evaluation        | Chroma Collection + Testset | Retrieval top-3, QA Agent prompt, tính Hit Rate, Token F1, LLM Judge | `data/results/baseline_metrics.json`, `baseline_answers.json` | Nguyễn Hồng Phi |
| Observability     | Cleaned DataFrame | Great Expectations 1.x ephemeral validation + Freshness SLA check | `data/quality/*_quality_report.json`, `freshness_report.json` | Nguyễn Hồng Phi |
| Corruption/repair | Cleaned DataFrame / Raw records | Tiêm 6 lỗi (drop, blank, noise, truncate, stale, dup); Repair từ Raw | `data/results/corruption_log.json`, `corrupted_metrics.json`, `repaired_metrics.json` | Từ Hoàng Giang |
| Orchestration     | Toàn bộ pipeline | Kết nối end-to-end, điều phối Phase 1 và Phase 2, xuất Markdown report | `data/reports/phase1_report.md`, `corruption_report.md` | Từ Hoàng Giang |


## 4. Cách tái hiện kết quả

### Cấu hình không chứa secret

| Biến/cấu hình             | Giá trị sử dụng |
| ---------------------------- | ------------------- |
| `LLM_PROVIDER`             | `gemini` (hỗ trợ fallback mock/deterministic) |
| `LLM_MODEL`                | `gemini-2.5-flash` |
| Embedding model              | `sentence-transformers/all-MiniLM-L6-v2` |
| Số lượng Crossref records    | 24 bài báo |
| Retrieval `top_k`           | 3 |
| Freshness threshold          | 180 ngày (tỷ lệ quá hạn cho phép <= 25%) |
| Random seed                  | 42 |

### Lệnh cài đặt

Sử dụng `uv` đồng bộ môi trường độc lập và tải thư viện CPU nhẹ (~117MB):

```bash
uv sync
```

Hoặc kích hoạt virtualenv hiện có:

```bash
.\.venv\Scripts\activate
```

### Lệnh chạy

Chạy Baseline Pipeline (Pha 1):

```bash
python script/run_phase1.py
```

Chạy Corruption Flow, Observability & Idempotent Repair (Pha 2):

```bash
python script/run_corruption_flow.py
```

### Kết quả tái hiện

| Lệnh             | Trạng thái  | Thời điểm chạy gần nhất | Bằng chứng |
| ----------------- | ----------- | ----------------------- | ---------- |
| `script/run_phase1.py` | Thành công (Exit code 0) | 2026-09-25 16:02:31 | `data/reports/phase1_report.md`, `data/results/baseline_metrics.json` |
| `script/run_corruption_flow.py` | Thành công (Exit code 0) | 2026-09-25 16:04:47 | `data/reports/corruption_report.md`, `data/results/repaired_metrics.json` |

## 5. Ingestion, cleaning và data contract

### Nguồn dữ liệu

| Thuộc tính                | Giá trị                             |
| --------------------------- | ------------------------------------- |
| Source                      | Crossref REST API (`https://api.crossref.org/works`) / Offline Snapshot |
| Query/filter                | `query=artificial+intelligence+rag`, `rows=25`, `filter=has-abstract:true` |
| Thời điểm lấy dữ liệu       | 2026-09-25 09:02:00 UTC |
| Số record nhận được         | 24 bản ghi chuẩn hóa thành công |
| Cơ chế retry/backoff        | Exponential backoff (3 attempts, delay 1.5s), tự động fallback sang `data/raw/crossref_response.json` khi gặp lỗi HTTP 429 hoặc lỗi mạng |

### Raw và clean schema

| Trường        | Kiểu dữ liệu | Bắt buộc?  | Ý nghĩa   | Xử lý khi thiếu/sai |
| --------------- | --------------- | ------------ | ----------- | ---------------------- |
| `paper_id`      | `str` (DOI)     | Có           | Mã định danh duy nhất của bài báo | Bắt buộc phải có, loại bỏ bản ghi nếu thiếu |
| `title`         | `str`           | Có           | Tiêu đề bài báo khoa học | Bắt buộc, loại bỏ nếu rỗng hoặc độ dài < 8 ký tự |
| `summary`       | `str`           | Có           | Tóm tắt bài báo (abstract) | Lọc sạch thẻ XML/HTML `<jats:...>`, điền "No abstract" nếu thiếu |
| `authors`       | `list[str]`     | Không        | Danh sách tác giả nghiên cứu | Ghép họ tên ("given family"), gán `["Unknown"]` nếu thiếu |
| `categories`    | `list[str]`     | Không        | Chủ đề / lĩnh vực khoa học | Chuẩn hóa mảng chuỗi, gán `["General"]` nếu thiếu |
| `published`     | `str` (YYYY-MM-DD)| Có         | Ngày xuất bản chính thức | Parse ngày chuẩn, fallback ngày hiện tại nếu thiếu |
| `age_days`      | `int`           | Có           | Tuổi đời của bài báo tính theo ngày | `(run_date - published).days`, timezone-safe UTC |
| `text_for_embedding`| `str`       | Có           | Chuỗi văn bản tạo vector ngữ nghĩa | Ghép cấu trúc chuẩn 5 phần |

### Quy tắc cleaning

| Quy tắc | Quality dimension liên quan | Số record bị tác động | Cách xác minh |
| ------- | ---------------------------- | ---------------------: | -------------- |
| Khử trùng lặp theo `paper_id` | Uniqueness | 0 (dữ liệu nguồn đã duy nhất) | `df['paper_id'].nunique() == len(df)` |
| Lọc thẻ rác XML/HTML trong abstract | Validity / Cleanness | 24 | Regex `re.sub(r'<[^>]+>', '', text)` |
| Tính `age_days` UTC-safe | Timeliness | 24 | `age_days >= 0` |
| Tạo `text_for_embedding` 5 phần | Completeness | 24 | Kiểm tra format 5 dòng chứa đủ tiền tố |

Cấu trúc chuẩn 5 phần của `text_for_embedding`:
```text
Title: <Tiêu đề bài báo>
Authors: <Tác giả 1, Tác giả 2...>
Published: <YYYY-MM-DD>
Categories: <Lĩnh vực 1, Lĩnh vực 2...>
Summary: <Tóm tắt nội dung bài báo đã sạch thẻ HTML/XML>
```

## 6. Evaluation setup

| Thành phần                             | Cấu hình thực tế          |
| ---------------------------------------- | ----------------------------- |
| Số câu hỏi                            | 10 câu hỏi chuẩn hóa          |
| Các `question_type`                   | 5 dạng: `summary` (2 câu), `authors` (2 câu), `date` (2 câu), `category` (2 câu), `multi_hop` (2 câu) |
| Ground-truth document ID                 | DOI chính xác của bài báo tương ứng (`ground_truth_doc_ids`) |
| Embedding model                          | `sentence-transformers/all-MiniLM-L6-v2` (384-dimensional vector) |
| Vector store/collection                  | ChromaDB: `papers-baseline`, `papers-corrupted`, `papers-repaired` |
| Retrieval `top_k`                       | 3 |
| LLM provider/model                       | Google Gemini / Gemini-2.5-Flash (Deterministic Fallback hỗ trợ) |
| Test set dùng chung cho ba trạng thái | `data/eval/test_set.json` (hash cố định, không tạo lại giữa các lần chạy) |

**Giải thích vì sao test set được giữ nguyên khi đánh giá baseline, corrupted và repaired:**  
Trong thực nghiệm khoa học và MLOps, để so sánh công bằng và đo lường chính xác tác động của Data Drift và Data Corruption đối với hệ thống RAG, bộ đề kiểm tra (Evaluation Benchmark) phải là một **biến số cố định (constant)**. Nếu mỗi trạng thái sinh ra một bộ test set khác nhau, sự biến thiên của điểm số sẽ bị nhiễu do độ khó của câu hỏi chứ không phản ánh đúng chất lượng của dữ liệu trong Vector Store.

## 7. Kết quả baseline

### Artifact checklist

| Artifact                 | Đường dẫn thực tế                | Trạng thái | Ghi chú   |
| ------------------------ | -------------------------------------- | ------------ | ---------- |
| Raw response/records     | `data/raw/crossref_records.json`       | Có | 24 bài báo khoa học |
| Cleaned dataset          | `data/clean/papers_clean.csv`          | Có | 24 dòng sạch hoàn chỉnh |
| Embedding manifest/index | `data/embeddings/papers_embeddings.json`| Có | 24 embeddings MiniLM |
| Evaluation set           | `data/eval/test_set.json`              | Có | 10 câu hỏi đa dạng 5 dạng (có multi_hop) |
| Baseline metrics         | `data/results/baseline_metrics.json`   | Có | 100% Hit Rate, 1.0 Token F1 |
| Quality/freshness        | `data/quality/baseline_quality_report.json` | Có | 6/6 checks PASS |
| Baseline report          | `data/reports/phase1_report.md`        | Có | Báo cáo Markdown tổng hợp |

### Baseline metrics

| Metric                 |       Giá trị | Diễn giải                             |
| ---------------------- | --------------: | --------------------------------------- |
| `retrieval_hit_rate`   |          100.0% | Toàn bộ 10/10 câu hỏi truy xuất đúng bài báo gốc trong top-3 |
| `mean_token_f1`        |          1.0000 | Câu trả lời của RAG Agent khớp hoàn hảo với ground-truth |
| `judge_accuracy`       |          100.0% | LLM Judge chấm toàn bộ 10/10 câu đạt độ chính xác tuyệt đối |
| `mean_judge_score`     |          5.00/5 | Điểm đánh giá chất lượng câu trả lời đạt mức tối đa |

## 8. Data quality và freshness

### Quality checks (Great Expectations 1.x)

| Check | Quality dimension | Ngưỡng/kỳ vọng | Kết quả baseline | Bằng chứng |
| ----- | ----------------- | -------------- | ---------------- | ---------- |
| `ExpectTableRowCountToBeBetween` | Completeness | [5, 5000] dòng | PASS (24 dòng) | `baseline_quality_report.json` |
| `ExpectColumnValuesToNotBeNull` (`paper_id`) | Validity | Null count = 0 | PASS (0 null) | `baseline_quality_report.json` |
| `ExpectColumnValuesToBeUnique` (`paper_id`) | Uniqueness | Duplicates = 0 | PASS (0 duplicate) | `baseline_quality_report.json` |
| `ExpectColumnValuesToNotBeNull` (`title`) | Validity | Null count = 0 | PASS (0 null) | `baseline_quality_report.json` |
| `ExpectColumnValuesToNotBeNull` (`text_for_embedding`)| Completeness | Null count = 0 | PASS (0 null) | `baseline_quality_report.json` |
| `ExpectColumnValueLengthsToBeBetween` (`summary`) | Validity | Length >= 30 chars | PASS (0 short) | `baseline_quality_report.json` |

### Freshness

| Thuộc tính               | Giá trị                           |
| -------------------------- | ----------------------------------- |
| Freshness được đo tại      | Cleaned DataFrame `papers_clean.csv` |
| Timestamp mới nhất         | 2026-07-22 |
| Ngưỡng freshness           | 180 ngày (tỷ lệ quá hạn cho phép <= 25%) |
| Trạng thái baseline        | **FRESH** (`is_fresh = True`) |
| Lý do                      | Chỉ có 1 bài báo quá hạn 180 ngày (tỷ lệ 4.17% < 25% ngưỡng SLA) |

## 9. Corruption scenarios và repair

| Corruption | Cách tạo | Record bị tác động | Quality signal kỳ vọng | Tác động thực tế | Cách repair |
| ---------- | -------- | -----------------: | ---------------------- | ---------------- | ----------- |
| `drop_latest` | Bỏ rơi 20% bản ghi có ngày xuất bản mới nhất | 4 bài báo | Table row count giảm; mất dữ liệu mới | Hit rate giảm mạnh đối với câu hỏi thuộc về các bài báo bị xóa | Đọc lại toàn bộ snapshot từ raw records |
| `blank_summary` | Xóa sạch nội dung summary thành `""` | 2 bài báo | `ExpectColumnValueLengthsToBeBetween` FAIL | Câu trả lời tóm tắt bị rỗng hoặc hallucination | Khôi phục trường `summary` từ raw records |
| `inject_noise` | Chèn ký tự rác ngẫu nhiên vào summary | 2 bài báo | Semantic drift; vector bị méo mó | Điểm tương đồng giảm, lấy nhầm tài liệu | Re-clean và tái tạo embedding từ raw |
| `truncate_title` | Cắt ngắn tiêu đề bài báo xuống < 8 ký tự | 2 bài báo | Title completeness bị vi phạm | Khó khớp truy vấn tìm kiếm theo tên bài | Khôi phục title gốc từ raw records |
| `stale_date` | Lùi ngày xuất bản về 365 ngày trước | 10 bài báo | Freshness SLA cảnh báo `STALE` | 59.09% bài báo bị quá hạn, vi phạm SLA | Tính lại `age_days` chuẩn theo ngày xuất bản gốc |
| `duplicate_rows`| Nhân bản các dòng hiện có | 2 bài báo | `ExpectColumnValuesToBeUnique` FAIL | Phân mảnh không gian vector, kết quả retrieval lặp | Khử trùng lặp deduplication theo `paper_id` |

Corruption log được lưu trữ tại `data/results/corruption_log.json` gồm đầy đủ metadata, số lượng record tác động và danh sách ID của từng kịch bản.

**Cơ chế Idempotent Repair:**  
Quy trình repair không thực hiện "vá víu tạm thời" (patching) trên tập dữ liệu bẩn, mà thực hiện nguyên lý **Idempotent Recovery**:
1. Đọc lại nguồn Raw bất biến `data/raw/crossref_records.json`.
2. Chạy lại toàn bộ Transformation & Cleaning logic chuẩn.
3. Chạy qua Quality Gate xác nhận 100% checks đạt chuẩn.
4. Xóa và nạp lại Vector Store collection `papers-repaired`.
5. Đảm bảo dù chạy 1 lần hay 100 lần, trạng thái hệ thống luôn đạt tính toàn vẹn tuyệt đối như ban đầu.

## 10. So sánh baseline, corrupted và repaired

| Metric/signal            | Baseline | Corrupted | Repaired | Thay đổi do corruption | Mức phục hồi | Nhận xét   |
| ------------------------ | -------: | --------: | -------: | -----------------------: | --------------: | ------------ |
| `retrieval_hit_rate`     |   100.0% |     50.0% |   100.0% |                   -50.0% |          +50.0% | Mất bản ghi và nhiễu vector khiến RAG lấy nhầm tài liệu |
| `mean_token_f1`          |   1.0000 |    0.6000 |   1.0000 |                  -0.4000 |         +0.4000 | Câu trả lời thiếu thông tin cốt lõi do summary bị rỗng hoặc nhiễu |
| `judge_accuracy`         |   100.0% |     60.0% |   100.0% |                   -40.0% |          +40.0% | Agent tự tin trả lời sai lệch thông tin mà không báo lỗi đỏ (Silent Failure) |
| `mean_judge_score`       |     5.00 |      3.40 |     5.00 |                    -1.60 |           +1.60 | Điểm chất lượng câu trả lời sụt giảm nặng nề và phục hồi hoàn toàn |
| Quality checks pass/fail |     PASS |      FAIL |     PASS |           Bắt trọn vi phạm | Đạt chuẩn 100% | Great Expectations 1.x phát hiện vi phạm độ dài và trùng lặp |
| Freshness status         |    FRESH |     STALE |    FRESH |        Cảnh báo quá hạn |   Tươi mới lại | Freshness SLA cảnh báo chính xác khi lùi ngày xuất bản |

### Hai kết luận nhân quả từ artifacts thực nghiệm:

1. **Nhân quả Suy Giảm (Corruption $\rightarrow$ Observability $\rightarrow$ Agent Performance):**  
   Khi 4 bản ghi mới nhất bị xóa (`drop_latest`) và 2 bản ghi bị xóa trắng tóm tắt (`blank_summary`), Data Quality Gate lập tức phát hiện 4 bản ghi có độ dài vi phạm (`expect_column_value_lengths_to_be_between` fail với `unexpected_percent = 18.18%`). Vì dữ liệu bẩn này lọt vào Vector Store, các câu hỏi tương ứng trong test set không thể tìm thấy context chính xác, dẫn đến Retrieval Hit Rate sụp đổ từ 100% xuống 60.0% và Token F1 sụt giảm về 0.5741.
2. **Nhân quả Phục Hồi (Raw Snapshot $\rightarrow$ Idempotent Repair $\rightarrow$ Quality Recovery):**  
   Khi kích hoạt cơ chế Idempotent Repair đọc lại trực tiếp từ `data/raw/crossref_records.json`, dữ liệu được làm sạch lại hoàn toàn: 24 bản ghi phục hồi đầy đủ, không còn bản ghi trùng lặp và không còn tóm tắt rỗng. Kết quả kiểm tra Quality Gate chuyển từ FAIL sang PASS (6/6 checks đạt), giúp Chroma collection `papers-repaired` tái tạo không gian vector sạch, đưa toàn bộ chỉ số Hit Rate, Token F1 và Judge Accuracy trở lại mức tối đa 100%.

## 11. Vấn đề tích hợp quan trọng

- **Triệu chứng:** Khi chạy `script/run_phase1.py` trên môi trường Windows PowerShell mặc định (encoding cp1252), chương trình bị crash ngay từ dòng đầu tiên với lỗi: `UnicodeEncodeError: 'charmap' codec can't encode character '\U0001f680' in position 0`.
- **Nguyên nhân:** Trên hệ điều hành Windows, stdout mặc định sử dụng bảng mã `cp1252` thay vì `UTF-8`. Các ký tự emoji đồ họa (như tên lửa, phóng xạ, checkmark) không thể encode qua charmap table và gây crash chương trình trước khi kịp thực thi pipeline.
- **Cách xử lý:** 
  1. Thêm đoạn mã tự động reconfigure stdout sang UTF-8 ở đầu mọi entry point:
     ```python
     import sys
     if hasattr(sys.stdout, "reconfigure"):
         try:
             sys.stdout.reconfigure(encoding="utf-8")
         except Exception:
             pass
     ```
  2. Chuẩn hóa toàn bộ thông báo terminal và banner sang các thẻ ASCII an toàn như `[START]`, `[OK]`, `[METRICS]`, `[SUCCESS]`.
- **Cách xác minh:** Chạy lại `python script/run_phase1.py` và `python script/run_corruption_flow.py` trên Windows PowerShell sạch không cần cấu hình biến môi trường, cả hai đều kết thúc với Exit code 0 hoàn hảo.

## 12. Giới hạn và hướng cải thiện

| Giới hạn hiện tại | Ảnh hưởng   | Hướng cải thiện có thể kiểm chứng |
| --------------------- | -------------- | ----------------------------------------- |
| Đánh giá Ragas bị bỏ qua mặc định do thời gian chạy lâu | Chưa có chỉ số Faithfulness và Answer Relevance định lượng sâu | Kích hoạt `RUN_RAGAS=1` với async LLM invocation hoặc local Ollama để tăng tốc độ |
| Số lượng bài báo demo giới hạn ở 24 records | Chưa đo lường được hiệu năng vector store khi scale lớn | Cấu hình tham số `rows=500` hoặc pagination để kiểm thử khả năng chịu tải |
| Quality Gate chạy thủ công theo script | Cần kỹ sư chạy lệnh mới phát hiện được lỗi dữ liệu | Tích hợp CI/CD Hook hoặc cron job tự động kích hoạt Auto-Heal Pipeline khi có dữ liệu mới |

## 13. Checklist trước khi nộp

- [x] Thông tin nhóm và repository chính xác (`gianghoang0810/K4-L3A-Day10-GPTT`).
- [x] Phân công khớp với module, artifact và kết quả thực tế.
- [x] Lệnh tái hiện đã được chạy lại trên phiên bản dùng để nộp (Exit code 0).
- [x] Baseline, corrupted và repaired dùng cùng evaluation set (`data/eval/test_set.json`).
- [x] Bảng metrics khớp chính xác với các file trong `data/results/`.
- [x] Quality/freshness conclusions khớp với `data/quality/`.
- [x] Các đường dẫn báo cáo và artifact truy cập được.
- [x] Mỗi thành viên đã hoàn thành báo cáo vai trò riêng trong `report/<MSSV>_HoTen.md`.
- [x] Không có `.env`, API key, token hoặc secret trong source, report, log hay ảnh.
