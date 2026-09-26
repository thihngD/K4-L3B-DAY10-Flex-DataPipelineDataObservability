from copy import deepcopy
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path
import re

import pandas as pd
import pytest
import requests

from core.config import load_settings
from core.utils import read_json, write_json
from ingestion.cleaning import build_clean_dataframe
from ingestion.corruption import corrupt_clean_dataframe
from ingestion.crossref import fetch_source_records, parse_crossref_payload
from observability.quality import NOISE_REGEX
from pipelines import auto_repair
from pipelines.phase1 import _save_dataframe
from retrieval.index import LocalEmbeddingIndex, SearchResult

RUN_DATE = datetime(2026, 9, 26, tzinfo=UTC)


def source_payload():
    return {"message": {"items": [
        {
            "DOI": f"10.9999/source.{number:03}",
            "title": [f"Paper {number:02} on retrieval quality and data freshness"],
            "abstract": f"Study {number} examines reliable retrieval with scholarly metadata. It measures data quality and freshness.",
            "author": [{"given": "Example", "family": f"Researcher{number}"}],
            "subject": ["Information retrieval"],
            "published": {"date-parts": [[2026, 9, 1 + number]]},
        }
        for number in range(24)
    ]}}


class Response:
    def __init__(self, payload=None, status=200):
        self.payload = payload
        self.status_code = status

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError(f"HTTP {self.status_code}", response=self)

    def json(self):
        return deepcopy(self.payload)


class MemoryIndex:
    """Replace only vector storage; schema, GX, cleaning and evaluation run normally."""

    def __init__(self, df, settings, output_path):
        self.collection_name = LocalEmbeddingIndex._derive_collection_name(settings, output_path)
        self.documents = LocalEmbeddingIndex._build_documents(df)
        self.top_k = settings.top_k
        write_json(output_path, {"collection_name": self.collection_name})

    def lookup(self, value):
        return next((doc for doc in self.documents if value == doc["title"]), None)

    def search(self, query, top_k=None):
        return [SearchResult(doc["paper_id"], doc["title"], 1.0, doc["content"], doc["metadata"])
                for doc in self.documents[:top_k or self.top_k]]


@pytest.fixture
def settings(tmp_path, monkeypatch):
    settings = replace(load_settings(tmp_path), llm_provider="mock", model_name="mock", refresh_source=False)
    monkeypatch.setattr(auto_repair, "now_utc", lambda: RUN_DATE)
    monkeypatch.setattr(auto_repair, "load_settings", lambda: settings)
    monkeypatch.setattr(LocalEmbeddingIndex, "build", MemoryIndex)
    monkeypatch.setattr("requests.get", lambda *a, **k: pytest.fail("Auto-repair must not call the network"))
    monkeypatch.setenv("RUN_RAGAS", "0")
    return settings


def clean_rows():
    return build_clean_dataframe(parse_crossref_payload(source_payload()), RUN_DATE).to_dict(orient="records")


def corrupt_input(settings):
    """Apply the lab's six corruption scenarios and return their affected ids."""
    corrupted = corrupt_clean_dataframe(pd.DataFrame(clean_rows()), settings.paths.corruption_log)
    _save_dataframe(corrupted, settings.paths.corrupted_clean_json, settings.paths.corrupted_clean_csv)
    return {item["name"]: item["affected_paper_ids"] for item in read_json(settings.paths.corruption_log)["scenarios"]}


def repaired_rows(settings, result):
    return read_json(settings.paths.project_dir / result["run_directory"] / "papers_clean_repaired.json")


def previous_manifest(settings):
    path = settings.paths.project_dir / "data/auto_repair/latest.json"
    write_json(path, {"run_id": "previous-success"})
    return path, path.read_bytes()


def forbid_index(*args, **kwargs):
    pytest.fail("Unimproved data must not rebuild an index")


def test_healthy_input_is_left_alone(settings, monkeypatch):
    write_json(settings.paths.corrupted_clean_json, clean_rows())
    latest, before = previous_manifest(settings)
    monkeypatch.setattr(LocalEmbeddingIndex, "build", forbid_index)
    result = auto_repair.run_auto_repair(settings)
    assert result["status"] == "skipped_healthy"
    assert "repairs" not in result
    assert latest.read_bytes() == before


