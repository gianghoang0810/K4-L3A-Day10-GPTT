# Member Role Report — Day 10: Data Pipeline & Data Observability

## 1. Thông tin cá nhân

| Thông tin         | Nội dung                  |
| ------------------ | -------------------------- |
| Họ và tên          | Nguyễn Hồng Phi            |
| MSSV               | 2A202602750                |
| Khóa/Lớp           | AI-ENGINEER-K4 — VinUni    |
| Tên nhóm           | GPTT                       |
| Vai trò chính      | RAG, Vector Database, Data Observability & Evaluation |
| Repository         | https://github.com/gianghoang0810/K4-L3A-Day10-GPTT |
| Ngày hoàn thành    | 2026-09-25                 |

## 2. Vai trò và phạm vi công việc

### Phần việc sở hữu

| Module/deliverable | File/hàm phụ trách | Input nhận vào | Output bàn giao | Trạng thái |
| ------------------ | ------------------ | -------------- | --------------- | ---------- |
| Vector Index & Retrieval | `src/retrieval/index.py`, `src/retrieval/embeddings.py` | Cleaned DataFrame, Model MiniLM | 3 ChromaDB collections (`papers-baseline`, `papers-corrupted`, `papers-repaired`) | Hoàn thành |
| Retrieval QA Agent | `src/retrieval/qa.py` (`retrieve_context`, `answer_question`) | Query string, Chroma Collection | Top-k chunks, LLM answer có trích dẫn | Hoàn thành |
| Data Quality Gate (GX 1.x) | `src/observability/quality.py` (`validate_data_quality`) | Cleaned/Corrupted DataFrame | Báo cáo kiểm định 6 checks GX 1.x ephemeral mode | Hoàn thành |
| Freshness SLA Monitoring | `src/observability/quality.py` (`check_freshness_sla`) | Cleaned DataFrame, current time | `freshness_report.json` (ngưỡng 180 ngày, max 25% stale) | Hoàn thành |
| Evaluation Benchmark Testset | `src/evaluation/testset.py` (`load_or_create_test_set`) | Cleaned DataFrame | `test_set.json` (10 câu hỏi chuẩn phủ 5 query types) | Hoàn thành |
| Benchmark Evaluator & Metrics | `src/evaluation/testset.py`, `src/pipelines/phase1.py` | Chroma Index, Test Set | Hit Rate, Token F1, LLM Judge Accuracy | Hoàn thành |
| Pytest Test Suite (Bonus B3) | `tests/test_cleaning.py`, `test_quality.py`, `test_corruption_and_repair.py` | Clean data, raw records, GX suite | 6 automated unit tests PASS trong 4.60s | Hoàn thành |
| Interactive Dashboard (Bonus B1) | `report/dashboard.html`, `data/reports/dashboard.html` | Results JSON, Quality JSON | Dashboard glassmorphism dark-mode tương tác trực quan | Hoàn thành |

### Việc hỗ trợ ngoài phạm vi chính

| Hoạt động | Thành viên/module được hỗ trợ | Kết quả |
| --------- | ----------------------------- | ------- |
| Hỗ trợ thiết kế Idempotent Repair | Từ Hoàng Giang (`pipelines/corruption_flow.py`) | Định nghĩa các tiêu chuẩn phục hồi (Chroma re-indexing, xóa cache collection cũ tránh rò rỉ dữ liệu) |
| Chuẩn hóa định dạng Schema | Từ Hoàng Giang (`ingestion/cleaning.py`) | Thống nhất cấu trúc 5 phần của `text_for_embedding` nhằm tối ưu độ tương đồng cosine trong không gian vector 384 chiều |

## 3. Kết quả theo vai trò

| Nhiệm vụ đã thực hiện | File/hàm/artifact liên quan | Kết quả bàn giao | Cách xác minh |
| --------------------- | --------------------------- | ---------------- | ------------- |
| Thiết lập mô hình Embedding & Vector DB | `src/retrieval/index.py` | Embed 24 documents bằng `all-MiniLM-L6-v2`, nạp 3 collection ChromaDB cô lập | `python -X utf8 -c "..."` kiểm tra semantic search |
| Triển khai Quality Gate với GX 1.x | `src/observability/quality.py` | 6 checks chuẩn ephemeral mode phát hiện 100% vi phạm trên tập bẩn | `data/quality/corrupted_quality_report.json` |
| Xây dựng Testset 10 câu hỏi chuẩn | `src/evaluation/testset.py` | 10 câu hỏi chuẩn hóa gồm 5 dạng: `summary`, `authors`, `date`, `category`, `multi_hop` | `data/eval/test_set.json` |
| Đo lường suy giảm Silent Failure | `src/evaluation/testset.py` | Đo lường chính xác Hit Rate giảm từ 100% -> 60%, F1 giảm 1.0000 -> 0.5741 | `data/results/corrupted_metrics.json` |
| Viết bộ Test Suite Pytest (Bonus B3) | `tests/` | 6 tests tự động kiểm thử cleaning, quality gate, corruption & repair | `pytest tests/` (6 passed in 4.60s) |
| Thiết kế Dashboard trực quan (Bonus B1) | `report/dashboard.html` | Giao diện hiện đại có Chart.js so sánh 3 trạng thái, Radar Chart 6 chiều chất lượng | Mở trực tiếp trên trình duyệt |

