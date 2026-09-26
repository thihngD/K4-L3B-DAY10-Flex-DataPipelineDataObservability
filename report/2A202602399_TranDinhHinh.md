# Member Role Report — Day 10: Data Pipeline & Data Observability

## 1. Thông tin cá nhân

| Thông tin         | Nội dung                                                                 |
| ----------------- | ------------------------------------------------------------------------ |
| Họ và tên         | Trần Đình Hinh                                                           |
| MSSV              | 2A202602399                                                              |
| Khóa/Lớp          | K4 / K4-L3B-DAY10                                                        |
| Tên nhóm          | Flex                                                                    |
| Vai trò chính     | **M2 — Data model & Eval-set owner**                                     |
| Repository        | `https://github.com/thihngD/K4-L3B-DAY10-Flex-DataPipelineDataObservability` |
| Ngày hoàn thành   | 2026-09-26                                                               |

---

## 2. Vai trò và phạm vi công việc

### Phần việc sở hữu

| Module/deliverable | File/hàm phụ trách | Input nhận vào | Output bàn giao | Trạng thái |
| :--- | :--- | :--- | :--- | :--- |
| **Data Cleaning & Modeling (C2)** | `src/ingestion/cleaning.py`<br>- `CLEAN_COLUMNS`<br>- `compose_text_for_embedding`<br>- `build_clean_dataframe` | `list[PaperRecord]` từ C1 (snapshot `crossref_records.json`), `run_date: datetime` | DataFrame 16 cột chuẩn C2, hàm `compose_text_for_embedding` | Hoàn thành 100% |
| **Evaluation Test Set (C3)** | `src/evaluation/testset.py`<br>- `build_test_set` | Clean DataFrame (C2), `output_path` | `data/eval/test_set.json` (10 câu hỏi benchmark chuẩn C3) | Hoàn thành 100% |

### Việc hỗ trợ ngoài phạm vi chính

| Hoạt động | Thành viên/module được hỗ trợ | Kết quả |
| :--- | :--- | :--- |
| Hỗ trợ hợp đồng C2 cho Data Corruption | M1 (`src/ingestion/corruption.py`) | Bàn giao sớm `compose_text_for_embedding` và cấu trúc 16 cột để M1 viết 6 kịch bản tiêm lỗi không bị lệch format. |
| Hỗ trợ hợp đồng C2 cho Observability | M3 (`src/observability/quality.py`) | Đảm bảo DataFrame không có `None`/`NaN`, cột `age_days` tính chuẩn để 9 kiểm định của Great Expectations và Freshness SLA chạy thành công. |
| Hỗ trợ test set cho Integration | M4 (`src/pipelines/phase1.py`) | Đảm bảo test set 10 câu bọc đúng nháy đơn `'{title}'` để QA Router trong `retrieval/qa.py` trích xuất chính xác. |

---

## 3. Kết quả theo vai trò

| Nhiệm vụ đã thực hiện | File/hàm/artifact liên quan | Kết quả bàn giao | Cách xác minh |
| :--- | :--- | :--- | :--- |
| Data cleaning, dedupe & embedding format | `src/ingestion/cleaning.py` | 24 dòng sạch, 16 cột đúng `CLEAN_COLUMNS`, tính `age_days` | `python script/check_contracts.py clean` → `[OK]` |
| Deterministic benchmark test set | `src/evaluation/testset.py` | `data/eval/test_set.json` gồm đúng 10 câu qua 4 nhóm nghiệp vụ | `python script/check_contracts.py testset` → `[OK]` |

**Output cụ thể:**
- Log console chuẩn: `[cleaning] input=24 dropped_invalid=0 dropped_duplicates=0 output=24`.
- File test set gồm đúng: 3 câu `summary`, 3 câu `authors`, 2 câu `date`, 2 câu `categories`, tiêu đề được bọc nháy đơn chính xác.

---

## 4. Giải thích phần kỹ thuật đã thực hiện

