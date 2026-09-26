# Member Role Report — Day 10: Data Pipeline & Data Observability

## 1. Thông tin cá nhân

| Thông tin         | Nội dung                  |
| ------------------ | -------------------------- |
| Họ và tên       | Nguyễn Đức Thịnh             |
| MSSV               | 2A202602468                     |
| Khóa/Lớp         | K4              |
| Tên nhóm         | Flex     |
| Vai trò chính    | M3 — Observability & Reporting owner (nhánh `thihn/02468`) |
| Repository         | https://github.com/thihngD/K4-L3B-DAY10-Flex-DataPipelineDataObservability |
| Ngày hoàn thành | 2026-09-26 (code M3); báo cáo số liệu chờ official run |

## 2. Vai trò và phạm vi công việc

### Phần việc sở hữu

| Module/deliverable | File/hàm phụ trách | Input nhận vào | Output bàn giao  | Trạng thái                                 |
| ------------------ | --------------------- | ---------------- | ----------------- | -------------------------------------------- |
| Data Quality Gate (GX 1.x) | `src/observability/quality.py` → `run_data_quality_checks` | Clean dataframe đúng contract C2 (từ M2 / corruption của M1) | Dict C4-§3 + `data/quality/<name>_quality_report.json` + suite `data/quality/gx/papers_suite_<name>.json` | Hoàn thành; đã test trên fixture và thử tích hợp local với code M1/M2 (§3). Artifact chính thức chờ official run (M4) |
| Freshness SLA | `src/observability/quality.py` → `build_freshness_report` | Clean dataframe (cột `published`, `age_days`) | Dict C4-§4 + JSON tại `report_path` do M4 truyền | Hoàn thành; đã test trên fixture và thử tích hợp local. Artifact chính thức chờ official run (M4) |
| Báo cáo Phase 1 | `src/observability/reporting.py` → `generate_phase1_report` | `source_summary`, metrics, quality, freshness (C6) | `data/reports/phase1_report.md` | Code hoàn thành, render thử bằng fixture; chờ M4 gọi trong `phase1.py` |
| Báo cáo đối chiếu 3 trạng thái | `src/observability/reporting.py` → `generate_corruption_report` | Metrics/quality/freshness 3 trạng thái + `corruption_log` | `data/reports/corruption_report.md` | Code hoàn thành, render thử bằng fixture; chờ M4 gọi trong `corruption_flow.py` |

Phần việc của tôi nằm giữa dữ liệu sạch và báo cáo: nhận dataframe của M2 (baseline, repaired) và M1 (corrupted) để phát tín hiệu chất lượng, rồi nhận metrics mà M4 sinh bằng `evaluate_pipeline` để viết báo cáo. M4 là người gọi các hàm của tôi trong 2 pipeline.

### Việc hỗ trợ ngoài phạm vi chính

| Hoạt động                         | Thành viên/module được hỗ trợ | Kết quả                    |
| ------------------------------------ | ------------------------------------ | ---------------------------- |
| Soạn bộ contract C1–C7, fixture và validator `script/check_contracts.py` để 4 người làm song song | Cả nhóm | Commit `cf9151a`, `1fc1503` trên `main`; `python script/check_contracts.py fixtures` → 6/6 OK |
| Cài môi trường `uv sync --extra dev`, phát hiện lỗi encoding console Windows | Cả nhóm | Hướng dẫn `setx PYTHONUTF8 1` (xem §6) |
| Sửa ví dụ trong `docs/rules/fixtures/README.md` (truyền `str` vào `read_json` gây `AttributeError`) | Cả nhóm | Ví dụ dùng `Path`, đã chạy lại thành công |

## 3. Kết quả theo vai trò

