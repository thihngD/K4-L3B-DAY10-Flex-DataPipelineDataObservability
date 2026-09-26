# C1 — Raw Records Contract (M1 → M2, M4)

> **Owner:** M1 · **Consumer:** M2 (`cleaning.py`), M4 (`phase1.py`, repair trong `corruption_flow.py`) · **Version:** v1.0

## 1. Chữ ký hàm (KHÔNG đổi)

```python
parse_crossref_payload(payload: dict) -> list[PaperRecord]
fetch_source_records(settings: Settings) -> list[PaperRecord]
load_raw_records(path: Path) -> list[PaperRecord]
```

Bonus B2 mở rộng tương thích ngược: `fetch_source_records(settings, *, live_only=False,
attempt_log=None)`. Khi `live_only=True`, luôn gọi mạng và không fallback snapshot;
caller dùng đường dẫn output riêng cho mỗi lần recovery. `attempt_log` là list nhận
kết quả từng HTTP attempt. Mặc định vẫn giữ hành vi C1 bên dưới.

`PaperRecord` (dataclass frozen, đã có trong `crossref.py`) — **không thêm/bớt/đổi tên trường.**

## 2. Trường của `PaperRecord`

| Trường | Kiểu | Lấy từ Crossref item | Chuẩn hoá bắt buộc | Khi thiếu/sai |
|---|---|---|---|---|
| `paper_id` | `str` | `DOI` | `strip()` giữ nguyên hoa/thường như snapshot (vd `10.1145/3637528.3671801`) | **Bỏ record** |
| `title` | `str` | `title[0]` | Bỏ tag JATS/HTML (`<[^>]+>`), `normalize_whitespace` | **Bỏ record** nếu rỗng |
| `summary` | `str` | `abstract` | Bỏ tag `<jats:p>`, `<jats:italic>`…, `html.unescape`, `normalize_whitespace` | **Bỏ record** nếu rỗng |
| `authors` | `list[str]` | `author[*]` → `"{given} {family}"` | strip; bỏ phần tử rỗng; nếu chỉ có `name` thì dùng `name` | `[]` |
| `categories` | `list[str]` | `subject` | strip, bỏ rỗng, giữ thứ tự | `[]` |
| `primary_category` | `str` | `categories[0]` | — | `"Uncategorized"` |
| `published` | `str` `YYYY-MM-DD` | `published.date-parts[0]` → `issued.date-parts[0]` → `created.date-time[:10]` | Thiếu tháng/ngày → `01` | **Bỏ record** nếu không có ngày nào |
| `updated` | `str` `YYYY-MM-DD` | `created.date-time[:10]` → `deposited.date-time[:10]` | — | = `published` |
| `abs_url` | `str` | `URL` | — | `f"https://doi.org/{DOI}"` |
| `pdf_url` | `str` | `link[*]` có `content-type` chứa `pdf` | — | = `abs_url` |
| `comment` | `str` | — | `f"Crossref record {DOI}"` | — |

**Không bao giờ trả `None`** cho bất kỳ trường nào (Chroma metadata không nhận `None`).

## 3. Hành vi `fetch_source_records`

1. `settings.refresh_source == False` **và** `settings.paths.raw_api_response` tồn tại → **đọc snapshot local, không gọi mạng** (mặc định — đảm bảo mọi người cùng dữ liệu, kết quả tái lập).
2. Ngược lại gọi `https://api.crossref.org/works` với `query=settings.source_query`, `filter=settings.source_filter`, `rows=settings.max_results`, timeout 30s; retry tối đa 3 lần với backoff `2**attempt` giây cho status `429/500/502/503/504` và lỗi mạng.
3. Hết retry / mất mạng → **fallback** đọc snapshot `raw_api_response`; in `[crossref] fallback to local snapshot: <lý do>`.
4. Chỉ ghi đè `raw_api_response` khi gọi API **thành công**.
5. Parse → ghi `raw_records_json` = `[dataclasses.asdict(r) for r in records]` bằng `core.utils.write_json`, thứ tự giữ nguyên như payload.
6. In: `[crossref] mode=<snapshot|live|fallback> records=<n>`.

`load_raw_records(path)` = `[PaperRecord(**item) for item in read_json(path)]`.

## 4. Nghiệm thu (M1 tự chạy)

```bash
python -c "from core.config import load_settings; from ingestion.crossref import fetch_source_records; s=load_settings(); r=fetch_source_records(s); print(f'Tín hiệu hoàn thành: Đã tải {len(r)} bài báo')"
python script/check_contracts.py raw
```

Kỳ vọng: `Đã tải 24 bài báo`; file `crossref_records.json` sinh lại **giống byte với bản đang commit** (`git diff --stat data/raw` rỗng).

## Changelog
| Version | Thay đổi | Người duyệt |
|---|---|---|
| v1.0 | Chốt ban đầu | cả nhóm |