### Vấn đề cần giải quyết
1. **Chuẩn hóa dữ liệu thô:** Dữ liệu Crossref thô thường chứa các thẻ XML/HTML rác (`<jats:p>`, `<jats:italic>`), khoảng trắng thừa, và có thể chứa bản ghi trùng lặp hoặc thiếu trường cốt lõi. Cần làm sạch triệt để và định hình cấu trúc cố định 16 cột.
2. **Định dạng Text cho Embedding:** Tránh hiện tượng lệch biểu diễn (Representation Drift) bằng cách chuẩn hóa mẫu ghép text 5 phần (`Title`, `Authors`, `Published`, `Categories`, `Summary`).
3. **Bộ câu hỏi đánh giá chuẩn hóa:** Cần một tập test 10 câu mang tính tất định (deterministic) để đánh giá nhất quán hiệu năng RAG qua cả 3 pha: Baseline, Corrupted, và Repaired.

### Cách triển khai
- **Khử trùng lặp và lọc rác $O(N)$:** Dùng `seen_ids: set()` ngay trong vòng lặp duyệt `PaperRecord` để lọc các bản ghi rỗng hoặc trùng DOI (`paper_id`) với chiến lược `keep="first"`.
- **Bảo toàn kiểu dữ liệu ngày:** Sử dụng `date.fromisoformat()` để tính khoảng cách `age_days = max(0, (run_date.date() - pub_date).days)`, nhưng vẫn giữ nguyên giá trị `published` ở dạng chuỗi ISO `YYYY-MM-DD` (không ép về `Timestamp`).
- **Sinh test set tất định:** Sắp xếp các bài báo hợp lệ theo `paper_id` tăng dần, chọn vị trí bằng công thức toán học phân bổ đều $\text{idx}_i = \text{round}(i \times (N - 1) / 9)$, gán câu hỏi theo thứ tự tuần hoàn 4 nhóm.

### Input, output và contract

| Thành phần | Mô tả |
| :--- | :--- |
| **Input** | `list[PaperRecord]` từ Contract C1, `run_date: datetime` (UTC) |
| **Output** | DataFrame 16 cột (Contract C2); `test_set.json` 10 items (Contract C3) |
| **Module phụ thuộc** | M1 (`ingestion/crossref.py` qua `PaperRecord`) |
| **Module sử dụng output** | M1 (`corruption.py`), M3 (`quality.py`), M4 (`phase1.py`, `corruption_flow.py`) |
| **Điều kiện lỗi cần xử lý** | Thiếu DOI/Title/Summary, published không đúng format ngày, trùng lặp DOI, giá trị `None`/`NaN`. |

### Cách xác minh
```bash
python script/check_contracts.py clean
python script/check_contracts.py testset
```
- **Kết quả mong đợi:** Cả hai hợp đồng đều báo `[OK]`.
- **Kết quả thực tế:**
  - `[OK] clean: data/clean/papers_clean.json`
  - `[OK] testset: data/eval/test_set.json`

---

## 5. Một quyết định kỹ thuật quan trọng

- **Bối cảnh:** Việc định dạng trường `published` trong Pandas DataFrame và cách ghép chuỗi đưa vào mô hình Embedding.
- **Các phương án đã cân nhắc:**
  1. *Phương án A:* Ép kiểu `published` thành `pd.Timestamp`/`datetime64` để dễ dùng các hàm datetime của Pandas. Ghép embedding tự do tùy tiện trong pipeline.
  2. *Phương án B:* Giữ `published` là chuỗi ISO `YYYY-MM-DD`, tính `age_days` dạng số nguyên `int`, và cố định hàm `compose_text_for_embedding` thành public API cho cả nhóm dùng chung.
- **Phương án đã chọn:** Phương án B.
- **Lý do:** 
  - `pd.Timestamp` khi serialize ra JSON hoặc nạp vào ChromaDB metadata thường bị lỗi không tương thích (ChromaDB chỉ nhận kiểu nguyên thủy: str, int, float, bool).
  - Việc public hàm `compose_text_for_embedding` giúp M1 khi tiêm lỗi dữ liệu (xóa summary, cắt ngắn tiêu đề) có thể gọi lại đúng hàm này để tính lại embedding text, đảm bảo tính nhất quán 100% giữa pha baseline và corrupted.
