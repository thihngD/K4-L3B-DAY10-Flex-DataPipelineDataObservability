from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from core.config import load_settings
from core.utils import write_text

METRIC_KEYS = ["retrieval_hit_rate", "mean_token_f1", "judge_accuracy", "mean_judge_score"]
NA = "N/A"


def _fmt(value: Any) -> str:
    if value is None:
        return NA
    if isinstance(value, bool):
        return "✅ True" if value else "❌ False"
    if isinstance(value, float):
        return f"{value:.4f}"
    if isinstance(value, (dict, list)):
        return f"`{json.dumps(value, ensure_ascii=False)}`"
    return str(value)


def _metric(value: Any) -> Any:
    """statistics.mean tra int khi moi diem bang nhau (vd 5); ep float de hien thi thong nhat 4 chu so."""
    if isinstance(value, int) and not isinstance(value, bool):
        return float(value)
    return value


def _num(value: Any) -> float | None:
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    return None


def _table(headers: list[str], rows: list[list[Any]]) -> list[str]:
    lines = ["| " + " | ".join(headers) + " |", "|" + "|".join("---" for _ in headers) + "|"]
    lines += ["| " + " | ".join(_fmt(cell) if not isinstance(cell, str) else cell for cell in row) + " |" for row in rows]
    return lines


def _artifact_lines() -> list[str]:
    """Liet ke artifact theo duong dan tuong doi (khong lo duong dan tuyet doi may local)."""
    paths = load_settings().paths
    root = paths.project_dir
    artifacts = [
        paths.raw_api_response, paths.raw_records_json, paths.clean_csv, paths.clean_json,
        paths.embeddings_json, paths.eval_testset, paths.baseline_metrics, paths.baseline_answers,
        paths.baseline_quality_report, paths.freshness_report, paths.baseline_report,
    ]
    lines = []
    for path in artifacts:
        mark = "✅" if path.exists() or path == paths.baseline_report else "❌ missing"
        lines.append(f"- `{path.relative_to(root).as_posix()}` {mark}")
    chroma = paths.chroma_dir
    lines.append(f"- `{chroma.relative_to(root).as_posix()}/` {'✅' if chroma.exists() else '❌ missing'}")
    return lines


def _check_rows(quality: dict[str, Any]) -> list[list[Any]]:
    return [
        [f"`{check['id']}`", check["dimension"], f"`{check['threshold']}`", check["observed_value"], check["success"]]
        for check in quality.get("checks", [])
    ]


def generate_phase1_report(
    report_path,
    source_summary: dict[str, Any],
    metrics: dict[str, Any],
    quality: dict[str, Any],
    freshness: dict[str, Any],
) -> None:
    """Markdown report cho baseline phase, heading co dinh theo C6-§3."""
    lines = ["# Phase 1 Baseline Report", ""]

    lines += ["## 1. Source", ""]
    lines += _table(["Key", "Value"], [[f"`{key}`", value] for key, value in source_summary.items()])

    lines += ["", "## 2. Retrieval & Answer Metrics", ""]
    metric_rows = [["`samples`", metrics.get("samples")]]
    metric_rows += [[f"`{key}`", _metric(metrics.get(key))] for key in METRIC_KEYS]
    metric_rows.append(["`ragas`", metrics.get("ragas")])
    lines += _table(["Metric", "Value"], metric_rows)

    lines += ["", "## 3. Data Quality (GX 1.x)", ""]
    lines.append(
        f"Suite `papers_suite_{quality.get('report_name', NA)}` — success = {_fmt(quality.get('success'))}, "
        f"GX success = {_fmt(quality.get('gx_success'))}, "
        f"passed {quality.get('passed_checks', NA)}/{quality.get('total_checks', NA)}, "
        f"row count = {quality.get('row_count', NA)}."
    )
    lines.append("")
    lines += _table(["ID", "Dimension", "Threshold", "Observed", "Pass"], _check_rows(quality))

    lines += ["", "## 4. Freshness SLA", ""]
    lines += _table(["Key", "Value"], [[f"`{key}`", value] for key, value in freshness.items()])

    lines += ["", "## 5. Artifacts", ""]
    lines += _artifact_lines()

    write_text(Path(report_path), "\n".join(lines) + "\n")


