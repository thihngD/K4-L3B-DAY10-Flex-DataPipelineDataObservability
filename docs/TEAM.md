# Danh Sách Thành Viên &amp; Báo Cáo Phân Công Nhóm

- **Tên Nhóm:** `Flex`
- **Mã Nhóm / Lớp:** `K4-L3B-DAY10`
- **Tên Repository Nộp Bài:** `K4-L3B-DAY10-Flex-DataPipelineDataObservability`

> Phân công chi tiết, timeline, quy tắc Git và contract input/output giữa các thành viên: [docs/rules/README.md](rules/README.md).

---

## # Thành viên


| STT | Họ và tên            | MSSV        | Email                                                 | Vai trò &amp; Phân công công việc                                                                                                                                     | Báo cáo cá nhân                                                                   |
| ---: | -------------------- | ----------- | ----------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------- |
| 1   | Nguyễn Danh Gia Minh | 2A202602441 | [giaminh10t1@gmail.com](mailto:giaminh10t1@gmail.com) | **M1 — Source &amp; Corruption owner** (`ingestion/crossref.py`, `ingestion/corruption.py`, `data/raw/`) · contract C1, C5 · nhánh `gminh`                            | [`report/2A202602441_NguyenDanhGiaMinh.md`](../report/2A202602441_NguyenDanhGiaMinh.md) |
| 2   | Trần Đình Hinh       | 2A202602399 | [hinh2872@gmail.com](mailto:hinh2872@gmail.com)       | **M2 — Data model &amp; Eval-set owner** (`ingestion/cleaning.py`, `evaluation/testset.py`) · contract C2, C3 · nhánh `TranDinhHinh`                                | [`report/2A202602399_TranDinhHinh.md`](../report/2A202602399_TranDinhHinh.md) |
| 3   | Nguyễn Đức Thịnh     | 2A202602468 | [thihnghldh@gmail.com](mailto:thihnghldh@gmail.com)   | **M3 — Observability &amp; Reporting owner** (`observability/quality.py` GX 1.x + Freshness, `observability/reporting.py`) · contract C4, C6-§3 · nhánh `thihn/02468` | [`report/2A202602468_NguyenDucThinh.md`](../report/2A202602468_NguyenDucThinh.md) |
| 4   | Văn Quốc Dũng        | 2A202602505 | [vvstdung89@gmail.com](mailto:vvstdung89@gmail.com) | **M4 — Trưởng nhóm / Integration &amp; Repair owner** (`pipelines/phase1.py`, `pipelines/corruption_flow.py`, official run &amp; artifacts) · contract C6 · nhánh `VanQuocDung` | [`report/2A202602505_VanQuocDung.md`](../report/2A202602505_VanQuocDung.md) |


---

## # Cá nhân

> Mỗi thành viên **tự khai** mục của mình sau khi hoàn thành (thiếu = −5đ/người). Chỉ ghi phần đã thực sự làm và có commit/artifact chứng minh.

### ## NguyenDanhGiaMinh-2A202602441 — M1 Source &amp; Corruption

- **Phạm vi được giao:** `parse_crossref_payload`, `fetch_source_records` (retry 429/503, fallback snapshot), `load_raw_records`; `corrupt_clean_dataframe` với 6 kịch bản + `corruption_log.json`.
- **Công việc chi tiết đã hoàn thành:** (tóm tắt từ `report/2A202602441_NguyenDanhGiaMinh.md`, commit `d9002a4` — M1 cần tự rà soát lại)
  - `src/ingestion/crossref.py`: parse Crossref (bỏ tag JATS/HTML, ghép tác giả, ngày `YYYY-MM-DD`, URL), snapshot-first; khi refresh thì retry tối đa 3 lần với backoff 1/2/4 giây cho 429/5xx và fallback snapshot. Snapshot trả 24 records, raw records sinh lại không đổi so với bản commit.
  - `src/ingestion/corruption.py`: 6 kịch bản C5 tất định (seed 42, chọn dòng không chồng lấn), dùng `compose_text_for_embedding` của M2; clean thật 24 → 21 dòng, số dòng bị tác động `[5, 3, 3, 3, 6, 2]`, không mutate input, không sinh null.
  - Official `corruption_log.json` chưa có — chờ M4 chạy `corruption_flow`.
