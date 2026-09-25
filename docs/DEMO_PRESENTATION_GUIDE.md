# HƯỚNG DẪN THUYẾT TRÌNH SLIDE & KỊCH BẢN LIVE DEMO
## Đề tài: Data Pipeline & Data Observability cho RAG Agent (Day 10)
**Nhóm:** `GPTT` &bull; **Lớp:** `AI-ENGINEER-K4 — VinUni`  
**Thành viên:**  
1. **Từ Hoàng Giang** (MSSV: `2A202602363`) — Trưởng nhóm / Pipeline Orchestration, Ingestion & Data Recovery  
2. **Nguyễn Hồng Phi** (MSSV: `2A202602750`) — RAG, Vector Database, Observability & Evaluation  
**Dashboard Trực Quan:** [`report/dashboard.html`](file:///d:/VinAI/DAY_10/K4-L3A-Day10-GPTT/report/dashboard.html)

---

## PHẦN 1: TỔNG QUAN LUỒNG THUYẾT TRÌNH (3 - 5 PHÚT)

### 1. Mở đầu ấn tượng (30 giây)
> *"Kính thưa thầy cô và các bạn, trong các hệ thống GenAI và RAG thực tế, nguy cơ lớn nhất không phải là code bị crash, mà là **'Silent Failure'** (Lỗi ngầm): Hệ thống vẫn báo HTTP 200 OK, LLM vẫn trả lời rất trôi chảy, nhưng thực chất là thông tin bịa đặt (Hallucination) do dữ liệu đầu vào bị lỗi.  
> Hôm nay, nhóm GPTT mang đến một giải pháp hoàn chỉnh: **Xây dựng Data Pipeline 7 tầng tích hợp Data Observability theo chuẩn Great Expectations 1.x**, mô phỏng lỗi ngầm và chứng minh cơ chế **Tự phục hồi dữ liệu (Idempotent Self-Healing)** khôi phục lại 100% hiệu năng của RAG Agent."*

---

## PHẦN 2: HƯỚNG DẪN CHI TIẾT TỪNG CHECKPOINT TRÊN DASHBOARD / SLIDE

Khi thuyết trình, bạn mở file [`report/dashboard.html`](file:///d:/VinAI/DAY_10/K4-L3A-Day10-GPTT/report/dashboard.html) trên trình duyệt, thanh điều hướng ở đầu trang (Navigation Pills) đã được chia theo đúng thứ tự từ **CP0 &rarr; CP5**:

```text
[ ★ Tổng quan ]  [ CP0: Ingestion ]  [ CP1: Cleaning & GX 1.x ]  [ CP2: ChromaDB & Testset ]  [ CP3: Baseline ]  [ CP4: Corruption ]  [ CP5: Repair ]  [ + Bonus ]
```

---

### Slide / Mục 0: Tổng Quan Chỉ Số 3 Trạng Thái
- **Mục đích:** Đưa ra "bức tranh toàn cảnh" trước khi đi vào chi tiết kỹ thuật.
- **Điểm cần chỉ trên Dashboard:**
  - 5 thẻ KPI đầu trang:
    - **Retrieval Hit Rate:** $100\% \rightarrow 60\% \rightarrow 100\%$ (Phục hồi $+40\%$).
    - **Token F1 Score:** $1.0000 \rightarrow 0.5741 \rightarrow 1.0000$ (Phục hồi $+0.4259$).
    - **LLM Judge:** $100\% \rightarrow 60\% \rightarrow 100\%$ (Điểm $5.0 \rightarrow 3.4 \rightarrow 5.0$).
    - **Quality Gate:** $6/6$ checks đạt chuẩn.
    - **Freshness SLA:** $4.17\%$ stale (an toàn dưới ngưỡng $25\%$).
  - Biểu đồ Bar Chart so sánh 3 trạng thái và Radar Chart 5 chiều chất lượng dữ liệu (Completeness, Uniqueness, Validity, Timeliness, Semantic Fidelity).
- **Lời thoại gợi ý:**
  > *"Như thầy cô thấy trên biểu đồ đối chiếu, khi dữ liệu bị lỗi, chất lượng Retrieval và Answer F1 giảm sút nghiêm trọng tới 40%. Nhưng sau khi kích hoạt cơ chế Idempotent Repair, toàn bộ chỉ số đã phục hồi nguyên vẹn 100% như ban đầu."*

---

### Checkpoint 0: Data Ingestion & Bảo Toàn Raw Metadata
- **Mục đích:** Xây dựng tầng Ingestion tin cậy cao, bảo toàn nguyên bản dữ liệu thô.
- **Điểm kỹ thuật cốt lõi:**
  1. **Kiến trúc Dual-Mode:** Ưu tiên gọi Crossref REST API thời gian thực với cơ chế retry/backoff. Khi mạng mất kết nối hoặc bị rate limit (`HTTP 429`), hệ thống tự động fallback về snapshot offline tại `data/raw/crossref_response.json`.
  2. **Raw Preservation Contract:** Raw metadata được bảo toàn bất biến trong `data/raw/crossref_records.json` (24 bài báo), đóng vai trò là "Single Source of Truth" cho toàn bộ pipeline sau này.
- **Lệnh demo tại chỗ (nếu thầy cô yêu cầu):**
  ```powershell
  python -X utf8 -c "from core.config import load_settings; from ingestion.crossref import fetch_source_records; s=load_settings(); r=fetch_source_records(s); print(f'Tín hiệu hoàn thành: Đã tải {len(r)} bài báo')"
  ```
  *(Kết quả: `Tín hiệu hoàn thành: Đã tải 24 bài báo`)*.

---

### Checkpoint 1: Data Cleaning & Great Expectations 1.x Quality Gate
- **Mục đích:** Chuẩn hóa dữ liệu thô thành dạng Vector-Ready và dựng rào chắn kiểm định tự động.
- **Điểm kỹ thuật cốt lõi:**
  1. **Feature Engineering:**
     - Khử trùng lặp theo `paper_id` (DOI).
     - Tính trường `age_days` an toàn theo UTC: `(now_utc - published_utc).days`.
     - Ghép chuỗi ngữ cảnh 5 phần: `Title: ... | Abstract: ... | Authors: ... | Categories: ... | Published: ...` để embedding tối ưu ngữ nghĩa.
  2. **Chốt kiểm dịch Great Expectations 1.x (Ephemeral Mode):**
     - Chạy hoàn toàn in-memory, gồm 6 checks thiết yếu: Kích thước bảng (20-30 dòng), Unique ID, Non-null ID/Title/Summary, và độ dài tóm tắt $\ge 20$ ký tự.
  3. **Freshness SLA Monitoring:** Tỷ lệ bài quá hạn (>180 ngày) chỉ chiếm **4.17% (1/24 bài)**, tuân thủ nghiêm ngặt SLA ($\le 25\%$).
- **Lệnh demo tại chỗ:**
  ```powershell
  python -X utf8 -c "from datetime import datetime, timezone; from core.config import load_settings; from ingestion.crossref import load_raw_records; from ingestion.cleaning import build_clean_dataframe; s=load_settings(); df=build_clean_dataframe(load_raw_records(s.paths.raw_records_json), datetime.now(timezone.utc)); print(f'Tín hiệu hoàn thành: Clean thành công {len(df)} dòng')"
  ```

---

### Checkpoint 2: ChromaDB Vector Store & Benchmark Test Set
- **Mục đích:** Xây dựng cơ sở dữ liệu vector và bộ câu hỏi đánh giá chuẩn mực.
- **Điểm kỹ thuật cốt lõi:**
  1. **Vector Isolation (Cô lập không gian vector):** Sử dụng model `all-MiniLM-L6-v2` (384 chiều). Quản lý 3 collection ChromaDB độc lập (`papers-baseline`, `papers-corrupted`, `papers-repaired`), tuyệt đối không để rò rỉ dữ liệu giữa các lần thử nghiệm.
  2. **Test Set 10 câu hỏi bao quát 5 nhóm nghiệp vụ:**
     - `summary` (2 câu) &bull; `authors` (2 câu) &bull; `date` (2 câu) &bull; `category` (2 câu) &bull; `multi_hop` (2 câu).
     - Mỗi câu hỏi gắn liền với `ground_truth_doc_ids` (DOI) để đo lường định lượng Hit Rate.
- **Lệnh demo tại chỗ:**
  ```powershell
  python -X utf8 -c "from core.config import load_settings; from evaluation.testset import load_or_create_test_set; import pandas as pd; s=load_settings(); df=pd.read_json(s.paths.clean_json); ts=load_or_create_test_set(df, s.paths.test_set_json); print(f'Tín hiệu hoàn thành: Test set gồm {len(ts.samples)} câu hỏi')"
  ```

---

### Checkpoint 3: Baseline Pipeline & Báo Cáo Pha 1
- **Mục đích:** Thiết lập mốc chuẩn (Ground Truth Baseline) khi hệ thống hoạt động với dữ liệu sạch 100%.
- **Kết quả nghiệm thu:**
  - **Retrieval Hit Rate (Top-3):** **100.0%** (10/10 câu hỏi tìm thấy đúng tài liệu nguồn).
  - **Mean Token F1 Score:** **1.0000** (Câu trả lời trích xuất hoàn toàn khớp với ground truth).
  - **LLM Judge Accuracy:** **100.0%** (Điểm tuyệt đối **5.0 / 5.0**).
  - Toàn bộ pipeline chạy khép kín qua file điều phối [`src/pipelines/phase1.py`](file:///d:/VinAI/DAY_10/K4-L3A-Day10-GPTT/src/pipelines/phase1.py).

---

### Checkpoint 4: Synthetic Corruption & Hiện Tượng "Silent Failure"
- **Mục đích:** Giả lập các sự cố dữ liệu thực tế và chứng minh tác hại khôn lường của lỗi ngầm.
- **6 Kịch bản tiêm lỗi thực tế:**
  1. `drop_latest`: Xóa mất 20% bài báo mới nhất &rarr; Gây thiếu hụt kiến thức mới.
  2. `blank_summary`: Xóa sạch tóm tắt thành rỗng &rarr; Vi phạm độ dài GX 1.x.
  3. `inject_noise`: Chèn ký tự rác vào tóm tắt &rarr; Phá vỡ khoảng cách vector embedding.
  4. `truncate_title`: Cắt ngắn tiêu đề &lt; 8 ký tự &rarr; Mất từ khóa truy vấn ngữ cảnh.
  5. `stale_date`: Lùi ngày về quá khứ 365 ngày &rarr; Freshness vi phạm nặng lên 59.09%.
  6. `duplicate_rows`: Nhân bản dòng &rarr; Gây sai lệch thống kê và vi phạm Unique ID.
- **Hiện tượng Silent Failure:**
  > *"RAG Agent không hề báo lỗi crash, nhưng Hit Rate lập tức rớt từ 100% xuống 60%. Do không tìm thấy tài liệu gốc, LLM tự bịa ra câu trả lời (Hallucination) cho 4/10 câu hỏi. Đây là lý do nếu không có Data Observability Gate, doanh nghiệp sẽ phục vụ thông tin sai cho người dùng mà không hề hay biết!"*

---

### Checkpoint 5: Idempotent Repair & Tự Phục Hồi Dữ Liệu
- **Mục đích:** Tự động sửa chữa dữ liệu và đưa hệ thống AI trở lại phong độ đỉnh cao.
- **Quyết định kiến trúc sống còn:**
  - **Không chọn In-place Patching:** Sửa cục bộ trên dataframe lỗi dễ gây sót lỗi và làm ô nhiễm trạng thái.
  - **Chọn Idempotent Replay from Raw Snapshot:** Đọc lại dữ liệu thô bất biến `data/raw/crossref_records.json`, chạy lại pipeline làm sạch và tái nạp lại ChromaDB collection `papers-repaired`.
- **Kết quả phục hồi:**
  - Vượt qua 6/6 checks của Great Expectations 1.x.
  - Freshness SLA quay về mức chuẩn $4.17\%$.
  - Hit Rate và Token F1 khôi phục trọn vẹn về **100%** và **1.0000**.

---

### Phần Bonus (+10 điểm Rubric)
1. **Bonus B1 (+5đ):** Dashboard trực quan tương tác Dark-Mode Glassmorphism tại [`report/dashboard.html`](file:///d:/VinAI/DAY_10/K4-L3A-Day10-GPTT/report/dashboard.html) có thanh điều hướng Checkpoint, biểu đồ Chart.js so sánh 3 trạng thái và Radar Chart 5 chiều chất lượng.
2. **Bonus B2 (+5đ):** Pipeline tự phát hiện bất thường và kích hoạt tự chữa lành (`src/pipelines/auto_heal.py`, `script/run_auto_heal.py`).
3. **Bonus B3 (+5đ):** Bộ kiểm thử tự động Pytest với 6 unit tests (`tests/`) chạy trong 5.5s đạt **6/6 PASSED** chuẩn CI/CD.

---

## PHẦN 3: KỊCH BẢN THAO TÁC TERMINAL TRONG BUỔI DEMO (1 - 2 PHÚT)

Khi lên bảng demo, bạn có thể mở sẵn 2 cửa sổ: **Trình duyệt (Dashboard)** và **Terminal (PowerShell)**:

### Bước 1: Trình diễn kiểm thử tự động toàn diện (Pytest)
Gõ lệnh:
```powershell
.\.venv\Scripts\pytest.exe tests/ -v
```
👉 *Chỉ vào màn hình:* **6 passed** — Minh chứng code được bảo vệ bằng unit test tự động.

### Bước 2: Chạy luồng kiểm định Phase 1 (Baseline Pipeline)
Gõ lệnh:
```powershell
python script/run_phase1.py
```
👉 *Chỉ vào màn hình:* Pipeline chạy 5 giai đoạn, in ra `[SUCCESS] Phase 1 pipeline completed successfully. Hit Rate: 100.0%, Mean Token F1: 1.0000`.

### Bước 3: Chạy luồng Tiêm lỗi & Tự Phục Hồi (Phase 2 Flow)
Gõ lệnh:
```powershell
python script/run_corruption_flow.py
```
👉 *Chỉ vào terminal:*
1. Dòng thông báo tiêm 6 lỗi & Quality check FAILED.
2. Bảng kết quả RAG sụt giảm: Hit Rate rớt xuống 60%.
3. Dòng thông báo kích hoạt **Idempotent Repair** từ Raw records.
4. Bảng tổng kết 3 trạng thái: Hit Rate và F1 phục hồi lại **100%**.

---

## PHẦN 4: BỘ CÂU HỎI PHẢN BIỆN (Q&A CHEAT SHEET)

Dưới đây là các câu hỏi Giảng viên rất hay hỏi và câu trả lời chuẩn xác để lấy điểm tối đa:

### Q1: Tại sao nhóm lại chọn Great Expectations 1.x "Ephemeral Mode" thay vì tạo folder cấu hình YAML?
> **Trả lời:**  
> *"Thưa thầy/cô, Great Expectations 1.x khuyến nghị sử dụng **Ephemeral Mode** (Code-first in RAM) cho các data pipeline hiện đại. Nó giúp:  
> 1. Không bị phụ thuộc vào các đường dẫn tuyệt đối trong file YAML tĩnh khi chia sẻ dự án giữa các máy tính khác nhau.  
> 2. Tốc độ kiểm định cực nhanh (dưới 0.3s) vì dữ liệu xử lý trực tiếp trên RAM, không phải đọc ghi ổ đĩa liên tục.  
> 3. Tích hợp trực tiếp và liền mạch vào các framework CI/CD và Orchestrator như Airflow hoặc Prefect."*

### Q2: Hiện tượng "Silent Failure" là gì và tại sao các công cụ APM truyền thống lại bó tay?
> **Trả lời:**  
> *"Dạ, Silent Failure là hiện tượng chất lượng suy giảm ngầm nhưng không làm sập ứng dụng. Mã HTTP trả về vẫn là 200 OK, latency vẫn ổn định. Các công cụ giám sát hạ tầng như Datadog hay Prometheus chỉ kiểm tra xem service có sống không (Liveness check), chứ không thể hiểu được ngữ nghĩa của câu trả lời. Chỉ có **Data Observability** (kiểm định độ dài, tính duy nhất, freshness ở đầu vào) và **RAG Evaluation** (đo lường Hit Rate, Token F1, LLM Judge ở đầu ra) mới phát hiện được hiện tượng này."*

### Q3: Vì sao phải phục hồi từ Raw Snapshot mà không sửa trực tiếp (In-place) trên file bị lỗi?
> **Trả lời:**  
> *"Dạ, trong nguyên lý MLOps và Data Engineering, việc sửa chắp vá (In-place patching) là một anti-pattern vì tiềm ẩn rủi ro sót lỗi và gây ô nhiễm trạng thái (State Pollution). Ngược lại, **Idempotent Replay** lấy raw snapshot bất biến làm nguồn chân lý duy nhất (Single Source of Truth). Dù dữ liệu có bị phá hủy hay tiêm 100 loại lỗi khác nhau, việc chạy lại quy trình làm sạch từ nguồn gốc luôn luôn đảm bảo đầu ra sạch 100% và có tính tái lập hoàn toàn."*

### Q4: Vì sao phải cố định bộ Test Set 10 câu hỏi cho cả 3 lần đo Baseline, Corrupted và Repaired?
> **Trả lời:**  
> *"Dạ, đây là nguyên tắc biến kiểm soát (Controlled Experiment) trong phương pháp nghiên cứu khoa học. Nếu ta thay đổi câu hỏi giữa các lần đo, sự tăng giảm điểm số có thể do độ khó của câu hỏi thay vì chất lượng thực sự của dữ liệu. Giữ cố định 10 câu hỏi chuẩn hóa là điều kiện tiên quyết để đánh giá khách quan sự biến động hiệu năng của RAG."*