- **Bằng chứng:** `python script/check_contracts.py clean` → `[OK]` — validator này kiểm tra `published` là chuỗi khớp `^\d{4}-\d{2}-\d{2}$` và `text_for_embedding` đúng định dạng 5 phần. Sau khi ghi `papers_clean.json` và đọc lại bằng `pd.read_json`, cột `published` vẫn là kiểu chuỗi. (Bộ Great Expectations của M3 **không** có check định dạng ngày; không dùng GX làm bằng chứng cho điểm này.)

---

## 6. Một lỗi hoặc blocker đã xử lý

- **Triệu chứng/lỗi nguyên văn:** Khi chạy `python -c "from evaluation.testset import build_test_set..."` để tự kiểm tra độc lập, hệ thống báo lỗi:
  `ModuleNotFoundError: No module named 'chromadb'` phát sinh từ `evaluation/__init__.py`.
- **Lệnh hoặc bước tái hiện:** Chạy test trực tiếp trong môi trường chưa kích hoạt `.venv` đầy đủ dependencies của retrieval.
- **Nguyên nhân gốc:** `evaluation/__init__.py` import cùng lúc `metrics.py` (vốn phụ thuộc vào `chromadb` và `MiniLMEmbeddings`). Trong khi đó, module `testset.py` của M2 hoàn toàn độc lập và chỉ xử lý dữ liệu logic thuần túy với `pandas`.
- **Cách xử lý:** Viết script kiểm tra cô lập nạp trực tiếp `testset.py` để verify độc lập, đồng thời đảm bảo chạy đúng trên môi trường virtualenv chuẩn của dự án có đầy đủ thư viện theo quy ước CP0.
- **Điều học được:** Khi thiết kế các gói thư viện dùng chung trong team, nên tránh side-effect import các module nặng vào `__init__.py` ở top-level nếu các submodule con có thể chạy độc lập.

---

## 7. Hiểu biết về luồng end-to-end

1. **Dữ liệu đi từ Crossref đến vector index:** 
   Crossref REST API trả về JSON thô → M1 parse thành `PaperRecord` (C1) → M2 làm sạch, khử trùng lặp, chuẩn hóa định dạng 5 phần `text_for_embedding` (C2) → M4 đưa vào mô hình `sentence-transformers/all-MiniLM-L6-v2` để sinh vector embeddings và lưu vào ChromaDB collection `papers-baseline`.
2. **Evaluation set và ground-truth document IDs:** 
   Bộ test gồm 10 câu hỏi tiêu biểu đại diện cho 4 tác vụ nghiệp vụ. `ground_truth_doc_ids` chứa ID bài báo chính xác để tính `retrieval_hit_rate` (liệu bài báo đúng có nằm trong top-k trả về không). `ground_truth` chứa câu trả lời chuẩn để tính `mean_token_f1` so sánh độ khớp giữa câu trả lời và thực tế. Câu trả lời do `retrieval/qa.py` trích xuất theo luật từ metadata của tài liệu top-1 (authors/published/categories/câu đầu của summary); LLM chỉ được dùng làm giám khảo cho `judge_accuracy`/`mean_judge_score`.
3. **Quality checks khác freshness monitoring ở điểm nào:** 
   - *Quality checks (Great Expectations):* Kiểm soát tính toàn vẹn về cấu trúc và cú pháp (số lượng dòng, không null, độ dài chuỗi tối thiểu, không chứa ký tự rác, tính duy nhất của ID).
   - *Freshness monitoring:* Kiểm soát tính thời sự của tri thức (tỷ lệ bài báo quá hạn `age_days > 180`). Dữ liệu có thể hoàn toàn sạch và đúng schema nhưng vẫn vi phạm Freshness nếu bài báo quá cũ.
4. **Vì sao phải dùng cùng test set cho 3 trạng thái:** 
   Để đảm bảo tính khoa học và biến kiểm soát duy nhất là **chất lượng dữ liệu**. Nếu thay đổi câu hỏi kiểm thử giữa các pha, ta không thể kết luận được sự suy giảm hiệu năng là do dữ liệu bẩn hay do câu hỏi khó hơn.
