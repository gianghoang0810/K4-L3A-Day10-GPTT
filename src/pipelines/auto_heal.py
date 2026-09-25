from __future__ import annotations

from datetime import UTC, datetime
import json
from pathlib import Path
import sys

import pandas as pd

from core.config import load_settings
from core.utils import read_json, write_csv
from evaluation.metrics import evaluate_pipeline
from ingestion.cleaning import build_clean_dataframe
from ingestion.crossref import load_raw_records
from observability.quality import build_freshness_report, run_data_quality_checks
from retrieval.index import LocalEmbeddingIndex

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass


def auto_heal_pipeline(candidate_df: pd.DataFrame, settings=None) -> dict:
    """Tu dong kiem dinh, phat hien bat thuong va tu dong rollback/repair tu Raw records (Bonus B2)."""
    if settings is None:
        settings = load_settings()

    print("\n" + "=" * 65)
    print("[AUTO-HEAL] KHOI CHAY HE THONG TU DONG PHAT HIEN LOI & PHUC HOI")
    print("=" * 65)

    audit_log = {
        "timestamp": datetime.now(UTC).isoformat(),
        "input_rows": len(candidate_df),
        "anomalies_detected": [],
        "action_taken": "NONE",
        "recovery_status": "SKIPPED",
    }

    # 1. Kiem dinh Quality Gate & Freshness SLA
    print("[1/3] Kiem dinh Quality Gate (GX 1.x) va Freshness SLA...")
    quality = run_data_quality_checks(candidate_df, settings, "candidate")
    freshness = build_freshness_report(candidate_df, settings)

    is_healthy = quality.get("success", False) and freshness.get("is_fresh", False)

    if not quality.get("success", False):
        failed_count = quality.get("failed_checks", 0)
        audit_log["anomalies_detected"].append(f"Quality Gate FAIL: {failed_count} expectations violated")
        print(f"  [!] Canh bao: Phat hien {failed_count} vi pham trong Quality Gate!")

    if not freshness.get("is_fresh", False):
        stale_ratio = freshness.get("stale_ratio", 0.0)
        audit_log["anomalies_detected"].append(f"Freshness SLA FAIL: Stale ratio {stale_ratio*100:.1f}% > 25%")
        print(f"  [!] Canh bao: Dữ liệu quá hạn Freshness SLA ({stale_ratio*100:.1f}%)!")

    # 2. Xu ly tu dong: Neu khoe manh thi giu nguyen, neu loi thi tu dong sua chua
    if is_healthy:
        print("  [OK] Du lieu hoan toan khoe manh. Khong can can thiep!")
        audit_log["action_taken"] = "NO_ACTION_REQUIRED"
        audit_log["recovery_status"] = "HEALTHY"
        return audit_log

    print("\n[2/3] KICH HOAT CO CHE TU DONG ROLLBACK & IDEMPOTENT REPAIR...")
    audit_log["action_taken"] = "AUTOMATIC_ROLLBACK_AND_REPAIR"

    raw_path = settings.paths.raw_records_json
    if not raw_path.exists():
        raise FileNotFoundError(f"Khong tim thay raw snapshot tai: {raw_path}")

    raw_records = load_raw_records(raw_path)
    run_date = datetime.now(UTC)
    repaired_df = build_clean_dataframe(raw_records, run_date)

    # Luu dataframe da duoc tu dong sua
    write_csv(repaired_df, settings.paths.clean_csv)
    repaired_df.to_json(settings.paths.clean_json, orient="records", indent=2)

    # 3. Kiem dinh lai sau khi sua chua
    print("\n[3/3] Tai kiem dinh sau sua chua & Tai tao Vector Store...")
    repaired_quality = run_data_quality_checks(repaired_df, settings, "auto_healed")
    repaired_freshness = build_freshness_report(repaired_df, settings)

    if repaired_quality.get("success") and repaired_freshness.get("is_fresh"):
        print("  [SUCCESS] Du lieu da duoc phuc hoi ve trang thai sach tuyet doi (100% checks PASS)!")
        audit_log["recovery_status"] = "SUCCESS"
        audit_log["repaired_rows"] = len(repaired_df)

        # Re-index collection
        index = LocalEmbeddingIndex.build(repaired_df, settings, settings.paths.embeddings_json)
        print(f"  [SUCCESS] Vector Collection '{settings.baseline_collection_name}' da duoc tai tao an toan.")
    else:
        print("  [ERROR] Phuc hoi that bai. Can su can thiep cua ky su du lieu.")
        audit_log["recovery_status"] = "FAILED"

    # Ghi nhat ky audit vao data/results/
    log_path = settings.paths.baseline_metrics.parent / "auto_heal_log.json"
    with open(log_path, "w", encoding="utf-8") as f:
        json.dump(audit_log, f, indent=2)
    print(f"\n[OK] Da ghi nhat ky tu dong khac phuc su co: {log_path}")
    print("=" * 65 + "\n")
    return audit_log


def main() -> None:
    settings = load_settings()
    # Kiem tra thu voi tap du lieu bi loi
    corrupted_json = settings.paths.corrupted_clean_json
    if corrupted_json.exists():
        print(f"[*] Thu nghiem Auto-Heal voi dataset loi: {corrupted_json}")
        candidate_df = pd.read_json(corrupted_json)
    elif settings.paths.clean_json.exists():
        candidate_df = pd.read_json(settings.paths.clean_json)
    else:
        raise FileNotFoundError("Chua co dataset de kiem thu Auto-Heal.")

    auto_heal_pipeline(candidate_df, settings)


if __name__ == "__main__":
    main()