| Nhiệm vụ đã thực hiện | File/hàm/artifact liên quan | Kết quả bàn giao       | Cách xác minh         |
| --------------------------- | ----------------------------- | ------------------------- | ----------------------- |
| Quality gate GX 1.x ephemeral: 8 expectation + 1 check freshness, ID cố định theo C4 | `quality.py::run_data_quality_checks` | Dict 10 key + JSON report + JSON suite | Chạy trên `clean.sample.json` → `passed=8/9 failed=['row_count']` (đúng kỳ vọng vì fixture chỉ 12 dòng < 23); validator `quality` → OK |
| Kiểm tra gate bắt được lỗi | `quality.py` | — | Tự làm bẩn thủ công 1 bản fixture (không phải `corruption.py` của M1): fail đúng 6 check `row_count`, `paper_id_unique`, `title_length`, `summary_length`, `summary_no_noise`, `freshness_sla`; 3 check `*_not_null` vẫn pass |
| Freshness report | `quality.py::build_freshness_report` | JSON 9 key | Fixture → `stale_rows=1/12`, `stale_ratio=0.0833`, `is_fresh=True`; validator `freshness` → OK |
| Report Phase 1 | `reporting.py::generate_phase1_report` | Markdown 5 mục cố định | Render bằng fixture, kiểm tra đủ heading và bảng 9 check |
| Thử tích hợp local (không phải official run): worktree tạm merge `origin/main` + `gminh` (d9002a4) + `TranDinhHinh` (ccb9851) + code M3, không commit | `quality.py` trên clean/corrupted thật | Baseline: `[quality] test: success=True passed=9/9 failed=[]` → in `Tín hiệu hoàn thành: Quality check status = True` (CP1). Corrupted 24→21 dòng: `passed=3/9 failed=['row_count', 'paper_id_unique', 'title_length', 'summary_length', 'summary_no_noise', 'freshness_sla']`, `stale_ratio=0.2857` | Khớp đúng bảng kỳ vọng C4-§5; validator `clean`, `quality`, `corruption_log` → OK |
| Report 3 trạng thái | `reporting.py::generate_corruption_report` | Markdown 4 mục: bảng so sánh (Δ, Recovery %), check fail, scenarios, findings sinh tự động | Render bằng fixture có và không có 3 kwargs tuỳ chọn → bản thiếu kwargs hiện `N/A`, không crash |

Output cụ thể phần việc của tôi tạo ra: bảng **Three-State Comparison** trong `data/reports/corruption_report.md`. Mọi số trong bảng và mục Findings đều tính trực tiếp từ dict đầu vào (Δ Corruption = Corrupted − Baseline, Δ Repair = Repaired − Corrupted, Recovery % = Δ Repair / (Baseline − Corrupted)), không có câu nhận định viết cứng — nên báo cáo không thể "đẹp hơn" số liệu thật.

## 4. Giải thích phần kỹ thuật đã thực hiện

### Vấn đề cần giải quyết

Khi dữ liệu bị bẩn, RAG vẫn chạy và trả lời bình thường nhưng sai (silent failure). Cần một chốt kiểm dịch tự động phát hiện dữ liệu bẩn **trước** khi vào index, cộng với tín hiệu độ mới của dữ liệu, và một báo cáo nối được "dữ liệu thay đổi → tín hiệu quality thay đổi → metric của agent thay đổi".

### Cách triển khai

- **GX 1.x ephemeral:** `gx.get_context(mode="ephemeral")` → pandas data source → dataframe asset → batch definition whole dataframe → `ExpectationSuite` tên `papers_suite_<report_name>` → `ValidationDefinition.run(batch_parameters={"dataframe": df})`. Không dùng API cũ (`ge.from_pandas`, `validator.expect_*`).
- **8 expectation**: row count 23..24 (`ceil(0.95*max_results)`..`max_results`), not-null cho `paper_id`/`title`/`summary`, unique `paper_id`, độ dài `title ≥ 8`, `summary ≥ 50`, và regex `[@#$%&*~^]{4,}` không được xuất hiện trong summary. Mỗi check tương ứng một kịch bản corruption của C5.
- **Gắn kết quả về check ID:** mỗi expectation được gắn `meta={"check_id": ...}`, sau khi validate tôi map `result.results` theo `meta` chứ không theo thứ tự — tránh lệch nếu GX trả kết quả khác thứ tự thêm vào.
- **Kiểu dữ liệu:** GX trả numpy scalar; hàm `_json_safe` ép về kiểu JSON thuần và làm tròn 4 chữ số để `write_json` không lỗi.
- **Freshness:** `stale = age_days > 180`, `stale_ratio = stale/total`, `is_fresh = stale_ratio ≤ 0.25`. Một helper `_freshness_summary` dùng chung cho cả check `freshness_sla` trong quality report và `build_freshness_report` → hai file không thể lệch nhau.
- `success = gx_success AND is_fresh`, đồng thời giữ riêng `gx_success` để phân biệt lỗi schema/validity với lỗi timeliness.
- **Reporting:** heading và hàng/cột cố định theo C6-§3; đường dẫn artifact ghi tương đối so với project root (tránh lộ `D:\...`); bool hiển thị ✅/❌; delta của số nguyên hiển thị dạng nguyên.