5. **Repair được xem là thành công dựa trên:** 
   - *Về mặt dữ liệu:* Tập dữ liệu sau sửa chữa có `set(repaired.paper_id) == set(baseline.paper_id)` và đủ 24 dòng sạch.
   - *Về mặt Observability:* Quality Gate và Freshness SLA chuyển từ `False` (báo động ở corrupted) trở lại `True`.
   - *Về mặt Agent:* Các chỉ số `retrieval_hit_rate` và `mean_token_f1` phục hồi tiệm cận hoặc bằng 100% so với Baseline.

---

## 8. Phân tích kết quả

> ⏳ **Chưa có official run** (M4 chưa chạy `run_phase1.py` / `run_corruption_flow.py`). Bảng chỉ được điền bằng số chép từ `data/reports/corruption_report.md` của official run, kèm hash commit artifact. Không suy diễn từ fixture hay lần chạy thử.

### Metrics chính

| Metric/signal | Baseline | Corrupted | Repaired | Nhận xét của cá nhân M2 |
| :--- | :---: | :---: | :---: | :--- |
| `retrieval_hit_rate` | N/A | N/A | N/A | Chưa có official run |
| `mean_token_f1` | N/A | N/A | N/A | Chưa có official run |
| `judge_accuracy` | N/A | N/A | N/A | Chưa có official run |
| `mean_judge_score` | N/A | N/A | N/A | Chưa có official run |
| Quality checks | N/A | N/A | N/A | Chưa có official run. Kỳ vọng theo C4-§5: 9/9 → 3/9 → 9/9. Lưu ý: summary rỗng `""` **không** bị check not-null bắt, chỉ `summary_length` bắt được. |
| Freshness status | N/A | N/A | N/A | Chưa có official run. Kỳ vọng theo C4-§5: fresh → stale (do `stale_date` lùi `published` 400 ngày) → fresh. |

### Kết luận từ số liệu:
1. Chưa kết luận: cần corrupted quality/freshness report và corrupted metrics từ official run để xác lập chuỗi corruption → quality signal → agent metric.
2. Chưa kết luận: cần repaired quality/freshness report và repaired metrics từ official run để xác định mức phục hồi.

---

## 9. Điều học được và hướng cải thiện

### Ba điều quan trọng nhất:
1. **Tầm quan trọng của Data Contract:** Khi làm việc nhóm với quy mô lớn, việc chốt trước hợp đồng dữ liệu (schema, kiểu dữ liệu, các trường bắt buộc) giúp các thành viên phát triển song song mà không bị phụ thuộc hay gây xung đột mã nguồn.
2. **Data Observability là chốt chặn sống còn:** RAG Agent rất dễ gặp lỗi ngầm (*Silent Failure*) — mô hình vẫn trả lời nhưng câu trả lời sai do dữ liệu nền bị hỏng. Data Quality Gate giúp phát hiện sự cố ngay từ tầng dữ liệu trước khi ảnh hưởng tới người dùng.
3. **Tính Idempotent trong Pipeline:** Cơ chế khôi phục từ nguồn thô (Raw) thay vì cố gắng "sửa chữa ngược" trên dữ liệu bẩn đảm bảo pipeline luôn có thể tái lập và đưa hệ thống về trạng thái tin cậy nhất.

### Hướng cải thiện nếu có thêm thời gian:
- Tích hợp thêm các kỹ thuật **Semantic Chunking** chuyên sâu hơn trong hàm `compose_text_for_embedding` thay vì chỉ nối chuỗi đơn thuần, giúp mô hình embedding nắm bắt ngữ cảnh tốt hơn cho các bài báo khoa học có tóm tắt dài.

---

## 10. Cam kết của thành viên

Đánh dấu sau khi tự kiểm tra:
- [x] Nội dung báo cáo phản ánh đúng phần việc và mức hiểu của tôi.
- [x] Tôi có thể giải thích luồng end-to-end, không chỉ module mình phụ trách.
- [x] Mọi kết luận về kết quả đều có artifact hoặc metric để đối chiếu.
- [x] Tôi không ghi “đã chạy thành công” cho phần chưa được kiểm chứng.
- [x] Báo cáo không chứa `.env`, API key, token hoặc secret.
- [x] Báo cáo này không phải bản sao nguyên văn của báo cáo nhóm hoặc báo cáo thành viên khác.

**Họ và tên:** Trần Đình Hinh  
**Ngày xác nhận:** 2026-09-26  