def test_lab_corruption_is_repaired_as_far_as_the_table_allows(settings):
    affected = corrupt_input(settings)
    before = settings.paths.corrupted_clean_json.read_bytes()
    result = auto_repair.run_auto_repair(settings)
    assert result["status"] == "partial", result.get("error")
    assert result["input_rows"] == 21
    assert result["output_rows"] == 16
    assert result["repair_summary"] == {
        "dropped_duplicate": 2, "repaired_field": 9, "dropped_row": 3, "unrecoverable_field": 3,
    }
    assert result["repaired_fields"] == {"summary:strip_noise": 3, "published:from_updated": 6}
    # Deleted rows leave no trace and truncated titles cannot be lengthened.
    assert result["remaining_failures"] == ["row_count", "title_length"]

    clean = {row["paper_id"]: row for row in clean_rows()}
    repaired = {row["paper_id"]: row for row in repaired_rows(settings, result)}
    assert set(repaired) == set(clean) - set(affected["drop_latest_records"]) - set(affected["blank_summary"])
    for paper_id, row in repaired.items():
        if paper_id in affected["inject_noise"]:
            assert not re.search(NOISE_REGEX, row["summary"])
            assert row["summary"].replace(" ", "") == clean[paper_id]["summary"].replace(" ", "")
        elif paper_id in affected["truncate_title"]:
            assert row["title"] == clean[paper_id]["title"][:6].strip()
        else:
            assert row == clean[paper_id]
    assert settings.paths.corrupted_clean_json.read_bytes() == before
    manifest = read_json(settings.paths.project_dir / "data/auto_repair/latest.json")
    assert manifest["run_id"] == result["run_id"]
    assert manifest["status"] == "partial"
    assert manifest["remaining_failures"] == ["row_count", "title_length"]
    assert (settings.paths.project_dir / manifest["embeddings_manifest"]).is_file()


@pytest.mark.parametrize(("defect", "expected"), [
    ("missing_summary", {"summary:from_text_for_embedding": 1}),
    ("wrong_type", {"authors:from_authors_joined": 1}),
    ("invalid_date", {"published:from_updated": 1}),
    ("future_date", {"published:from_updated": 1}),
])
def test_schema_defects_are_fixed_from_copies_inside_the_row(settings, defect, expected):
    rows = clean_rows()
    if defect == "missing_summary":
        del rows[0]["summary"]
    elif defect == "wrong_type":
        rows[0]["authors"] = "not a list"
    elif defect == "invalid_date":
        rows[0]["published"] = "not a date"
    else:
        rows[0]["published"] = "2027-01-01"
    write_json(settings.paths.corrupted_clean_json, rows)
    result = auto_repair.run_auto_repair(settings)
    assert result["status"] == "completed", result.get("error")
    assert not result["input_validation"]["schema"]["success"]
    assert result["repaired_fields"] == expected
    assert repaired_rows(settings, result) == clean_rows()


def test_rows_without_a_paper_id_are_dropped(settings):
    write_json(settings.paths.corrupted_clean_json, clean_rows() + [{"title": "Orphan row without an identifier"}])
    result = auto_repair.run_auto_repair(settings)
    assert result["status"] == "completed", result.get("error")
    assert result["repair_summary"] == {"dropped_row": 1}
    assert repaired_rows(settings, result) == clean_rows()


@pytest.mark.parametrize(("content", "status"), [("{broken", "repair_failed"), ("[]", "validation_failed")])
def test_input_with_nothing_to_repair_is_not_published(settings, monkeypatch, content, status):
    settings.paths.corrupted_clean_json.parent.mkdir(parents=True, exist_ok=True)
    settings.paths.corrupted_clean_json.write_text(content, encoding="utf-8")
    latest, before = previous_manifest(settings)
    monkeypatch.setattr(LocalEmbeddingIndex, "build", forbid_index)
    result = auto_repair.run_auto_repair(settings)
    assert result["status"] == status
    assert latest.read_bytes() == before


def test_data_that_is_simply_too_old_is_not_published(settings, monkeypatch):
    write_json(settings.paths.corrupted_clean_json, clean_rows())
    # Nothing is wrong with the records; they have aged past the freshness SLA.
    monkeypatch.setattr(auto_repair, "now_utc", lambda: datetime(2027, 9, 26, tzinfo=UTC))
    monkeypatch.setattr(LocalEmbeddingIndex, "build", forbid_index)
    latest, before = previous_manifest(settings)
    result = auto_repair.run_auto_repair(settings)
    assert result["status"] == "validation_failed"
    assert result["repairs"] == []
    assert result["remaining_failures"] == ["freshness_sla"]
    assert (settings.paths.project_dir / result["run_directory"] / "papers_clean_repaired.json").is_file()
    assert latest.read_bytes() == before


