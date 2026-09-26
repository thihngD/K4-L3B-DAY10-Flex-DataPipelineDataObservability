"""Exercise orchestration with real cleaning, GX, evaluation, and reporting.

Only vector search is replaced so regression tests need no model download.
"""
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path
import shutil

import pytest

from core.config import load_settings
from core.utils import read_json
from pipelines import corruption_flow, phase1
from retrieval.index import LocalEmbeddingIndex, SearchResult


class MemoryIndex:
    def __init__(self, df, settings, output_path=None):
        self.collection_name = LocalEmbeddingIndex._derive_collection_name(settings, output_path)
        self.documents = LocalEmbeddingIndex._build_documents(df)
        self.top_k = settings.top_k

    def lookup(self, value):
        return next((d for d in self.documents if value.lower() in {
            d["paper_id"].lower(), d["title"].lower()
        }), None)

    def search(self, query, top_k=None):
        words = set(query.lower().split())
        documents = sorted(self.documents, key=lambda d: len(words & set(d["title"].lower().split())), reverse=True)
        return [SearchResult(d["paper_id"], d["title"], 1.0, d["content"], d["metadata"])
                for d in documents[:top_k or self.top_k]]


@pytest.fixture
def pipeline_settings(tmp_path, monkeypatch):
    settings = replace(load_settings(tmp_path), llm_provider="mock", model_name="mock",
                       refresh_source=False, refresh_test_set=False)
    monkeypatch.setattr(phase1, "load_settings", lambda: settings)
    monkeypatch.setattr(corruption_flow, "load_settings", lambda: settings)
    monkeypatch.setattr("observability.reporting.load_settings", lambda: settings)
    monkeypatch.setattr(LocalEmbeddingIndex, "build", MemoryIndex)
    monkeypatch.setattr(phase1, "now_utc", lambda: datetime(2026, 9, 26, tzinfo=UTC))
    monkeypatch.setenv("RUN_RAGAS", "0")
    settings.paths.raw_api_response.parent.mkdir(parents=True)
    root = Path(__file__).resolve().parents[1]
    shutil.copyfile(root / "data/raw/crossref_response.json", settings.paths.raw_api_response)
    return settings


def test_baseline_corruption_repair_is_repeatable(pipeline_settings, monkeypatch, capsys):
    paths = pipeline_settings.paths
    phase1.main()
    frozen = paths.eval_testset.read_bytes()
    baseline_bytes = paths.clean_json.read_bytes()
    raw_bytes = paths.raw_records_json.read_bytes()
    baseline_metrics = read_json(paths.baseline_metrics)
    assert baseline_metrics["samples"] == 10
    assert read_json(paths.baseline_quality_report)["success"] is True
    assert read_json(paths.freshness_report)["is_fresh"] is True
    assert read_json(paths.baseline_metrics.with_name("baseline_run.json"))["fetch_mode"] == "snapshot"

    def unexpected_call(*args, **kwargs):
        pytest.fail("The comparison must reuse raw records and the frozen benchmark")

    monkeypatch.setattr(phase1, "build_test_set", unexpected_call)
    # A second baseline run must leave the existing benchmark byte-for-byte intact.
    phase1.main()
    monkeypatch.setattr(phase1, "fetch_source_records", unexpected_call)
    monkeypatch.setattr("requests.get", unexpected_call)
    # Even on a later day repair uses the baseline clock.
    monkeypatch.setattr(corruption_flow, "now_utc", lambda: datetime(2027, 9, 26, tzinfo=UTC))
    corruption_flow.main()
    first_metrics = read_json(paths.corrupted_metrics)
    assert read_json(paths.corrupted_quality_report)["success"] is False
    assert read_json(paths.quality_dir / "corrupted_freshness_report.json")["is_fresh"] is False
    assert read_json(paths.quality_dir / "repaired_quality_report.json")["success"] is True
    assert read_json(paths.repaired_metrics) == baseline_metrics
    assert paths.repaired_clean_json.read_bytes() == baseline_bytes
    assert len(read_json(paths.corruption_log)["scenarios"]) == 6
    assert first_metrics["mean_token_f1"] < baseline_metrics["mean_token_f1"]

    corruption_flow.main()
    assert read_json(paths.corrupted_metrics) == first_metrics
    assert read_json(paths.repaired_metrics) == baseline_metrics
    assert paths.clean_json.read_bytes() == baseline_bytes
    assert paths.raw_records_json.read_bytes() == raw_bytes
    assert paths.eval_testset.read_bytes() == frozen
    assert "| Metric | Baseline | Corrupted | Repaired |" in paths.comparison_report.read_text(encoding="utf-8")
    assert "[repair] verified=True" in capsys.readouterr().out


def test_missing_baseline_has_actionable_error(pipeline_settings):
    with pytest.raises(SystemExit, match="Run script/run_phase1.py first"):
        corruption_flow.main()
    assert not pipeline_settings.paths.corruption_log.exists()


@pytest.mark.parametrize("artifact", ["eval_testset", "raw_records_json", "clean_json"])
def test_modified_input_is_rejected_before_corruption(pipeline_settings, artifact):
    phase1.main()
    paths = pipeline_settings.paths
    changed_path = getattr(paths, artifact)
    changed_path.write_bytes(changed_path.read_bytes() + b"\n")
    with pytest.raises(SystemExit, match="Baseline input changed"):
        corruption_flow.main()
    assert not paths.corruption_log.exists()


def test_benchmark_refresh_is_explicit(pipeline_settings, monkeypatch):
    paths = pipeline_settings.paths
    paths.eval_testset.parent.mkdir(parents=True)
    paths.eval_testset.write_text("[]", encoding="utf-8")
    monkeypatch.setattr(phase1, "load_settings", lambda: replace(pipeline_settings, refresh_test_set=True))
    phase1.main()
    assert len(read_json(paths.eval_testset)) == 10

