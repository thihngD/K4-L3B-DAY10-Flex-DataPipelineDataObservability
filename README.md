# K4-L3B-Day10 — Data Pipeline & Data Observability for RAG

> **Hình thức:** Teamwork | **Thời lượng:** 240 phút  
> **Lịch học (Lớp B - Ca Sáng):** Thứ 7 (26/09/2026) 09:00 – 13:00  
> ⏰ **Hạn nộp LMS:** 23:59:59 cùng ngày

---

## 🧭 Đọc gì, theo thứ tự nào?

| # | Tài liệu | Mô tả |
|:---:|---|---|
| 1️⃣ | **Codelab trên VLearn LMS** | Hướng dẫn từng bước + nộp bài (mở trên trình duyệt) |
| 2️⃣ | [CHECKPOINTS.md](docs/CHECKPOINTS.md) | Phân bổ thời gian 240 phút & deliverables từng mốc |
| 3️⃣ | [RUBRIC.md](docs/RUBRIC.md) | Tiêu chí chấm điểm (100 chuẩn + 10 bonus) |
| 4️⃣ | [SUBMISSION.md](docs/SUBMISSION.md) | Nội quy, deadline, bảo mật & checklist nộp bài |
| 5️⃣ | [TEAM.md](docs/TEAM.md) | Điền thông tin nhóm & báo cáo cá nhân |
| 6️⃣ | [rules/README.md](docs/rules/README.md) | Phân công 4 thành viên, timeline, contract input/output (C1–C7), fixture & `script/check_contracts.py` |

---

## Repo có sẵn gì? (Scaffolded Baseline)

- `data/raw/` — Snapshot offline Crossref API (`crossref_response.json`)
- `src/` — Khung pipeline thu thập, embedding MiniLM, đánh giá metrics (có `TODO(student)`)
- `script/` — Entrypoints: `run_phase1.py`, `run_corruption_flow.py`

## Học viên cần làm gì?

1. Hoàn thiện **Data Quality Gate** (Great Expectations 1.x) trong `src/observability/quality.py`
2. Tích hợp **Freshness Check** (`age_days`) vào Quality Gate
3. Chạy **Baseline → Corruption → Repair** → xuất bảng đối chiếu 3 trạng thái
4. **Live Demo** trên bảng & nộp link repo lên VLearn LMS

## Bonus B1: Observability dashboard

```powershell
.\.venv\Scripts\python.exe dashboard/build_dashboard.py
```

Đọc artifact của baseline, corrupted, repaired và lần auto-repair B2 mới nhất rồi sinh
`dashboard/index.html` (một file HTML, mở offline bằng trình duyệt). Dashboard hiển thị trạng thái
quality gate và freshness SLA, phân bố `age_days` so với baseline, cảnh báo drift (số dòng, tuổi
bài báo, metric) và kết quả từng check theo từng trạng thái. Chạy lại lệnh sau mỗi lần pipeline chạy.

## Bonus B2: Auto-repair từng record

```powershell
.\.venv\Scripts\python.exe script/run_corruption_flow.py --auto-repair
```

Kiểm tra `data/clean/papers_clean_corrupted.json`; khi schema hoặc quality/freshness gate fail,
pipeline tự sửa từng record chỉ dựa trên chính bảng đó: bỏ dòng trùng, bỏ nhiễu, khôi phục ngày
từ `updated`, lấy lại field từ các cột dẫn xuất và bỏ dòng không khôi phục được. Dữ liệu sửa xong
được kiểm định lại và publish ở trạng thái `completed` hoặc `partial`. Không đọc snapshot và không
gọi mạng. Lệnh không có `--auto-repair` vẫn chạy flow bắt buộc ban đầu.

Xem [hướng dẫn và bằng chứng B2](docs/AUTO_REPAIR.md) về log, artifact, kiểm thử và xử lý lỗi.