### Input, output và contract

| Thành phần                   | Mô tả                                     |
| ------------------------------ | ------------------------------------------- |
| Input                          | Dataframe 16 cột theo C2 (bắt buộc có `paper_id`, `title`, `summary`, `published`, `age_days`); `Settings`; metrics dict (C6-§4); `corruption_log` (C5-§4) |
| Output                         | Quality dict (C4-§3), freshness dict (C4-§4), `data/quality/*.json`, `data/quality/gx/papers_suite_*.json`, `data/reports/phase1_report.md`, `data/reports/corruption_report.md` |
| Module phụ thuộc             | `ingestion/cleaning.py` (M2), `ingestion/corruption.py` (M1), `evaluation/metrics.py` (có sẵn), `core/config.py`, `core/utils.py` |
| Module sử dụng output        | `pipelines/phase1.py`, `pipelines/corruption_flow.py` (M4); group report §7, §8, §10 |
| Điều kiện lỗi cần xử lý | Summary rỗng `""` không bị not-null bắt (đã có check độ dài); dataframe rỗng (ratio = 0, không chia 0); thiếu quality/freshness baseline trong report → `N/A`; mẫu số Recovery = 0 → `N/A` |

### Cách xác minh

```bash
uv run python script/check_contracts.py fixtures
uv run python -c "from pathlib import Path; import pandas as pd; from core.config import load_settings; from observability.quality import run_data_quality_checks; s=load_settings(project_dir=Path('../m3_scratch')); r=run_data_quality_checks(pd.read_json('docs/rules/fixtures/clean.sample.json'), s, 'fixture'); print(r['passed_checks'], r['total_checks'])"
```

(`project_dir` trỏ ra ngoài repo để không sinh artifact thử nghiệm trong `data/`.)

- **Kết quả mong đợi:** fixture 12 dòng fail duy nhất `row_count`; bản làm bẩn thủ công fail 6 check theo bảng C4-§5; mọi JSON qua validator.
- **Kết quả thực tế:** `[quality] fixture: success=False passed=8/9 failed=['row_count']`; bản làm bẩn: `passed=3/9 failed=['row_count', 'paper_id_unique', 'title_length', 'summary_length', 'summary_no_noise', 'freshness_sla']`; validator `quality`/`freshness` → `[OK]`.
- **Artifact/log:** chưa có artifact chính thức trong `data/quality/` — sẽ sinh khi M4 chạy official run.

## 5. Một quyết định kỹ thuật quan trọng

- **Bối cảnh:** Freshness SLA ("không quá 25% bài có `age_days > 180`") có thể làm trong GX hoặc tính riêng.
- **Các phương án đã cân nhắc:** (1) Dùng `ExpectColumnValuesToBeBetween(column="age_days", max_value=180, mostly=0.75)` trong suite; (2) tính `stale_ratio` bằng pandas trong một helper, đưa vào quality report như check thứ 9 `freshness_sla`, và tách cờ `gx_success`.
- **Phương án đã chọn:** (2).
- **Lý do:** `build_freshness_report` cũng cần đúng con số `stale_ratio`/`stale_rows` → một helper dùng chung đảm bảo quality report và freshness report không bao giờ lệch nhau. Tách `gx_success` khỏi `success` giúp report phân biệt "dữ liệu hỏng cấu trúc" với "dữ liệu cũ" — hai loại sự cố có cách xử lý khác nhau (repair vs re-fetch). Đổi lại, check freshness không nằm trong GX suite JSON.
- **Bằng chứng quyết định phù hợp:** Trên bản làm bẩn thủ công, report hiển thị riêng `freshness_sla` fail với `observed_value=0.4615`, `unexpected_count=6`, trong khi 5 check GX khác fail độc lập; `freshness_report.json` và `quality.freshness` cho cùng số.

## 6. Một lỗi hoặc blocker đã xử lý

