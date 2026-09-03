"""
sample_size_calculation.py

Pre-experiment power analysis for the onboarding-flow A/B test defined in
reports/hypothesis.md. Calculates the required sample size per group to
reliably detect the target effect, given a fixed significance level and
desired statistical power.

This calculation is performed BEFORE the results are analyzed (Phase 4),
consistent with the pre-registration principle documented in
reports/pre_registration.md.
"""

from statsmodels.stats.power import NormalIndPower
from statsmodels.stats.proportion import proportion_effectsize

# ---------------------------------------------------------------------------
# Assumptions (must match reports/hypothesis.md)
# ---------------------------------------------------------------------------

BASELINE_RATE = 0.38          # control Day-7 activation rate
MDE_ABSOLUTE = 0.05           # minimum detectable effect, absolute lift
TREATMENT_RATE = BASELINE_RATE + MDE_ABSOLUTE

ALPHA = 0.05                  # significance level (Type I error rate)
POWER = 0.80                  # desired statistical power (1 - Type II error rate)

# Approximate daily signup volume available for the test, used to translate
# required sample size into an expected test duration.
ESTIMATED_DAILY_SIGNUPS = 20000 / 42   # matches the simulated data generator
ESTIMATED_DAILY_SIGNUPS_PER_GROUP = ESTIMATED_DAILY_SIGNUPS / 2


def calculate_required_sample_size():
    effect_size = proportion_effectsize(TREATMENT_RATE, BASELINE_RATE)

    analysis = NormalIndPower()
    n_per_group = analysis.solve_power(
        effect_size=effect_size,
        alpha=ALPHA,
        power=POWER,
        ratio=1.0,
        alternative="two-sided",
    )

    return effect_size, n_per_group


if __name__ == "__main__":
    effect_size, n_per_group = calculate_required_sample_size()
    total_n = n_per_group * 2
    days_needed = n_per_group / ESTIMATED_DAILY_SIGNUPS_PER_GROUP

    print("Power Analysis — Onboarding Flow Experiment")
    print("-" * 50)
    print(f"Baseline (control) activation rate:  {BASELINE_RATE:.1%}")
    print(f"Target (treatment) activation rate:  {TREATMENT_RATE:.1%}")
    print(f"Minimum detectable effect (absolute): {MDE_ABSOLUTE:.1%}")
    print(f"Effect size (Cohen's h):              {effect_size:.4f}")
    print(f"Significance level (alpha):           {ALPHA}")
    print(f"Statistical power:                    {POWER:.0%}")
    print("-" * 50)
    print(f"Required sample size per group:       {n_per_group:.0f}")
    print(f"Required total sample size:           {total_n:.0f}")
    print(f"Estimated daily signups per group:    {ESTIMATED_DAILY_SIGNUPS_PER_GROUP:.0f}")
    print(f"Estimated test duration:              {days_needed:.1f} days "
          f"(~{days_needed / 7:.1f} weeks)")
