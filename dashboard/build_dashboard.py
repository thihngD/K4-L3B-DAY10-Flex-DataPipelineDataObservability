"""Build the B1 observability dashboard from pipeline artifacts.

Reads the baseline, corrupted, repaired and latest auto-repair (B2) artifacts,
computes drift alerts against the baseline and writes one self-contained
`dashboard/index.html` that opens offline in any browser.

    python dashboard/build_dashboard.py
"""
from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
from statistics import median
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
OUTPUT = Path(__file__).resolve().parent / "index.html"
TEMPLATE = Path(__file__).resolve().parent / "template.html"

VOLUME_WARNING = 0.05
VOLUME_CRITICAL = 0.20
AGE_SHIFT_DAYS = 30
METRIC_DROP = 0.05


def _load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8")) if path.is_file() else None


def _relative(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def _state(key: str, label: str, clean: Path, quality: Path, freshness: Path, metrics: Path) -> dict[str, Any] | None:
    rows, quality_report, freshness_report = _load(clean), _load(quality), _load(freshness)
    if rows is None or quality_report is None or freshness_report is None:
        return None
    metric_values = _load(metrics)
    return {
        "key": key,
        "label": label,
        "rows": len(rows),
        "ages": [row["age_days"] for row in rows],
        "quality": {
            "success": quality_report["success"],
            "passed": quality_report["passed_checks"],
            "total": quality_report["total_checks"],
            "checks": [
                {key: check[key] for key in ("id", "dimension", "success", "observed_value", "threshold", "unexpected_count")}
                for check in quality_report["checks"]
            ],
        },
        "freshness": {key: freshness_report[key] for key in (
            "stale_rows", "total_rows", "stale_ratio", "is_fresh", "threshold_days", "max_stale_ratio",
            "latest_published", "oldest_published",
        )},
        "metrics": None if metric_values is None else {key: metric_values[key] for key in (
            "retrieval_hit_rate", "mean_token_f1", "judge_accuracy", "mean_judge_score",
        )},
        "sources": [_relative(path) for path in (clean, quality, freshness, metrics) if path.is_file()],
    }


def _auto_repair_state() -> dict[str, Any] | None:
    latest = _load(DATA / "auto_repair" / "latest.json")
    if latest is None:
        return None
    run_dir = ROOT / latest["run_directory"]
    state = _state(
        "auto_repair", "Auto-repair (B2)",
        run_dir / "papers_clean_repaired.json",
        run_dir / "quality" / "repaired_quality_report.json",
        run_dir / "quality" / "repaired_freshness_report.json",
        run_dir / "repaired_metrics.json",
    )
    log = _load(run_dir / "repair_log.json")
    if state is None or log is None:
        return None
    state["repair"] = {
        "run_id": log["run_id"],
        "status": log["status"],
        "finished_at": log.get("finished_at"),
        "input_rows": log.get("input_rows"),
        "output_rows": log.get("output_rows"),
        "remaining_failures": log.get("remaining_failures") or [],
        "summary": log.get("repair_summary", {}),
        "fields": log.get("repaired_fields", {}),
        "unrecoverable": [
            {"paper_id": item["paper_id"], "field": item["field"], "value": item.get("value"), "reason": item["reason"]}
            for item in log.get("repairs", []) if item["action"] == "unrecoverable_field"
        ],
        "log": _relative(run_dir / "repair_log.json"),
    }
    return state


def _alerts(state: dict[str, Any], baseline: dict[str, Any]) -> list[dict[str, str]]:
    """Compare one state with the baseline and describe every signal that drifted."""
    alerts = []
    for check in state["quality"]["checks"]:
        if not check["success"]:
            observed = (f"{check['unexpected_count']} rows" if check["unexpected_count"]
                        else f"observed {check['observed_value']}")
            alerts.append({
                "level": "critical",
                "title": f"Quality check failed: {check['id']}",
                "detail": f"{check['dimension']} · {observed} · threshold {check['threshold']}",
            })
    rows, base_rows = state["rows"], baseline["rows"]
    change = (rows - base_rows) / base_rows if base_rows else 0.0
    if abs(change) >= VOLUME_WARNING:
        alerts.append({
            "level": "critical" if abs(change) >= VOLUME_CRITICAL else "warning",
            "title": f"Volume drift {change:+.1%}",
            "detail": f"{rows} rows vs {base_rows} in the baseline",
        })
    shift = median(state["ages"]) - median(baseline["ages"]) if state["ages"] and baseline["ages"] else 0
    if abs(shift) >= AGE_SHIFT_DAYS:
        alerts.append({
            "level": "warning",
            "title": f"Age distribution drift: median {shift:+.0f} days",
            "detail": f"median age {median(state['ages']):.0f} days vs {median(baseline['ages']):.0f} in the baseline",
        })
    if state["metrics"] and baseline["metrics"]:
        for key, name in (("retrieval_hit_rate", "Retrieval hit rate"), ("mean_token_f1", "Mean token F1")):
            drop = baseline["metrics"][key] - state["metrics"][key]
            if drop >= METRIC_DROP:
                alerts.append({
                    "level": "warning",
                    "title": f"{name} dropped {drop:.2f}",
                    "detail": f"{state['metrics'][key]:.4f} vs {baseline['metrics'][key]:.4f} in the baseline",
                })
    if not alerts:
        alerts.append({"level": "good", "title": "No drift vs baseline", "detail": "All checks pass and signals match the baseline"})
    return alerts


def build() -> Path:
    states = [
        _state("baseline", "Baseline", DATA / "clean/papers_clean.json", DATA / "quality/baseline_quality_report.json",
               DATA / "quality/freshness_report.json", DATA / "results/baseline_metrics.json"),
        _state("corrupted", "Corrupted", DATA / "clean/papers_clean_corrupted.json",
               DATA / "quality/corrupted_quality_report.json", DATA / "quality/corrupted_freshness_report.json",
               DATA / "results/corrupted_metrics.json"),
        _state("repaired", "Repaired (raw)", DATA / "clean/papers_clean_repaired.json",
               DATA / "quality/repaired_quality_report.json", DATA / "quality/repaired_freshness_report.json",
               DATA / "results/repaired_metrics.json"),
        _auto_repair_state(),
    ]
    states = [state for state in states if state is not None]
    if not states or states[0]["key"] != "baseline":
        raise SystemExit("Run script/run_phase1.py first: baseline artifacts are missing")
    for state in states:
        state["alerts"] = _alerts(state, states[0])
    log = _load(DATA / "results/corruption_log.json")
    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "states": states,
        "scenarios": [] if log is None else [
            {key: scenario[key] for key in ("name", "description", "affected_rows")} for scenario in log["scenarios"]
        ],
    }
    # Escape "</" so the embedded JSON cannot close its <script> element.
    data = json.dumps(payload, ensure_ascii=False).replace("</", "<\\/")
    OUTPUT.write_text(TEMPLATE.read_text(encoding="utf-8").replace("__DASHBOARD_DATA__", data), encoding="utf-8")
    print(f"[dashboard] states={[state['key'] for state in states]} output={_relative(OUTPUT)}")
    return OUTPUT


if __name__ == "__main__":
    build()