- **Điều học được / Đóng góp chính:** Snapshot raw bất biến giúp các module dùng cùng nguồn dữ liệu và cho phép tái dựng pipeline; corruption cần tất định và log rõ records bị tác động để liên hệ thay đổi dữ liệu với quality và RAG metrics.

### ## TranDinhHinh-2A202602399 - M2 Data model &amp; Eval-set

- **Phạm vi được giao:** `build_clean_dataframe` (khử trùng lặp, tính `age_days`, sinh `text_for_embedding` chuẩn 5 phần), `compose_text_for_embedding`, `build_test_set` (10 câu hỏi chuẩn hóa thuộc 4 nhóm nghiệp vụ).
- **Công việc chi tiết đã hoàn thành:** 
  1. Triển khai hoàn thiện Contract C2 trong `src/ingestion/cleaning.py`: Chuẩn hóa văn bản, xử lý triệt để giá trị rỗng/None, dedupe theo `paper_id`, tính `age_days` chuẩn UTC, sort theo `published` desc và `paper_id` asc.
  2. Triển khai hoàn thiện Contract C3 trong `src/evaluation/testset.py`: Xây dựng bộ test set 10 câu tất định, phân bổ 3 summary / 3 authors / 2 date / 2 categories, bọc nháy đơn tiêu đề để khớp router của `qa.py`.
  3. Chạy script kiểm định contract độc lập: Đạt `[OK] clean` và `[OK] testset`.
- **Điều học được / Đóng góp chính:** Nắm vững nguyên tắc Data Contract trong Data Engineering hiện đại; hiểu sâu về việc chuẩn hóa cấu trúc dữ liệu trước khi đưa vào mô hình Embedding nhằm tránh hiện tượng Data Drift; thiết kế bộ Benchmark Test Set mang tính tái lập (deterministic) cho hệ thống RAG.

### ## NguyenDucThinh-2A202602468 — M3 Observability &amp; Reporting

- **Phạm vi được giao:** Quality Gate GX 1.x (9 check cố định), Freshness SLA, `generate_phase1_report`, `generate_corruption_report` (bảng 3 trạng thái).
- **Công việc chi tiết đã hoàn thành:**
  - `run_data_quality_checks`: GX 1.x ephemeral context + `ExpectationSuite` + `ValidationDefinition`, 8 expectation (row count, not-null ×3, unique `paper_id`, độ dài title/summary, regex noise) + check `freshness_sla`; ghi `data/quality/<name>_quality_report.json` và suite `data/quality/gx/papers_suite_<name>.json`.
  - `build_freshness_report`: latest/oldest published, `stale_rows`, `stale_ratio`, `is_fresh` (ngưỡng 180 ngày, tối đa 25% stale), dùng chung công thức với quality gate.
  - `generate_phase1_report` và `generate_corruption_report` (bảng Baseline/Corrupted/Repaired với Δ Corruption, Δ Repair, Recovery %, danh sách check fail, bảng scenario, findings sinh tự động từ số liệu); thêm 3 kwargs tuỳ chọn `baseline_quality`, `baseline_freshness`, `corruption_log` theo C6.
  - Đã kiểm chứng bằng fixture và thử tích hợp local với code M1 (`gminh`) + M2 (`TranDinhHinh`): baseline pass 9/9 (CP1 `Quality check status = True`), corrupted fail đúng 6 check theo C4-§5. Báo cáo markdown với số thật chờ `phase1.py`/`corruption_flow.py` (M4) và official run.
  - Ngoài phạm vi: soạn bộ contract `docs/rules/` C1–C7, fixture, `script/check_contracts.py`; hướng dẫn cài môi trường (`uv sync`, `PYTHONUTF8=1`).
- **Điều học được / Đóng góp chính:** Quality gate phải được thiết kế theo từng kịch bản lỗi cụ thể — check not-null không bắt được summary rỗng `""`, cần thêm check độ dài; đó chính là dạng silent failure mà quality gate phải chặn trước khi dữ liệu vào index.

