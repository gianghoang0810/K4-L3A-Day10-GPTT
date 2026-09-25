from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from core.config import load_settings
from core.utils import read_json, write_csv
from evaluation.metrics import evaluate_pipeline
from evaluation.testset import build_test_set
from ingestion.cleaning import build_clean_dataframe
from ingestion.crossref import fetch_source_records
from observability.quality import build_freshness_report, run_data_quality_checks
from observability.reporting import generate_phase1_report
from retrieval.index import LocalEmbeddingIndex
import sys

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass


def main() -> None:
    """Xay dung va dieu phoi Baseline Pipeline end-to-end (Phase 1)."""
    print("\n" + "=" * 60)
    print("[START] KHOI CHAY BASELINE PIPELINE (PHASE 1)")
    print("=" * 60)

    # 1. Load settings
    settings = load_settings()
    print(f"[*] Thu muc du an: {settings.paths.project_dir}")
    print(f"[*] LLM Provider: {settings.llm_provider} (Model: {settings.model_name})")

    # 2. Ingestion: Lay raw records (Dual-mode: API hoac fallback snapshot)
    print("\n[Step 1/5] Ingestion: Thu thap va bao toan du lieu raw...")
    records = fetch_source_records(settings)
    print(f"  -> Da nap thanh cong {len(records)} ban ghi tu nguon.")

    # 3. Cleaning: Chuan hoa, tinh age_days va text_for_embedding
    print("\n[Step 2/5] Cleaning: Tien xu ly va chuan hoa schema...")
    run_date = datetime.now(UTC)
    clean_df = build_clean_dataframe(records, run_date)
    write_csv(clean_df, settings.paths.clean_csv)
    clean_df.to_json(settings.paths.clean_json, orient="records", indent=2)
    print(f"  -> Da xuat du lieu sach: {settings.paths.clean_csv} ({len(clean_df)} dong)")

    # 4. Data Observability Gate: Kiem dinh chat luong bang Great Expectations 1.x
    print("\n[Step 3/5] Data Observability Gate: Kiem dinh Great Expectations 1.x & Freshness...")
    quality_report = run_data_quality_checks(clean_df, settings, "baseline")
    freshness_report = build_freshness_report(clean_df, settings)
    status_str = "PASSED (100%)" if quality_report.get("success") else "FAILED"
    fresh_str = "FRESH" if freshness_report.get("is_fresh") else "STALE"
    print(f"  -> Quality Gate: {status_str} (Passed {quality_report.get('passed_checks')}/{quality_report.get('total_checks')} checks)")
    print(f"  -> Freshness SLA: {fresh_str} (Stale ratio: {freshness_report.get('stale_ratio') * 100:.1f}%)")

    # 5. ChromaDB Vector Store Indexing
    print("\n[Step 4/5] Vector Store Indexing: Tao embedding MiniLM va nap ChromaDB...")
    index = LocalEmbeddingIndex.build(clean_df, settings, settings.paths.embeddings_json)
    print(f"  -> Da index {len(clean_df)} tai lieu vao collection '{settings.baseline_collection_name}'")

    # 6. Evaluation Benchmark
    print("\n[Step 5/5] Evaluation Benchmark: Sinh test set va danh gia Baseline...")
    if settings.refresh_test_set or not settings.paths.eval_testset.exists():
        test_set = build_test_set(clean_df, settings.paths.eval_testset)
        print(f"  -> Da sinh moi {len(test_set)} cau hoi test vao {settings.paths.eval_testset}")
    else:
        test_set = read_json(settings.paths.eval_testset)
        print(f"  -> Su dung bo test set co san gom {len(test_set)} cau hoi.")

    bundle = evaluate_pipeline(
        settings=settings,
        index=index,
        test_set_path=settings.paths.eval_testset,
        metrics_output_path=settings.paths.baseline_metrics,
        answers_output_path=settings.paths.baseline_answers,
    )

    metrics = bundle.summary
    print("\n" + "-" * 50)
    print("[METRICS] KET QUA DANH GIA BASELINE (BENCHMARKS):")
    print(f"  - Retrieval Hit Rate : {metrics.get('retrieval_hit_rate', 0.0) * 100:.1f}%")
    print(f"  - Mean Token F1      : {metrics.get('mean_token_f1', 0.0):.4f}")
    print(f"  - Judge Accuracy     : {metrics.get('judge_accuracy', 0.0) * 100:.1f}%")
    print(f"  - Mean Judge Score   : {metrics.get('mean_judge_score', 0.0):.2f} / 5.0")
    print("-" * 50)

    # 7. Sinh bao cao Markdown Pha 1
    source_summary = {
        "source_api": settings.source_api,
        "total_records": len(records),
        "clean_rows": len(clean_df),
        "raw_response_path": str(settings.paths.raw_api_response),
        "raw_records_path": str(settings.paths.raw_records_json),
    }
    generate_phase1_report(
        report_path=settings.paths.baseline_report,
        source_summary=source_summary,
        metrics=metrics,
        quality=quality_report,
        freshness=freshness_report,
    )
    print(f"[OK] Da sinh thanh cong bao cao: {settings.paths.baseline_report}")
    print("=" * 60)
    print("[SUCCESS] HOAN THANH BASELINE PIPELINE (PHASE 1) THANH CONG!")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    main()