def _delta_row(label: str, base: Any, corr: Any, rep: Any, display=None) -> list[Any]:
    """Δ Corruption = C - B; Δ Repair = R - C; Recovery % = ΔRepair / (B - C) * 100."""
    b, c, r = _num(base), _num(corr), _num(rep)
    delta_corr = c - b if b is not None and c is not None else None
    delta_rep = r - c if r is not None and c is not None else None
    if delta_corr is not None and delta_rep is not None and b - c != 0:
        recovery = f"{delta_rep / (b - c) * 100:.1f}%"
    else:
        recovery = NA
    def is_int(value: Any) -> bool:
        return isinstance(value, int) and not isinstance(value, bool)

    if delta_corr is not None and is_int(base) and is_int(corr):
        delta_corr = int(delta_corr)
    if delta_rep is not None and is_int(corr) and is_int(rep):
        delta_rep = int(delta_rep)
    cells = display or [base, corr, rep]
    return [label, *cells, delta_corr, delta_rep, recovery]


def _passed(quality: dict[str, Any] | None) -> tuple[Any, str]:
    if not quality:
        return None, NA
    return quality.get("passed_checks"), f"{quality.get('passed_checks')}/{quality.get('total_checks')}"


def _failed_checks(quality: dict[str, Any] | None) -> list[dict[str, Any]]:
    return [check for check in (quality or {}).get("checks", []) if not check.get("success")]


def _findings(
    states: dict[str, dict[str, Any]],
    qualities: dict[str, dict[str, Any] | None],
    freshnesses: dict[str, dict[str, Any] | None],
) -> list[str]:
    """Moi cau deu sinh tu so lieu dau vao, khong co nhan dinh viet cung."""
    findings = []
    base, corr, rep = states["baseline"], states["corrupted"], states["repaired"]
    for key in METRIC_KEYS:
        b, c, r = _num(base.get(key)), _num(corr.get(key)), _num(rep.get(key))
        if b is None or c is None or r is None:
            findings.append(f"`{key}`: thiếu số liệu ở ít nhất một trạng thái — không kết luận.")
            continue
        if c == b:
            findings.append(f"`{key}` không đổi sau corruption ({b:.4f}) — corruption không tác động đo được lên metric này.")
            continue
        direction = "giảm" if c < b else "tăng"
        recovery = (r - c) / (b - c) * 100
        findings.append(
            f"`{key}` {direction} {abs(c - b):.4f} sau corruption ({b:.4f} → {c:.4f}); "
            f"sau repair đạt {r:.4f}, phục hồi {recovery:.1f}% phần chênh lệch."
        )

    for state in ("baseline", "corrupted", "repaired"):
        quality = qualities.get(state)
        if not quality:
            findings.append(f"Quality gate `{state}`: không có dữ liệu.")
            continue
        failed = [check["id"] for check in _failed_checks(quality)]
        findings.append(
            f"Quality gate `{state}`: pass {quality.get('passed_checks')}/{quality.get('total_checks')}"
            + (f", fail {', '.join(f'`{item}`' for item in failed)}." if failed else ", không có check fail.")
        )

    corrupted_checks = {check["id"]: check for check in (qualities.get("corrupted") or {}).get("checks", [])}
    not_null = corrupted_checks.get("summary_not_null")
    length = corrupted_checks.get("summary_length")
    if not_null and length and not_null["success"] and not length["success"]:
        findings.append(
            "Silent failure: `summary_not_null` vẫn pass trên dữ liệu corrupted (summary rỗng là `\"\"` chứ không phải null), "
            f"chỉ `summary_length` phát hiện được ({length['unexpected_count']} dòng vi phạm)."
        )

    for state in ("baseline", "corrupted", "repaired"):
        freshness = freshnesses.get(state)
        if freshness:
            findings.append(
                f"Freshness `{state}`: {freshness.get('stale_rows')}/{freshness.get('total_rows')} dòng stale "
                f"(ratio {_fmt(freshness.get('stale_ratio'))}, ngưỡng {freshness.get('max_stale_ratio')}) → "
                f"is_fresh = {freshness.get('is_fresh')}."
            )
    return findings


