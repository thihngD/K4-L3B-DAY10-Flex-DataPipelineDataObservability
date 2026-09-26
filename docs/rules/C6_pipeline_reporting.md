# C6 — Pipeline, Metrics & Reporting Contract (M4 ↔ M3)

> **Owner:** M4 (§1, §2, §4) · M3 (§3 — nội dung markdown) · **Version:** v1.0

## 1. `phase1.main()` — thứ tự bước & artifact (M4)

| # | Bước | Gọi | Artifact |
|---|---|---|---|
| 1 | `settings = load_settings()`; `run_date = now_utc()` (dùng **một** `run_date` cho cả run) | core | — |
| 2 | Raw | `fetch_source_records(settings)` (C1) | `data/raw/*.json` |
| 3 | Clean | `build_clean_dataframe(records, run_date)` (C2) → ghi JSON+CSV theo C2-§5 | `data/clean/papers_clean.{json,csv}` |
| 4 | Index | `LocalEmbeddingIndex.build(df, settings)` → collection `papers-baseline` | `data/chroma/`, `data/embeddings/papers_embeddings.json` |
| 5 | Test set | Load hoặc `build_test_set` theo C3-§5 | `data/eval/test_set.json` |
| 6 | Evaluate | `evaluate_pipeline(settings, index, eval_testset, baseline_metrics, baseline_answers)` | `data/results/baseline_{metrics,answers}.json` |
| 7 | Quality | `run_data_quality_checks(df, settings, "baseline")` (C4) | `data/quality/baseline_quality_report.json` |
| 8 | Freshness | `build_freshness_report(df, settings, settings.paths.freshness_report)` | `data/quality/freshness_report.json` |
| 9 | Report | `generate_phase1_report(baseline_report, source_summary, metrics, quality, freshness)` | `data/reports/phase1_report.md` |
| 10 | (tuỳ chọn) Agent demo 2–3 câu nếu `LLM_PROVIDER` ≠ `mock` và có key; lỗi thì bỏ qua, **không** làm fail pipeline | `build_agent`, `run_agent_question` | `data/results/agent_demo_answers.json` |

Console cuối: `[phase1] done hit_rate=<x> token_f1=<y> quality=<bool> fresh=<bool>`. Exit code 0.

### `source_summary` — đúng các key

```json
{
  "source_api": "Crossref REST API",
  "source_query": "...", "source_filter": "...",
  "fetch_mode": "snapshot",
  "raw_records": 24, "clean_rows": 24,
  "run_date": "2026-09-26T03:00:00+00:00",
  "embedding_model": "sentence-transformers/all-MiniLM-L6-v2",
  "collection_name": "papers-baseline", "top_k": 4,
  "llm_provider": "mock", "llm_model": "...",
  "test_set_path": "data/eval/test_set.json", "test_set_size": 10, "test_set_sha256": "..."
}
```

Đường dẫn trong mọi dict/report ghi **tương đối so với project root** (tránh lộ `D:\...` → −5đ).

## 2. `corruption_flow.main()` — thứ tự bước (M4)

| # | Bước | Artifact |
|---|---|---|
| 1 | Load `baseline_metrics.json`, `papers_clean.json`, baseline quality + freshness. Thiếu → `raise SystemExit("Run script/run_phase1.py first")` | — |
| 2 | `corrupted = corrupt_clean_dataframe(clean_df, settings.paths.corruption_log)` (C5) | `data/results/corruption_log.json` |
| 3 | Ghi corrupted JSON/CSV | `data/clean/papers_clean_corrupted.{json,csv}` |
| 4 | `LocalEmbeddingIndex.build(corrupted, settings, settings.paths.corrupted_embeddings_json)` → `papers-corrupted`; evaluate **cùng `eval_testset`** | `data/results/corrupted_{metrics,answers}.json` |
| 5 | Quality `"corrupted"` + freshness → `quality_dir/"corrupted_freshness_report.json"` | `data/quality/corrupted_*.json` |
| 6 | **Repair**: `load_raw_records(raw_records_json)` → `build_clean_dataframe(records, run_date)` — **không** đọc từ corrupted, **không** gọi mạng | `data/clean/papers_clean_repaired.{json,csv}` |
| 7 | Xác minh repair: `set(repaired.paper_id) == set(baseline.paper_id)` và `len` bằng nhau; in `[repair] verified=<bool>` | — |
| 8 | Index `papers-repaired` (`repaired_embeddings_json`), evaluate cùng test set, quality `"repaired"`, freshness `repaired_freshness_report.json` | `data/results/repaired_*.json`, `data/quality/repaired_*.json` |
| 9 | `generate_corruption_report(...)` (§3) rồi **in nội dung bảng 3 trạng thái ra console** | `data/reports/corruption_report.md` |

