# Phase 4 Results — Onboarding Flow Experiment

## Primary Metric — Day-7 Activation Rate
- Control: n=9829, rate=37.79%, 95% CI=(36.83%, 38.75%)
- Treatment: n=9767, rate=43.05%, 95% CI=(42.07%, 44.04%)
- Absolute lift: +5.27% (95% CI: 3.89% to 6.64%)
- Relative lift: +13.94%
- p-value: 0.000000 (significant at alpha=0.05)

## Guardrail Metrics
- **[PASSED]** retained_30d moved up by 2.84% (p=0.0001); this direction is not a guardrail concern.
- **[FAILED]** had_support_ticket moved up by 1.56% (p=0.0001); this direction is a guardrail failure.

## Recommendation
**DO NOT SHIP**

One or more guardrail metrics regressed significantly.

## Methodology Validation
- True effect baked into simulated data: 5.00%
- Observed 95% CI of lift: (3.89%, 6.64%)
- True effect recovered within CI: True