Output cụ thể: `data/results/baseline_metrics.json` (Hit Rate 100%, F1 1.0000) và `data/results/corrupted_metrics.json` (Hit Rate 60%, F1 0.5741) chứng minh rõ ràng hiện tượng Silent Failure.

## 4. Giải thích phần kỹ thuật đã thực hiện

### Vấn đề cần giải quyết
1. **Cô lập không gian vector (Vector Isolation):** Cần lưu trữ vector embeddings của 3 trạng thái (Baseline, Corrupted, Repaired) mà không để xảy ra hiện tượng rò rỉ tài liệu (data leakage) giữa các lần thử nghiệm.
2. **Data Observability chuẩn doanh nghiệp:** Xây dựng hàng rào kiểm định tự động (Quality Gate) dựa trên Great Expectations 1.x Ephemeral Mode để phát hiện sự suy thoái dữ liệu ngay từ đầu vào.
3. **Phát hiện Silent Failure trong RAG:** Chứng minh rằng khi dữ liệu bị lỗi, LLM vẫn có thể sinh câu trả lời nghe rất trôi chảy nhưng thực chất là sai lệch hoàn toàn (Hallucination) do thông tin ngữ cảnh bị thiếu hụt.

### Cách triển khai
1. **Vector Database Management:**
   - Sử dụng mô hình `sentence-transformers/all-MiniLM-L6-v2` tạo vector 384 chiều cho trường `text_for_embedding`.
   - Tạo 3 ChromaDB collection riêng biệt: `papers-baseline`, `papers-corrupted`, và `papers-repaired`. Mỗi lần re-index hoặc repair, collection tương ứng sẽ được reset và nạp mới hoàn toàn.
2. **Great Expectations 1.x Ephemeral Mode:**
   - Chuyển đổi hoàn toàn sang kiến trúc mới của GX 1.x: Khởi tạo context thông qua `gx.get_context(mode="ephemeral")`.
   - Kết nối Pandas DataFrame thông qua `context.data_sources.add_pandas("runtime_source")`.
   - Định nghĩa Expectation Suite với 6 checks cốt lõi:
     - `expect_table_row_count_to_be_between(min_value=20, max_value=30)` (Schema/Volume).
     - `expect_column_values_to_be_unique(column="paper_id")` (Uniqueness).
     - `expect_column_values_to_not_be_null(column="paper_id")` (Completeness).
     - `expect_column_values_to_not_be_null(column="title")` (Completeness).
     - `expect_column_values_to_not_be_null(column="summary")` (Completeness).
     - `expect_column_value_lengths_to_be_between(column="summary", min_value=20)` (Validity).
3. **Benchmark Testset & Metric Calculation:**
   - Xây dựng 10 câu hỏi mẫu cố định với `ground_truth_doc_ids` tương ứng (DOI).
   - Truy vấn ChromaDB top-3: Nếu `ground_truth_doc_id` xuất hiện trong kết quả truy xuất -> `Hit Rate = 1`, ngược lại `0`.
   - Tính Token F1 score giữa câu trả lời sinh ra từ context và ground-truth answer.
   - LLM Judge đánh giá độ chính xác thực tế dựa trên mức độ tương đồng ngữ nghĩa.

### Input, output và contract

| Thành phần | Chi tiết |
| ---------- | -------- |
| Input | `papers_clean.json` (DataFrame), cấu hình model embedding |
| Output | Vector embeddings trong ChromaDB, `quality_report.json`, `test_set.json`, metrics JSON |
| Contract | Chroma metadata chứa `paper_id`, `title`, `published_date`, `categories`; Testset có đủ 5 loại câu hỏi |
| Xử lý ngoại lệ | Tự động xử lý fallback mock LLM khi không có Gemini API key; reset ChromaDB an toàn khi trùng tên collection |

### Cách xác minh

```bash
# Kiểm tra bộ unit test tự động (Bonus B3)
pytest tests/ -v

# Kiểm tra chất lượng dữ liệu và freshness
python -X utf8 -c "from core.config import load_settings; from observability.quality import validate_data_quality, check_freshness_sla; import pandas as pd; s=load_settings(); df=pd.read_json(s.paths.clean_json); print('Quality Valid:', validate_data_quality(df, s).is_valid); print('Freshness Valid:', check_freshness_sla(df, s).is_valid)"

# Kiểm tra Semantic Search trên ChromaDB
python -X utf8 -c "from core.config import load_settings; from retrieval.index import LocalEmbeddingIndex; import pandas as pd; s=load_settings(); df=pd.read_json(s.paths.clean_json); docs=df.to_dict('records'); idx=LocalEmbeddingIndex(settings=s, collection_name='papers-baseline', documents=docs, persist_path=s.paths.chroma_dir); idx.build_from_clean(); res=idx.semantic_search('machine learning', top_k=2); print('Tìm thấy:', len(res), 'tài liệu')"
```

