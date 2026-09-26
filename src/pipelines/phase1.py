from __future__ import annotations

from hashlib import sha256
from pathlib import Path

import pandas as pd

from core.config import load_settings
from core.utils import ensure_parent, now_utc, read_json, write_csv, write_json
from evaluation.metrics import evaluate_pipeline
from evaluation.testset import build_test_set
from ingestion.cleaning import build_clean_dataframe
from ingestion.crossref import fetch_source_records
from observability.quality import build_freshness_report, run_data_quality_checks
from observability.reporting import generate_phase1_report
from retrieval.index import LocalEmbeddingIndex


def _save_dataframe(df: pd.DataFrame, json_path: Path, csv_path: Path) -> None:
    ensure_parent(json_path)
    df.to_json(json_path, orient="records", force_ascii=False, indent=2)
    write_csv(df, csv_path)


def _file_hash(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def main() -> None:
    """Build and evaluate the baseline, preserving the benchmark between runs."""
    settings = load_settings()
    paths = settings.paths
    run_date = now_utc()
    snapshot = paths.raw_api_response
    snapshot_mtime = snapshot.stat().st_mtime_ns if snapshot.exists() else None
    records = fetch_source_records(settings)
    # The source rewrites the snapshot only on a successful live fetch.
    if snapshot_mtime is not None and not settings.refresh_source:
        fetch_mode = "snapshot"
    elif snapshot.stat().st_mtime_ns == snapshot_mtime:
        fetch_mode = "fallback"
    else:
        fetch_mode = "live"

    df = build_clean_dataframe(records, run_date)
    if df.empty:
        raise ValueError("No valid papers remain after cleaning the source records.")
    _save_dataframe(df, paths.clean_json, paths.clean_csv)
    index = LocalEmbeddingIndex.build(df, settings)

    if settings.refresh_test_set or not paths.eval_testset.exists():
        test_set = build_test_set(df, paths.eval_testset)
    else:
        test_set = read_json(paths.eval_testset)
    if not test_set:
        raise ValueError("The evaluation set is empty; rerun with REFRESH_TEST_SET=1.")

    bundle = evaluate_pipeline(
        settings, index, paths.eval_testset, paths.baseline_metrics, paths.baseline_answers
    )
    quality = run_data_quality_checks(df, settings, "baseline")
    freshness = build_freshness_report(df, settings, paths.freshness_report)
    source_summary = {
        "source_api": settings.source_api,
        "source_query": settings.source_query,
        "source_filter": settings.source_filter,
        "fetch_mode": fetch_mode,
        "raw_records": len(records),
        "clean_rows": len(df),
        "run_date": run_date.isoformat(),
        "embedding_model": settings.embedding_model,
        "collection_name": index.collection_name,
        "top_k": settings.top_k,
        "llm_provider": settings.llm_provider,
        "llm_model": settings.model_name,
        "test_set_path": paths.eval_testset.relative_to(paths.project_dir).as_posix(),
        "test_set_size": len(test_set),
        "test_set_sha256": _file_hash(paths.eval_testset),
    }
    generate_phase1_report(paths.baseline_report, source_summary, bundle.summary, quality, freshness)
    # Keep the comparison tied to the baseline's time and exact input snapshots.
    write_json(paths.baseline_metrics.with_name("baseline_run.json"), {
        **source_summary,
        "raw_records_sha256": _file_hash(paths.raw_records_json),
        "clean_sha256": _file_hash(paths.clean_json),
    })
    print(
        f"[phase1] done hit_rate={bundle.summary['retrieval_hit_rate']:.4f} "
        f"token_f1={bundle.summary['mean_token_f1']:.4f} "
        f"quality={quality['success']} fresh={freshness['is_fresh']}"
    )
