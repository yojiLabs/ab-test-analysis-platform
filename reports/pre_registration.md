# Pre-Registration: Onboarding Flow Experiment

**Status:** Locked before results are analyzed.
**Date written:** Prior to Phase 4 (results analysis).

This document exists to fix the experiment design in advance, preventing
any reframing of the hypothesis, metric definitions, or success criteria
after results are known. All parameters below are final as of this
writing.

## What Is Being Tested

A 3-step signup flow (treatment) is compared against the existing 6-step
signup flow (control). Full background and rationale are documented in
`hypothesis.md`.

## Primary Metric

Day-7 activation rate, as defined in `hypothesis.md`: the proportion of
signed-up users who complete all 3 key onboarding actions (add payment
method, create first project, invite a teammate) within 7 days of signup.

## Guardrail Metrics

- 30-day retention rate
- Support ticket rate within 7 days of signup

## Statistical Design

| Parameter | Value |
|---|---|
| Baseline (control) activation rate | 38% |
| Minimum detectable effect (MDE) | 5 percentage points, absolute (38% → 43%) |
| Significance level (alpha) | 0.05, two-sided |
| Statistical power | 80% |
| Required sample size per group | 1,512 |
| Required total sample size | 3,023 |
| Estimated test duration | ~6–7 days, based on estimated signup volume |

The MDE of 5 percentage points was chosen as the smallest lift considered
practically meaningful for this decision — a smaller true effect either
would not justify the engineering cost of the change, or would require an
impractically long test to detect reliably. This threshold, not just
statistical significance, is what determines the final ship / no-ship
recommendation.

## Decision Rule (Set in Advance)

- **Ship** the treatment if the observed lift is statistically significant
  at alpha = 0.05 AND the observed effect meets or exceeds the 5-point MDE
  AND no guardrail metric shows a statistically significant regression.
- **Do not ship** if the primary metric is not significant, or if a
  guardrail metric regresses significantly, regardless of the primary
  metric result.
- **Inconclusive / extend test** if the primary metric shows a positive
  but sub-MDE effect that has not yet reached significance by the planned
  end date.

## Planned Test Duration

The test is planned to run for the sample size required above, rounded up
to full weeks to control for day-of-week effects (avoiding a partial-week
cutoff that could bias the result toward whichever days happened to be
included). No interim peeking or early stopping based on results is
planned — the test runs to the pre-determined sample size before any
metric is reviewed.

## Known Limitations

- This is a simulated experiment; the baseline rate and effect size are
  informed by published industry benchmarks (see `hypothesis.md`) but are
  not drawn from a real production system.
- The pre-registration process here is performed as a demonstration of
  methodology; in a production setting, this document would typically be
  reviewed and signed off by a second stakeholder before the test launches.
