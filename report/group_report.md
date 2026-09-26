# Group Report — Day 10: Data Pipeline &amp; Data Observability

## 1. Thông tin bài nộp


| Thông tin       | Nội dung                                                                                                                                                 |
| --------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Khóa/Lớp        | K4 — `K4-L3B-DAY10`                                                                                                                                      |
| Tên nhóm        | Flex                                                                                                                                                     |
| Repository      | [https://github.com/thihngD/K4-L3B-DAY10-Flex-DataPipelineDataObservability](https://github.com/thihngD/K4-L3B-DAY10-Flex-DataPipelineDataObservability) |
| Ngày hoàn thành | 2026-09-26                                                                                                                                               |


### Thành viên và phân công


| STT | Họ và tên            | MSSV        | Vai trò chính                                    | Module/deliverable sở hữu                                                                                                                                                              |
| ---: | -------------------- | ----------- | ------------------------------------------------ | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 1   | Nguyễn Danh Gia Minh | 2A202602441 | M1 — Source &amp; Corruption owner               | `src/ingestion/crossref.py`, `src/ingestion/corruption.py`, `data/raw/` · contract C1, C5                                                                                              |
| 2   | Trần Đình Hinh       | 2A202602399 | M2 — Data model &amp; Eval-set owner             | `src/ingestion/cleaning.py`, `src/evaluation/testset.py` · contract C2, C3                                                                                                             |
| 3   | Nguyễn Đức Thịnh     | 2A202602468 | M3 — Observability &amp; Reporting owner         | `src/observability/quality.py`, `src/observability/reporting.py` · contract C4, C6-§3; bộ contract `docs/rules/`                                                                       |
| 4   | Văn Quốc Dũng        | 2A202602505 | M4 — Trưởng nhóm, Integration &amp; Repair owner | `src/pipelines/phase1.py`, `src/pipelines/corruption_flow.py`, `tests/test_pipelines.py`, toàn bộ artifact `data/{clean,chroma,embeddings,eval,quality,results,reports}` · contract C6 |


Chi tiết tự khai của từng thành viên: [`docs/TEAM.md`](../docs/TEAM.md) và các báo cáo cá nhân trong thư mục `report/`.

## 2. Tóm tắt kết quả

**Tóm tắt của nhóm:**

Nhóm Flex đã hoàn thành toàn bộ luồng bắt buộc: ingestion Crossref (snapshot-first, retry/backoff, fallback), cleaning theo contract C2, embedding `all-MiniLM-L6-v2` với ChromaDB, bộ benchmark 10 câu cố định, Quality Gate Great Expectations 1.x (8 expectation + `freshness_sla`), Freshness SLA, 6 kịch bản corruption, repair từ raw và báo cáo đối chiếu 3 trạng thái.

Baseline tạo đủ 12 artifact liệt kê trong `phase1_report.md` §5 (raw, clean 24 dòng, embeddings, collection `papers-baseline`, test set, metrics, answers, quality/freshness report, report). Baseline đạt `retrieval_hit_rate`, `mean_token_f1`, `judge_accuracy` = 1.0000, quality 9/9, `is_fresh = True`.

Corruption làm quality gate còn 3/9 và freshness chuyển sang `False` (`stale_ratio` 0.0417 → 0.2857). Tác động rõ nhất lên agent là `truncate_title`: tiêu đề bị cắt còn 6 ký tự khiến tra cứu tiêu đề chính xác thất bại, agent trả lời theo bài gần giống (q03 sai ngày, q05 trả lời rỗng). `drop_latest_records` làm mất tài liệu ground truth của q02. Ba metric chính giảm còn 0.8000, `mean_judge_score` 5.0 → 4.2.

Repair dựng lại từ `data/raw/crossref_records.json` với cùng `run_date` của baseline; dữ liệu repaired trùng từng byte với baseline và phục hồi 100% mọi metric và check.

Giới hạn lớn nhất: đánh giá chạy với `LLM_PROVIDER=mock` nên judge là heuristic fallback, Ragas chưa chạy, và benchmark chỉ có 10 câu nên mỗi câu tương ứng 0.1 điểm metric.

## 3. Kiến trúc và luồng dữ liệu

### Luồng end-to-end

```text
Crossref API (snapshot-first; refresh → retry/backoff → fallback snapshot)
    -> data/raw/crossref_response.json + crossref_records.json      (M1)
    -> build_clean_dataframe(records, run_date)                      (M2)
    -> data/clean/papers_clean.{json,csv}  (24 dòng × 16 cột)
    -> MiniLM embedding + ChromaDB collection papers-baseline        (M4 gọi index)
    -> test_set.json (đóng băng) -> evaluate baseline                 (M2 test set, M4 orchestrate)
    -> GX 1.x quality gate + freshness report -> phase1_report.md    (M3)
    -> baseline_run.json (run_date + SHA-256 raw/clean/test set)     (M4)
    ─── script/run_corruption_flow.py ─────────────────────────────
    -> kiểm tra manifest -> corrupt_clean_dataframe (6 kịch bản)     (M1)
    -> papers-corrupted: re-index + re-evaluate + quality/freshness
    -> repair: load_raw_records -> build_clean_dataframe(run_date baseline) -> verify   (M4)
    -> papers-repaired: re-index + re-evaluate + quality/freshness
    -> corruption_report.md (bảng 3 trạng thái)                       (M3)
```

### Trách nhiệm của từng khối


| Khối              | Input                                                                                                     | Xử lý chính                                                                                                                                                                                                                         | Output/artifact                                                                                                            | Owner                                          |
| ----------------- | --------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------- |
| Ingestion         | Crossref REST API (query + filter trong `core/config.py`) hoặc snapshot `data/raw/crossref_response.json` | Snapshot-first; khi `REFRESH_SOURCE=1`: timeout, retry tối đa 3 lần (backoff 1/2/4 giây) cho 429/5xx, fallback snapshot; parse bỏ tag JATS/HTML, ghép tác giả, chuẩn hóa ngày `YYYY-MM-DD`; bỏ record thiếu DOI/title/abstract/ngày | `data/raw/crossref_response.json`, `data/raw/crossref_records.json` (24 records)                                           | Nguyễn Danh Gia Minh (M1)                      |
| Cleaning          | `list[PaperRecord]` + `run_date` UTC do M4 truyền                                                         | Chuẩn hóa text, lọc dòng rỗng, dedupe `paper_id`, tính `age_days`, sinh `text_for_embedding` 5 phần, sort cố định, không `None`/`NaN`                                                                                               | `data/clean/papers_clean.{json,csv}`                                                                                       | Trần Đình Hinh (M2)                            |
| Embedding/index   | Clean DataFrame                                                                                           | `sentence-transformers/all-MiniLM-L6-v2`, ChromaDB persist tại `data/chroma/`, dựng lại collection mỗi lần chạy, `top_k = 4`                                                                                                        | `data/chroma/`, `data/embeddings/papers_embeddings{,_corrupted,_repaired}.json`                                            | Văn Quốc Dũng (M4)                             |
| Evaluation        | Clean DataFrame, index                                                                                    | `build_test_set` 10 câu tất định (3 summary / 3 authors / 2 date / 2 categories); `evaluate_pipeline` tính hit rate, token F1, judge                                                                                                | `data/eval/test_set.json`, `data/results/*_metrics.json`, `*_answers.json`                                                 | Trần Đình Hinh (M2)                            |
| Observability     | DataFrame + `Settings`                                                                                    | GX 1.x ephemeral context: 8 expectation + check `freshness_sla`; freshness report (stale khi `age_days > 180`, tối đa 25% stale); sinh 2 báo cáo Markdown                                                                           | `data/quality/*_quality_report.json`, `*freshness_report.json`, `data/quality/gx/papers_suite_*.json`, `data/reports/*.md` | Nguyễn Đức Thịnh (M3)                          |
| Corruption/repair | Clean baseline (corruption); raw records (repair)                                                         | 6 kịch bản tất định, seed 42, chọn dòng không chồng lấn (M1); repair từ raw với `run_date` baseline và kiểm chứng trùng khớp (M4)                                                                                                   | `data/clean/papers_clean_{corrupted,repaired}.{json,csv}`, `data/results/corruption_log.json`                              | Nguyễn Danh Gia Minh (M1) + Văn Quốc Dũng (M4) |
| Orchestration     | `Settings`/biến môi trường, artifact baseline                                                             | `phase1.main` → `corruption_flow.main`; manifest `baseline_run.json` khóa input bằng SHA-256; từ chối chạy khi thiếu baseline hoặc input đã đổi                                                                                     | `data/reports/*.md`, `data/results/*.json`                                                                                 | Văn Quốc Dũng (M4)                             |


## 4. Cách tái hiện kết quả

### Cấu hình không chứa secret


| Biến/cấu hình             | Giá trị sử dụng                                                              |
| ------------------------- | ---------------------------------------------------------------------------- |
| `LLM_PROVIDER`            | `mock`                                                                       |
| `LLM_MODEL`               | `mock`                                                                       |
| Embedding model           | `sentence-transformers/all-MiniLM-L6-v2`                                     |
| Số lượng Crossref records | 24 (`max_results = 24`; snapshot có `message.total-results = 24`)            |
| Retrieval `top_k`         | 4                                                                            |
| Freshness threshold       | Stale khi `age_days > 180`; đạt SLA khi `stale_ratio ≤ 0.25`                 |
| Random seed, nếu có       | 42 (corruption)                                                              |
| Khác                      | `REFRESH_SOURCE=0`, `REFRESH_TEST_SET=0`, `RUN_RAGAS=0` (xem `.env.example`) |


### Lệnh cài đặt

```bash
uv sync --extra dev
```

### Lệnh chạy

PowerShell, từ thư mục gốc repo:

```powershell
$env:LLM_PROVIDER = 'mock'
$env:LLM_MODEL = 'mock'
$env:REFRESH_SOURCE = '0'
$env:REFRESH_TEST_SET = '0'
$env:RUN_RAGAS = '0'
.venv/Scripts/python.exe script/run_phase1.py
.venv/Scripts/python.exe script/run_corruption_flow.py
.venv/Scripts/python.exe script/run_corruption_flow.py --auto-repair
.venv/Scripts/python.exe dashboard/build_dashboard.py
.venv/Scripts/python.exe -m pytest -q
```

Tương đương với `uv`: `uv run python script/run_phase1.py` rồi `uv run python script/run_corruption_flow.py`.

### Kết quả tái hiện


| Lệnh                        | Trạng thái            | Thời điểm chạy gần nhất                                                     | Bằng chứng                                                                                                            |
| --------------------------- | --------------------- | --------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------- |
| Baseline pipeline           | Thành công            | 2026-09-26 11:25:47 (UTC+7) — `run_date = 2026-09-26T04:25:47.757226+00:00` | `data/results/baseline_run.json`, `data/reports/phase1_report.md`                                                     |
| Corruption flow             | Thành công            | 2026-09-26 11:26:44 (UTC+7) — `corruption_log.generated_at`                 | `data/reports/corruption_report.md`; artifact `papers_clean_repaired.*` chỉ được ghi sau khi `[repair] verified=True` |
| `pytest -q`                 | 28 passed             | Chạy lại tối 2026-09-26                                                     | `tests/test_pipelines.py` (6), `tests/test_auto_repair.py` (19), `tests/test_evaluation.py` (3)                       |
| `script/check_contracts.py` | 14/14 artifact `[OK]` | Chạy lại tối 2026-09-26                                                     | raw, clean (baseline + repaired), testset, 3 freshness, 3 quality, corruption_log, 3 metrics                          |
| Dashboard B1 (`dashboard/build_dashboard.py`) | Thành công | 2026-09-26 23:18 (UTC+7) | `dashboard/index.html`: quality gate, freshness SLA, phân bố `age_days`, cảnh báo drift so với baseline cho 4 trạng thái |


## 5. Ingestion, cleaning và data contract

### Nguồn dữ liệu


| Thuộc tính            | Giá trị                                                                                                                                                                                          |
| --------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| Source                | Crossref REST API (`works`)                                                                                                                                                                      |
| Query/filter          | Query `agentic retrieval augmented generation large language model`; filter `from-pub-date:2026-03-30,has-abstract:true`                                                                         |
| Thời điểm lấy dữ liệu | Snapshot có sẵn trong repo (commit `aa10f99`, 2026-09-25); baseline đọc snapshot lúc `2026-09-26T04:25:47Z` với `fetch_mode = snapshot`                                                          |
| Số record nhận được   | 24 raw records → 24 clean rows                                                                                                                                                                   |
| Cơ chế retry/backoff  | Chỉ khi `REFRESH_SOURCE=1`: retry tối đa 3 lần với backoff 1/2/4 giây cho 429/5xx/timeout, hết lượt thì fallback snapshot. M1 kiểm chứng bằng mock timeout (4 request, fallback trả 24 records). |


### Raw và clean schema

Clean schema gồm đúng 16 cột theo thứ tự `CLEAN_COLUMNS` (C2-§2); không ô nào là `None`/`NaN` — giá trị thiếu dùng chuỗi rỗng `""`.


| Trường                                                         | Kiểu dữ liệu       | Bắt buộc? | Ý nghĩa                                               | Xử lý khi thiếu/sai                                                                |
| -------------------------------------------------------------- | ------------------ | --------- | ----------------------------------------------------- | ---------------------------------------------------------------------------------- |
| `paper_id`                                                     | `str` (DOI)        | Có        | Định danh tài liệu, dùng làm ground truth             | Rỗng → loại dòng; trùng → giữ bản đầu (`keep="first"`)                             |
| `title`                                                        | `str`              | Có        | Tiêu đề, dùng cho tra cứu chính xác trong QA          | Rỗng → loại dòng; GX yêu cầu `len ≥ 8`                                             |
| `summary`                                                      | `str`              | Có        | Abstract đã bỏ tag JATS/HTML                          | Rỗng → loại dòng; GX yêu cầu `len ≥ 50` và không chứa chuỗi nhiễu `[@#$%&*~^]{4,}` |
| `authors`, `categories`                                        | `list[str]`        | Không     | Danh sách tác giả/chủ đề                              | Thiếu → danh sách rỗng                                                             |
| `published`                                                    | `str` `YYYY-MM-DD` | Có        | Ngày xuất bản, giữ dạng chuỗi                         | Record không có ngày hợp lệ bị M1 loại ở bước parse                                |
| `updated`, `abs_url`, `pdf_url`, `comment`, `primary_category` | `str`              | Không     | Metadata phụ                                          | Thiếu → `""`                                                                       |
| `age_days`                                                     | `int`              | Có        | Số ngày từ `published` đến `run_date`                 | `max(0, …)`; dùng cho freshness                                                    |
| `authors_joined`, `categories_joined`                          | `str`              | Có        | `", ".join(...)`, dùng trả lời câu authors/categories | Suy ra từ list                                                                     |
| `summary_chars`                                                | `int`              | Có        | `len(summary)`                                        | Suy ra từ `summary`                                                                |
| `text_for_embedding`                                           | `str`              | Có        | Văn bản 5 phần đưa vào embedding                      | Suy ra, xem bên dưới                                                               |


### Quy tắc cleaning

Dòng log của lần chạy: `[cleaning] input=24 dropped_invalid=0 dropped_duplicates=0 output=24`.


| Quy tắc                                                                | Quality dimension liên quan | Số record bị tác động              | Cách xác minh                                     |
| ---------------------------------------------------------------------- | --------------------------- | ----------------------------------: | ------------------------------------------------- |
| Chuẩn hóa `title`/`summary`: bỏ tag sót, gom khoảng trắng (idempotent) | Validity                    | Áp dụng mọi dòng (không đếm riêng) | `check_contracts.py clean` → `[OK]`               |
| Loại dòng có `paper_id`/`title`/`summary` rỗng                         | Completeness                | 0                                  | `dropped_invalid=0`                               |
| Dedupe theo `paper_id`, giữ bản đầu                                    | Uniqueness                  | 0                                  | `dropped_duplicates=0`; GX `paper_id_unique` pass |
| Tính `age_days` theo `run_date` UTC                                    | Timeliness                  | 24                                 | `freshness_report.json`                           |
| Sort `published` giảm dần rồi `paper_id` tăng dần                      | Consistency (tái lập)       | 24                                 | Chạy lại cho JSON trùng từng byte                 |


`**text_for_embedding`, document ID và `age_days`:** `text_for_embedding` ghép cố định 5 dòng `Title: … / Authors: … / Published: … / Categories: … / Summary: …` qua hàm dùng chung `compose_text_for_embedding` (M1 cũng dùng hàm này khi tính lại văn bản sau corruption). Document ID là DOI Crossref (`paper_id`), giữ nguyên từ raw đến index và test set. `age_days = max(0, (run_date.date() − published).days)`; `run_date` do pipeline truyền vào một lần cho mỗi baseline (cleaning không tự gọi `now()`) và được lưu trong `baseline_run.json` để repair dùng lại.

## 6. Evaluation setup


| Thành phần                            | Cấu hình thực tế                                                                                                                                               |
| ------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Số câu hỏi                            | 10                                                                                                                                                             |
| Các `question_type`                   | `summary` (3), `authors` (3), `date` (2), `categories` (2)                                                                                                     |
| Ground-truth document ID              | Chọn tất định: sort bài theo `paper_id`, lấy vị trí `round(i × (N − 1) / 9)`; mỗi câu lưu `ground_truth_doc_ids = [paper_id]`. Hit khi DOI này nằm trong top-k |
| Embedding model                       | `sentence-transformers/all-MiniLM-L6-v2`                                                                                                                       |
| Vector store/collection               | ChromaDB persist `data/chroma/`; `papers-baseline`, `papers-corrupted`, `papers-repaired`                                                                      |
| Retrieval `top_k`                     | 4                                                                                                                                                              |
| LLM provider/model                    | `mock` / `mock` (judge dùng heuristic fallback theo token F1)                                                                                                  |
| Test set dùng chung cho ba trạng thái | `data/eval/test_set.json`, SHA-256 `c74629783d6a6c2ad1bfbc3e3c60bfb724e3e55a08d0102c7013bcaafb796c8e`                                                          |


**Vì sao giữ nguyên test set:** mục tiêu là đo tác động của dữ liệu, nên dữ liệu phải là biến duy nhất thay đổi giữa ba trạng thái. Nếu sinh lại câu hỏi từ dữ liệu corrupted, câu hỏi sẽ trỏ tới tiêu đề đã bị cắt hoặc bài đã bị xóa, và chênh lệch metric không còn phân biệt được do dữ liệu hay do đề. `phase1.py` chỉ tạo test set khi file chưa tồn tại hoặc `REFRESH_TEST_SET=1`; `corruption_flow.py` so SHA-256 của test set với manifest và dừng nếu khác.

## 7. Kết quả baseline

### Artifact checklist


| Artifact                 | Đường dẫn thực tế                    | Trạng thái | Ghi chú                                          |
| ------------------------ | ------------------------------------ | ---------- | ------------------------------------------------ |
| Raw response/records     | `data/raw/`                          | Có         | 24 records, `check_contracts raw` OK             |
| Cleaned dataset          | `data/clean/`                        | Có         | Baseline + corrupted + repaired (JSON/CSV)       |
| Embedding manifest/index | `data/embeddings/`, `data/chroma/`   | Có         | 3 manifest + 3 collection Chroma                 |
| Evaluation set           | `data/eval/`                         | Có         | 10 câu, `check_contracts testset` OK             |
| Baseline metrics         | `data/results/baseline_metrics.json` | Có         | Kèm `baseline_answers.json`, `baseline_run.json` |
| Quality/freshness        | `data/quality/`                      | Có         | 3 quality report, 3 freshness report, 3 GX suite |
| Baseline report          | `data/reports/phase1_report.md`      | Có         | Sinh tự động từ pipeline                         |


### Baseline metrics


| Metric               | Giá trị | Diễn giải                                                                                                                                                                                |
| -------------------- | -------: | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `retrieval_hit_rate` | 1.0000  | Cả 10 câu có tài liệu ground truth trong top-4. Câu hỏi chứa tiêu đề đặt trong nháy đơn và router tra cứu tiêu đề chính xác trước khi tìm vector, nên trên dữ liệu sạch đây là mức trần. |
| `mean_token_f1`      | 1.0000  | Câu trả lời trích nguyên trường metadata (authors/date/categories) hoặc câu đầu của summary, trùng khớp ground truth.                                                                    |
| `judge_accuracy`     | 1.0000  | 10/10 câu được judge chấm đúng. Judge là heuristic fallback do provider `mock`, không phải LLM judge thật.                                                                               |
| `mean_judge_score`   | 5.0000  | Mọi câu đạt điểm tối đa 5.                                                                                                                                                               |
| Ragas, nếu có        | N/A     | `RUN_RAGAS=0`: `{"skipped": "Set RUN_RAGAS=1 to enable the slower Ragas pass."}`                                                                                                         |


Baseline đạt trần nên chủ yếu xác nhận pipeline đưa đúng dữ liệu vào index; ý nghĩa nằm ở mức suy giảm khi dữ liệu hỏng (§10).

## 8. Data quality và freshness

### Quality checks

Suite `papers_suite_baseline`: success = True, passed 9/9, row count = 24. Bằng chứng: `data/quality/baseline_quality_report.json`, `data/quality/gx/papers_suite_baseline.json`.


| Check               | Quality dimension     | Ngưỡng/kỳ vọng                   | Kết quả baseline | Bằng chứng                     |
| ------------------- | --------------------- | -------------------------------- | ---------------- | ------------------------------ |
| `row_count`         | Volume                | `23..24` (`ceil(0.95 × 24)`..24) | Pass — 24        | `baseline_quality_report.json` |
| `paper_id_not_null` | Completeness          | không null                       | Pass — 0.0000    | như trên                       |
| `title_not_null`    | Completeness          | không null                       | Pass — 0.0000    | như trên                       |
| `summary_not_null`  | Completeness          | không null                       | Pass — 0.0000    | như trên                       |
| `paper_id_unique`   | Uniqueness            | unique                           | Pass — 0.0000    | như trên                       |
| `title_length`      | Validity              | `len ≥ 8`                        | Pass — 0.0000    | như trên                       |
| `summary_length`    | Completeness/Validity | `len ≥ 50`                       | Pass — 0.0000    | như trên                       |
| `summary_no_noise`  | Validity              | không khớp `[@#$%&*~^]{4,}`      | Pass — 0.0000    | như trên                       |
| `freshness_sla`     | Timeliness            | tỷ lệ `age_days > 180` ≤ 0.25    | Pass — 0.0417    | như trên                       |


Giá trị "observed" của các check theo cột là % dòng vi phạm.

### Freshness


| Thuộc tính            | Giá trị                                                                                                       |
| --------------------- | ------------------------------------------------------------------------------------------------------------- |
| Freshness được đo tại | Clean dataset đưa vào index (`age_days` tính theo `run_date` baseline) — `data/quality/freshness_report.json` |
| Timestamp mới nhất    | `latest_published = 2026-07-22` (cũ nhất `2026-03-28`)                                                        |
| Ngưỡng freshness      | 180 ngày; tối đa 25% dòng stale                                                                               |
| Trạng thái baseline   | Fresh (`is_fresh = True`)                                                                                     |
| Lý do                 | 1/24 dòng quá 180 ngày → `stale_ratio = 0.0417 ≤ 0.25`                                                        |


## 9. Corruption scenarios và repair

Seed 42, input 24 dòng → output 21 dòng; các kịch bản chọn dòng không chồng lấn nên mỗi dòng chỉ chịu một loại lỗi.


| Corruption            | Cách tạo                              | Record bị tác động | Quality signal kỳ vọng                             | Tác động thực tế                                                                                                                                       | Cách repair     |
| --------------------- | ------------------------------------- | ------------------: | -------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------ | --------------- |
| `drop_latest_records` | Xóa 20% bài mới nhất (`fraction=0.2`) | 5                  | `row_count` fail                                   | `row_count` fail (21, ngoài 23..24). Mất tài liệu ground truth của q02 → retrieval miss                                                                | Dựng lại từ raw |
| `blank_summary`       | Đặt `summary = ""`                    | 3                  | `summary_length` fail; `summary_not_null` vẫn pass | Đúng kỳ vọng: `summary_length` fail (14.2857%), `summary_not_null` pass — silent failure. Góp phần làm q05 trả lời rỗng                                | Dựng lại từ raw |
| `inject_noise`        | Chèn `@#$%&*~^` vào summary           | 3                  | `summary_no_noise` fail                            | `summary_no_noise` fail (14.2857%). Không đổi câu trả lời nào trong benchmark                                                                          | Dựng lại từ raw |
| `truncate_title`      | Cắt tiêu đề còn 6 ký tự               | 3                  | `title_length` fail                                | `title_length` fail (14.2857%). 3 câu hỏi trỏ vào bài bị cắt: q03 sai, q05 sai, q10 vẫn đúng                                                           | Dựng lại từ raw |
| `stale_date`          | Lùi `published` 400 ngày              | 6                  | `freshness_sla` fail                               | `stale_ratio` 0.2857 &gt; 0.25 → `freshness_sla` fail, `is_fresh = False`. Không câu hỏi `date` nào trỏ vào bài bị lùi ngày nên không đổi metric agent | Dựng lại từ raw |
| `duplicate_rows`      | Nhân bản nguyên dòng                  | 2                  | `paper_id_unique` fail                             | `paper_id_unique` fail (19.0476% = 4/21 dòng). Không đổi câu trả lời                                                                                   | Dựng lại từ raw |


Corruption log:

- Đường dẫn: `data/results/corruption_log.json`
- Trạng thái: Có (`check_contracts corruption_log` → `[OK]`)
- Nhận xét: Log có `seed`, `input_rows`/`output_rows`, `generated_at` và với mỗi kịch bản: tên, mô tả, tham số, số dòng bị tác động và danh sách `affected_paper_ids` — đủ để truy từng câu trả lời sai về đúng kịch bản gây ra.

**Repair từ nguồn đáng tin cậy:** repair không "sửa ngược" dữ liệu corrupted (không thể khôi phục summary đã xóa hay 5 bài đã bị drop). Thay vào đó `corruption_flow.py` đọc lại `data/raw/crossref_records.json` bằng `load_raw_records`, chạy lại `build_clean_dataframe` với đúng `run_date` lưu trong `baseline_run.json`, không gọi mạng. Trước khi index, pipeline kiểm chứng repaired có cùng số dòng, cùng tập `paper_id`, cùng toàn bộ nội dung và cùng `age_days` với baseline; nếu không khớp thì dừng với `SystemExit`. Mỗi lần chạy dựng lại collection nên chạy nhiều lần không tích lũy bản ghi trùng. Kết quả: `papers_clean_repaired.json` trùng từng byte với `papers_clean.json`, và chạy corruption flow hai lần liên tiếp cho metrics giống nhau.

## 10. So sánh baseline, corrupted và repaired

Số liệu Baseline, Corrupted, Repaired chép từ `data/reports/corruption_report.md` §1. Cột Auto-repair B2 lấy từ [metrics](../data/auto_repair/20260926T154257352219Z-59897f5e/repaired_metrics.json) và [quality report](../data/auto_repair/20260926T154257352219Z-59897f5e/quality/repaired_quality_report.json) của run B2 (xem mục Bonus B2 bên dưới).


| Metric/signal            | Baseline | Corrupted | Repaired | Auto-repair B2 | Thay đổi do corruption | Mức phục hồi | Nhận xét                                                  |
| ------------------------ | --------: | ---------: | --------: | --------------: | ----------------------: | ------------: | --------------------------------------------------------- |
| `retrieval_hit_rate`     | 1.0000   | 0.8000    | 1.0000   | 0.9000         | -0.2000                | 100.0%       | Miss ở q02 (bài bị drop) và q05 (tiêu đề bị cắt); B2 còn miss q02 |
| `mean_token_f1`          | 1.0000   | 0.8000    | 1.0000   | 0.8000         | -0.2000                | 100.0%       | Sai ở q03 và q05 — không trùng với tập câu miss retrieval; B2 vẫn sai 2 câu này |
| `judge_accuracy`         | 1.0000   | 0.8000    | 1.0000   | 0.8000         | -0.2000                | 100.0%       | Cùng 2 câu q03, q05                                       |
| `mean_judge_score`       | 5.0000   | 4.2000    | 5.0000   | 4.2000         | -0.8000                | 100.0%       | 8 câu × 5 + 2 câu × 1 = 42/10                             |
| Quality checks pass/fail | 9/9      | 3/9       | 9/9      | 7/9            | -6                     | 100.0%       | 6 check fail đúng 6 kịch bản; B2 còn fail `row_count`, `title_length` |
| Freshness status         | True     | False     | True     | True           | `stale_ratio` +0.2440  | 100.0%       | 1/24 → 6/21 → 1/24 dòng stale; B2 1/16                    |

Cột "Thay đổi do corruption" và "Mức phục hồi" tính cho Repaired (repair bắt buộc từ raw). B2 là bonus chỉ dùng chính bảng corrupted: 16 dòng, status `partial`.


**Kết luận nhân quả:**

1. `truncate_title` cắt tiêu đề `3671806` và `3671811` còn `Semant`, `Hybrid` → `title_length` fail (3/21 dòng) → tra cứu tiêu đề chính xác trong `retrieval/qa.py` không tìm thấy, router rơi về top-1 của vector search là bài "Advanced Perspectives on …" cùng chủ đề. Với q03, agent trả ngày `2026-06-06` của bài kia thay vì `2026-05-02`: `token_f1 = 0` dù `retrieval_hit` vẫn True (ground truth ở hạng 2). Với q05, top-1 là `3671823` — bài đã bị `blank_summary` — nên câu trả lời rỗng. Kết quả: `mean_token_f1` và `judge_accuracy` 1.0 → 0.8.
2. `drop_latest_records` xóa 5 bài mới nhất → `row_count = 21` fail → tài liệu ground truth của q02 (`3671804`) biến mất, `retrieval_hit_rate` 1.0 → 0.8 (cùng q05). q02 vẫn được trả lời đúng vì bài anh em `3671816` có cùng tác giả, cho thấy hit rate và answer metric có thể lệch nhau — cần theo dõi cả hai.
3. Repair dựng lại từ raw với `run_date` baseline → dữ liệu trùng từng byte với baseline, quality 9/9 và `stale_ratio` 0.0417 → mọi metric agent trở về 1.0000, phục hồi 100%.

Kết quả khác kỳ vọng: `stale_date`, `inject_noise` và `duplicate_rows` làm quality/freshness gate báo lỗi nhưng không làm giảm metric agent, vì không câu hỏi nào dùng trường bị hỏng của các bài đó (nhiễu nằm trong summary nhưng câu hỏi về bài đó hỏi ngày; bài bị lùi ngày không có câu hỏi `date`). Đây là lý do quality gate cần chạy độc lập với benchmark: benchmark nhỏ không bao phủ hết lỗi dữ liệu.

### Bonus B2: auto-repair từ bảng corrupted

`script/run_corruption_flow.py --auto-repair` kiểm tra lại `data/clean/papers_clean_corrupted.json`; khi gate fail, pipeline tự sửa từng record chỉ bằng dữ liệu của chính bảng (không đọc raw snapshot, baseline hay corruption log, không gọi mạng), kiểm định lại rồi publish ở trạng thái `completed` hoặc `partial`. Run `20260926T154257352219Z-59897f5e` (22:42 UTC+7), provider `mock` (judge heuristic), status `partial`; số liệu nằm trong cột Auto-repair B2 của bảng trên. Số dòng 21 → 16. Hit rate tăng 0.8 → 0.9 vì q05 vào lại top-4 khi bỏ 2 dòng summary rỗng chiếm chỗ. Sửa được từ bảng: 2 dòng trùng, nhiễu ở 3 summary (1 summary còn từ `semantic` bị tách thành `sema ntic`) và 6 ngày xuất bản. Không sửa được: 5 dòng bị xóa và 3 tiêu đề bị cắt, vì dữ liệu không còn dấu vết nào của chúng; đây là lý do repair bắt buộc phải dựng lại từ raw. Chi tiết: [AUTO_REPAIR.md](../docs/AUTO_REPAIR.md), [repair log](../data/auto_repair/20260926T154257352219Z-59897f5e/repair_log.json).

## 11. Vấn đề tích hợp quan trọng

- **Triệu chứng:** Repair dựng lại từ raw nhưng dùng thời điểm hiện tại làm `run_date` sẽ cho `age_days` khác baseline ngay khi sang ngày khác — tái hiện: cùng raw, `run_date` lùi thêm 1 ngày cho 24/24 dòng có `age_days` khác baseline. Khi đó bước kiểm chứng nội dung thất bại và freshness của repaired không còn so sánh được với baseline. Tương tự, nếu test set, raw hoặc clean bị thay đổi giữa hai lệnh, bảng 3 trạng thái sẽ so sánh các input khác nhau mà không báo lỗi.
- **Nguyên nhân:** `age_days` của M2 phụ thuộc `run_date`; freshness của M3 đọc `age_days`; còn baseline (`run_phase1.py`) và corruption flow là hai lệnh chạy ở hai thời điểm khác nhau, không có gì ràng buộc chúng dùng cùng input và cùng mốc thời gian.
- **Cách xử lý:** `phase1.py` ghi manifest `data/results/baseline_run.json` gồm `run_date` và SHA-256 của raw records, clean JSON, test set. `corruption_flow.py` kiểm tra đủ artifact baseline, so hash và dừng với thông báo "Baseline input changed (…); run script/run_phase1.py first" nếu khác, rồi dùng lại `run_date` của manifest cho repair và kiểm chứng cả `age_days`.
- **Cách xác minh:** `pytest -q tests/test_pipelines.py` → 6 passed, gồm test chạy baseline → corruption → repair hai lần cho kết quả giống nhau, test thiếu baseline, 3 test sửa từng input (test set/raw/clean) bị từ chối, test refresh benchmark có chủ đích. Với lần chạy thật: `cmp papers_clean.json papers_clean_repaired.json` trùng khớp; `[repair] verified=True`.

## 12. Giới hạn và hướng cải thiện


| Giới hạn hiện tại                                                                                                                   | Ảnh hưởng                                                                                                | Hướng cải thiện có thể kiểm chứng                                                                                                    |
| ----------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------ |
| (M1) Lần chạy chính thức dùng snapshot; nhánh gọi Crossref live chỉ được kiểm bằng mock                                             | Chưa có bằng chứng retry/fallback với lỗi mạng thật                                                      | Bổ sung pytest cho parser (ngày thiếu tháng/ngày, JATS/HTML, record thiếu trường) và retry/fallback; đo bằng coverage                |
| (M2) `text_for_embedding` là nối chuỗi 5 phần cố định                                                                               | Summary dài bị embed chung một vector, khó phân biệt các bài "Advanced Perspectives on …" gần giống nhau | Thử semantic chunking; so `retrieval_hit_rate` trên cùng test set trước/sau                                                          |
| (M3) Ngưỡng check cố định cho snapshot 24 bài (`row_count 23..24`, `title ≥ 8`, `summary ≥ 50`); gate chỉ báo cáo, không chặn index | Khi refresh live số bài thay đổi có thể báo động giả; dữ liệu fail gate vẫn được index                   | Tham số hóa ngưỡng theo baseline; thêm chế độ gate chặn index khi fail; kiểm bằng lần chạy corrupted phải dừng trước bước index      |
| (M4) Đánh giá với `LLM_PROVIDER=mock`: judge heuristic, Ragas tắt; benchmark 10 câu                                                 | Mỗi câu = 0.1 điểm metric; chưa đo chất lượng sinh câu trả lời của LLM thật                              | Chạy lại với provider thật và `RUN_RAGAS=1` trên cùng test set; mở rộng benchmark để mọi kịch bản corruption có câu hỏi bị ảnh hưởng |


## 13. Checklist trước khi nộp

- [x] Thông tin nhóm và repository chính xác.
- [x] Phân công khớp với module, artifact và kết quả thực tế.
- [x] Lệnh tái hiện đã được chạy lại trên phiên bản dùng để nộp.
- [x] Baseline, corrupted và repaired dùng cùng evaluation set.
- [x] Bảng metrics khớp với các file trong `data/results/`.
- [x] Quality/freshness conclusions khớp với `data/quality/`.
- [x] Các đường dẫn báo cáo và artifact truy cập được.
- [ ] Mỗi thành viên đã hoàn thành báo cáo vai trò riêng.
- [x] Không có `.env`, API key, token hoặc secret trong source, report, log hay ảnh.

