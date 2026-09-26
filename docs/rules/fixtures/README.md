# Fixtures — dữ liệu mẫu ĐÚNG CONTRACT, SỐ LIỆU GIẢ

> ⚠️ Chỉ dùng để dev/test song song khi module upstream chưa xong. **Cấm chép số từ đây vào bất kỳ báo cáo nào** (bịa số liệu = −20đ). Metrics trong `metrics.sample.json` là số bịa có chủ đích (0.123, 0.456…) để dễ nhận ra nếu bị chép nhầm.

| File | Contract | Dùng bởi | Ghi chú |
|---|---|---|---|
| `clean.sample.json` | C2 | M1 (corruption), M3 (quality), M2 (testset), M4 (index/evaluate) | 12 dòng lấy từ raw snapshot, `run_date = 2026-09-26`. Đủ để build index thật và sinh test set 10 câu |
| `test_set.sample.json` | C3 | M4 | Khớp `clean.sample.json`; chạy `evaluate_pipeline` được |
| `quality.sample.json` | C4 | M3 (reporting), M4 | `row_count` fail (12 < 23) — minh hoạ nhánh fail |
| `freshness.sample.json` | C4 | M3 (reporting), M4 | |
| `corruption_log.sample.json` | C5 | M3 (reporting) | Kịch bản 12 dòng → `stale_date`/`duplicate_rows` = 0 dòng |
| `metrics.sample.json` | C6-§4 | M3 (reporting) | Số giả |
| `source_summary.sample.json` | C6-§1 | M3 (`generate_phase1_report`) | |

Ví dụ M3 test report không cần pipeline:

```python
from pathlib import Path
from core.utils import read_json   # read_json nhận Path, không nhận str
from observability.reporting import generate_corruption_report
F = Path("docs/rules/fixtures")
m, q, f, log = (read_json(F / n) for n in ["metrics.sample.json", "quality.sample.json", "freshness.sample.json", "corruption_log.sample.json"])
generate_corruption_report("scratch_corruption_report.md", m, m, m, q, q, f, f,
                           baseline_quality=q, baseline_freshness=f, corruption_log=log)
```

Kiểm tra lại fixture: `python script/check_contracts.py fixtures`.