Idempotent: chạy `run_corruption_flow.py` 2 lần liên tiếp → metrics giống nhau (collection bị xoá & tạo lại trong `index.build`).

## 3. Reporting (M3)

### Chữ ký — mở rộng tương thích ngược (thêm kwargs tuỳ chọn ở CUỐI)

```python
generate_phase1_report(report_path, source_summary, metrics, quality, freshness) -> None

generate_corruption_report(
    report_path, baseline_metrics, corrupted_metrics, repaired_metrics,
    corrupted_quality, repaired_quality, corrupted_freshness, repaired_freshness,
    baseline_quality: dict | None = None,
    baseline_freshness: dict | None = None,
    corruption_log: dict | None = None,
) -> None
```

M4 **luôn truyền** 3 kwargs mới. Nếu `None` → cột/mục tương ứng ghi `N/A`.

### `phase1_report.md` — các heading cố định

`# Phase 1 Baseline Report` → `## 1. Source` (bảng từ `source_summary`) → `## 2. Retrieval & Answer Metrics` (samples, 4 metric, ragas) → `## 3. Data Quality (GX 1.x)` (bảng 9 check: ID | Dimension | Threshold | Observed | Pass) → `## 4. Freshness SLA` (bảng key C4-§4) → `## 5. Artifacts` (danh sách path tương đối).

### `corruption_report.md` — các heading cố định

1. `# Corruption Impact Report`
2. `## 1. Three-State Comparison` — bảng **đúng hàng/cột**:

| Metric | Baseline | Corrupted | Repaired | Δ Corruption | Δ Repair | Recovery % |
|---|---:|---:|---:|---:|---:|---:|
| `retrieval_hit_rate` | | | | | | |
| `mean_token_f1` | | | | | | |
| `judge_accuracy` | | | | | | |
| `mean_judge_score` | | | | | | |
| Quality checks passed | `p/t` | | | | | |
| Quality success | bool | | | | | |
| Freshness `is_fresh` | bool | | | | | |
| `stale_ratio` | | | | | | |
| Row count | | | | | | |

   - `Δ Corruption = Corrupted − Baseline`; `Δ Repair = Repaired − Corrupted`; `Recovery % = Δ Repair / (Baseline − Corrupted) × 100`, `N/A` khi mẫu = 0 hoặc giá trị bool.
   - Số thực làm tròn 4 chữ số; **mọi số lấy từ dict đầu vào**, không hardcode.
3. `## 2. Failed Quality Checks` — mỗi trạng thái: danh sách `id` fail + `observed_value`.
4. `## 3. Corruption Scenarios` — bảng từ `corruption_log.scenarios`: name | params | affected_rows.
5. `## 4. Findings` — câu sinh tự động từ số liệu (vd "`mean_token_f1` giảm 0.35 sau corruption và phục hồi 100%"); **không** viết câu định tính cố định.

## 4. Metrics — schema (sinh bởi `evaluate_pipeline`, đóng băng)

Key trong `*_metrics.json`: `samples`, `retrieval_hit_rate`, `mean_token_f1`, `judge_accuracy`, `mean_judge_score`, `ragas`. **Không ai** được thêm/đổi tên key; báo cáo dùng đúng tên này.

## 5. Official run (M4)

1. Sau code freeze, trên `main` sạch: `.env` đã chốt provider (ghi vào group report §4) → `python script/run_phase1.py` → `python script/run_corruption_flow.py`.
2. Commit toàn bộ artifact trong **một** commit `artifacts: official run <YYYY-MM-DD HH:MM>`; báo hash commit vào nhóm.
3. Từ đây mọi số trong group/individual report **chỉ chép từ artifact của commit đó**. Có sửa code → chạy lại official run, báo hash mới.

## 6. Bonus B2 — auto-repair từng record riêng biệt

`python script/run_corruption_flow.py --auto-repair` kiểm tra dữ liệu corrupted đã có;
khi schema/quality/freshness gate fail thì tự sửa từng record chỉ dựa trên chính bảng đó
(bỏ dòng trùng, bỏ nhiễu, khôi phục ngày từ `updated`, lấy lại field từ các cột dẫn xuất,
bỏ dòng không khôi phục được), rồi kiểm định lại: qua hết → `completed`; sửa được một phần
mà không làm fail thêm check nào → `partial`; còn lại không publish. Không đọc snapshot,
baseline, corruption log và không gọi mạng. Artifact nằm riêng tại `data/auto_repair/`.
Không có flag thì vẫn chạy flow bắt buộc tại §2.
Chi tiết và bằng chứng: [AUTO_REPAIR.md](../AUTO_REPAIR.md).

## Changelog
| Version | Thay đổi | Người duyệt |
|---|---|---|
| v1.0 | Chốt ban đầu; thêm 3 kwargs tuỳ chọn cho `generate_corruption_report` | cả nhóm |
