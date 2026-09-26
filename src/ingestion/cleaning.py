from __future__ import annotations

from datetime import date, datetime
import re
from typing import Any, Mapping

import pandas as pd

from core.utils import normalize_whitespace
from ingestion.crossref import PaperRecord

CLEAN_COLUMNS: list[str] = [
    "paper_id",
    "title",
    "summary",
    "authors",
    "categories",
    "primary_category",
    "published",
    "updated",
    "abs_url",
    "pdf_url",
    "comment",
    "age_days",
    "authors_joined",
    "categories_joined",
    "summary_chars",
    "text_for_embedding",
]


def compose_text_for_embedding(row: Mapping[str, Any]) -> str:
    """Ghép chuỗi đại diện embedding 5 phần cố định theo chuẩn Contract C2."""
    return "\n".join([
        f"Title: {row['title']}",
        f"Authors: {row['authors_joined']}",
        f"Published: {row['published']}",
        f"Categories: {row['categories_joined']}",
        f"Summary: {row['summary']}",
    ])


def _clean_text(value: str) -> str:
    """Loại bỏ tag XML/HTML còn sót và chuẩn hoá khoảng trắng."""
    if not value:
        return ""
    no_tags = re.sub(r"<[^>]+>", "", value)
    return normalize_whitespace(no_tags)


def build_clean_dataframe(records: list[PaperRecord], run_date: datetime) -> pd.DataFrame:
    """Clean raw records thành DataFrame sẵn sàng để embed và index.
    
    Tuân thủ đúng quy tắc xử lý 7 bước theo Contract C2:
    1. Chuẩn hoá title, summary.
    2. Tính age_days = max(0, (run_date.date() - date.fromisoformat(published)).days).
    3. Lọc bỏ các dòng có paper_id / title / summary rỗng.
    4. Dedupe theo paper_id, keep='first'.
    5. Tính các cột 13-16 (authors_joined, categories_joined, summary_chars, text_for_embedding).
    6. Sort published giảm dần, paper_id tăng dần, reset_index và reorder đúng CLEAN_COLUMNS.
    7. In dòng log chuẩn: [cleaning] input=<n> dropped_invalid=<a> dropped_duplicates=<b> output=<m>.
    """
    total_input = len(records)
    run_d = run_date.date() if hasattr(run_date, "date") else run_date

    valid_rows: list[dict[str, Any]] = []
    dropped_invalid = 0

    for rec in records:
        pid = str(rec.paper_id or "").strip()
        cleaned_title = _clean_text(rec.title or "")
        cleaned_summary = _clean_text(rec.summary or "")

        # 3. Lọc bỏ record có paper_id, title hoặc summary rỗng
        if not pid or not cleaned_title or not cleaned_summary:
            dropped_invalid += 1
            continue

        # Đảm bảo published ở định dạng YYYY-MM-DD
        pub_str = str(rec.published or "").strip()
        if not pub_str:
            dropped_invalid += 1
            continue

        try:
            pub_date = date.fromisoformat(pub_str[:10])
            age_days = max(0, (run_d - pub_date).days)
            published_val = pub_date.isoformat()
        except (ValueError, TypeError):
            dropped_invalid += 1
            continue

        upd_str = str(rec.updated or "").strip()
        updated_val = upd_str[:10] if upd_str else published_val

        authors_list = [str(a).strip() for a in (rec.authors or []) if str(a).strip()]
        categories_list = [str(c).strip() for c in (rec.categories or []) if str(c).strip()]
        primary_cat = str(rec.primary_category or "").strip() or (categories_list[0] if categories_list else "Uncategorized")
        abs_url = str(rec.abs_url or "").strip() or f"https://doi.org/{pid}"
        pdf_url = str(rec.pdf_url or "").strip() or abs_url
        comment_val = str(rec.comment or "").strip() or f"Crossref record {pid}"

        authors_joined = ", ".join(authors_list)
        categories_joined = ", ".join(categories_list)
        summary_chars = len(cleaned_summary)

        row_dict: dict[str, Any] = {
            "paper_id": pid,
            "title": cleaned_title,
            "summary": cleaned_summary,
            "authors": authors_list,
            "categories": categories_list,
            "primary_category": primary_cat,
            "published": published_val,
            "updated": updated_val,
            "abs_url": abs_url,
            "pdf_url": pdf_url,
            "comment": comment_val,
            "age_days": int(age_days),
            "authors_joined": authors_joined,
            "categories_joined": categories_joined,
            "summary_chars": summary_chars,
        }
        row_dict["text_for_embedding"] = compose_text_for_embedding(row_dict)
        valid_rows.append(row_dict)

    if not valid_rows:
        empty_df = pd.DataFrame(columns=CLEAN_COLUMNS)
        print(f"[cleaning] input={total_input} dropped_invalid={dropped_invalid} dropped_duplicates=0 output=0")
        return empty_df

    # 4. Khử trùng lặp theo paper_id, giữ bản ghi đầu tiên
    seen_ids: set[str] = set()
    deduped_rows: list[dict[str, Any]] = []
    dropped_duplicates = 0

    for r in valid_rows:
        if r["paper_id"] in seen_ids:
            dropped_duplicates += 1
        else:
            seen_ids.add(r["paper_id"])
            deduped_rows.append(r)

    df = pd.DataFrame(deduped_rows)

    # 6. Sắp xếp: published giảm dần, paper_id tăng dần
    df = df.sort_values(
        by=["published", "paper_id"],
        ascending=[False, True]
    ).reset_index(drop=True)

    # Đảm bảo đúng 16 cột và đúng thứ tự CLEAN_COLUMNS
    df = df[CLEAN_COLUMNS]

    print(
        f"[cleaning] input={total_input} dropped_invalid={dropped_invalid} "
        f"dropped_duplicates={dropped_duplicates} output={len(df)}"
    )
    return df