def test_repair_reads_nothing_but_the_corrupted_table(settings, monkeypatch):
    corrupt_input(settings)
    forbidden = {settings.paths.raw_api_response, settings.paths.raw_records_json,
                 settings.paths.clean_json, settings.paths.corruption_log}
    for path in forbidden - {settings.paths.corruption_log}:
        write_json(path, {"untouched": path.name})
    original_open = Path.open

    def guarded_open(path, *args, **kwargs):
        if path in forbidden:
            pytest.fail(f"Auto-repair read {path.name}")
        return original_open(path, *args, **kwargs)

    monkeypatch.setattr(Path, "open", guarded_open)
    result = auto_repair.run_auto_repair(settings)
    assert result["status"] == "partial", result.get("error")


def test_repaired_date_answers_the_frozen_benchmark(settings):
    affected = corrupt_input(settings)
    paper = next(row for row in clean_rows() if row["paper_id"] == affected["stale_date"][0])
    write_json(settings.paths.eval_testset, [{
        "id": "q01", "question_type": "date",
        "question": f"When was the paper '{paper['title']}' published?",
        "ground_truth": paper["published"], "ground_truth_doc_ids": [paper["paper_id"]],
    }])
    original = settings.paths.eval_testset.read_bytes()
    result = auto_repair.run_auto_repair(settings)
    assert result["status"] == "partial", result.get("error")
    assert result["evaluation"]["metrics"]["samples"] == 1
    assert result["evaluation"]["metrics"]["mean_token_f1"] == 1.0
    assert settings.paths.eval_testset.read_bytes() == original
    assert (settings.paths.project_dir / result["run_directory"] / "test_set.json").read_bytes() == original


@pytest.mark.parametrize("failure_stage", ["index", "evaluation", "publish"])
def test_downstream_failure_keeps_previous_manifest(settings, monkeypatch, failure_stage):
    corrupt_input(settings)
    latest, before = previous_manifest(settings)

    def fail(*args, **kwargs):
        raise RuntimeError("Simulated downstream failure")

    if failure_stage == "index":
        monkeypatch.setattr(LocalEmbeddingIndex, "build", fail)
    elif failure_stage == "evaluation":
        write_json(settings.paths.eval_testset, [])
        monkeypatch.setattr(auto_repair, "evaluate_pipeline", fail)
    else:
        monkeypatch.setattr(Path, "replace", fail)
    result = auto_repair.run_auto_repair(settings)
    assert result["status"] == f"{failure_stage}_failed"
    assert latest.read_bytes() == before


def test_cli_entry_exit_codes(settings):
    corrupt_input(settings)
    auto_repair.main()  # A partial repair is published and exits normally.
    settings.paths.corrupted_clean_json.write_text("{broken", encoding="utf-8")
    with pytest.raises(SystemExit) as error:
        auto_repair.main()
    assert error.value.code == 1


@pytest.mark.parametrize("network_fails", [False, True])
def test_live_only_fetcher_ignores_existing_snapshot_even_when_refresh_is_disabled(settings, monkeypatch, network_fails):
    write_json(settings.paths.raw_api_response, source_payload())
    before = settings.paths.raw_api_response.read_bytes()
    monkeypatch.setattr("ingestion.crossref.read_json", lambda *a, **k: pytest.fail("Strict live mode cannot read a snapshot"))
    monkeypatch.setattr("ingestion.crossref.time.sleep", lambda *a: None)

    def fetch(*args, **kwargs):
        if network_fails:
            raise requests.Timeout("offline")
        return Response(source_payload())

    monkeypatch.setattr("requests.get", fetch)
    attempts = []
    if network_fails:
        with pytest.raises(RuntimeError, match="fallback is disabled"):
            fetch_source_records(settings, live_only=True, attempt_log=attempts)
        assert settings.paths.raw_api_response.read_bytes() == before
        assert len(attempts) == 4
    else:
        assert len(fetch_source_records(settings, live_only=True, attempt_log=attempts)) == 24
        assert len(attempts) == 1


def test_default_fetcher_keeps_original_snapshot_fallback(settings, monkeypatch):
    write_json(settings.paths.raw_api_response, source_payload())
    before = settings.paths.raw_api_response.read_bytes()
    monkeypatch.setattr("ingestion.crossref.time.sleep", lambda *a: None)

    def offline(*args, **kwargs):
        raise requests.Timeout("offline")

    monkeypatch.setattr("requests.get", offline)
    attempts = []
    records = fetch_source_records(replace(settings, refresh_source=True), attempt_log=attempts)
    assert len(records) == 24
    assert len(attempts) == 4
    assert settings.paths.raw_api_response.read_bytes() == before