### ## Văn Quốc Dũng-2A202602505 — M4 Integration &amp; Repair (Trưởng nhóm)

- **Phạm vi được giao:** `phase1.main`, `corruption_flow.main` (corrupt → evaluate → idempotent repair từ raw → compare), bonus B2 auto-repair từ chính bảng corrupted, merge nhánh, official run, ráp `group_report.md`.
- **Công việc chi tiết đã hoàn thành:**
  - Hoàn thiện [`src/pipelines/phase1.py`](../src/pipelines/phase1.py): nạp cấu hình, lấy raw records từ Crossref/snapshot, gọi cleaning với một `run_date` UTC, lưu clean JSON/CSV, tạo collection `papers-baseline`, đánh giá, chạy quality/freshness và sinh `phase1_report.md` theo C6.
  - Đóng băng benchmark: chỉ tạo `data/eval/test_set.json` khi chưa tồn tại hoặc `REFRESH_TEST_SET=1`; các trạng thái baseline/corrupted/repaired dùng cùng file 10 câu hỏi. Lưu thời điểm baseline và SHA-256 của raw records, clean JSON, test set trong [`baseline_run.json`](../data/results/baseline_run.json).
  - Hoàn thiện [`src/pipelines/corruption_flow.py`](../src/pipelines/corruption_flow.py): kiểm tra đủ artifact baseline; từ chối chạy nếu input đã đổi so với manifest; gọi 6 kịch bản corruption của M1, ghi JSON/CSV, tạo collection `papers-corrupted`, đánh giá và ghi quality/freshness tương ứng.
  - Trong flow bắt buộc, tích hợp repair từ `data/raw/crossref_records.json` bằng `load_raw_records` → `build_clean_dataframe`; không gọi lại Crossref và không suy ngược từ dữ liệu corrupted. Với manifest mới, dùng lại `run_date` baseline để giữ nguyên `age_days`. Kiểm chứng số dòng, tập `paper_id`, toàn bộ nội dung và `age_days` trước khi tạo collection `papers-repaired`.
  - Hoàn thiện bonus B2 trong [`src/pipelines/auto_repair.py`](../src/pipelines/auto_repair.py), gọi bằng `--auto-repair`: kiểm tra schema và quality/freshness của corrupted JSON; khi fail thì tự sửa từng dòng chỉ bằng dữ liệu của chính bảng: bỏ dòng trùng, bỏ token nhiễu, khôi phục ngày xuất bản từ `updated`, lấy lại field bị thiếu từ `text_for_embedding`/`*_joined`, bỏ dòng không khôi phục được và báo tiêu đề/summary quá ngắn; ghi audit từng thay đổi. Không đọc snapshot, baseline, corruption log và không gọi mạng. Hai phiên bản trước được thay thế: live re-fetch (batch live không chứa bài nào của benchmark vì snapshot là dữ liệu tổng hợp) và sửa từ raw snapshot (trùng với repair từ raw của flow bắt buộc). Candidate được kiểm định lại: qua hết → `completed`; sửa được một phần mà không làm fail thêm check nào → `partial`; còn lại không publish. Chỉ cập nhật `data/auto_repair/latest.json` (kèm `status`, `remaining_failures`) sau khi indexing và evaluation (nếu có benchmark) hoàn tất. Lỗi được ghi audit và giữ manifest thành công trước đó.
  - Gọi hàm báo cáo của M3 với đủ `baseline_quality`, `baseline_freshness`, `corruption_log`; lưu [`corruption_report.md`](../data/reports/corruption_report.md) và in bảng ba trạng thái ra console. Xử lý ký tự Unicode khi stdout Windows dùng encoding hạn chế.
  - Hoàn thiện bonus B1 trong [`dashboard/build_dashboard.py`](../dashboard/build_dashboard.py): đọc artifact của baseline, corrupted, repaired và lần B2 mới nhất, tính cảnh báo drift so với baseline (check fail, số dòng, median `age_days`, hit rate/token F1) rồi sinh [`dashboard/index.html`](../dashboard/index.html) — một file HTML mở offline, có chọn trạng thái, ô trạng thái quality/freshness, histogram `age_days` kèm ngưỡng 180 ngày, bảng 9 check × 4 trạng thái, biểu đồ metric và kết quả B2.
  - Bổ sung các biến `REFRESH_SOURCE`, `REFRESH_TEST_SET`, `RUN_RAGAS` và hướng dẫn dùng provider `mock` trong [`.env.example`](../.env.example).
  - Bổ sung [`tests/test_pipelines.py`](../tests/test_pipelines.py): 6 test kiểm tra luồng baseline → corruption → repair và tính lặp lại, thiếu baseline, thay đổi từng input (test set/raw/clean), refresh benchmark có chủ đích. Regression test dùng vector search trong bộ nhớ; cleaning, GX, evaluation và reporting chạy code thật.
  - Bổ sung [`tests/test_auto_repair.py`](../tests/test_auto_repair.py): 19 test case: chạy đúng 6 kịch bản corruption của M1 rồi kiểm tra chính xác dòng nào được sửa, bị bỏ hoặc bị báo và kết quả publish `partial`; input khỏe được bỏ qua; lỗi schema được sửa từ bản sao trong dòng; dòng không có `paper_id` bị bỏ; input không có gì để sửa và dữ liệu quá hạn freshness không được publish; cấm đọc raw snapshot, baseline clean và corruption log; exit code; giữ manifest trước khi index/evaluation/publication lỗi; và 3 test cho hàm fetch. Test B2 cấm gọi mạng; chỉ vector store được mock, corruption/cleaning/GX/evaluation chạy thật.
  - Sau khi chạy judge thật, sửa [`evaluation/metrics.py`](../src/evaluation/metrics.py) để câu trả lời rỗng/whitespace luôn có `score=1`, `correct=False` trước khi gọi LLM; thêm 3 regression case trong [`tests/test_evaluation.py`](../tests/test_evaluation.py).
