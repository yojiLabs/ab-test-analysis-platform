"""
run_phase4_analysis.py

Loads the analysis-ready experiment data, runs the primary metric test and
guardrail checks using src/experiment_analysis.py, validates the result
against the known ground truth baked into the simulated data (Phase 2),
prints a full readable report, and saves the results to reports/ as both
a markdown summary and a machine-readable JSON file (for reuse by the
Streamlit app in Phase 5 and the case study in Phase 6).
"""

import json
import sqlite3
import sys
from pathlib import Path

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
REPORTS_DIR = Path("reports")


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


def metric_result_to_dict(result) -> dict:
    return {
        "metric_name": result.metric_name,
        "n_control": result.n_control,
        "n_treatment": result.n_treatment,
        "rate_control": result.rate_control,
        "rate_treatment": result.rate_treatment,
        "ci_control": list(result.ci_control),
        "ci_treatment": list(result.ci_treatment),
        "absolute_lift": result.absolute_lift,
        "relative_lift": result.relative_lift,
        "diff_ci": [float(result.diff_ci[0]), float(result.diff_ci[1])],
        "z_stat": result.z_stat,
        "p_value": result.p_value,
        "alpha": result.alpha,
        "is_significant": result.is_significant,
    }


def write_json_report(primary, retention, tickets, guardrail_checks, recommendation, truth_recovered):
    REPORTS_DIR.mkdir(exist_ok=True)
    payload = {
        "primary_metric": metric_result_to_dict(primary),
        "guardrails": {
            "retained_30d": metric_result_to_dict(retention),
            "had_support_ticket": metric_result_to_dict(tickets),
        },
        "guardrail_checks": guardrail_checks,
        "recommendation": recommendation,
        "mde_absolute": MDE_ABSOLUTE,
        "true_lift_ground_truth": TRUE_LIFT_GROUND_TRUTH,
        "truth_recovered_within_ci": truth_recovered,
    }
    out_path = REPORTS_DIR / "phase4_results.json"
    out_path.write_text(json.dumps(payload, indent=2))
    return out_path


def write_markdown_report(primary, retention, tickets, guardrail_checks, recommendation, truth_recovered):
    REPORTS_DIR.mkdir(exist_ok=True)
    lo, hi = primary.diff_ci

    lines = [
        "# Phase 4 Results — Onboarding Flow Experiment",
        "",
        "## Primary Metric — Day-7 Activation Rate",
        f"- Control: n={primary.n_control}, rate={primary.rate_control:.2%}, "
        f"95% CI=({primary.ci_control[0]:.2%}, {primary.ci_control[1]:.2%})",
        f"- Treatment: n={primary.n_treatment}, rate={primary.rate_treatment:.2%}, "
        f"95% CI=({primary.ci_treatment[0]:.2%}, {primary.ci_treatment[1]:.2%})",
        f"- Absolute lift: {primary.absolute_lift:+.2%} "
        f"(95% CI: {lo:.2%} to {hi:.2%})",
        f"- Relative lift: {primary.relative_lift:+.2%}",
        f"- p-value: {primary.p_value:.6f} "
        f"({'significant' if primary.is_significant else 'not significant'} at alpha={primary.alpha})",
        "",
        "## Guardrail Metrics",
    ]
    for check in guardrail_checks:
        status = "FAILED" if check["failed"] else "PASSED"
        lines.append(f"- **[{status}]** {check['reason']}")

    lines += [
        "",
        "## Recommendation",
        f"**{recommendation['decision']}**",
        "",
        recommendation["reason"],
        "",
        "## Methodology Validation",
        f"- True effect baked into simulated data: {TRUE_LIFT_GROUND_TRUTH:.2%}",
        f"- Observed 95% CI of lift: ({lo:.2%}, {hi:.2%})",
        f"- True effect recovered within CI: {truth_recovered}",
    ]

    out_path = REPORTS_DIR / "phase4_results.md"
    out_path.write_text("\n".join(lines))
    return out_path


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
    truth_recovered = bool(lo <= TRUE_LIFT_GROUND_TRUTH <= hi)
    print("\nMETHODOLOGY VALIDATION")
    print("-" * 22)
    print(f"  True effect baked into simulated data: {TRUE_LIFT_GROUND_TRUTH:.2%}")
    print(f"  Observed 95% CI of lift: ({lo:.4f}, {hi:.4f})")
    print(f"  True effect recovered within CI: {truth_recovered}")
    if not truth_recovered:
        print("  WARNING: statistical methodology may have an error — "
              "investigate before trusting analysis on real data.")

    json_path = write_json_report(
        primary, retention, tickets, guardrail_checks, recommendation, truth_recovered
    )
    md_path = write_markdown_report(
        primary, retention, tickets, guardrail_checks, recommendation, truth_recovered
    )
    print(f"\nSaved results to: {md_path} and {json_path}")


if __name__ == "__main__":
    main()