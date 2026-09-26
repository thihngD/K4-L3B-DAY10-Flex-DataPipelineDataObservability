# RULES — Phân công 4 thành viên & Contract dùng chung

> **Mục đích:** 4 người code **song song, độc lập** ngay từ phút đầu. Mọi chỗ "output của người này là input của người kia" đã được **chốt trường / kiểu / đường dẫn** trong các file `C*.md` dưới đây. Mỗi người code theo contract, tự test bằng fixture, không cần chờ người khác.
>
> **Contract version:** `v1.0` (chốt 2026-09-26). Đổi contract → xem mục 6.

---

## 1. Phân công

| TV | Nhánh Git | Vai trò | File sở hữu (chỉ owner được sửa) | Output bàn giao | Contract phải tuân thủ |
|---|---|---|---|---|---|
| **M1** | `gminh` | Source & Corruption owner | `src/ingestion/crossref.py`, `src/ingestion/corruption.py`, `data/raw/*` | Raw response + raw records; hàm `corrupt_clean_dataframe` + `corruption_log.json` | Phát hành: **C1**, **C5** · Tiêu thụ: C2 |
| **M2** | `TranDinhHinh` | Data model & Eval-set owner | `src/ingestion/cleaning.py`, `src/evaluation/testset.py` | Clean dataframe + `text_for_embedding`; test set 10 câu | Phát hành: **C2**, **C3** · Tiêu thụ: C1 |
| **M3** | `thihn/02468` | Observability & Reporting owner | `src/observability/quality.py`, `src/observability/reporting.py` | GX 1.x quality report, freshness report, `phase1_report.md`, `corruption_report.md` | Phát hành: **C4**, **C6-§3** · Tiêu thụ: C2, C5, C6 |
| **M4** | `VanQuocDung` | Integration & Repair owner (Trưởng nhóm) | `src/pipelines/phase1.py`, `src/pipelines/corruption_flow.py`, `.env.example`, toàn bộ artifact sinh ra trong `data/{clean,chroma,embeddings,eval,quality,results,reports}` | 2 flow chạy end-to-end, repair idempotent, **official run** + bộ metrics 3 trạng thái | Phát hành: **C6** · Tiêu thụ: C1–C5 |

**Code dùng chung đã hoàn chỉnh — ĐÓNG BĂNG, không ai sửa:** `src/core/*`, `src/retrieval/*`, `src/evaluation/metrics.py`, `script/run_*.py`. Nếu buộc phải sửa → M4 sửa và thông báo cả nhóm.

**Bonus (chỉ làm khi phần bắt buộc xong):** M3 → B1 dashboard (`dashboard/`), M4 → B2 auto-repair trong `corruption_flow.py`, M1 → B3 pytest (`tests/`).

---

## 2. Bản đồ phụ thuộc (ai chờ ai → đã được cắt bằng contract + fixture)

```text
             C1 raw records                C2 clean schema              C3 test set
M1 crossref ───────────────▶ M2 cleaning ─────────────────▶ M2 testset ─────────────┐
                                 │  C2                                              │
                                 ├──────────▶ M1 corruption ── C5 log + corrupted df ┤
                                 ├──────────▶ M3 quality/freshness ── C4 dicts ──────┤
                                 │                                                   ▼
                                 └──────────────────────────────────────────▶ M4 phase1 / corruption_flow
                                                                                     │ C6 metrics + source_summary
                                                                                     ▼
                                                                         M3 reporting ─▶ data/reports/*.md
```

