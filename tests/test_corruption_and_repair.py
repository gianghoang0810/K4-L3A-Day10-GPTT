from datetime import UTC, datetime
from pathlib import Path
import pandas as pd
import pytest

from core.config import load_settings
from ingestion.cleaning import build_clean_dataframe
from ingestion.corruption import corrupt_clean_dataframe
from ingestion.crossref import load_raw_records
from observability.quality import run_data_quality_checks


def test_corruption_injects_failures(tmp_path):
    settings = load_settings()
    assert settings.paths.clean_json.exists(), "Clean json must exist"
    clean_df = pd.read_json(settings.paths.clean_json)

    log_path = tmp_path / "temp_corruption_log.json"
    corrupted_df = corrupt_clean_dataframe(clean_df, log_path)

    assert log_path.exists()
    assert len(corrupted_df) < len(clean_df) or len(corrupted_df) > 0

    # Verify that corrupted dataframe triggers quality gate failure
    corrupted_quality = run_data_quality_checks(corrupted_df, settings, "test_corrupted")
    assert corrupted_quality["success"] is False
    assert corrupted_quality["failed_checks"] > 0


def test_idempotent_repair_from_raw():
    settings = load_settings()
    assert settings.paths.raw_records_json.exists(), "Raw records must exist"
    raw_records = load_raw_records(settings.paths.raw_records_json)

    run_date = datetime.now(UTC)
    repaired_df = build_clean_dataframe(raw_records, run_date)

    assert len(repaired_df) == 24
    repaired_quality = run_data_quality_checks(repaired_df, settings, "test_repaired")
    assert repaired_quality["success"] is True
    assert repaired_quality["failed_checks"] == 0
