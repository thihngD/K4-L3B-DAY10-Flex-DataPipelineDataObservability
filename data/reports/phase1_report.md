# Phase 1 Baseline Report

## 1. Source

| Key | Value |
|---|---|
| `source_api` | Crossref REST API |
| `source_query` | agentic retrieval augmented generation large language model |
| `source_filter` | from-pub-date:2026-03-30,has-abstract:true |
| `fetch_mode` | snapshot |
| `raw_records` | 24 |
| `clean_rows` | 24 |
| `run_date` | 2026-09-26T04:25:47.757226+00:00 |
| `embedding_model` | sentence-transformers/all-MiniLM-L6-v2 |
| `collection_name` | papers-baseline |
| `top_k` | 4 |
| `llm_provider` | mock |
| `llm_model` | mock |
| `test_set_path` | data/eval/test_set.json |
| `test_set_size` | 10 |
| `test_set_sha256` | c74629783d6a6c2ad1bfbc3e3c60bfb724e3e55a08d0102c7013bcaafb796c8e |

## 2. Retrieval & Answer Metrics

| Metric | Value |
|---|---|
| `samples` | 10 |
| `retrieval_hit_rate` | 1.0000 |
| `mean_token_f1` | 1.0000 |
| `judge_accuracy` | 1.0000 |
| `mean_judge_score` | 5.0000 |
| `ragas` | `{"skipped": "Set RUN_RAGAS=1 to enable the slower Ragas pass."}` |

## 3. Data Quality (GX 1.x)

Suite `papers_suite_baseline` — success = ✅ True, GX success = ✅ True, passed 9/9, row count = 24.

| ID | Dimension | Threshold | Observed | Pass |
|---|---|---|---|---|
| `row_count` | Volume | `23..24` | 24 | ✅ True |
| `paper_id_not_null` | Completeness | `no nulls` | 0.0000 | ✅ True |
| `title_not_null` | Completeness | `no nulls` | 0.0000 | ✅ True |
| `summary_not_null` | Completeness | `no nulls` | 0.0000 | ✅ True |
| `paper_id_unique` | Uniqueness | `unique` | 0.0000 | ✅ True |
| `title_length` | Validity | `len>=8` | 0.0000 | ✅ True |
| `summary_length` | Completeness/Validity | `len>=50` | 0.0000 | ✅ True |
| `summary_no_noise` | Validity | `[@#$%&*~^]{4,}` | 0.0000 | ✅ True |
| `freshness_sla` | Timeliness | `age_days>180 ratio<=0.25` | 0.0417 | ✅ True |

## 4. Freshness SLA

| Key | Value |
|---|---|
| `latest_published` | 2026-07-22 |
| `oldest_published` | 2026-03-28 |
| `stale_rows` | 1 |
| `total_rows` | 24 |
| `stale_ratio` | 0.0417 |
| `threshold_days` | 180 |
| `max_stale_ratio` | 0.2500 |
| `is_fresh` | ✅ True |
| `generated_at` | 2026-09-26T04:25:53+00:00 |

## 5. Artifacts

- `data/raw/crossref_response.json` ✅
- `data/raw/crossref_records.json` ✅
- `data/clean/papers_clean.csv` ✅
- `data/clean/papers_clean.json` ✅
- `data/embeddings/papers_embeddings.json` ✅
- `data/eval/test_set.json` ✅
- `data/results/baseline_metrics.json` ✅
- `data/results/baseline_answers.json` ✅
- `data/quality/baseline_quality_report.json` ✅
- `data/quality/freshness_report.json` ✅
- `data/reports/phase1_report.md` ✅
- `data/chroma/` ✅
