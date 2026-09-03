"""
experiment_analysis.py

Reusable statistical analysis functions for evaluating A/B test results on
binary (proportion) metrics. Used by both the results notebook and the
Streamlit app, so the analysis logic exists in exactly one place.

All functions operate on a pandas DataFrame with one row per user,
containing at minimum a variant column and one or more binary (0/1)
metric columns, matching the analysis_ready table produced in Phase 2.
"""

from dataclasses import dataclass

from statsmodels.stats.proportion import (
    proportions_ztest,
    proportion_confint,
    confint_proportions_2indep,
)


@dataclass
class MetricResult:
    metric_name: str
    n_control: int
    n_treatment: int
    rate_control: float
    rate_treatment: float
    ci_control: tuple
    ci_treatment: tuple
    absolute_lift: float
    relative_lift: float
    diff_ci: tuple
    z_stat: float
    p_value: float
    alpha: float
    is_significant: bool


def analyze_binary_metric(
    df,
    metric_col: str,
    variant_col: str = "variant",
    control_label: str = "control",
    treatment_label: str = "treatment",
    alpha: float = 0.05,
) -> MetricResult:
    """
    Runs a two-proportion z-test comparing a binary metric between control
    and treatment groups, returning sample sizes, rates, confidence
    intervals, lift, and significance.
    """
    control = df.loc[df[variant_col] == control_label, metric_col]
    treatment = df.loc[df[variant_col] == treatment_label, metric_col]

    n_c, n_t = len(control), len(treatment)
    x_c, x_t = int(control.sum()), int(treatment.sum())

    rate_c = x_c / n_c
    rate_t = x_t / n_t

    ci_c = proportion_confint(x_c, n_c, alpha=alpha, method="wilson")
    ci_t = proportion_confint(x_t, n_t, alpha=alpha, method="wilson")

    z_stat, p_value = proportions_ztest([x_t, x_c], [n_t, n_c])

    diff_ci = confint_proportions_2indep(x_t, n_t, x_c, n_c, method="wald")

    absolute_lift = rate_t - rate_c
    relative_lift = (absolute_lift / rate_c) if rate_c > 0 else float("nan")

    return MetricResult(
        metric_name=metric_col,
        n_control=n_c,
        n_treatment=n_t,
        rate_control=rate_c,
        rate_treatment=rate_t,
        ci_control=ci_c,
        ci_treatment=ci_t,
        absolute_lift=absolute_lift,
        relative_lift=relative_lift,
        diff_ci=diff_ci,
        z_stat=z_stat,
        p_value=p_value,
        alpha=alpha,
        is_significant=bool(p_value < alpha),
    )


def meets_mde(result: MetricResult, mde_absolute: float) -> bool:
    """
    Practical-significance check: whether the observed lift meets or
    exceeds the pre-registered minimum detectable effect, not just
    statistical significance. A result can be statistically significant
    with an effect too small to matter, or vice versa in edge cases.
    """
    return result.is_significant and result.absolute_lift >= mde_absolute


def check_guardrail(result: MetricResult, bad_direction: str) -> dict:
    """
    Evaluates a guardrail metric against a pre-specified "bad" direction.

    bad_direction: "increase" if a rise in this metric is undesirable
                   (e.g. support ticket rate), or "decrease" if a drop is
                   undesirable (e.g. retention rate).

    Returns a dict with a pass/fail flag and the reasoning, rather than a
    single boolean, so the result can be surfaced transparently in reports.
    """
    if bad_direction not in ("increase", "decrease"):
        raise ValueError("bad_direction must be 'increase' or 'decrease'")

    moved_in_bad_direction = bool(
        result.absolute_lift > 0 if bad_direction == "increase"
        else result.absolute_lift < 0
    )

    failed = bool(result.is_significant and moved_in_bad_direction)

    return {
        "metric_name": result.metric_name,
        "failed": failed,
        "absolute_lift": result.absolute_lift,
        "p_value": result.p_value,
        "reason": (
            f"{result.metric_name} moved {'up' if result.absolute_lift > 0 else 'down'} "
            f"by {abs(result.absolute_lift):.2%} (p={result.p_value:.4f}); "
            f"this direction is {'a guardrail failure' if failed else 'not a guardrail concern'}."
        ),
    }


def generate_recommendation(
    primary_result: MetricResult,
    mde_absolute: float,
    guardrail_checks: list,
) -> dict:
    """
    Applies the pre-registered decision rule (see reports/pre_registration.md):

    - Ship if the primary metric is significant AND meets the MDE
      AND no guardrail has failed.
    - Do not ship if any guardrail failed, regardless of the primary result.
    - Otherwise, inconclusive.
    """
    primary_meets_mde = meets_mde(primary_result, mde_absolute)
    any_guardrail_failed = any(g["failed"] for g in guardrail_checks)

    if any_guardrail_failed:
        decision = "DO NOT SHIP"
        reason = "One or more guardrail metrics regressed significantly."
    elif primary_meets_mde:
        decision = "SHIP"
        reason = (
            "Primary metric is statistically significant and meets the "
            "pre-registered minimum detectable effect; no guardrail failures."
        )
    elif primary_result.is_significant:
        decision = "INCONCLUSIVE"
        reason = (
            "Primary metric is statistically significant but the observed "
            "lift is below the pre-registered MDE; effect may be too small "
            "to justify the change."
        )
    else:
        decision = "DO NOT SHIP"
        reason = "Primary metric did not reach statistical significance."

    return {"decision": decision, "reason": reason}