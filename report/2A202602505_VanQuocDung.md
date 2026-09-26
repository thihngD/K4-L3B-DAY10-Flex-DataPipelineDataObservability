# Member Role Report — Day 10: Data Pipeline &amp; Data Observability

## 1. Thông tin cá nhân


| Thông tin       | Nội dung                                                                                                                                                 |
| --------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Họ và tên       | Văn Quốc Dũng                                                                                                                                            |
| MSSV            | 2A202602505                                                                                                                                              |
| Khóa/Lớp        | K4 — `K4-L3B-DAY10`                                                                                                                                      |
| Tên nhóm        | Flex                                                                                                                                                     |
| Vai trò chính   | M4 — Trưởng nhóm, Integration &amp; Repair owner                                                                                                         |
| Repository      | [https://github.com/thihngD/K4-L3B-DAY10-Flex-DataPipelineDataObservability](https://github.com/thihngD/K4-L3B-DAY10-Flex-DataPipelineDataObservability) |
| Ngày hoàn thành | 2026-09-26                                                                                                                                               |


## 2. Vai trò và phạm vi công việc

### Phần việc sở hữu


| Module/deliverable                | File/hàm phụ trách                                                                           | Input nhận vào                                                                                                                             | Output bàn giao                                                                                                                                                                                              | Trạng thái                                           |
| --------------------------------- | -------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | ---------------------------------------------------- |
| Baseline orchestration            | `src/pipelines/phase1.py`: `main`, `_save_dataframe`, `_file_hash`                           | `Settings`; raw records từ `fetch_source_records` (M1); `build_clean_dataframe` (M2); `build_test_set` (M2); quality/freshness/report (M3) | `data/clean/papers_clean.{json,csv}`, collection `papers-baseline`, `data/eval/test_set.json`, `baseline_{metrics,answers}.json`, quality/freshness report, `phase1_report.md`, manifest `baseline_run.json` | Hoàn thành                                           |
| Corruption flow + repair          | `src/pipelines/corruption_flow.py`: `main`                                                   | Artifact baseline + manifest; `corrupt_clean_dataframe` (M1); `data/raw/crossref_records.json`                                             | `papers_clean_{corrupted,repaired}.{json,csv}`, collection `papers-corrupted`/`papers-repaired`, metrics/answers 2 trạng thái, quality/freshness 2 trạng thái, `corruption_report.md`                        | Hoàn thành                                           |
| Bonus B2: auto-repair từ chính bảng corrupted | `src/pipelines/auto_repair.py` (`_repair_row`, `_repair_records`, `run_auto_repair`), flag `--auto-repair` | Chỉ `data/clean/papers_clean_corrupted.json`; không đọc snapshot, baseline, corruption log, không gọi mạng | Audit từng sửa đổi, candidate quality/freshness, index riêng và manifest `data/auto_repair/latest.json` có `status`/`remaining_failures` | Hoàn thành, chạy 22:42 UTC+7 ngày 26/09/2026, status `partial` |
| Bonus B1: observability dashboard | `dashboard/build_dashboard.py` (`build`, `_alerts`), `dashboard/template.html` | Artifact clean/quality/freshness/metrics của baseline, corrupted, repaired và lần B2 mới nhất; `corruption_log.json` | `dashboard/index.html`: một file HTML mở offline, chọn trạng thái, cảnh báo drift, histogram `age_days`, bảng check | Hoàn thành, sinh lúc 23:18 UTC+7 ngày 26/09/2026 |
| Regression test cho orchestration, B2 và evaluator | `tests/test_pipelines.py` (6 case), `tests/test_auto_repair.py` (19 case), `tests/test_evaluation.py` (3 case) | Vector store được mock, test B2 cấm gọi mạng; corruption, cleaning, GX, evaluation và reporting chạy thật | `pytest -q` → **28 passed** | Hoàn thành |
| Cấu hình chạy                     | `.env.example`: `REFRESH_SOURCE`, `REFRESH_TEST_SET`, `RUN_RAGAS`, gợi ý `LLM_PROVIDER=mock` | —                                                                                                                                          | Lệnh tái hiện không cần API key                                                                                                                                                                              | Hoàn thành                                           |
| Chạy local + tổng hợp báo cáo | `data/{clean,chroma,embeddings,eval,quality,results,reports}`, `data/auto_repair/`, `report/group_report.md` | Code đã tích hợp của cả nhóm | Bộ artifact flow bắt buộc và B2, báo cáo có nguồn số liệu | Đã kiểm chứng local; chưa phải official run trên `main` |


Phần của tôi nằm ở cuối chuỗi phụ thuộc: tôi tích hợp ingestion, cleaning, quality và corruption theo contract C1–C5, chịu trách nhiệm cho thứ tự chạy, đường dẫn artifact, tính tái lập và repair. Với bonus B2, ban đầu tôi mở rộng hàm fetch của M1 bằng keyword `live_only` và `attempt_log` để re-fetch live; sau khi phát hiện batch live không chứa bài nào của benchmark (xem §5), tôi chuyển B2 sang tự sửa từng record chỉ dựa trên chính bảng corrupted, và B2 không còn gọi hàm fetch. Code index/embedding (`src/retrieval/`) và `evaluate_pipeline` là code starter; tôi gọi chúng và bổ sung guard cho `_judge_answer` để LLM không chấm câu trả lời rỗng là đúng.

### Việc hỗ trợ ngoài phạm vi chính


| Hoạt động                                                 | Thành viên/module được hỗ trợ          | Kết quả                                                                                                                                                                                                                                                  |
| --------------------------------------------------------- | -------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Kiểm chứng output của các module khác trong lần chạy thật | M1, M2, M3                             | 14/14 artifact đạt `script/check_contracts.py` (raw, clean ×2, testset, freshness ×3, quality ×3, corruption_log, metrics ×3); log cleaning `input=24 dropped_invalid=0 dropped_duplicates=0 output=24`; số dòng corruption `[5, 3, 3, 3, 6, 2]` khớp C5 |
| Truyền đủ tham số cho hàm báo cáo của M3                  | M3 (`generate_corruption_report`)      | Gọi kèm `baseline_quality`, `baseline_freshness`, `corruption_log` để bảng 3 trạng thái có cột baseline quality/freshness và bảng scenario                                                                                                               |
| Xử lý in báo cáo ra console Windows                       | M3 (nội dung báo cáo có `Δ`, `✅`, `❌`) | Corruption flow không crash khi stdout dùng cp1252 (xem §6)                                                                                                                                                                                              |


## 3. Kết quả theo vai trò


| Nhiệm vụ đã thực hiện                                                           | File/hàm/artifact liên quan                    | Kết quả bàn giao                                                                    | Cách xác minh                                                            |
| ------------------------------------------------------------------------------- | ---------------------------------------------- | ----------------------------------------------------------------------------------- | ------------------------------------------------------------------------ |
| Nối các module thành baseline pipeline, dùng một `run_date` UTC cho cả lần chạy | `phase1.py`                                    | 24 raw → 24 clean; hit rate/token F1/judge = 1.0000; quality 9/9; fresh             | `data/reports/phase1_report.md`                                          |
| Đóng băng benchmark và khóa input baseline bằng manifest                        | `phase1.py` → `data/results/baseline_run.json` | `run_date` + SHA-256 của raw records, clean JSON, test set                          | `corruption_flow.py` từ chối chạy khi hash khác; 3 test tham số hóa      |
| Corruption → re-index → re-evaluate trên cùng test set                          | `corruption_flow.py`                           | 24 → 21 dòng; 3 metric chính 0.8000; quality 3/9; `is_fresh = False`                | `data/results/corrupted_metrics.json`, `data/quality/corrupted_*.json`   |
| Repair từ raw và kiểm chứng trước khi index                                     | `corruption_flow.py`                           | `[repair] verified=True`; repaired JSON trùng từng byte với baseline; recovery 100% | `cmp data/clean/papers_clean.json data/clean/papers_clean_repaired.json` |
| Bonus B2: gate fail → tự sửa từ chính bảng corrupted rồi kiểm định lại | `auto_repair.py`, `data/auto_repair/20260926T154257352219Z-59897f5e/` | 21 → 16 dòng: bỏ 2 dòng trùng, bỏ nhiễu 3 summary, khôi phục 6 ngày, bỏ 3 dòng summary rỗng, báo 3 tiêu đề bị cắt; quality 3/9 → 7/9; status `partial` | `repair_log.json`, `repaired_metrics.json`, `quality/` trong thư mục run |
| Bonus B1: dashboard quan sát chất lượng dữ liệu và drift | `dashboard/build_dashboard.py` → `dashboard/index.html` | 4 trạng thái; so với baseline, corrupted có 6 check fail, số dòng −12.5%, hit rate/token F1 giảm 0.20; B2 còn 2 check fail, số dòng −33.3% | Mở `dashboard/index.html`; kiểm tra bằng ảnh chụp headless Chrome |
| Regression test cho luồng tích hợp, B2 và evaluator | `tests/test_pipelines.py`, `tests/test_auto_repair.py`, `tests/test_evaluation.py` | **28 passed** (6 + 19 + 3 case) | `.venv/Scripts/python.exe -m pytest -q` |


Output cụ thể: `data/reports/corruption_report.md` — bảng 3 trạng thái được sinh từ một lần chạy duy nhất trên cùng raw snapshot, cùng test set (SHA-256 `c74629…96c8e`) và cùng `run_date`, nên mọi chênh lệch trong bảng chỉ đến từ dữ liệu.

Bonus B2 có artifact riêng và được đánh giá bằng bản sao của cùng test set. B2 chỉ dùng chính bảng corrupted nên không khôi phục được dòng bị xóa, tiêu đề bị cắt và summary bị xóa trắng; các check còn fail được ghi trong `remaining_failures`. Ba artifact B2 (`clean`, `quality`, `metrics`) đã được `script/check_contracts.py` kiểm tra và đều `[OK]`.

## 4. Giải thích phần kỹ thuật đã thực hiện

### Vấn đề cần giải quyết

Các module của M1–M3 đúng contract riêng lẻ nhưng chưa tạo ra kết luận nào. Phần của tôi phải ghép chúng thành hai lệnh chạy được end-to-end, và quan trọng hơn là đảm bảo phép so sánh baseline/corrupted/repaired là so sánh công bằng: cùng câu hỏi, cùng nguồn raw, cùng mốc thời gian tính `age_days` — và repair phải thật sự khôi phục dữ liệu chứ không chỉ làm đẹp metric.

Bonus B2 bổ sung tình huống pipeline chỉ có dữ liệu đã hỏng trong tay: phải tự phát hiện lỗi, tự sửa những gì bảng còn đủ thông tin, báo rõ những gì không sửa được, kiểm định lại candidate và không ghi đè index thành công trước đó khi recovery thất bại.

### Cách triển khai

`**phase1.py`:** lấy `run_date = now_utc()` một lần rồi truyền xuống cleaning, để mọi `age_days` trong lần chạy tính theo cùng một mốc. `fetch_mode` được suy ra từ `mtime` của snapshot: không bật refresh → `snapshot`; bật refresh mà snapshot không bị ghi lại → `fallback`; snapshot được ghi mới → `live`. Sau khi lưu clean JSON/CSV và build index, test set chỉ được tạo khi chưa tồn tại hoặc `REFRESH_TEST_SET=1`; các lần chạy sau đọc lại file cũ. Cuối cùng tôi ghi `baseline_run.json` gồm `source_summary` và SHA-256 của ba input.

`**corruption_flow.py`:** kiểm tra đủ 6 artifact baseline, nếu thiếu thì dừng với hướng dẫn "Run script/run_phase1.py first". So hash của test set, raw và clean với manifest; khác thì dừng. Sau đó: corrupt (M1) → lưu → build `papers-corrupted` → evaluate → quality/freshness. Repair đọc lại raw bằng `load_raw_records`, chạy `build_clean_dataframe` với `run_date` của manifest, rồi so repaired với baseline trên số dòng, tập `paper_id`, toàn bộ cột và `age_days`. Chỉ khi khớp mới lưu, build `papers-repaired`, evaluate và gọi báo cáo của M3.

**`auto_repair.py` (B2):** đọc corrupted JSON và kiểm tra schema trước GX. Nếu schema/quality/freshness đều pass thì ghi `skipped_healthy`. Khi gate fail, `_repair_records` xử lý từng dòng chỉ bằng dữ liệu của chính bảng: dòng trùng `paper_id` bị bỏ; `_repair_row` bỏ token nhiễu trong title/summary, khôi phục `published` từ `updated` khi ngày xuất bản không hợp lệ, ở tương lai hoặc sớm hơn `updated` (trong dữ liệu sạch hai trường này luôn bằng nhau), lấy lại title/summary bị thiếu từ dòng tương ứng trong `text_for_embedding` và authors/categories từ `*_joined`. Dòng không còn `paper_id`, title, summary hoặc ngày hợp lệ bị bỏ; tiêu đề dưới 8 ký tự hoặc summary dưới 50 ký tự không thể kéo dài nên được giữ lại cho retrieval và ghi `unrecoverable_field`. `build_clean_dataframe` tính lại các cột dẫn xuất theo thời điểm chạy. Candidate được kiểm định lại bằng cùng gate: qua hết → `completed`; sửa được một số check fail mà không làm fail thêm check nào → `partial`, publish kèm `remaining_failures`; còn lại → `validation_failed`, không publish. Mỗi run có thư mục artifact và collection riêng; chỉ cập nhật `latest.json` bằng thao tác thay file nguyên tử sau khi index và evaluation (nếu có test set) hoàn tất. Lỗi ở repair/validation/index/evaluation/publication trả exit code 1, ghi audit và giữ manifest trước đó. B2 không đọc snapshot, baseline, corruption log hay test set để sửa và không gọi mạng.

### Input, output và contract


| Thành phần              | Mô tả                                                                                                                                                                                                         |
| ----------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Input                   | `Settings` (`core/config.py` + biến môi trường); `data/raw/crossref_response.json`; các hàm theo C1–C5                                                                                                        |
| Output                  | Toàn bộ artifact C6-§1 (baseline) và C6-§2 (corruption/repair), thêm `data/results/baseline_run.json`                                                                                                         |
| Module phụ thuộc        | `ingestion/crossref.py`, `ingestion/cleaning.py`, `ingestion/corruption.py`, `evaluation/testset.py`, `evaluation/metrics.py`, `retrieval/index.py`, `observability/quality.py`, `observability/reporting.py` |
| Module sử dụng output   | `script/run_phase1.py`, `script/run_corruption_flow.py`, `tests/test_pipelines.py`, group report                                                                                                              |
| Điều kiện lỗi cần xử lý | Cleaning trả DataFrame rỗng; test set rỗng; thiếu artifact baseline; input baseline bị sửa sau khi chạy; raw không tái tạo được baseline; stdout Windows không mã hóa được ký tự Unicode                      |

Input duy nhất của B2 là `data/clean/papers_clean_corrupted.json`; output nằm trong `data/auto_repair/<run_id>/`. Test set là input đánh giá tùy chọn, không cung cấp nội dung repair. Chi tiết interface và artifact: [AUTO_REPAIR.md](../docs/AUTO_REPAIR.md).


### Cách xác minh

```powershell
$env:LLM_PROVIDER = 'mock'; $env:LLM_MODEL = 'mock'; $env:RUN_RAGAS = '0'
.venv/Scripts/python.exe script/run_phase1.py
.venv/Scripts/python.exe script/run_corruption_flow.py
.venv/Scripts/python.exe script/run_corruption_flow.py
.venv/Scripts/python.exe script/run_corruption_flow.py --auto-repair
.venv/Scripts/python.exe dashboard/build_dashboard.py
.venv/Scripts/python.exe -m pytest -q
```

- **Kết quả mong đợi:** hai flow thoát mã 0; corrupted giảm metric và fail các check tương ứng 6 kịch bản; repaired trùng baseline; chạy corruption flow lần 2 cho kết quả như lần 1.
- **Kết quả thực tế của flow bắt buộc:** baseline 1.0000/9 check pass; corrupted 0.8000 và 3/9; repaired từ raw 1.0000 và 9/9; console in `[repair] verified=True`; metrics hai lần chạy corruption giống nhau; raw, clean baseline và test set giữ nguyên từng byte. Bộ test đầy đủ sau khi thêm B2 và guard evaluator: **28 passed**; tái hiện bằng `pytest -q`.
- **Kết quả thực tế của B2:** repair log ghi 2 dòng trùng bị bỏ, 3 summary được bỏ nhiễu, 6 ngày được khôi phục từ `updated`, 3 dòng summary rỗng bị bỏ và 3 tiêu đề bị cắt được báo `unrecoverable_field`; 21 → 16 dòng, quality 3/9 → 7/9 (còn fail `row_count`, `title_length`), stale 1/16, status `partial`. Trên benchmark: hit rate 0.9000, token F1 0.8000, judge accuracy (heuristic) 0.8000. Số liệu chi tiết tại §8.
- **Artifact/log:** `data/results/baseline_run.json`, `data/results/*_metrics.json`, `data/reports/phase1_report.md`, `data/reports/corruption_report.md`.

## 5. Một quyết định kỹ thuật quan trọng

- **Bối cảnh:** Sau corruption, 5 bài bị xóa, 3 summary bị xóa trắng, 3 tiêu đề bị cắt, 6 ngày bị lùi, 3 summary có nhiễu và 2 dòng trùng. Cần chọn cách đưa dữ liệu về trạng thái đúng.
- **Các phương án đã cân nhắc:**
  1. Sửa trên chính bảng corrupted: dedupe, bỏ nhiễu, dùng lại thông tin còn trong dòng (`updated`, các cột dẫn xuất), bỏ dòng không khôi phục được.
  2. Gọi lại Crossref live để lấy dữ liệu mới.
  3. Dựng lại từ raw snapshot bất biến `data/raw/crossref_records.json` bằng chính `build_clean_dataframe`, với `run_date` của baseline.
  4. Sửa từng record: đối chiếu từng dòng corrupted với raw snapshot đã xác minh hash theo `paper_id`, chỉ khôi phục phần bị hỏng và ghi lại từng thay đổi.
- **Phương án đã chọn:** Phương án 3 cho flow bắt buộc cần tái tạo chính xác corpus; phương án 1 cho bonus B2, sau khi đã thử phương án 2 và 4.
- **Lý do:** Flow bắt buộc cần chứng minh metric phục hồi, mà phương án 1 không đủ thông tin để khôi phục bài bị drop, summary bị xóa hoặc tiêu đề bị cắt. Phương án 3 tất định, không cần mạng, dùng lại cùng cleaning và `run_date` để so sánh trực tiếp với baseline; lệch mốc 1 ngày làm `age_days` thay đổi. Với B2, phương án 2 đã chạy thật (run `20260926T143315418143Z-6059c4bf`): batch live đạt quality 9/9 nhưng 0/10 DOI benchmark có mặt. Kiểm tra lại cho thấy snapshot của repo là dữ liệu tổng hợp: DOI `10.1145/3637528.3671801` trên Crossref thật là bài KDD 2024 “A Multimodal Foundation Agent for Financial Trading…”, không phải bài “Agentic Retrieval-Augmented Generation…” trong snapshot. Phương án 4 (run `20260926T151303743236Z-7fa95ebe`) khôi phục đủ nhưng chỉ lặp lại repair từ raw của flow bắt buộc, vì mọi giá trị đúng đều lấy từ cùng snapshot. Vì vậy B2 chọn phương án 1: tự chữa chỉ bằng chính bảng corrupted và ghi rõ từng lỗi còn lại. Phương án này sửa được nhiều hơn dự kiến nhờ hai chỗ dư thừa trong dữ liệu: `updated` vẫn giữ ngày gốc nên 6 ngày bị lùi được khôi phục chính xác, và các cột dẫn xuất (`text_for_embedding`, `*_joined`) là bản sao để lấy lại field bị thiếu. Giới hạn chấp nhận: không khôi phục được bài bị drop, summary bị xóa hay tiêu đề bị cắt, và bỏ nhiễu có thể để lại một từ bị tách đôi.
- **Bằng chứng quyết định phù hợp:** Flow bắt buộc có repaired JSON trùng baseline, quality 9/9, `stale_ratio` 0.0417 và 4 metric phục hồi 100%. B2 theo phương án 1 nâng quality từ 3/9 lên 7/9, khôi phục chính xác 6/6 ngày và 2/3 summary nhiễu, hit rate 0.8000 → 0.9000; còn fail `row_count` (16 dòng) và `title_length` (3 dòng). Phương án 4 đạt 9/9 và 1.0000 nhưng trùng với repair từ raw; phương án 2 đạt 9/9 nhưng hit rate 0.0000.

## 6. Một lỗi hoặc blocker đã xử lý

- **Triệu chứng/lỗi nguyên văn** (tái hiện lại bằng cách in báo cáo ra stdout cp1252):
`UnicodeEncodeError: 'charmap' codec can't encode character 'Δ' in position 107: character maps to <undefined>`
- **Lệnh hoặc bước tái hiện:** trên Windows, khi stdout bị chuyển hướng (pipe/file/terminal tích hợp) Python dùng codepage hệ thống; mô phỏng bằng `PYTHONIOENCODING=cp1252` rồi `print` nội dung `data/reports/corruption_report.md`.
- **Nguyên nhân gốc:** Báo cáo của M3 dùng `Δ`, `✅`, `❌`; cp1252 không có các ký tự này. Bước in bảng là bước cuối của `corruption_flow.py`, nên lỗi làm lệnh thoát với mã khác 0 dù mọi artifact đã ghi xong — vi phạm tiêu chí "chạy exit code 0" trong checklist nộp bài.
- **Cách xử lý:** File báo cáo vẫn ghi UTF-8 như cũ; chỉ phần in ra console được mã hóa theo `sys.stdout.encoding` với `errors="replace"` rồi giải mã lại, nên ký tự không hỗ trợ thành `?` thay vì ném exception.
- **Cách xác minh sau khi sửa:** chạy đúng đoạn in đó dưới `PYTHONIOENCODING=cp1252`: bảng in ra với `? Corruption`, `? Repair`, mã thoát 0; file `corruption_report.md` vẫn giữ nguyên `Δ`.
- **Điều học được:** Lệnh pipeline phải thoát mã 0 trên mọi môi trường chấm; phần hiển thị không được làm hỏng một lần chạy đã tạo xong artifact. Nên tách "ghi artifact" khỏi "trình bày" và kiểm tra riêng điều kiện môi trường (encoding, đường dẫn).

## 7. Hiểu biết về luồng end-to-end

**Câu trả lời:**

1. **Từ Crossref đến vector index:** Mặc định pipeline đọc snapshot `crossref_response.json` (chỉ gọi API khi `REFRESH_SOURCE=1`, có retry và fallback). M1 parse thành 24 record có DOI, tiêu đề, abstract đã bỏ tag, tác giả, ngày và lưu `crossref_records.json`. M2 chuẩn hóa, lọc, dedupe, tính `age_days` theo `run_date` tôi truyền vào và ghép `text_for_embedding` 5 phần. Tôi đưa DataFrame đó vào `LocalEmbeddingIndex.build`: mỗi dòng được embed bằng MiniLM và lưu vào collection Chroma kèm metadata (tác giả, ngày, chủ đề, summary) để QA trích câu trả lời.
2. **Evaluation set và ground truth:** Mỗi câu hỏi nêu tiêu đề trong nháy đơn và lưu DOI của bài đúng. `retrieval_hit` = DOI đó có nằm trong top-4 hay không; `token_f1` so câu trả lời với đáp án chuẩn; judge chấm đúng/sai. Lần smoke dùng heuristic với provider `mock`; sau đó chấm lại saved answers bằng `gpt-4o-mini`, câu trả lời rỗng bị guard loại trước khi dùng verdict. Hai loại metric này đo hai tầng khác nhau: tìm đúng tài liệu và trả lời đúng.
3. **Quality checks khác freshness:** Quality checks kiểm tra dữ liệu có đúng hình dạng và nội dung hay không (số dòng, null, unique, độ dài, ký tự nhiễu). Freshness kiểm tra dữ liệu còn đủ mới hay không (tỷ lệ bài có `age_days > 180` không vượt 25%). Một dataset có thể sạch hoàn toàn mà vẫn stale — như kịch bản `stale_date` chỉ làm fail `freshness_sla`.
4. **Cùng test set cho ba trạng thái:** để dữ liệu là biến duy nhất thay đổi. Nếu đề đổi theo dữ liệu, không thể biết metric giảm do dữ liệu hỏng hay do đề khác. Vì vậy tôi đóng băng `test_set.json` và kiểm tra SHA-256 trước mỗi lần chạy corruption flow.
5. **Repair thành công dựa trên:** với flow bắt buộc, `[repair] verified=True`, repaired JSON trùng baseline, quality 9/9, fresh và metric phục hồi trên cùng test set. Với B2, `completed` nghĩa là candidate sau khi sửa qua toàn bộ gate; `partial` nghĩa là đã sửa được một phần check fail mà không làm fail thêm check nào, và `remaining_failures` ghi những lỗi bảng corrupted không đủ thông tin để sửa. Audit phải được đọc cùng metric: lần live re-fetch trước đó cho thấy dữ liệu hợp lệ chưa chắc trả lời được benchmark.

## 8. Phân tích kết quả

### Metrics chính


Hai cột đầu thuộc flow bắt buộc dùng snapshot; cột B2 là dữ liệu corrupted sau khi tự sửa chỉ bằng chính bảng đó, đánh giá bằng cùng benchmark 10 câu đã đóng băng. Với hai cột đầu, hai hàng judge lấy từ lần chấm LLM thật có guard câu trả lời rỗng; dữ liệu, saved answers, retrieval và token F1 không đổi. Với B2, judge là heuristic của lần chạy `mock`, chưa chấm bằng LLM thật.

| Metric/signal | Baseline | Corrupted | Auto-repair B2 (từ bảng corrupted) | Nhận xét của cá nhân |
| --- | ---: | ---: | ---: | --- |
| Số câu đánh giá (`samples`) | 10 | 10 | 10 | Test set giữ nguyên SHA-256 |
| `retrieval_hit_rate` | 1.0000 | 0.8000 | 0.9000 | B2 còn miss q02 vì bài ground truth bị xóa; q05 vào lại top-4 khi 2 dòng summary rỗng chiếm chỗ bị bỏ |
| `mean_token_f1` | 1.0000 | 0.8000 | 0.8000 | B2 vẫn sai q03/q05: cả hai hỏi bài có tiêu đề bị cắt |
| `judge_accuracy` | 1.0000 | 0.8000 | 0.8000 | Hai cột đầu: 19 verdict LLM thật, câu rỗng corrupted q05 bị guard chấm sai; B2: heuristic |
| `mean_judge_score` | 5.0000 | 4.2000 | 4.2000 | B2: heuristic |
| Quality checks passed | 9/9 | 3/9 | 7/9 | B2 còn fail `row_count` và `title_length` |
| Quality success | True | False | False | B2 publish ở trạng thái `partial` |
| Freshness `is_fresh` | True | False | True | 6 ngày bị lùi được khôi phục từ `updated` |
| `stale_ratio` | 0.0417 | 0.2857 | 0.0625 | B2 có 1/16 dòng quá 180 ngày, cùng bài stale với baseline |
| Số dòng | 24 | 21 | 16 | B2 bỏ 2 dòng trùng và 3 dòng summary rỗng; không thể bổ sung 5 dòng bị xóa |

Nguồn retrieval/token F1 của flow bắt buộc: [`baseline_metrics.json`](../data/results/baseline_metrics.json), [`corrupted_metrics.json`](../data/results/corrupted_metrics.json), [quality/freshness](../data/quality/) và [corruption report gốc dùng mock](../data/reports/corruption_report.md).

### LLM judge thật và kiểm tra câu trả lời rỗng

Ngày 26/09/2026, từ `14:52:03` đến `14:53:05 UTC` (21:52–21:53 UTC+7), chạy 40 judgment bằng OpenAI `gpt-4o-mini`, response model `gpt-4o-mini-2024-07-18`, temperature 0. Dùng cùng prompt/rubric của evaluator và cùng 40 saved answers (10 mỗi trạng thái); không cho phép fallback heuristic. Chỉ chấm lại câu trả lời, không gọi Crossref hoặc rebuild index. [Manifest gốc](../data/results/llm_judge/20260926T145203166848Z/run.json) lưu prompt, model, thời gian, token usage và SHA-256 input; [response gốc](../data/results/llm_judge/20260926T145203166848Z/judgments.json) lưu verdict và reasoning.

Kiểm tra từng verdict phát hiện LLM chấm B2 q04/q08 rỗng (phiên bản live re-fetch) là đúng (`score=5`) và cho corrupted q05 rỗng `score=3`, `correct=False`. Vì vậy bổ sung guard trong [`_judge_answer`](../src/evaluation/metrics.py): câu trả lời rỗng hoặc chỉ có whitespace luôn `score=1`, `correct=False`, không gọi LLM. Kết quả cuối giữ nguyên 37 verdict LLM cho câu có nội dung và áp guard cho 3 câu rỗng; response gốc được giữ lại. Đây là kiểm tra tất định cho trường hợp không có câu trả lời, không suy điểm LLM từ token F1.

Nguồn judge của hai cột đầu: [baseline](../data/results/llm_judge/20260926T145203166848Z/validated/baseline_metrics.json), [corrupted](../data/results/llm_judge/20260926T145203166848Z/validated/corrupted_metrics.json) và [manifest phương pháp đã kiểm định](../data/results/llm_judge/20260926T145203166848Z/validated/run.json). Lần chấm này còn gồm 10 câu của phiên bản B2 cũ (live re-fetch, [metrics](../data/results/llm_judge/20260926T145203166848Z/validated/auto_repair_metrics.json)), chưa chấm phiên bản B2 hiện tại. Judge accuracy cuối là 1.0000 / 0.8000 (B2 live cũ 0.0000); mean judge score là 5.0000 / 4.2000 (B2 live cũ 1.2000). Ragas chưa chạy; benchmark chỉ có 10 câu và LLM judge vẫn có thể sai, như các verdict rỗng đã phát hiện.

### Bonus B2: kết quả sửa từ bảng corrupted

Run `20260926T154257352219Z-59897f5e` bắt đầu `2026-09-26T15:42:57.352219+00:00`, hoàn tất `15:43:04 UTC` (22:42:57–22:43:04 UTC+7), status `partial`. Input corrupted 21 dòng fail 6/9 check (`row_count`, `paper_id_unique`, `title_length`, `summary_length`, `summary_no_noise`, `freshness_sla`). Không đọc file nào khác và không gọi mạng. MiniLM/Chroma chạy thật, `top_k=4`, provider/model `mock`, judge fallback heuristic, `RUN_RAGAS=0`.

| Hành động trong repair log | Số lượng | Chi tiết |
| --- | ---: | --- |
| `dropped_duplicate` | 2 | Dòng trùng `paper_id` xuất hiện sau bị bỏ |
| `repaired_field` | 9 | 3 summary bỏ token nhiễu (2 khớp baseline chính xác, 1 còn từ `semantic` bị tách thành `sema ntic`); 6 ngày xuất bản khôi phục từ `updated` |
| `dropped_row` | 3 | Summary rỗng, không còn bản sao nào trong dòng |
| `unrecoverable_field` | 3 | Tiêu đề còn 6 ký tự (`Advanc`, `Hybrid`, `Semant`), giữ lại cho retrieval |

Kết quả 16 dòng, quality 7/9, stale 1/16 (bài xuất bản `2026-03-28`, 182 ngày). Hai check còn fail là giới hạn của việc không dùng nguồn ngoài: `row_count` vì 5 bài bị xóa không để lại dấu vết, `title_length` vì phần còn lại của tiêu đề không còn ở đâu trong dòng (corruption đã ghi đè cả `text_for_embedding`). Một regression test cấm B2 đọc raw snapshot, baseline clean và corruption log. Benchmark giữ SHA-256 `c74629783d6a6c2ad1bfbc3e3c60bfb724e3e55a08d0102c7013bcaafb796c8e`.

Nguồn B2: [repair audit](../data/auto_repair/20260926T154257352219Z-59897f5e/repair_log.json), [metrics](../data/auto_repair/20260926T154257352219Z-59897f5e/repaired_metrics.json), [quality](../data/auto_repair/20260926T154257352219Z-59897f5e/quality/repaired_quality_report.json) và [freshness](../data/auto_repair/20260926T154257352219Z-59897f5e/quality/repaired_freshness_report.json).

**Các phiên bản trước.** Live re-fetch (run `20260926T143315418143Z-6059c4bf`): quality 9/9 nhưng **0/10 DOI ground truth** có trong batch live, hit rate 0.0000, token F1 0.0150, judge accuracy LLM thật 0.0000, do snapshot của repo là dữ liệu tổng hợp. Sửa từ raw snapshot (run `20260926T151303743236Z-7fa95ebe`): 24 dòng, quality 9/9, hit rate 1.0000, nhưng trùng với repair từ raw của flow bắt buộc (xem §5). Artifact của cả hai được giữ lại để đối chiếu.


### Kết luận từ số liệu

1. `truncate_title` cắt tiêu đề bài `3671806` còn `Semant` → `title_length` fail (3/21 dòng) → câu hỏi q03 nêu tiêu đề đầy đủ nên tra cứu chính xác không khớp, QA dùng top-1 vector search là bài "Advanced Perspectives on Semantic Layer Integration…" và trả `2026-06-06` thay vì `2026-05-02` → `mean_token_f1` và `judge_accuracy` giảm dù `retrieval_hit` của q03 vẫn True.
2. Repair dựng lại 24 dòng từ raw với `run_date` baseline → quality 9/9, `stale_ratio` 0.0417, `is_fresh = True` → q02, q03, q05 trả lời đúng trở lại, cả 4 metric về 1.0000/5.0000.
3. Bonus B2 phát hiện gate fail → chỉ dựa trên bảng corrupted, bỏ 2 dòng trùng, bỏ nhiễu 3 summary, khôi phục 6 ngày từ `updated`, bỏ 3 dòng summary rỗng → quality 3/9 lên 7/9, stale 6/21 xuống 1/16 → hit rate 0.8000 lên 0.9000 nhưng token F1 giữ 0.8000, vì hai câu sai (q03, q05) đều cần tiêu đề bị cắt mà bảng không còn giữ. Dữ liệu tự sửa được sạch hơn nhưng không trả lời tốt hơn: phục hồi chất lượng dữ liệu và phục hồi hiệu năng truy vấn là hai tiêu chí cần báo cáo riêng.

**Corruption ảnh hưởng rõ nhất:** `truncate_title`. Tiêu đề là khóa mà QA router dùng để tra cứu chính xác, nên khi tiêu đề hỏng, agent rơi về vector search và dễ chọn nhầm bài "anh em" có tiêu đề gần giống. Nó liên quan tới cả 2 câu trả lời sai (q03; q05 kết hợp với `blank_summary` vì bài bị chọn nhầm `3671823` có summary rỗng nên câu trả lời rỗng).

**Kết quả khác kỳ vọng:** Tôi kỳ vọng `stale_date` sẽ làm sai các câu hỏi về ngày, nhưng không câu `date` nào trỏ vào 6 bài bị lùi ngày, nên nó chỉ làm fail freshness. Ngoài ra q02 mất tài liệu ground truth nhưng vẫn trả lời đúng vì bài `3671816` có cùng tác giả. Tôi kiểm tra bằng cách đối chiếu `ground_truth_doc_ids` và top-1 của từng câu trong `corrupted_answers.json` với `affected_paper_ids` trong `corruption_log.json`. Kết luận: benchmark 10 câu không bao phủ mọi lỗi, nên quality gate phải chạy độc lập với metric agent.

## 9. Điều học được và hướng cải thiện

### Ba điều quan trọng nhất

1. **Data pipeline:** Tái lập không tự có. Cùng code nhưng khác `run_date`, khác test set hoặc raw bị sửa là đủ làm bảng so sánh mất ý nghĩa; manifest với hash và mốc thời gian biến giả định "cùng input" thành điều pipeline tự kiểm tra.
2. **Data quality/observability:** Check not-null không bắt được chuỗi rỗng — cần check theo từng dạng lỗi cụ thể. Quality gate và freshness cho tín hiệu sớm hơn và rộng hơn metric agent: 6 check fail trong khi chỉ 2–3 câu hỏi bị ảnh hưởng.
3. **Data và RAG agent:** Lỗi dữ liệu nhỏ ở trường làm khóa tra cứu (tiêu đề) gây sai câu trả lời một cách "tự tin" — agent vẫn trả lời, chỉ là trả lời theo tài liệu khác. Hit rate có thể giữ nguyên trong khi câu trả lời sai, nên phải theo dõi cả hai tầng.

### Nếu có thêm thời gian

Bonus B2 đã hoàn thành: tự sửa từ chính bảng corrupted và kiểm chứng trên dữ liệu thật; đã chạy LLM judge thật và thêm guard câu trả lời rỗng. B2 chỉ sửa được những gì bảng còn giữ, nên dòng bị xóa và tiêu đề bị cắt vẫn cần một nguồn đáng tin; bước tiếp theo là cho `partial` gọi một nguồn như vậy (snapshot đã xác minh hoặc re-fetch kèm tiêu chí coverage của benchmark, vì lần live re-fetch cho thấy quality pass chưa đảm bảo chứa tài liệu cần trả lời). Cần chấm B2 mới bằng LLM thật, mở rộng bộ câu hỏi, theo dõi coverage độc lập với quality/freshness, kiểm tra chéo verdict LLM và chạy `RUN_RAGAS=1` để đánh giá sâu hơn. Không thay benchmark cũ chỉ để làm điểm B2 tăng.

## 10. Cam kết của thành viên

Đánh dấu sau khi tự kiểm tra:

- [x] Nội dung báo cáo phản ánh đúng phần việc và mức hiểu của tôi.
- [x] Tôi có thể giải thích luồng end-to-end, không chỉ module mình phụ trách.
- [x] Mọi kết luận về kết quả đều có artifact hoặc metric để đối chiếu.
- [x] Tôi không ghi “đã chạy thành công” cho phần chưa được kiểm chứng.
- [x] Báo cáo không chứa `.env`, API key, token hoặc secret.
- [x] Báo cáo này không phải bản sao nguyên văn của báo cáo nhóm hoặc báo cáo thành viên khác.

**Họ và tên:** Văn Quốc Dũng
**Ngày xác nhận:** 2026-09-26
