# Experiment Hypothesis: Simplified Onboarding Flow

## Background

New users currently go through a 6-step signup flow that collects account details,
company info, team size, use case, and optional preferences all before they reach
the product. Product analytics shows a meaningful drop-off during signup, and only
a minority of users who do complete signup go on to take the actions that
correlate with long-term retention.

**Current state:** ~38% of new signups reach "activation" (defined below) within
7 days.

## Proposed Change

Reduce the signup flow from 6 steps to 3 steps by collecting only the essentials
(email, password, company name) up front, and moving everything else
(team size, use case, preferences) to an optional in-app step after signup.

## Hypothesis

Reducing signup friction will increase the Day-7 activation rate, because fewer
high-intent users will drop off before ever reaching the product. We expect this
to primarily affect top-of-funnel completion, not necessarily deepen engagement
for users who would have signed up anyway.

**Null hypothesis (H0):** Simplifying the signup flow has no effect on Day-7
activation rate.

**Alternative hypothesis (H1):** Simplifying the signup flow increases Day-7
activation rate.

## Primary Metric

**Day-7 Activation Rate**

- **Definition:** % of users who complete ALL 3 of the following within 7 days
  of signing up:
  1. Add a payment method (or start trial)
  2. Create their first project/workspace
  3. Invite at least one teammate
- **Numerator:** Users who complete all 3 actions within 7 days
- **Denominator:** All users who complete signup
- **Metric type:** Binary (proportion) — determines statistical test (two-proportion z-test)
- **Time window:** 7 days from signup date (chosen because it captures early
  intent-to-use without waiting so long that we delay the read-out)

## Guardrail Metrics

Guardrails exist to catch trade-offs the primary metric alone would miss —
each one represents a different stakeholder's concern.

1. **30-Day Retention Rate**
   - **Why it matters:** A shorter signup flow could bring in lower-intent
     users who convert on paper but don't stick around. This protects against
     "activation inflation" that doesn't translate to real value.
   - **Definition:** % of users still active (logged in + performed 1+ core
     action) 30 days after signup.

2. **Support Ticket Rate (per new user, first 7 days)**
   - **Why it matters:** Deferring fields like "use case" and "team size" to
     post-signup could create confusion (e.g., users unsure how to configure
     their workspace), showing up as increased support load.
   - **Definition:** # of support tickets opened / # of new signups, within
     first 7 days.

## Experiment Design (high level — full sample size calc in Phase 3)

- **Unit of randomization:** Individual user (signup session)
- **Split:** 50/50 treatment (3-step flow) vs. control (6-step flow)
- **Primary metric owner (hypothetical stakeholder):** Growth/Product team
- **Guardrail owners (hypothetical stakeholders):** Customer Success
  (support tickets), Product leadership (30-day retention)

## Assumptions

All company details, user data, and specific numbers in this document are
fictional and constructed for demonstration purposes — no real product or
company is represented. However, the baseline activation rate and the
premise that signup friction suppresses activation are grounded in publicly
published SaaS benchmarks rather than picked arbitrarily:

- Industry activation-rate benchmarks vary widely by vertical, from roughly
  5% (FinTech & Insurance) to nearly 55% (AI/ML), based on Userpilot's 2024
  Product Metrics Benchmarks report covering 547 SaaS companies. The 38%
  baseline used here sits in a realistic mid-range for a general B2B SaaS
  product.
- More recent aggregated benchmark data (2025–2026) puts the average SaaS
  activation rate at approximately 37–37.5%, closely matching the baseline
  assumed in this document.
- Reducing the amount of information collected during signup is a
  recognized, commonly cited lever for improving activation rate, which is
  the basis for this experiment's proposed change.
- Published estimates suggest activation-rate improvements can have an
  outsized effect on revenue (one widely cited figure: a 25% relative
  increase in activation rate correlating with a 34% increase in revenue
  over 12 months), which is why this metric is treated as high-priority in
  the hypothetical scenario.

Sources: Userpilot 2024 Product Metrics Benchmarks Report; aggregated 2025–2026
SaaS onboarding benchmark summaries (shno.co, DEV Community).

## Pre-Registration Note

This document is written *before* generating or analyzing any experiment data.
Locking in the hypothesis, primary metric, and guardrails in advance avoids
p-hacking or reframing "what we were testing" after seeing favorable results —
a standard practice on real experimentation teams.

---