- **Kết quả kiểm chứng local ngày 26/09/2026:**
  - Baseline chạy lúc `2026-09-26T04:25:47.757226+00:00` (11:25:47 UTC+7), nguồn `snapshot`, 24 raw records → 24 clean rows, không loại bản ghi invalid hoặc duplicate. Dùng MiniLM `sentence-transformers/all-MiniLM-L6-v2` và Chroma thật, `top_k=4`, `LLM_PROVIDER=mock`, `LLM_MODEL=mock`, `RUN_RAGAS=0`.
  - Bộ test đầy đủ: **28 passed** (6 case flow bắt buộc + 19 case B2 + 3 case guard evaluator); tái hiện bằng `.venv/Scripts/python.exe -m pytest -q`. **14 artifact** của flow bắt buộc đã đạt contract; kiểm tra thêm **3 artifact B2** (`clean`, `quality`, `metrics`) bằng `script/check_contracts.py`: tất cả `[OK]`.
  - Chạy corruption flow hai lần liên tiếp: corrupted/repaired metrics giống nhau giữa hai lần; raw records, clean baseline và benchmark giữ nguyên từng byte; repaired JSON trùng baseline JSON; console báo `[repair] verified=True`.
  - Bonus B2 chạy lúc `2026-09-26T15:42:57.352219+00:00` và hoàn tất `15:43:04 UTC` (22:42:57–22:43:04 UTC+7), run `20260926T154257352219Z-59897f5e`: bỏ 2 dòng trùng, bỏ nhiễu 3 summary (1 còn từ `semantic` bị tách thành `sema ntic`), khôi phục 6 ngày từ `updated`, bỏ 3 dòng summary rỗng, báo 3 tiêu đề bị cắt; 21 → 16 dòng; quality từ 3/9 lên 7/9 (còn fail `row_count`, `title_length`), stale từ 6/21 xuống 1/16; status `partial`. MiniLM/Chroma chạy thật; provider `mock`, judge heuristic, `RUN_RAGAS=0`. Hash các artifact baseline/raw/corrupted và benchmark gốc không đổi.
  - Các phiên bản B2 trước được giữ artifact để đối chiếu: live re-fetch (run `20260926T143315418143Z-6059c4bf`) đạt quality 9/9 nhưng 0/10 DOI ground truth, hit rate 0.0000; sửa từ raw snapshot (run `20260926T151303743236Z-7fa95ebe`) đạt 9/9 và 1.0000 nhưng trùng với repair từ raw.
  - Test set SHA-256: `c74629783d6a6c2ad1bfbc3e3c60bfb724e3e55a08d0102c7013bcaafb796c8e`.


