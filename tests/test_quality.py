from datetime import UTC, datetime
import pandas as pd
import pytest

from core.config import load_settings
from ingestion.cleaning import build_clean_dataframe
from observability.quality import build_freshness_report, run_data_quality_checks


@pytest.fixture
def clean_sample_df():
    settings = load_settings()
    if settings.paths.clean_json.exists():
        return pd.read_json(settings.paths.clean_json)
    # Fallback synthetic clean dataframe
    return pd.DataFrame([
        {
            "paper_id": f"10.1234/test.{i}",
            "title": f"Valid Paper Title Number {i}",
            "summary": "This is a comprehensive summary that satisfies all length requirements.",
            "authors": ["Author A"],
            "categories": ["AI"],
            "published": "2026-06-01",
            "age_days": 100,
            "text_for_embedding": f"Title: Valid Paper {i}\nSummary: Valid summary longer than 30 chars.",
        }
        for i in range(10)
    ])


def test_quality_gate_passes_on_clean_data(clean_sample_df):
    settings = load_settings()
    report = run_data_quality_checks(clean_sample_df, settings, "test_clean")
    assert report["success"] is True
    assert report["failed_checks"] == 0
    assert report["passed_checks"] == 6


def test_freshness_report_calculation(clean_sample_df):
    settings = load_settings()
    report = build_freshness_report(clean_sample_df, settings)
    assert "is_fresh" in report
    assert "stale_ratio" in report
    assert report["threshold_days"] == 180
    assert report["max_stale_ratio_allowed"] == 0.25
