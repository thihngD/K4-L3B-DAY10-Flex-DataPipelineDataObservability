from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import date
import html
from pathlib import Path
import re
import time

import requests

from core.config import Settings
from core.utils import normalize_whitespace, read_json, write_json


@dataclass(frozen=True)
class PaperRecord:
    paper_id: str
    title: str
    summary: str
    authors: list[str]
    categories: list[str]
    primary_category: str
    published: str
    updated: str
    abs_url: str
    pdf_url: str
    comment: str


def parse_crossref_payload(payload: dict) -> list[PaperRecord]:
    """Convert Crossref work items into the stable raw-record schema."""

    def clean_text(value: object) -> str:
        text = html.unescape(str(value or ""))
        return normalize_whitespace(re.sub(r"<[^>]+>", " ", text))

    def date_from_parts(value: object) -> str | None:
        if not isinstance(value, dict):
            return None
        date_parts = value.get("date-parts")
        if not isinstance(date_parts, list) or not date_parts or not isinstance(date_parts[0], list):
            return None
        try:
            parts = [int(part) for part in date_parts[0]]
            if not parts:
                return None
            year = parts[0]
            month = parts[1] if len(parts) > 1 else 1
            day = parts[2] if len(parts) > 2 else 1
            return date(year, month, day).isoformat()
        except (TypeError, ValueError):
            return None

    def date_from_datetime(value: object) -> str | None:
        if not isinstance(value, str) or len(value) < 10:
            return None
        try:
            return date.fromisoformat(value[:10]).isoformat()
        except ValueError:
            return None

    message = payload.get("message", {})
    items = message.get("items", []) if isinstance(message, dict) else []
    records: list[PaperRecord] = []

    for item in items:
        if not isinstance(item, dict):
            continue
        paper_id = str(item.get("DOI") or "").strip()
        title_values = item.get("title")
        title_value = title_values[0] if isinstance(title_values, list) and title_values else title_values
        title = clean_text(title_value)
        summary = clean_text(item.get("abstract"))
        if not paper_id or not title or not summary:
            continue

        authors: list[str] = []
        author_values = item.get("author", [])
        if isinstance(author_values, list):
            for author in author_values:
                if not isinstance(author, dict):
                    continue
                given = str(author.get("given") or "").strip()
                family = str(author.get("family") or "").strip()
                name = normalize_whitespace(f"{given} {family}")
                if not name:
                    name = str(author.get("name") or "").strip()
                if name:
                    authors.append(name)

        subject_values = item.get("subject", [])
        categories = (
            [str(category).strip() for category in subject_values if str(category).strip()]
            if isinstance(subject_values, list)
            else []
        )
        published = date_from_parts(item.get("published")) or date_from_parts(item.get("issued"))
        created = item.get("created")
        if not published and isinstance(created, dict):
            published = date_from_datetime(created.get("date-time"))
        if not published:
            continue

        deposited = item.get("deposited")
        updated = (
            date_from_datetime(created.get("date-time")) if isinstance(created, dict) else None
        ) or (date_from_datetime(deposited.get("date-time")) if isinstance(deposited, dict) else None) or published

        abs_url = str(item.get("URL") or "").strip() or f"https://doi.org/{paper_id}"
        pdf_url = abs_url
        links = item.get("link", [])
        if isinstance(links, list):
            for link in links:
                if isinstance(link, dict) and "pdf" in str(link.get("content-type") or "").lower():
                    pdf_url = str(link.get("URL") or abs_url).strip() or abs_url
                    break

        records.append(
            PaperRecord(
                paper_id=paper_id,
                title=title,
                summary=summary,
                authors=authors,
                categories=categories,
                primary_category=categories[0] if categories else "Uncategorized",
                published=published,
                updated=updated,
                abs_url=abs_url,
                pdf_url=pdf_url,
                comment=f"Crossref record {paper_id}",
            )
        )
    return records


def fetch_source_records(settings: Settings) -> list[PaperRecord]:
    """Fetch Crossref records, preferring the shared local snapshot by default."""
    snapshot_path = settings.paths.raw_api_response
    use_snapshot = not settings.refresh_source and snapshot_path.exists()
    mode = "snapshot"

    if use_snapshot:
        payload = read_json(snapshot_path)
    else:
        params = {
            "query": settings.source_query,
            "filter": settings.source_filter,
            "rows": settings.max_results,
        }
        retry_statuses = {429, 500, 502, 503, 504}
        payload = None
        last_error: Exception | None = None
        for attempt in range(4):
            try:
                response = requests.get("https://api.crossref.org/works", params=params, timeout=30)
                response.raise_for_status()
                payload = response.json()
                write_json(snapshot_path, payload)
                mode = "live"
                break
            except requests.HTTPError as exc:
                last_error = exc
                status = exc.response.status_code if exc.response is not None else None
                if status not in retry_statuses:
                    break
            except requests.RequestException as exc:
                last_error = exc
            except ValueError as exc:
                last_error = exc
                break

            if attempt < 3:
                time.sleep(2**attempt)

        if payload is None:
            if not snapshot_path.exists():
                raise RuntimeError(f"Crossref request failed and no local snapshot is available: {last_error}")
            print(f"[crossref] fallback to local snapshot: {last_error}")
            payload = read_json(snapshot_path)
            mode = "fallback"

    records = parse_crossref_payload(payload)
    write_json(settings.paths.raw_records_json, [asdict(record) for record in records])
    print(f"[crossref] mode={mode} records={len(records)}")
    return records


def load_raw_records(path: Path) -> list[PaperRecord]:
    """Load the persisted raw-record snapshot into PaperRecord instances."""
    return [PaperRecord(**item) for item in read_json(path)]