def generate_corruption_report(
    report_path,
    baseline_metrics: dict[str, Any],
    corrupted_metrics: dict[str, Any],
    repaired_metrics: dict[str, Any],
    corrupted_quality: dict[str, Any],
    repaired_quality: dict[str, Any],
    corrupted_freshness: dict[str, Any],
    repaired_freshness: dict[str, Any],
    baseline_quality: dict[str, Any] | None = None,
    baseline_freshness: dict[str, Any] | None = None,
    corruption_log: dict[str, Any] | None = None,
) -> None:
    """Markdown report so sanh baseline/corrupted/repaired, cau truc co dinh theo C6-§3."""
    states = {"baseline": baseline_metrics, "corrupted": corrupted_metrics, "repaired": repaired_metrics}
    qualities = {"baseline": baseline_quality, "corrupted": corrupted_quality, "repaired": repaired_quality}
    freshnesses = {"baseline": baseline_freshness, "corrupted": corrupted_freshness, "repaired": repaired_freshness}

    lines = ["# Corruption Impact Report", ""]
    lines += ["## 1. Three-State Comparison", ""]
    rows = [_delta_row(f"`{key}`", *(_metric(states[s].get(key)) for s in states)) for key in METRIC_KEYS]

    passed = [_passed(qualities[s]) for s in states]
    rows.append(_delta_row("Quality checks passed", *(p[0] for p in passed), display=[p[1] for p in passed]))
    success = [(qualities[s] or {}).get("success") for s in states]
    rows.append(["Quality success", *success, NA, NA, NA])
    fresh = [(freshnesses[s] or {}).get("is_fresh") for s in states]
    rows.append(["Freshness `is_fresh`", *fresh, NA, NA, NA])
    rows.append(_delta_row("`stale_ratio`", *((freshnesses[s] or {}).get("stale_ratio") for s in states)))
    rows.append(_delta_row("Row count", *((qualities[s] or {}).get("row_count") for s in states)))
    lines += _table(["Metric", "Baseline", "Corrupted", "Repaired", "Δ Corruption", "Δ Repair", "Recovery %"], rows)
    lines += [
        "",
        "Δ Corruption = Corrupted − Baseline · Δ Repair = Repaired − Corrupted · "
        "Recovery % = Δ Repair / (Baseline − Corrupted) × 100 (N/A khi mẫu số = 0 hoặc giá trị bool).",
    ]

    lines += ["", "## 2. Failed Quality Checks", ""]
    for state in states:
        if qualities[state] is None:
            lines.append(f"- **{state}**: N/A (không có quality report)")
            continue
        failed = _failed_checks(qualities[state])
        if not failed:
            lines.append(f"- **{state}**: không có check fail")
        else:
            detail = ", ".join(f"`{check['id']}` (observed {_fmt(check['observed_value'])})" for check in failed)
            lines.append(f"- **{state}**: {detail}")

    lines += ["", "## 3. Corruption Scenarios", ""]
    if corruption_log:
        lines.append(
            f"Seed `{corruption_log.get('seed')}` · input {corruption_log.get('input_rows')} dòng → "
            f"output {corruption_log.get('output_rows')} dòng."
        )
        lines.append("")
        lines += _table(
            ["Scenario", "Params", "Affected rows"],
            [[f"`{s['name']}`", s.get("params"), s.get("affected_rows")] for s in corruption_log.get("scenarios", [])],
        )
    else:
        lines.append("N/A (không có corruption log)")

    lines += ["", "## 4. Findings", ""]
    lines += [f"- {item}" for item in _findings(states, qualities, freshnesses)]

    write_text(Path(report_path), "\n".join(lines) + "\n")