Hai cột đầu thuộc flow bắt buộc dùng snapshot; cột B2 là dữ liệu corrupted sau khi tự sửa chỉ bằng chính bảng đó, cùng benchmark đã đóng băng. Với hai cột đầu, hai hàng judge dùng kết quả chấm lại bằng LLM thật và guard câu trả lời rỗng bên dưới; dữ liệu, câu trả lời, retrieval và token F1 giữ nguyên. Với B2, judge là heuristic của lần chạy `mock`, chưa chấm bằng LLM thật.

| Chỉ số | Baseline | Corrupted | Auto-repair B2 (từ bảng corrupted) |
| --- | ---: | ---: | ---: |
| Số câu đánh giá (`samples`) | 10 | 10 | 10 |
| `retrieval_hit_rate` | 1.0000 | 0.8000 | 0.9000 |
| `mean_token_f1` | 1.0000 | 0.8000 | 0.8000 |
| `judge_accuracy` | 1.0000 | 0.8000 | 0.8000 (heuristic) |
| `mean_judge_score` | 5.0000 | 4.2000 | 4.2000 (heuristic) |
| Quality checks passed | 9/9 | 3/9 | 7/9 |
| Quality success | True | False | False (`partial`) |
| Freshness `is_fresh` | True | False | True |
| `stale_ratio` | 0.0417 | 0.2857 | 0.0625 |
| Số dòng | 24 | 21 | 16 |


Nguồn retrieval/token F1 và quality: [`baseline_metrics.json`](../data/results/baseline_metrics.json), [`corrupted_metrics.json`](../data/results/corrupted_metrics.json), các quality/freshness report trong [`data/quality/`](../data/quality/) và [báo cáo đối chiếu gốc dùng mock](../data/reports/corruption_report.md).

Nguồn judge đã kiểm định: [baseline](../data/results/llm_judge/20260926T145203166848Z/validated/baseline_metrics.json), [corrupted](../data/results/llm_judge/20260926T145203166848Z/validated/corrupted_metrics.json), [B2 live cũ](../data/results/llm_judge/20260926T145203166848Z/validated/auto_repair_metrics.json) và [manifest phương pháp](../data/results/llm_judge/20260926T145203166848Z/validated/run.json). Lần chấm này có trước phiên bản B2 hiện tại nên chưa chấm B2 mới. Chạy OpenAI `gpt-4o-mini` (response model `gpt-4o-mini-2024-07-18`), temperature 0, từ `14:52:03` đến `14:53:05 UTC` ngày 26/09/2026: 40 API judgment, không fallback heuristic. Kết quả cuối giữ 37 verdict LLM cho câu trả lời có nội dung và áp guard cho 3 câu rỗng (corrupted q05, B2 q04/q08). LLM ban đầu chấm nhầm hai câu B2 rỗng là đúng; giữ [response gốc](../data/results/llm_judge/20260926T145203166848Z/judgments.json) để đối chiếu. Chỉ chấm lại saved answers, không re-fetch hoặc dựng lại index.

Nguồn B2: [repair audit](../data/auto_repair/20260926T154257352219Z-59897f5e/repair_log.json), [metrics](../data/auto_repair/20260926T154257352219Z-59897f5e/repaired_metrics.json), [quality](../data/auto_repair/20260926T154257352219Z-59897f5e/quality/repaired_quality_report.json) và [freshness](../data/auto_repair/20260926T154257352219Z-59897f5e/quality/repaired_freshness_report.json); phiên bản cũ: [live re-fetch](../data/auto_repair/20260926T143315418143Z-6059c4bf/repair_log.json), [sửa từ raw snapshot](../data/auto_repair/20260926T151303743236Z-7fa95ebe/repair_log.json). Hướng dẫn: [AUTO_REPAIR.md](AUTO_REPAIR.md).

