from __future__ import annotations

from math import ceil
from typing import Any

import great_expectations as gx
import great_expectations.expectations as gxe
import pandas as pd

from core.config import Settings
from core.utils import now_utc, write_json

MAX_STALE_RATIO = 0.25
NOISE_REGEX = r"[@#$%&*~^]{4,}"
TITLE_MIN_LEN = 8
SUMMARY_MIN_LEN = 50


def _json_safe(value: Any) -> Any:
    """GX tra ve numpy scalar/list; ep ve kieu JSON thuan de write_json khong loi."""
    if hasattr(value, "item"):
        return value.item()
    if isinstance(value, float):
        return round(value, 4)
    if isinstance(value, (list, tuple)):
        return [_json_safe(item) for item in value]
    if isinstance(value, dict):
        return {str(key): _json_safe(item) for key, item in value.items()}
    return value


def _freshness_summary(df: pd.DataFrame, settings: Settings) -> dict[str, Any]:
    total_rows = int(len(df))
    stale_rows = int((df["age_days"] > settings.freshness_threshold_days).sum()) if total_rows else 0
    stale_ratio = round(stale_rows / total_rows, 4) if total_rows else 0.0
    return {
        "stale_rows": stale_rows,
        "total_rows": total_rows,
        "stale_ratio": stale_ratio,
        "is_fresh": stale_ratio <= MAX_STALE_RATIO,
    }


def _check_specs(settings: Settings) -> list[tuple[str, str, str | None, str, str, Any]]:
    """(id, expectation, column, dimension, threshold, gx expectation) theo dung thu tu C4-§2."""
    min_rows = ceil(0.95 * settings.max_results)
    max_rows = settings.max_results
    return [
        ("row_count", "ExpectTableRowCountToBeBetween", None, "Volume", f"{min_rows}..{max_rows}",
         gxe.ExpectTableRowCountToBeBetween(min_value=min_rows, max_value=max_rows)),
        ("paper_id_not_null", "ExpectColumnValuesToNotBeNull", "paper_id", "Completeness", "no nulls",
         gxe.ExpectColumnValuesToNotBeNull(column="paper_id")),
        ("title_not_null", "ExpectColumnValuesToNotBeNull", "title", "Completeness", "no nulls",
         gxe.ExpectColumnValuesToNotBeNull(column="title")),
        ("summary_not_null", "ExpectColumnValuesToNotBeNull", "summary", "Completeness", "no nulls",
         gxe.ExpectColumnValuesToNotBeNull(column="summary")),
        ("paper_id_unique", "ExpectColumnValuesToBeUnique", "paper_id", "Uniqueness", "unique",
         gxe.ExpectColumnValuesToBeUnique(column="paper_id")),
        ("title_length", "ExpectColumnValueLengthsToBeBetween", "title", "Validity", f"len>={TITLE_MIN_LEN}",
         gxe.ExpectColumnValueLengthsToBeBetween(column="title", min_value=TITLE_MIN_LEN)),
        ("summary_length", "ExpectColumnValueLengthsToBeBetween", "summary", "Completeness/Validity",
         f"len>={SUMMARY_MIN_LEN}",
         gxe.ExpectColumnValueLengthsToBeBetween(column="summary", min_value=SUMMARY_MIN_LEN)),
        ("summary_no_noise", "ExpectColumnValuesToNotMatchRegex", "summary", "Validity", NOISE_REGEX,
         gxe.ExpectColumnValuesToNotMatchRegex(column="summary", regex=NOISE_REGEX)),
    ]


def run_data_quality_checks(df: pd.DataFrame, settings: Settings, report_name: str) -> dict[str, Any]:
    """Quality gate GX 1.x (8 expectation) + Freshness SLA, theo contract C4."""
    context = gx.get_context(mode="ephemeral")
    data_source = context.data_sources.add_pandas(name="papers_source")
    data_asset = data_source.add_dataframe_asset(name="papers_asset")
    batch_def = data_asset.add_batch_definition_whole_dataframe("papers_batch")

    specs = _check_specs(settings)
    suite = context.suites.add(gx.ExpectationSuite(name=f"papers_suite_{report_name}"))
    for check_id, *_, expectation in specs:
        expectation.meta = {"check_id": check_id}
        suite.add_expectation(expectation)

    validation = context.validation_definitions.add(
        gx.ValidationDefinition(name=f"papers_validation_{report_name}", data=batch_def, suite=suite)
    )
    result = validation.run(batch_parameters={"dataframe": df})
    results_by_id = {item.expectation_config.meta["check_id"]: item for item in result.results}

    checks: list[dict[str, Any]] = []
    for check_id, expectation_name, column, dimension, threshold, _ in specs:
        item = results_by_id[check_id]
        detail = item.result or {}
        observed = detail.get("observed_value", detail.get("unexpected_percent", 0.0))
        checks.append(
            {
                "id": check_id,
                "expectation": expectation_name,
                "column": column,
                "dimension": dimension,
                "success": bool(item.success),
                "observed_value": _json_safe(observed),
                "unexpected_count": int(detail.get("unexpected_count") or 0),
                "threshold": threshold,
            }
        )

    freshness = _freshness_summary(df, settings)
    checks.append(
        {
            "id": "freshness_sla",
            "expectation": f"custom:stale_ratio<={MAX_STALE_RATIO}",
            "column": None,
            "dimension": "Timeliness",
            "success": freshness["is_fresh"],
            "observed_value": freshness["stale_ratio"],
            "unexpected_count": freshness["stale_rows"],
            "threshold": f"age_days>{settings.freshness_threshold_days} ratio<={MAX_STALE_RATIO}",
        }
    )

    gx_success = bool(result.success)
    passed = sum(1 for check in checks if check["success"])
    report = {
        "report_name": report_name,
        "success": gx_success and freshness["is_fresh"],
        "gx_success": gx_success,
        "row_count": int(len(df)),
        "passed_checks": passed,
        "failed_checks": len(checks) - passed,
        "total_checks": len(checks),
        "checks": checks,
        "freshness": freshness,
        "generated_at": now_utc().isoformat(timespec="seconds"),
    }

    write_json(settings.paths.quality_dir / f"{report_name}_quality_report.json", report)
    write_json(settings.paths.gx_dir / f"papers_suite_{report_name}.json", _json_safe(suite.to_json_dict()))
    failed = [check["id"] for check in checks if not check["success"]]
    print(f"[quality] {report_name}: success={report['success']} passed={passed}/{len(checks)} failed={failed}")
    return report


def build_freshness_report(df: pd.DataFrame, settings: Settings, report_path) -> dict[str, Any]:
    """Freshness SLA: stale khi age_days > threshold; is_fresh khi stale_ratio <= 25% (C4-§4)."""
    summary = _freshness_summary(df, settings)
    published = df["published"].astype(str) if len(df) else pd.Series(dtype=str)
    payload = {
        "latest_published": published.max() if len(published) else None,
        "oldest_published": published.min() if len(published) else None,
        "stale_rows": summary["stale_rows"],
        "total_rows": summary["total_rows"],
        "stale_ratio": summary["stale_ratio"],
        "threshold_days": settings.freshness_threshold_days,
        "max_stale_ratio": MAX_STALE_RATIO,
        "is_fresh": summary["is_fresh"],
        "generated_at": now_utc().isoformat(timespec="seconds"),
    }
    write_json(report_path, payload)
    return payload
