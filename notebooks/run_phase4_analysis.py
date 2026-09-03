"""
run_phase4_analysis.py

Loads the analysis-ready experiment data, runs the primary metric test and
guardrail checks using src/experiment_analysis.py, validates the result
against the known ground truth baked into the simulated data (Phase 2),
and prints a full readable report.
"""

import sqlite3
import sys

import pandas as pd

sys.path.insert(0, "src")
from experiment_analysis import (
    analyze_binary_metric,
    check_guardrail,
    generate_recommendation,
)

DB_PATH = "data/experiment.db"
MDE_ABSOLUTE = 0.05          # must match reports/pre_registration.md
TRUE_LIFT_GROUND_TRUTH = 0.05  # must match data/generate_data.py TRUE_ABSOLUTE_LIFT


def load_data() -> pd.DataFrame:
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql("SELECT * FROM analysis_ready", conn)
    conn.close()
    return df


def print_metric_report(result, label: str):
    print(f"\n{label}")
    print("-" * len(label))
    print(f"  Control:    n={result.n_control:>6}  rate={result.rate_control:.4f}  "
          f"95% CI=({result.ci_control[0]:.4f}, {result.ci_control[1]:.4f})")
    print(f"  Treatment:  n={result.n_treatment:>6}  rate={result.rate_treatment:.4f}  "
          f"95% CI=({result.ci_treatment[0]:.4f}, {result.ci_treatment[1]:.4f})")
    print(f"  Absolute lift: {result.absolute_lift:+.4f}  "
          f"(95% CI: {result.diff_ci[0]:.4f} to {result.diff_ci[1]:.4f})")
    print(f"  Relative lift: {result.relative_lift:+.2%}")
    print(f"  z-stat: {result.z_stat:.4f}   p-value: {result.p_value:.6f}")
    print(f"  Significant at alpha={result.alpha}: {result.is_significant}")


def main():
    df = load_data()

    primary = analyze_binary_metric(df, "day7_activated")
    print_metric_report(primary, "PRIMARY METRIC — Day-7 Activation Rate")

    retention = analyze_binary_metric(df, "retained_30d")
    print_metric_report(retention, "GUARDRAIL — 30-Day Retention Rate")

    tickets = analyze_binary_metric(df, "had_support_ticket")
    print_metric_report(tickets, "GUARDRAIL — Support Ticket Rate")

    guardrail_checks = [
        check_guardrail(retention, bad_direction="decrease"),
        check_guardrail(tickets, bad_direction="increase"),
    ]

    print("\nGUARDRAIL CHECK RESULTS")
    print("-" * 23)
    for check in guardrail_checks:
        status = "FAILED" if check["failed"] else "PASSED"
        print(f"  [{status}] {check['reason']}")

    recommendation = generate_recommendation(
        primary_result=primary,
        mde_absolute=MDE_ABSOLUTE,
        guardrail_checks=guardrail_checks,
    )

    print("\nFINAL RECOMMENDATION")
    print("-" * 21)
    print(f"  Decision: {recommendation['decision']}")
    print(f"  Reason:   {recommendation['reason']}")

    # Validation against known ground truth
    lo, hi = primary.diff_ci
    truth_recovered = lo <= TRUE_LIFT_GROUND_TRUTH <= hi
    print("\nMETHODOLOGY VALIDATION")
    print("-" * 22)
    print(f"  True effect baked into simulated data: {TRUE_LIFT_GROUND_TRUTH:.2%}")
    print(f"  Observed 95% CI of lift: ({lo:.4f}, {hi:.4f})")
    print(f"  True effect recovered within CI: {truth_recovered}")
    if not truth_recovered:
        print("  WARNING: statistical methodology may have an error — "
              "investigate before trusting analysis on real data.")


if __name__ == "__main__":
    main()
