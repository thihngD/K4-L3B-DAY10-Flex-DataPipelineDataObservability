from __future__ import annotations

from collections import Counter
from dataclasses import fields, replace
from datetime import date, datetime
from hashlib import sha256
import json
import re
from typing import Any
from uuid import uuid4

import pandas as pd

from core.config import Settings, load_settings
from core.utils import normalize_whitespace, now_utc, write_json
from evaluation.metrics import evaluate_pipeline
from ingestion.cleaning import CLEAN_COLUMNS, build_clean_dataframe, compose_text_for_embedding
from ingestion.crossref import PaperRecord
from observability.quality import (
    NOISE_REGEX, SUMMARY_MIN_LEN, TITLE_MIN_LEN, build_freshness_report, run_data_quality_checks,
)
from pipelines.phase1 import _save_dataframe
from retrieval.index import LocalEmbeddingIndex

# Fields that come from the source; cleaning derives every other column from them.
SOURCE_FIELDS = [field.name for field in fields(PaperRecord) if field.name != "paper_id"]
# Line prefixes of the copies that cleaning writes into text_for_embedding.
EMBEDDED_PREFIXES = {"title": "Title: ", "summary": "Summary: "}


def _schema_errors(payload: Any, run_date: datetime) -> list[dict[str, Any]]:
    """Check the clean contract before GX or indexing can encounter bad types."""
    if not isinstance(payload, list):
        return [{"reason": "Expected a JSON list of records"}]
    errors = []
    list_fields = {"authors", "categories"}
    integer_fields = {"age_days", "summary_chars"}
    for position, row in enumerate(payload):
        if not isinstance(row, dict):
            errors.append({"row": position, "reason": "Expected a record object"})
            continue
        invalid_fields = []
        for column in CLEAN_COLUMNS:
            value = row.get(column)
            if column in list_fields:
                valid = isinstance(value, list) and all(isinstance(item, str) for item in value)
            elif column in integer_fields:
                valid = type(value) is int and value >= 0
            else:
                valid = isinstance(value, str)
            if not valid:
                invalid_fields.append(column)
        if invalid_fields:
            errors.append({"row": position, "reason": "Missing or invalid field types", "fields": invalid_fields})
            continue
        if not row["paper_id"].strip():
            errors.append({"row": position, "field": "paper_id", "reason": "Empty identifier"})
        for column in ("published", "updated"):
            try:
                parsed = date.fromisoformat(row[column])
                if parsed.isoformat() != row[column] or parsed > run_date.date():
                    raise ValueError("Date must be YYYY-MM-DD and not in the future")
            except ValueError:
                errors.append({"row": position, "field": column, "reason": "Invalid or future date"})
        derived = {
            "summary_chars": len(row["summary"]),
            "authors_joined": ", ".join(row["authors"]),
            "categories_joined": ", ".join(row["categories"]),
        }
        derived["text_for_embedding"] = compose_text_for_embedding({**row, **derived})
        for column, value in derived.items():
            if row[column] != value:
                errors.append({"row": position, "field": column, "reason": "Derived value is inconsistent"})
    return errors


def _validate(payload: Any, settings: Settings, run_date: datetime, name: str) -> dict[str, Any]:
    errors = _schema_errors(payload, run_date)
    schema = {"success": not errors, "errors": errors}
    write_json(settings.paths.quality_dir / f"{name}_schema_report.json", schema)
    if errors:
        return {"success": False, "schema": schema, "quality": None, "freshness": None}
    frame = pd.DataFrame(payload, columns=CLEAN_COLUMNS)
    # A saved age naturally changes over time; assess freshness at this run's clock.
    frame["age_days"] = [max(0, (run_date.date() - date.fromisoformat(row["published"])).days) for row in payload]
    quality = run_data_quality_checks(frame, settings, name)
    freshness = build_freshness_report(frame, settings, settings.paths.quality_dir / f"{name}_freshness_report.json")
    return {"success": quality["success"], "schema": schema, "quality": quality, "freshness": freshness}


def _failed_checks(validation: dict[str, Any]) -> list[str] | None:
    """Failed check ids, or None when the schema failed before any check ran."""
    if validation["quality"] is None:
        return None
    return [check["id"] for check in validation["quality"]["checks"] if not check["success"]]


def _valid_date(value: Any, run_date: datetime) -> str | None:
    """Return the value if it is a YYYY-MM-DD date that is not in the future."""
    try:
        parsed = date.fromisoformat(value)
    except (TypeError, ValueError):
        return None
    return value if parsed.isoformat() == value and parsed <= run_date.date() else None


def _preview(value: Any, limit: int = 80) -> Any:
    return value[:limit] + "..." if isinstance(value, str) and len(value) > limit else value