- **Triệu chứng/lỗi nguyên văn:** `UnicodeEncodeError: 'charmap' codec can't encode characters in position 6-7: character maps to <undefined>`
- **Lệnh hoặc bước tái hiện:** Trên Windows, chạy lệnh nghiệm thu CP0 `python -c "import chromadb, great_expectations, sentence_transformers; print('Môi trường sẵn sàng')"`.
- **Nguyên nhân gốc:** Import thành công; lỗi nằm ở `print` — stdout của Python trên console Windows dùng bảng mã cp1252 không mã hoá được ký tự tiếng Việt. Mọi lệnh nghiệm thu trong CHECKPOINTS đều in tiếng Việt nên cả nhóm sẽ gặp.
- **Cách xử lý:** Bật UTF-8 mode của Python: `export PYTHONUTF8=1` (bash) / `setx PYTHONUTF8 1` (Windows, mở terminal mới). Trong `script/check_contracts.py` tôi giữ output thuần ASCII để không phụ thuộc cấu hình này.
- **Cách xác minh sau khi sửa:** Chạy lại lệnh → in `Môi trường sẵn sàng`, `gx 1.18.0 | chromadb 1.5.9 | st 5.5.1`.
- **Điều học được:** Phân biệt lỗi của chương trình với lỗi của môi trường hiển thị: đọc traceback đến frame cuối (`codecs.charmap_encode`) thay vì kết luận "import hỏng".

## 7. Hiểu biết về luồng end-to-end

Giải thích ngắn gọn bằng lời của bạn:

1. Dữ liệu đi từ Crossref đến vector index như thế nào?
2. Evaluation set và ground-truth document IDs dùng để đo retrieval/answer quality ra sao?
3. Quality checks khác freshness monitoring ở điểm nào trong bài lab?
4. Vì sao phải dùng cùng test set cho baseline, corrupted và repaired?
5. Repair được xem là thành công dựa trên artifact và metric nào?

**Câu trả lời:**

[TODO — tự viết bằng lời của mình trước khi nộp.]

## 8. Phân tích kết quả

> ⏳ **Chưa có số liệu.** Bảng dưới chỉ được điền bằng số chép từ `data/reports/corruption_report.md` của **official run do M4 thực hiện** (C6-§5), kèm hash commit artifact. Không dùng số từ fixture.

### Metrics chính

| Metric/signal          | Baseline | Corrupted | Repaired | Nhận xét của cá nhân |
| ---------------------- | -------: | --------: | -------: | ------------------------- |
| `retrieval_hit_rate` | chờ official run | chờ | chờ | |
| `mean_token_f1`      | chờ | chờ | chờ | |
| `judge_accuracy`     | chờ | chờ | chờ | |
| `mean_judge_score`   | chờ | chờ | chờ | |
| Quality checks         | chờ | chờ | chờ | Kỳ vọng theo C4-§5: 9/9 → 3/9 → 9/9 (cần đối chiếu số thật) |
| Freshness status       | chờ | chờ | chờ | Kỳ vọng: fresh → stale → fresh (cần đối chiếu số thật) |

### Kết luận từ số liệu

1. [Chờ official run] Data corruption → quality/freshness signal thay đổi → agent metric thay đổi.
2. [Chờ official run] Repair action → quality/freshness signal phục hồi → agent metric phục hồi hoặc chưa phục hồi.

Corruption nào ảnh hưởng rõ nhất và vì sao?

[Chờ official run.]

Kết quả nào khác với kỳ vọng ban đầu?

[Chờ official run.]

## 9. Điều học được và hướng cải thiện

### Ba điều quan trọng nhất

1. [TODO — tự viết.]
2. [TODO — tự viết.]
3. [TODO — tự viết.]

### Nếu có thêm thời gian

[TODO — tự viết.]

## 10. Cam kết của thành viên

Đánh dấu sau khi tự kiểm tra:

- [ ] Nội dung báo cáo phản ánh đúng phần việc và mức hiểu của tôi.
- [ ] Tôi có thể giải thích luồng end-to-end, không chỉ module mình phụ trách.
- [ ] Mọi kết luận về kết quả đều có artifact hoặc metric để đối chiếu.
- [ ] Tôi không ghi “đã chạy thành công” cho phần chưa được kiểm chứng.
- [ ] Báo cáo không chứa `.env`, API key, token hoặc secret.
- [ ] Báo cáo này không phải bản sao nguyên văn của báo cáo nhóm hoặc báo cáo thành viên khác.

**Họ và tên:** Nguyễn Đức Thịnh
**Ngày xác nhận:** [YYYY-MM-DD]
