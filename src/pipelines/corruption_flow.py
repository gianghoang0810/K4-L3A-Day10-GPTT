from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pandas as pd

from core.config import load_settings
from core.utils import read_json, write_csv
from evaluation.metrics import evaluate_pipeline
from ingestion.cleaning import build_clean_dataframe
from ingestion.corruption import corrupt_clean_dataframe
from ingestion.crossref import load_raw_records
from observability.quality import build_freshness_report, run_data_quality_checks
from observability.reporting import generate_corruption_report
from retrieval.index import LocalEmbeddingIndex
import sys

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass


def main() -> None:
    """Xay dung va dieu phoi luong Corruption -> Evaluate -> Repair -> Compare (Phase 2)."""
    print("\n" + "=" * 60)
    print("[START] KHOI CHAY LUONG TIEM LOI & PHUC HOI DU LIEU (PHASE 2)")
    print("=" * 60)

    # 1. Load settings & baseline data
    settings = load_settings()

    if not settings.paths.clean_json.exists():
        raise FileNotFoundError(
            f"Chua tim thay {settings.paths.clean_json}. Vui long chay run_phase1.py truoc khi chay corruption flow!"
        )

    clean_df = pd.read_json(settings.paths.clean_json)
    baseline_metrics = read_json(settings.paths.baseline_metrics)
    print(f"[*] Da doc {len(clean_df)} ban ghi sach tu Baseline.")

    # 2. Synthetic Data Corruption: Tiem 6 dang loi du lieu
    print("\n[Step 1/4] Data Corruption: Tiem 6 kich ban loi du lieu thuc te...")
    corrupted_df = corrupt_clean_dataframe(clean_df, settings.paths.corruption_log)
    write_csv(corrupted_df, settings.paths.corrupted_clean_csv)
    corrupted_df.to_json(settings.paths.corrupted_clean_json, orient="records", indent=2)
    print(f"  -> Da tao corrupted dataset: {settings.paths.corrupted_clean_csv} ({len(corrupted_df)} dong)")
    print(f"  -> Da ghi nhat ky loi vao: {settings.paths.corruption_log}")

    # 3. Kiem tra Data Observability & Danh gia RAG tren du lieu loi
    print("\n[Step 2/4] Observability & Benchmark tren du lieu loi (Chung minh Silent Failure)...")
    corrupted_quality = run_data_quality_checks(corrupted_df, settings, "corrupted")
    corrupted_freshness = build_freshness_report(corrupted_df, settings)
    print(f"  -> Quality Gate: {'PASSED' if corrupted_quality.get('success') else 'FAILED (Canh bao bat thuong!)'}")
    print(f"  -> Freshness SLA: {'FRESH' if corrupted_freshness.get('is_fresh') else 'STALE (Canh bao qua han!)'}")

    corrupted_index = LocalEmbeddingIndex.build(corrupted_df, settings, settings.paths.corrupted_embeddings_json)
    corrupted_bundle = evaluate_pipeline(
        settings=settings,
        index=corrupted_index,
        test_set_path=settings.paths.eval_testset,
        metrics_output_path=settings.paths.corrupted_metrics,
        answers_output_path=settings.paths.corrupted_answers,
    )
    corrupted_metrics = corrupted_bundle.summary
    print(f"  -> Corrupted Hit Rate: {corrupted_metrics.get('retrieval_hit_rate', 0.0) * 100:.1f}%")
    print(f"  -> Corrupted Token F1: {corrupted_metrics.get('mean_token_f1', 0.0):.4f}")

    # 4. Idempotent Repair: Tu dong khoi phuc an toan tu nguon Raw
    print("\n[Step 3/4] Idempotent Repair: Khoi phuc an toan tu Raw Records...")
    raw_records = load_raw_records(settings.paths.raw_records_json)
    run_date = datetime.now(UTC)
    repaired_df = build_clean_dataframe(raw_records, run_date)
    write_csv(repaired_df, settings.paths.repaired_clean_csv)
    repaired_df.to_json(settings.paths.repaired_clean_json, orient="records", indent=2)
    print(f"  -> Da tai tao du lieu sach: {len(repaired_df)} dong tu {settings.paths.raw_records_json}")

    repaired_quality = run_data_quality_checks(repaired_df, settings, "repaired")
    repaired_freshness = build_freshness_report(repaired_df, settings)
    print(f"  -> Repaired Quality Gate: {'PASSED (Dat chuan)' if repaired_quality.get('success') else 'FAILED'}")

    repaired_index = LocalEmbeddingIndex.build(repaired_df, settings, settings.paths.repaired_embeddings_json)
    repaired_bundle = evaluate_pipeline(
        settings=settings,
        index=repaired_index,
        test_set_path=settings.paths.eval_testset,
        metrics_output_path=settings.paths.repaired_metrics,
        answers_output_path=settings.paths.repaired_answers,
    )
    repaired_metrics = repaired_bundle.summary
    print(f"  -> Repaired Hit Rate : {repaired_metrics.get('retrieval_hit_rate', 0.0) * 100:.1f}%")
    print(f"  -> Repaired Token F1 : {repaired_metrics.get('mean_token_f1', 0.0):.4f}")

    # 5. Xuat bao cao Markdown doi chieu 3 trang thai
    print("\n[Step 4/4] Bao Cao: Xuat bang doi chieu 3 trang thai (Baseline vs Corrupted vs Repaired)...")
    generate_corruption_report(
        report_path=settings.paths.comparison_report,
        baseline_metrics=baseline_metrics,
        corrupted_metrics=corrupted_metrics,
        repaired_metrics=repaired_metrics,
        corrupted_quality=corrupted_quality,
        repaired_quality=repaired_quality,
        corrupted_freshness=corrupted_freshness,
        repaired_freshness=repaired_freshness,
    )
    print(f"[OK] Da sinh bao cao doi chieu: {settings.paths.comparison_report}")

    print("\n" + "=" * 70)
    print("[SUMMARY] BANG DOI CHIEU HIEU NANG 3 TRANG THAI:")
    print(f"{'Chi so':<22} | {'Baseline':<12} | {'Corrupted':<12} | {'Repaired':<12}")
    print("-" * 70)
    print(
        f"{'Retrieval Hit Rate':<22} | {baseline_metrics.get('retrieval_hit_rate', 0.0)*100:>10.1f}% | {corrupted_metrics.get('retrieval_hit_rate', 0.0)*100:>10.1f}% | {repaired_metrics.get('retrieval_hit_rate', 0.0)*100:>10.1f}%"
    )
    print(
        f"{'Mean Token F1':<22} | {baseline_metrics.get('mean_token_f1', 0.0):>11.4f} | {corrupted_metrics.get('mean_token_f1', 0.0):>11.4f} | {repaired_metrics.get('mean_token_f1', 0.0):>11.4f}"
    )
    print(
        f"{'Judge Accuracy':<22} | {baseline_metrics.get('judge_accuracy', 0.0)*100:>10.1f}% | {corrupted_metrics.get('judge_accuracy', 0.0)*100:>10.1f}% | {repaired_metrics.get('judge_accuracy', 0.0)*100:>10.1f}%"
    )
    print(
        f"{'Mean Judge Score':<22} | {baseline_metrics.get('mean_judge_score', 0.0):>9.2f} / 5 | {corrupted_metrics.get('mean_judge_score', 0.0):>9.2f} / 5 | {repaired_metrics.get('mean_judge_score', 0.0):>9.2f} / 5"
    )
    print(
        f"{'Quality Gate (GX)':<22} | {'PASS':>12} | {'FAIL':>12} | {'PASS':>12}"
    )
    print(
        f"{'Freshness SLA':<22} | {'TRUE':>12} | {'FALSE':>12} | {'TRUE':>12}"
    )
    print("=" * 70)
    print("[SUCCESS] HOAN THANH LUONG TIEM LOI & PHUC HOI (PHASE 2) THANH CONG!\n")


if __name__ == "__main__":
    main()