- **Kết quả thực tế:** 6/6 tests Pytest đạt PASS tuyệt đối, Quality Gate báo cáo `is_valid: True`, ChromaDB truy xuất chính xác 2 tài liệu phù hợp.

## 5. Một quyết định kỹ thuật quan trọng

- **Bối cảnh:** Lựa chọn phương thức triển khai Great Expectations trong môi trường CI/CD và pipeline dữ liệu (sử dụng thư mục cấu hình tĩnh `great_expectations/` truyền thống hay sử dụng chế độ `ephemeral mode` trong code Python).
- **Các phương án đã cân nhắc:**
  - *Phương án A (File-based Configuration):* Tạo thư mục `great_expectations/` với các file `great_expectations.yml`, checkpoints YAML và stores JSON.
  - *Phương án B (Code-first Ephemeral Mode - GX 1.x):* Khởi tạo `get_context(mode="ephemeral")` hoàn toàn trong runtime Python của `src/observability/quality.py`.
- **Phương án đã chọn:** Phương án B (Ephemeral Mode).
- **Lý do:**
  1. *Đơn giản hóa hạ tầng:* Loại bỏ sự cồng kềnh của hàng chục file cấu hình YAML phụ thuộc đường dẫn tuyệt đối, giúp repository gọn gàng và dễ chia sẻ giữa các thành viên.
  2. *Tương thích chuẩn Great Expectations 1.x:* GX 1.x khuyến nghị sử dụng fluent API và ephemeral mode cho các pipeline phân tán hoặc containerized.
  3. *Tốc độ thực thi:* Khởi tạo trong RAM (in-memory) nhanh hơn đáng kể so với việc đọc ghi ổ đĩa liên tục, giảm thời gian chạy pipeline.
- **Bằng chứng:** Hàm `validate_data_quality` chạy xong toàn bộ 6 checks chỉ trong 0.25 giây, xuất báo cáo JSON chi tiết lưu trữ tập trung tại `data/quality/`.

## 6. Một lỗi hoặc blocker đã xử lý

- **Triệu chứng:** Khi chạy kịch bản đánh giá trên tập dữ liệu bị lỗi (corrupted dataset), RAG Agent vẫn sinh ra câu trả lời rất tự tin và đầy đủ ngữ pháp, nhưng Token F1 và Judge Accuracy lại giảm sâu xuống 60%.
- **Lệnh tái hiện:** `python script/run_corruption_flow.py` và kiểm tra file `data/results/corrupted_answers.json`.
- **Nguyên nhân gốc:** Đây chính là hiện tượng **Silent Failure** kinh điển của hệ thống RAG:
  1. Khi một bài báo bị xóa (`DropPaperCorruption`) hoặc tóm tắt bị chèn rác (`NoiseCorruption`), vector embedding của nó bị biến dạng hoặc biến mất khỏi ChromaDB.
  2. Khâu Retrieval không tìm thấy bài báo liên quan nhất (`Hit Rate = 0`), thay vào đó trả về các bài báo khác kém liên quan hơn.
  3. LLM không nhận được ngữ cảnh đúng nhưng vẫn cố gắng trả lời dựa trên kiến thức chung hoặc thông tin rác trong prompt, dẫn đến hiện tượng Hallucination mà không hề ném ra bất kỳ mã lỗi HTTP hay Exception nào.
- **Cách xử lý:** 
  - Thiết lập Quality Gate chặn đứng ngay từ tầng dữ liệu đầu vào.
  - Xây dựng cơ chế cảnh báo tự động: Khi Quality Gate thất bại, lập tức ngắt luồng Indexing và kích hoạt cơ chế Idempotent Repair.
- **Cách xác minh sau khi sửa:** Khi chạy `run_auto_heal.py`, pipeline phát hiện vi phạm quality gate và tự động rollback, ngăn chặn hoàn toàn dữ liệu bẩn lọt vào vector database.
- **Điều học được:** Trong các ứng dụng GenAI/RAG, hệ thống giám sát phần mềm truyền thống (như check exit code, HTTP 200) là không đủ. Bắt buộc phải có Data Observability và Retrieval Benchmark để phát hiện lỗi ngữ nghĩa âm thầm.

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

**Họ và tên:** Nguyễn Hồng Phi  
**MSSV:** 2A202602750  
**Chữ ký xác thực:** *Nguyễn Hồng Phi*
