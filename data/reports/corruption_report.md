# Corruption Impact Report

## 1. Three-State Comparison

| Metric | Baseline | Corrupted | Repaired | Δ Corruption | Δ Repair | Recovery % |
|---|---|---|---|---|---|---|
| `retrieval_hit_rate` | 1.0000 | 0.8000 | 1.0000 | -0.2000 | 0.2000 | 100.0% |
| `mean_token_f1` | 1.0000 | 0.8000 | 1.0000 | -0.2000 | 0.2000 | 100.0% |
| `judge_accuracy` | 1.0000 | 0.8000 | 1.0000 | -0.2000 | 0.2000 | 100.0% |
| `mean_judge_score` | 5.0000 | 4.2000 | 5.0000 | -0.8000 | 0.8000 | 100.0% |
| Quality checks passed | 9/9 | 3/9 | 9/9 | -6 | 6 | 100.0% |
| Quality success | ✅ True | ❌ False | ✅ True | N/A | N/A | N/A |
| Freshness `is_fresh` | ✅ True | ❌ False | ✅ True | N/A | N/A | N/A |
| `stale_ratio` | 0.0417 | 0.2857 | 0.0417 | 0.2440 | -0.2440 | 100.0% |
| Row count | 24 | 21 | 24 | -3 | 3 | 100.0% |

Δ Corruption = Corrupted − Baseline · Δ Repair = Repaired − Corrupted · Recovery % = Δ Repair / (Baseline − Corrupted) × 100 (N/A khi mẫu số = 0 hoặc giá trị bool).

## 2. Failed Quality Checks

- **baseline**: không có check fail
- **corrupted**: `row_count` (observed 21), `paper_id_unique` (observed 19.0476), `title_length` (observed 14.2857), `summary_length` (observed 14.2857), `summary_no_noise` (observed 14.2857), `freshness_sla` (observed 0.2857)
- **repaired**: không có check fail

## 3. Corruption Scenarios

Seed `42` · input 24 dòng → output 21 dòng.

| Scenario | Params | Affected rows |
|---|---|---|
| `drop_latest_records` | `{"fraction": 0.2, "count": 5}` | 5 |
| `blank_summary` | `{"count": 3}` | 3 |
| `inject_noise` | `{"count": 3, "noise_token": "@#$%&*~^"}` | 3 |
| `truncate_title` | `{"count": 3, "max_len": 6}` | 3 |
| `stale_date` | `{"count": 6, "shift_days": 400}` | 6 |
| `duplicate_rows` | `{"count": 2}` | 2 |

## 4. Findings

- `retrieval_hit_rate` giảm 0.2000 sau corruption (1.0000 → 0.8000); sau repair đạt 1.0000, phục hồi 100.0% phần chênh lệch.
- `mean_token_f1` giảm 0.2000 sau corruption (1.0000 → 0.8000); sau repair đạt 1.0000, phục hồi 100.0% phần chênh lệch.
- `judge_accuracy` giảm 0.2000 sau corruption (1.0000 → 0.8000); sau repair đạt 1.0000, phục hồi 100.0% phần chênh lệch.
- `mean_judge_score` giảm 0.8000 sau corruption (5.0000 → 4.2000); sau repair đạt 5.0000, phục hồi 100.0% phần chênh lệch.
- Quality gate `baseline`: pass 9/9, không có check fail.
- Quality gate `corrupted`: pass 3/9, fail `row_count`, `paper_id_unique`, `title_length`, `summary_length`, `summary_no_noise`, `freshness_sla`.
- Quality gate `repaired`: pass 9/9, không có check fail.
- Silent failure: `summary_not_null` vẫn pass trên dữ liệu corrupted (summary rỗng là `""` chứ không phải null), chỉ `summary_length` phát hiện được (3 dòng vi phạm).
- Freshness `baseline`: 1/24 dòng stale (ratio 0.0417, ngưỡng 0.25) → is_fresh = True.
- Freshness `corrupted`: 6/21 dòng stale (ratio 0.2857, ngưỡng 0.25) → is_fresh = False.
- Freshness `repaired`: 1/24 dòng stale (ratio 0.0417, ngưỡng 0.25) → is_fresh = True.
