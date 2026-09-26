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
| 2 |Trần Đình Hinh|2A202602399 | hinh2872@gmail.com | **M2 — Data model & Eval-set owner** (`ingestion/cleaning.py`, `evaluation/testset.py`) · contract C2, C3 | `report/2A202602399_TranDinhHinh.md` |
| 3 | | | | **M3 — Observability & Reporting owner** (`observability/quality.py` GX 1.x + Freshness, `observability/reporting.py`) · contract C4, C6-§3 | `report/<MSSV3>_HoTen.md` |
| 4 | | | | **M4 — Trưởng nhóm / Integration & Repair owner** (`pipelines/phase1.py`, `pipelines/corruption_flow.py`, official run & artifacts) · contract C6 | `report/<MSSV4>_HoTen.md` |

---

## # Cá nhân

> Mỗi thành viên **tự khai** mục của mình sau khi hoàn thành (thiếu = −5đ/người). Chỉ ghi phần đã thực sự làm và có commit/artifact chứng minh.

### ## HoVaTen1-MSSV1 — M1 Source & Corruption
- **Phạm vi được giao:** `parse_crossref_payload`, `fetch_source_records` (retry 429/503, fallback snapshot), `load_raw_records`; `corrupt_clean_dataframe` với 6 kịch bản + `corruption_log.json`.
- **Công việc chi tiết đã hoàn thành:** [tự khai]
- **Điều học được / Đóng góp chính:** [tự khai]

### ## TranDinhHinh-2A202602399 - M2 Data model & Eval-set
- **Phạm vi được giao:** `build_clean_dataframe` (khử trùng lặp, tính `age_days`, sinh `text_for_embedding` chuẩn 5 phần), `compose_text_for_embedding`, `build_test_set` (10 câu hỏi chuẩn hóa thuộc 4 nhóm nghiệp vụ).
- **Công việc chi tiết đã hoàn thành:** 
  1. Triển khai hoàn thiện Contract C2 trong `src/ingestion/cleaning.py`: Chuẩn hóa văn bản, xử lý triệt để giá trị rỗng/None, dedupe theo `paper_id`, tính `age_days` chuẩn UTC, sort theo `published` desc và `paper_id` asc.
  2. Triển khai hoàn thiện Contract C3 trong `src/evaluation/testset.py`: Xây dựng bộ test set 10 câu tất định, phân bổ 3 summary / 3 authors / 2 date / 2 categories, bọc nháy đơn tiêu đề để khớp router của `qa.py`.
  3. Chạy script kiểm định contract độc lập: Đạt `[OK] clean` và `[OK] testset`.
- **Điều học được / Đóng góp chính:** Nắm vững nguyên tắc Data Contract trong Data Engineering hiện đại; hiểu sâu về việc chuẩn hóa cấu trúc dữ liệu trước khi đưa vào mô hình Embedding nhằm tránh hiện tượng Data Drift; thiết kế bộ Benchmark Test Set mang tính tái lập (deterministic) cho hệ thống RAG.

### ## HoVaTen3-MSSV3 — M3 Observability & Reporting
- **Phạm vi được giao:** Quality Gate GX 1.x (9 check cố định), Freshness SLA, `generate_phase1_report`, `generate_corruption_report` (bảng 3 trạng thái).
- **Công việc chi tiết đã hoàn thành:** [tự khai]
- **Điều học được / Đóng góp chính:** [tự khai]

### ## HoVaTen4-MSSV4 — M4 Integration & Repair (Trưởng nhóm)
- **Phạm vi được giao:** `phase1.main`, `corruption_flow.main` (corrupt → evaluate → idempotent repair từ raw → compare), merge nhánh, official run, ráp `group_report.md`.
- **Công việc chi tiết đã hoàn thành:** [tự khai]
- **Điều học được / Đóng góp chính:** [tự khai]