- **Phân tích flow bắt buộc:** Corruption làm retrieval hit rate và token F1 giảm 0.2000; repair từ raw khôi phục toàn bộ mức giảm trên benchmark này. Sáu check lỗi là `row_count`, `paper_id_unique`, `title_length`, `summary_length`, `summary_no_noise`, `freshness_sla`. Tỷ lệ stale tăng từ 1/24 lên 6/21, vượt SLA tối đa 25%, rồi trở về 1/24 sau repair từ raw. Summary rỗng vẫn qua check not-null nhưng bị check độ dài phát hiện.
- **Phân tích bonus B2:** Chỉ dựa trên bảng corrupted, B2 sửa được 4/6 check fail (`paper_id_unique`, `summary_length`, `summary_no_noise`, `freshness_sla`) và nâng hit rate từ 0.8000 lên 0.9000; token F1 giữ 0.8000 vì q03/q05 cần tiêu đề bị cắt. Hai check còn fail là giới hạn của việc không có nguồn ngoài: 5 dòng bị xóa không để lại dấu vết (`row_count`) và phần còn lại của 3 tiêu đề không còn ở đâu trong dòng (`title_length`). Nhờ `updated` vẫn giữ ngày gốc, 6/6 ngày bị lùi được khôi phục chính xác. Phiên bản live re-fetch trước đó đạt quality 9/9 nhưng **0/10 DOI ground truth** có trong batch live, vì snapshot là dữ liệu tổng hợp: DOI `10.1145/3637528.3671801` trên Crossref thật là một bài KDD 2024 khác. Quality pass và khôi phục benchmark là hai tiêu chí riêng.
- **Giới hạn và trạng thái bàn giao:** Đây là kết quả kiểm chứng local trên nhánh `merTest`; code/artifact mới chưa commit, chưa phải official run trên `main` theo C6-§5. Đã chấm lại bằng LLM thật với guard câu trả lời rỗng; benchmark chỉ có 10 câu, verdict LLM vẫn cần kiểm tra và Ragas chưa chạy. Artifact pipeline gốc và [`group_report.md`](../report/group_report.md) ghi nhận lần chạy mock trước đó; bảng này và báo cáo cá nhân [`2A202602505_VanQuocDung.md`](../report/2A202602505_VanQuocDung.md) dùng số judge mới có nguồn riêng.
- **Điều học được / Đóng góp chính:** Tích hợp các module theo contract C1–C6 giúp hoàn chỉnh luồng dữ liệu và truy vết mỗi kết quả về artifact tương ứng. So sánh ba trạng thái cần cùng benchmark, cùng nguồn raw và cùng mốc thời gian tính freshness. Repair từ raw bất biến kết hợp rebuild collection giúp tránh tích lũy bản ghi trùng; cần kiểm tra cả nội dung và metrics qua nhiều lần chạy để chứng minh tính idempotent.

**Lệnh tái hiện flow smoke bằng mock trên PowerShell** (từ thư mục gốc repo, sau khi cài dependencies và tải model; không tái hiện lần chấm LLM riêng ở trên):

```powershell
$env:LLM_PROVIDER = 'mock'
$env:LLM_MODEL = 'mock'
$env:REFRESH_SOURCE = '0'
$env:REFRESH_TEST_SET = '0'
$env:RUN_RAGAS = '0'
.venv/Scripts/python.exe script/run_phase1.py
.venv/Scripts/python.exe script/run_corruption_flow.py
.venv/Scripts/python.exe script/run_corruption_flow.py
.venv/Scripts/python.exe script/run_corruption_flow.py --auto-repair
.venv/Scripts/python.exe dashboard/build_dashboard.py
.venv/Scripts/python.exe -m pytest -q
```

Flow bắt buộc giữ mốc thời gian baseline nhờ manifest; B2 dùng thời điểm chạy hiện tại để kiểm tra freshness và chỉ sửa từ chính bảng corrupted, không đọc snapshot và không gọi mạng. Bảng trên ghi nhận kết quả ngày 26/09/2026.
