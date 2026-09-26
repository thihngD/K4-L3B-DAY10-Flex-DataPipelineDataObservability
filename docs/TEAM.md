# Danh Sách Thành Viên & Báo Cáo Phân Công Nhóm

- **Tên Nhóm:** `[Điền tên nhóm]`
- **Mã Nhóm / Lớp:** `K4-L3B-DAY10`
- **Tên Repository Nộp Bài:** `K4-L3B-DAY10-TenNhom-DataPipelineDataObservability`

> Phân công chi tiết, timeline, quy tắc Git và contract input/output giữa các thành viên: [docs/rules/README.md](rules/README.md).

---

## # Thành viên

| STT | Họ và tên | MSSV | Email | Vai trò & Phân công công việc | Báo cáo cá nhân |
|---:|---|---|---|---|---|
| 1 | | | | **M1 — Source & Corruption owner** (`ingestion/crossref.py`, `ingestion/corruption.py`, `data/raw/`) · contract C1, C5 | `report/<MSSV1>_HoTen.md` |
| 2 | | | | **M2 — Data model & Eval-set owner** (`ingestion/cleaning.py`, `evaluation/testset.py`) · contract C2, C3 | `report/<MSSV2>_HoTen.md` |
| 3 | Nguyễn Đức Thịnh | 2A202602468 | thihnghldh@gmail.com | **M3 — Observability & Reporting owner** (`observability/quality.py` GX 1.x + Freshness, `observability/reporting.py`) · contract C4, C6-§3 · nhánh `thihn/02468` | [`report/NguyenDucThinh-0268.md`](../report/NguyenDucThinh-0268.md) |
| 4 | | | | **M4 — Trưởng nhóm / Integration & Repair owner** (`pipelines/phase1.py`, `pipelines/corruption_flow.py`, official run & artifacts) · contract C6 | `report/<MSSV4>_HoTen.md` |

---

## # Cá nhân

> Mỗi thành viên **tự khai** mục của mình sau khi hoàn thành (thiếu = −5đ/người). Chỉ ghi phần đã thực sự làm và có commit/artifact chứng minh.

### ## HoVaTen1-MSSV1 — M1 Source & Corruption
- **Phạm vi được giao:** `parse_crossref_payload`, `fetch_source_records` (retry 429/503, fallback snapshot), `load_raw_records`; `corrupt_clean_dataframe` với 6 kịch bản + `corruption_log.json`.
- **Công việc chi tiết đã hoàn thành:** [tự khai]
- **Điều học được / Đóng góp chính:** [tự khai]

### ## HoVaTen2-MSSV2 — M2 Data model & Eval-set
- **Phạm vi được giao:** `build_clean_dataframe` (dedupe, `age_days`, `text_for_embedding` 5 phần), `compose_text_for_embedding`, `build_test_set` (10 câu, 4 loại, đóng băng).
- **Công việc chi tiết đã hoàn thành:** [tự khai]
- **Điều học được / Đóng góp chính:** [tự khai]

### ## NguyenDucThinh-2A202602468 — M3 Observability & Reporting
- **Phạm vi được giao:** Quality Gate GX 1.x (9 check cố định), Freshness SLA, `generate_phase1_report`, `generate_corruption_report` (bảng 3 trạng thái).
- **Công việc chi tiết đã hoàn thành:**
  - `run_data_quality_checks`: GX 1.x ephemeral context + `ExpectationSuite` + `ValidationDefinition`, 8 expectation (row count, not-null ×3, unique `paper_id`, độ dài title/summary, regex noise) + check `freshness_sla`; ghi `data/quality/<name>_quality_report.json` và suite `data/quality/gx/papers_suite_<name>.json`.
  - `build_freshness_report`: latest/oldest published, `stale_rows`, `stale_ratio`, `is_fresh` (ngưỡng 180 ngày, tối đa 25% stale), dùng chung công thức với quality gate.
  - `generate_phase1_report` và `generate_corruption_report` (bảng Baseline/Corrupted/Repaired với Δ Corruption, Δ Repair, Recovery %, danh sách check fail, bảng scenario, findings sinh tự động từ số liệu); thêm 3 kwargs tuỳ chọn `baseline_quality`, `baseline_freshness`, `corruption_log` theo C6.
  - Đã kiểm chứng bằng fixture và thử tích hợp local với code M1 (`gminh`) + M2 (`TranDinhHinh`): baseline pass 9/9 (CP1 `Quality check status = True`), corrupted fail đúng 6 check theo C4-§5. Báo cáo markdown với số thật chờ `phase1.py`/`corruption_flow.py` (M4) và official run.
  - Ngoài phạm vi: soạn bộ contract `docs/rules/` C1–C7, fixture, `script/check_contracts.py`; hướng dẫn cài môi trường (`uv sync`, `PYTHONUTF8=1`).
- **Điều học được / Đóng góp chính:** Quality gate phải được thiết kế theo từng kịch bản lỗi cụ thể — check not-null không bắt được summary rỗng `""`, cần thêm check độ dài; đó chính là dạng silent failure mà quality gate phải chặn trước khi dữ liệu vào index.

### ## HoVaTen4-MSSV4 — M4 Integration & Repair (Trưởng nhóm)
- **Phạm vi được giao:** `phase1.main`, `corruption_flow.main` (corrupt → evaluate → idempotent repair từ raw → compare), merge nhánh, official run, ráp `group_report.md`.
- **Công việc chi tiết đã hoàn thành:** [tự khai]
- **Điều học được / Đóng góp chính:** [tự khai]