def _repair_row(row: dict[str, Any], run_date: datetime) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Fix one row's source fields using only values the row itself still holds.

    Missing or blank fields are recovered from the copies cleaning wrote into the
    derived columns, noise tokens are stripped, and a publication date earlier
    than the record date in `updated` is restored from it.
    """
    fixed = {field: row.get(field) for field in SOURCE_FIELDS}
    fixes: list[dict[str, Any]] = []

    def restore(field: str, value: Any, method: str) -> None:
        fixes.append({"field": field, "method": method, "before": _preview(fixed[field]), "after": _preview(value)})
        fixed[field] = value

    embedded = row.get("text_for_embedding")
    lines = embedded.split("\n") if isinstance(embedded, str) else []
    for field, prefix in EMBEDDED_PREFIXES.items():
        copy = next((line[len(prefix):] for line in lines if line.startswith(prefix)), "")
        if (not isinstance(fixed[field], str) or not fixed[field].strip()) and copy.strip():
            restore(field, copy, "from_text_for_embedding")
        if isinstance(fixed[field], str) and re.search(NOISE_REGEX, fixed[field]):
            restore(field, normalize_whitespace(re.sub(rf"\s*{NOISE_REGEX}\s*", " ", fixed[field])), "strip_noise")

    for field in ("authors", "categories"):
        if not (isinstance(fixed[field], list) and all(isinstance(item, str) for item in fixed[field])):
            joined = row.get(f"{field}_joined")
            if isinstance(joined, str):
                restore(field, [item for item in joined.split(", ") if item], f"from_{field}_joined")
            else:
                restore(field, [], "cleared_invalid")

    published = _valid_date(fixed["published"], run_date)
    updated = _valid_date(fixed["updated"], run_date)
    # `updated` is the Crossref record date, which the parser also uses when a
    # publication date is missing; a publication date before it was shifted.
    if updated and (published is None or published < updated):
        restore("published", updated, "from_updated")
    elif published and updated is None:
        restore("updated", published, "from_published")

    for field in ("primary_category", "abs_url", "pdf_url", "comment"):
        if not isinstance(fixed[field], str):
            restore(field, "", "cleaning_default")
    return fixed, fixes


def _repair_records(payload: list[Any], run_date: datetime) -> tuple[list[PaperRecord], list[dict[str, Any]]]:
    """Repair the rows without any outside source.

    Drops repeated rows, fixes fields with `_repair_row` and drops rows whose
    paper_id, title, summary or publication date cannot be recovered. Titles and
    summaries that are too short cannot be lengthened; those rows are kept for
    retrieval and reported. Cleaning then recomputes the derived columns.
    """
    records: list[PaperRecord] = []
    repairs: list[dict[str, Any]] = []
    kept: set[str] = set()
    for position, row in enumerate(payload):
        paper_id = row.get("paper_id") if isinstance(row, dict) else None
        if not isinstance(paper_id, str) or not paper_id.strip():
            repairs.append({"action": "dropped_row", "row": position, "reason": "No paper_id"})
            continue
        if paper_id in kept:
            repairs.append({"action": "dropped_duplicate", "row": position, "paper_id": paper_id})
            continue
        fixed, fixes = _repair_row(row, run_date)
        repairs += [{"action": "repaired_field", "row": position, "paper_id": paper_id, **fix} for fix in fixes]
        lost = [field for field in ("title", "summary") if not isinstance(fixed[field], str) or not fixed[field].strip()]
        if not _valid_date(fixed["published"], run_date):
            lost.append("published")
        if lost:
            repairs.append({"action": "dropped_row", "row": position, "paper_id": paper_id,
                            "reason": f"Cannot recover {', '.join(lost)}"})
            continue
        for field, minimum in (("title", TITLE_MIN_LEN), ("summary", SUMMARY_MIN_LEN)):
            if len(fixed[field]) < minimum:
                repairs.append({"action": "unrecoverable_field", "row": position, "paper_id": paper_id,
                                "field": field, "reason": f"Shorter than {minimum} characters",
                                "value": _preview(fixed[field])})
        kept.add(paper_id)
        records.append(PaperRecord(paper_id=paper_id, **fixed))
    return records, repairs


def run_auto_repair(settings: Settings) -> dict[str, Any]:
    """Gate existing corrupted data, then repair it using only the data itself.

    No other file or network source is read. A repair that passes every check is
    published as `completed`; one that fixes some failed checks without breaking
    any is published as `partial`. All candidate artifacts and the index are
    isolated per run, the manifest is replaced atomically, and failures leave the
    previous manifest in place.
    """
    run_date = now_utc()
    run_id = run_date.strftime("%Y%m%dT%H%M%S%fZ") + "-" + uuid4().hex[:8]
    root = settings.paths.project_dir
    output_dir = root / "data" / "auto_repair"
    run_dir = output_dir / run_id
    run_dir.mkdir(parents=True)
    paths = replace(
        settings.paths,
        quality_dir=run_dir / "quality",
        gx_dir=run_dir / "quality" / "gx",
        repaired_clean_json=run_dir / "papers_clean_repaired.json",
        repaired_clean_csv=run_dir / "papers_clean_repaired.csv",
        repaired_embeddings_json=run_dir / "papers_embeddings_repaired.json",
        repaired_metrics=run_dir / "repaired_metrics.json",
        repaired_answers=run_dir / "repaired_answers.json",
        chroma_dir=run_dir / "chroma",
    )
    recovery_settings = replace(
        settings, paths=paths, repaired_collection_name=f"papers-auto-repair-{run_id.lower()}",
    )
    audit: dict[str, Any] = {
        "run_id": run_id,
        "status": "started",
        "started_at": run_date.isoformat(),
        "run_directory": run_dir.relative_to(root).as_posix(),
        "input_path": settings.paths.corrupted_clean_json.relative_to(root).as_posix(),
        "evaluation": {"status": "not_run"},
    }
    log_path = run_dir / "repair_log.json"

    def finish(status: str, error: str | None = None) -> dict[str, Any]:
        audit.update(status=status, finished_at=now_utc().isoformat())
        if error is not None:
            audit["error"] = error
        write_json(log_path, audit)
        print(f"[auto-repair] status={status} log={log_path.relative_to(root).as_posix()}")
        return audit

    write_json(log_path, audit)
    stage = "input"
    try:
        source_bytes = settings.paths.corrupted_clean_json.read_bytes()
        audit["input_sha256"] = sha256(source_bytes).hexdigest()
        try:
            payload = json.loads(source_bytes)
        except (ValueError, UnicodeDecodeError):
            payload = None  # Invalid JSON is a schema failure that no row repair can fix.
        audit["input_rows"] = len(payload) if isinstance(payload, list) else None
        stage = "validation"
        audit["input_validation"] = _validate(payload, recovery_settings, run_date, "corrupted")
        if audit["input_validation"]["success"]:
            return finish("skipped_healthy")

        audit["status"] = "repairing"
        write_json(log_path, audit)
        print("[auto-repair] quality/schema gate failed; repairing records from the input alone")
        stage = "repair"
        if not isinstance(payload, list):
            return finish("repair_failed", "Input is not a JSON list of records; nothing can be repaired")
        records, repairs = _repair_records(payload, run_date)
        audit["repair_summary"] = dict(Counter(item["action"] for item in repairs))
        audit["repaired_fields"] = dict(Counter(
            f"{item['field']}:{item['method']}" for item in repairs if item["action"] == "repaired_field"
        ))
        audit["repairs"] = repairs
        stage = "validation"
        repaired = build_clean_dataframe(records, run_date)
        audit["output_rows"] = len(repaired)
        _save_dataframe(repaired, paths.repaired_clean_json, paths.repaired_clean_csv)
        audit["candidate_validation"] = _validate(
            repaired.to_dict(orient="records"), recovery_settings, run_date, "repaired",
        )
        remaining = _failed_checks(audit["candidate_validation"])
        before = _failed_checks(audit["input_validation"])
        audit["remaining_failures"] = remaining
        # Publish a partial repair only if it fixes some failed checks and breaks none.
        if remaining is None or (before is not None and not set(remaining) < set(before)):
            return finish("validation_failed", "Repair did not improve the schema or quality gate")
        status = "partial" if remaining else "completed"

        stage = "index"
        index = LocalEmbeddingIndex.build(repaired, recovery_settings, paths.repaired_embeddings_json)
        audit["collection_name"] = index.collection_name
        stage = "evaluation"
        if settings.paths.eval_testset.is_file():
            # Freeze a copy for this run; the evaluation set never supplies repair data.
            frozen_testset = run_dir / "test_set.json"
            benchmark_bytes = settings.paths.eval_testset.read_bytes()
            frozen_testset.write_bytes(benchmark_bytes)
            audit["test_set_sha256"] = sha256(benchmark_bytes).hexdigest()
            bundle = evaluate_pipeline(
                recovery_settings, index, frozen_testset, paths.repaired_metrics, paths.repaired_answers,
            )
            audit["evaluation"] = {"status": "completed", "metrics": bundle.summary}
        else:
            audit["evaluation"] = {"status": "skipped", "reason": "No frozen evaluation set available"}

        stage = "publish"
        manifest = {
            "run_id": run_id,
            "status": status,
            "remaining_failures": remaining,
            "published_at": now_utc().isoformat(),
            "run_directory": audit["run_directory"],
            "clean_json": paths.repaired_clean_json.relative_to(root).as_posix(),
            "embeddings_manifest": paths.repaired_embeddings_json.relative_to(root).as_posix(),
            "repair_log": log_path.relative_to(root).as_posix(),
            "collection_name": index.collection_name,
        }
        audit.update(status=status, finished_at=now_utc().isoformat())
        write_json(log_path, audit)
        temporary_manifest = output_dir / f".latest-{run_id}.tmp"
        write_json(temporary_manifest, manifest)
        temporary_manifest.replace(output_dir / "latest.json")
        print(f"[auto-repair] status={status} remaining_failures={remaining} "
              f"log={log_path.relative_to(root).as_posix()}")
        return audit
    except Exception as exc:
        return finish(f"{stage}_failed", f"{type(exc).__name__}: {exc}")


def main() -> None:
    result = run_auto_repair(load_settings())
    if result["status"] not in {"completed", "partial", "skipped_healthy"}:
        raise SystemExit(1)
