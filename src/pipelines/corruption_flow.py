from __future__ import annotations

from datetime import datetime
import sys

import pandas as pd

from core.config import load_settings
from core.utils import now_utc, read_json
from evaluation.metrics import evaluate_pipeline
from ingestion.cleaning import build_clean_dataframe
from ingestion.corruption import corrupt_clean_dataframe
from ingestion.crossref import load_raw_records
from observability.quality import build_freshness_report, run_data_quality_checks
from observability.reporting import generate_corruption_report
from pipelines.phase1 import _file_hash, _save_dataframe
from retrieval.index import LocalEmbeddingIndex


def main() -> None:
    """Measure corruption and rebuild from raw data against the frozen benchmark."""
    settings = load_settings()
    paths = settings.paths
    required = (
        paths.baseline_metrics, paths.clean_json, paths.baseline_quality_report,
        paths.freshness_report, paths.eval_testset, paths.raw_records_json,
    )
    if any(not path.is_file() for path in required):
        raise SystemExit("Run script/run_phase1.py first")

    baseline_metrics = read_json(paths.baseline_metrics)
    baseline_quality = read_json(paths.baseline_quality_report)
    baseline_freshness = read_json(paths.freshness_report)
    baseline = pd.DataFrame(read_json(paths.clean_json))
    run_date = now_utc()
    manifest_path = paths.baseline_metrics.with_name("baseline_run.json")
    if manifest_path.exists():
        manifest = read_json(manifest_path)
        for path, key in (
            (paths.eval_testset, "test_set_sha256"),
            (paths.raw_records_json, "raw_records_sha256"),
            (paths.clean_json, "clean_sha256"),
        ):
            if _file_hash(path) != manifest[key]:
                raise SystemExit(f"Baseline input changed ({path.name}); run script/run_phase1.py first")
        run_date = datetime.fromisoformat(manifest["run_date"])

    corrupted = corrupt_clean_dataframe(baseline, paths.corruption_log)
    _save_dataframe(corrupted, paths.corrupted_clean_json, paths.corrupted_clean_csv)
    corrupted_index = LocalEmbeddingIndex.build(corrupted, settings, paths.corrupted_embeddings_json)
    corrupted_bundle = evaluate_pipeline(
        settings, corrupted_index, paths.eval_testset, paths.corrupted_metrics, paths.corrupted_answers
    )
    corrupted_quality = run_data_quality_checks(corrupted, settings, "corrupted")
    corrupted_freshness = build_freshness_report(
        corrupted, settings, paths.quality_dir / "corrupted_freshness_report.json"
    )

    repaired = build_clean_dataframe(load_raw_records(paths.raw_records_json), run_date)
    verified = (
        len(repaired) == len(baseline)
        and set(repaired["paper_id"]) == set(baseline["paper_id"])
    )
    # Age is time-dependent for legacy baselines without a run manifest.
    comparison_columns = [column for column in baseline.columns if column != "age_days"]
    verified = verified and (
        repaired[comparison_columns].to_dict(orient="records")
        == baseline[comparison_columns].to_dict(orient="records")
    )
    if manifest_path.exists():
        verified = verified and repaired["age_days"].tolist() == baseline["age_days"].tolist()
    print(f"[repair] verified={verified}")
    if not verified:
        raise SystemExit("Raw snapshot does not reproduce the baseline; run script/run_phase1.py first")
    _save_dataframe(repaired, paths.repaired_clean_json, paths.repaired_clean_csv)
    repaired_index = LocalEmbeddingIndex.build(repaired, settings, paths.repaired_embeddings_json)
    repaired_bundle = evaluate_pipeline(
        settings, repaired_index, paths.eval_testset, paths.repaired_metrics, paths.repaired_answers
    )
    repaired_quality = run_data_quality_checks(repaired, settings, "repaired")
    repaired_freshness = build_freshness_report(
        repaired, settings, paths.quality_dir / "repaired_freshness_report.json"
    )

    generate_corruption_report(
        paths.comparison_report, baseline_metrics, corrupted_bundle.summary, repaired_bundle.summary,
        corrupted_quality, repaired_quality, corrupted_freshness, repaired_freshness,
        baseline_quality=baseline_quality,
        baseline_freshness=baseline_freshness,
        corruption_log=read_json(paths.corruption_log),
    )
    report = paths.comparison_report.read_text(encoding="utf-8")
    comparison = report.split("## 1. Three-State Comparison", 1)[1].split("## 2.", 1)[0]
    # Redirected Windows consoles may not support the report's Unicode symbols.
    encoding = sys.stdout.encoding or "utf-8"
    print(comparison.strip().encode(encoding, errors="replace").decode(encoding))