| Cặp phụ thuộc | Người phát hành | Người tiêu thụ | Cách làm độc lập trước khi có code thật |
|---|---|---|---|
| Raw records | M1 | M2, M4 | `data/raw/crossref_records.json` **đã có sẵn** (24 bản ghi đúng C1). M2 load tạm bằng `[PaperRecord(**r) for r in json.load(...)]` |
| Clean dataframe | M2 | M1, M3, M4 | Dùng `docs/rules/fixtures/clean.sample.json` (đúng C2) |
| `compose_text_for_embedding` | M2 | M1 (corruption) | Định dạng chốt ở C2-§3. **M2 push hàm này đầu tiên (≤ 15')**. Trước đó M1 copy 5 dòng định dạng vào code tạm cục bộ |
| Test set | M2 | M4 | `docs/rules/fixtures/test_set.sample.json` |
| Quality / freshness dict | M3 | M4, M3-report | `fixtures/quality.sample.json`, `fixtures/freshness.sample.json` |
| Corruption log | M1 | M3-report, M4 | `fixtures/corruption_log.sample.json` |
| Metrics / source_summary | M4 (từ `evaluate_pipeline`) | M3-report | `fixtures/metrics.sample.json`, `fixtures/source_summary.sample.json` |

> ⚠️ Fixture chứa **số liệu giả** chỉ để dev/test. **Cấm** chép số từ fixture vào báo cáo (vi phạm "bịa số liệu" −20đ).

Kiểm tra output của mình có đúng contract: `python script/check_contracts.py <kind> [path]` (xem cuối file).

---

## 3. Danh mục contract

| File | Nội dung chốt | Owner |
|---|---|---|
| [C1_raw_records.md](C1_raw_records.md) | `PaperRecord` 11 trường, định dạng ngày/URL, hành vi fetch/fallback | M1 |
| [C2_clean_schema.md](C2_clean_schema.md) | 16 cột clean, kiểu, quy tắc dedupe/sort, `age_days`, `text_for_embedding` 5 phần | M2 |
| [C3_test_set.md](C3_test_set.md) | Schema câu hỏi, 4 template khớp `qa.py`, cách chọn paper, đóng băng test set | M2 |
| [C4_quality_freshness.md](C4_quality_freshness.md) | 9 check ID cố định, dict trả về, đường dẫn file, kết quả kỳ vọng 3 trạng thái | M3 |
| [C5_corruption.md](C5_corruption.md) | 6 kịch bản, tham số, seed, thứ tự, schema `corruption_log.json` | M1 |
| [C6_pipeline_reporting.md](C6_pipeline_reporting.md) | Thứ tự bước 2 flow, `source_summary`, metrics, repair, chữ ký report + cấu trúc markdown | M4 (+M3 §3) |
| [C7_report_fill_map.md](C7_report_fill_map.md) | Mục nào của `group_report.md` do ai điền, lấy số từ artifact/key nào | M4 |

---

## 4. Timeline 240'

| Mốc | M1 | M2 | M3 | M4 |
|---|---|---|---|---|
| 0–15' | Setup env, đọc C1/C5 | Setup, **push `compose_text_for_embedding` + hằng số cột (C2)** | Setup, đọc C4 | Setup, `.env`, kiểm tra 4 nhánh đã merge `main`, đọc toàn bộ C* |
| 15–60' | `crossref.py` (CP0) | `build_clean_dataframe` (CP1) | `run_data_quality_checks`, `build_freshness_report` (CP1) | `phase1.py` chạy với fixture |
| 60–95' | `corruption.py` (CP4) | `build_test_set` (CP2) | `generate_phase1_report` | Merge M1/M2/M3 bản đầu → chạy thật `run_phase1.py` (CP3) |
| 95–150' | Tự test corruption với clean thật; B3 nếu dư | Hỗ trợ M4 kiểm tra repaired == baseline | `generate_corruption_report` | `corruption_flow.py` + repair (CP4–CP5) |
| 150–180' | **Code freeze** — merge cuối vào `main` | ← | ← | ← |
| 180–210' | Viết individual + mục C7 được giao | ← | ← | **Official run** + commit artifact + ráp group report |
| 210–240' | Demo & Q&A (mọi người giải thích được end-to-end) | ← | ← | ← |

---

## 5. Quy tắc Git (tránh đè lên nhau)

1. Nhánh riêng: M1 `gminh` · M2 `TranDinhHinh` · M3 `thihn/02468` · M4 `VanQuocDung`. **Không push thẳng lên `main`.** Merge vào `main` bằng PR **"Create a merge commit"** (không squash, không rebase) để giữ commit từng người → Insights > Contributors đủ 4 người.
   - Bắt đầu làm: `git fetch origin && git checkout <nhánh> && git merge origin/main` (phải có `docs/rules/` trước khi code).
   - Khi `main` có thay đổi mới (rule, code người khác đã merge): `git merge origin/main` vào nhánh mình, không rebase nhánh đã push.
   - M4 tích hợp thử trước khi các PR vào `main`: tạo nhánh local `integration` từ `VanQuocDung` rồi `git merge origin/gminh origin/TranDinhHinh origin/thihn/02468` — **không push nhánh này**.
   - Thứ tự merge PR vào `main`: M2 → M1 → M3 → M4 (theo chiều phụ thuộc C2 → C5/C4 → C6).
2. **Chỉ `git add` file mình sở hữu**. Cấm `git add .` / `git add -A`. File dùng chung (`requirements.txt`, `pyproject.toml`, `uv.lock`, `src/core/*`, `src/retrieval/*`) chỉ đổi khi cả nhóm đồng ý.
3. Artifact sinh ra khi chạy thử cục bộ (`data/clean`, `data/chroma`, `data/results`…) **không commit** — chỉ M4 commit từ official run. `data/raw/*` chỉ M1 commit, và **không** thay snapshot trừ khi cả nhóm đồng ý.
4. `TEAM.md`, `group_report.md`: mỗi người chỉ sửa đúng mục của mình (C7) → tránh conflict. Báo cáo cá nhân: `report/<MSSV>_HoTen.md`.
5. Không commit `.env`. Không hardcode đường dẫn tuyệt đối — luôn dùng `settings.paths.*`.

---

## 6. Quy trình đổi contract

- Contract chỉ được đổi khi **owner phát hành + tất cả người tiêu thụ** đồng ý trong nhóm chat.
- Đổi thì: sửa file `C*.md`, tăng version (`v1.0 → v1.1`), ghi 1 dòng vào bảng changelog cuối file đó, commit riêng với message `contract: ...`.
- **Chỉ được mở rộng tương thích ngược** (thêm key/kwarg tuỳ chọn). Cấm đổi tên/xoá trường đã chốt sau mốc 60'.

---

## 7. Tự kiểm tra contract

```bash
python script/check_contracts.py raw            # data/raw/crossref_records.json
python script/check_contracts.py clean          # data/clean/papers_clean.json
python script/check_contracts.py testset        # data/eval/test_set.json
python script/check_contracts.py quality   data/quality/baseline_quality_report.json
python script/check_contracts.py freshness data/quality/freshness_report.json
python script/check_contracts.py corruption_log # data/results/corruption_log.json
python script/check_contracts.py metrics   data/results/baseline_metrics.json
python script/check_contracts.py fixtures       # tự kiểm tra toàn bộ fixture
```

Exit code 0 = đúng contract. Chạy trước mỗi lần merge.
