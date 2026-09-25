from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any
import uuid

import great_expectations as gx
from great_expectations.expectations import (
    ExpectColumnValueLengthsToBeBetween,
    ExpectColumnValuesToBeUnique,
    ExpectColumnValuesToNotBeNull,
    ExpectTableRowCountToBeBetween,
)
import pandas as pd

from core.config import Settings
from core.utils import write_json


def run_data_quality_checks(df: pd.DataFrame, settings: Settings, report_name: str) -> dict[str, Any]:
    """Chot kiem dich chat luong su dung Great Expectations 1.x ephemeral mode."""
    # Xac dinh duong dan luu report
    if report_name == "baseline":
        report_path = settings.paths.baseline_quality_report
    elif report_name == "corrupted":
        report_path = settings.paths.corrupted_quality_report
    else:
        report_path = settings.paths.quality_dir / f"{report_name}_quality_report.json"

    # Khoi tao ephemeral context (GX 1.x chuan)
    context = gx.get_context(mode="ephemeral")
    unique_suffix = f"{report_name}_{uuid.uuid4().hex[:6]}"
    data_source = context.data_sources.add_pandas(name=f"papers_source_{unique_suffix}")
    data_asset = data_source.add_dataframe_asset(name=f"papers_asset_{unique_suffix}")
    batch_def = data_asset.add_batch_definition_whole_dataframe(f"papers_batch_{unique_suffix}")
    batch = batch_def.get_batch(batch_parameters={"dataframe": df})

    # Dinh nghia ExpectationSuite gom 4 nhom expectations bat buoc
    suite = gx.ExpectationSuite(name=f"papers_suite_{unique_suffix}")
    expectations = [
        ExpectTableRowCountToBeBetween(min_value=5, max_value=5000),
        ExpectColumnValuesToNotBeNull(column="paper_id"),
        ExpectColumnValuesToNotBeNull(column="title"),
        ExpectColumnValuesToNotBeNull(column="text_for_embedding"),
        ExpectColumnValuesToBeUnique(column="paper_id"),
        ExpectColumnValueLengthsToBeBetween(column="summary", min_value=30),
    ]

    for exp in expectations:
        suite.add_expectation(exp)

    validation_result = batch.validate(suite)
    overall_success = bool(validation_result.success)

    check_results = []
    for item in validation_result.results:
        check_results.append(
            {
                "expectation_type": item.expectation_config.type if hasattr(item, "expectation_config") else "expectation",
                "success": bool(item.success),
                "result": item.result if hasattr(item, "result") else {},
            }
        )

    # Tinh toan Freshness SLA
    freshness = build_freshness_report(df, settings)

    report_payload: dict[str, Any] = {
        "report_name": report_name,
        "success": overall_success,
        "total_checks": len(check_results),
        "passed_checks": sum(1 for c in check_results if c["success"]),
        "failed_checks": sum(1 for c in check_results if not c["success"]),
        "results": check_results,
        "freshness": freshness,
        "timestamp": datetime.now(UTC).isoformat(),
    }

    write_json(report_path, report_payload)
    return report_payload


def build_freshness_report(df: pd.DataFrame, settings: Settings, report_path: Path | None = None) -> dict[str, Any]:
    """Giam sat Freshness SLA: Canh bao is_fresh = False neu ty le bai bao cu (>180 ngay) vuot 25%."""
    target_path = report_path or settings.paths.freshness_report

    if df.empty or "published" not in df.columns:
        payload = {
            "latest_published": "N/A",
            "oldest_published": "N/A",
            "stale_rows": 0,
            "total_rows": 0,
            "stale_ratio": 0.0,
            "threshold_days": settings.freshness_threshold_days,
            "max_stale_ratio_allowed": 0.25,
            "is_fresh": False,
        }
        write_json(target_path, payload)
        return payload

    latest_published = str(df["published"].max())
    oldest_published = str(df["published"].min())
    threshold_days = settings.freshness_threshold_days

    stale_rows = 0
    if "age_days" in df.columns:
        stale_rows = int((df["age_days"] > threshold_days).sum())

    total_rows = int(len(df))
    stale_ratio = float(stale_rows / total_rows) if total_rows > 0 else 0.0
    is_fresh = bool(stale_ratio <= 0.25)

    payload = {
        "latest_published": latest_published,
        "oldest_published": oldest_published,
        "stale_rows": stale_rows,
        "total_rows": total_rows,
        "stale_ratio": round(stale_ratio, 4),
        "threshold_days": threshold_days,
        "max_stale_ratio_allowed": 0.25,
        "is_fresh": is_fresh,
    }

    write_json(target_path, payload)
    return payload
