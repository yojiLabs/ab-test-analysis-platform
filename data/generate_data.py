"""
generate_data.py

Generates a synthetic A/B test dataset for the onboarding-flow experiment
defined in reports/hypothesis.md, and loads it into a SQLite database
following schema.sql.

The "TRUE EFFECT" constants below define the ground truth baked into the
generated data. These values are recorded so that the downstream
statistical analysis can later be validated against a known answer,
confirming the methodology correctly recovers the true effect rather than
an artifact of the test procedure.
"""

import sqlite3
import random
from datetime import date, datetime, timedelta

# ---------------------------------------------------------------------------
# CONFIG — the "ground truth" of this simulated world
# ---------------------------------------------------------------------------

N_USERS = 20_000
START_DATE = date(2026, 1, 1)
N_DAYS = 42  # 6 weeks of signups

# Baseline (control) Day-7 activation rate, grounded in the 38% baseline
# from the hypothesis doc.
BASELINE_ACTIVATION_RATE = 0.38

# TRUE treatment effect: +5 percentage points absolute lift.
# (38% -> 43%, a ~13% relative lift — a realistic, meaningful effect size,
# not an inflated one.)
TRUE_ABSOLUTE_LIFT = 0.05

# Guardrail ground truth: support ticket rate is *slightly* higher in
# treatment (deferred fields create minor confusion), but NOT dramatically —
# intentionally a borderline guardrail signal, meant to be caught by the
# guardrail check rather than obvious on inspection.
BASELINE_TICKET_RATE = 0.08
TREATMENT_TICKET_RATE = 0.095

# 30-day retention is driven mostly by whether a user activated, not by
# variant directly — i.e., no separate treatment effect on retention beyond
# what activation already explains. This is deliberate: retention is not
# expected to register as a guardrail failure in the analysis output.
RETENTION_RATE_IF_ACTIVATED = 0.70
RETENTION_RATE_IF_NOT_ACTIVATED = 0.20

# Bot/outlier accounts: junk signups that should be filtered before analysis.
BOT_RATE = 0.02

DB_PATH = "data/experiment.db"
SCHEMA_PATH = "sql/schema.sql"

random.seed(42)  # reproducibility


# ---------------------------------------------------------------------------
# Helpers for realistic noise
# ---------------------------------------------------------------------------

def day_of_week_multiplier(d: date) -> float:
    """Signup volume dips on weekends (typical B2B SaaS pattern)."""
    weekday = d.weekday()  # 0=Mon ... 6=Sun
    if weekday in (5, 6):
        return 0.55
    return 1.0


def seasonality_multiplier(day_index: int) -> float:
    """Slight upward trend in volume over the window (mild organic growth)."""
    return 1.0 + (day_index / N_DAYS) * 0.3


def build_signup_dates(n_users: int) -> list[date]:
    """Assigns each user a signup date, weighted by day-of-week + trend."""
    weights = []
    dates = []
    for i in range(N_DAYS):
        d = START_DATE + timedelta(days=i)
        w = day_of_week_multiplier(d) * seasonality_multiplier(i)
        dates.append(d)
        weights.append(w)

    return random.choices(dates, weights=weights, k=n_users)


# ---------------------------------------------------------------------------
# Main generation logic
# ---------------------------------------------------------------------------

def generate():
    signup_dates = build_signup_dates(N_USERS)

    users = []
    assignments = []
    events = []

    for user_id in range(1, N_USERS + 1):
        signup_date = signup_dates[user_id - 1]
        signup_dt = datetime.combine(signup_date, datetime.min.time()) + timedelta(
            hours=random.randint(0, 23), minutes=random.randint(0, 59)
        )

        is_bot = 1 if random.random() < BOT_RATE else 0
        users.append((user_id, signup_date.isoformat(), is_bot))

        # 50/50 random assignment
        variant = random.choice(["control", "treatment"])
        assignments.append((user_id, variant, signup_dt.isoformat()))

        # signup_complete event always fires
        events.append((user_id, "signup_complete", signup_dt.isoformat()))

        if is_bot:
            # Bots behave erratically: either instantly "complete" everything
            # (scripted abuse) or never do anything. Either way, they should
            # be excluded from real analysis — that's the point.
            if random.random() < 0.5:
                for ev in ["add_payment_method", "create_project", "invite_teammate"]:
                    events.append((user_id, ev, signup_dt.isoformat()))
            continue  # skip normal behavioral simulation for bots

        # Determine this user's true activation probability
        activation_prob = BASELINE_ACTIVATION_RATE
        if variant == "treatment":
            activation_prob += TRUE_ABSOLUTE_LIFT

        activated = random.random() < activation_prob

        if activated:
            # Spread the 3 key actions randomly within the 7-day window.
            # Generate the offset directly in hours (1 to 168 = exactly 7 days)
            # so it's structurally impossible to overshoot the window --
            # this was previously a bug (days + separate minutes could push
            # the timestamp past 7 days and silently fail the SQL window
            # check, undercounting activation).
            for ev in ["add_payment_method", "create_project", "invite_teammate"]:
                offset_hours = random.randint(1, 168)
                ev_time = signup_dt + timedelta(hours=offset_hours)
                events.append((user_id, ev, ev_time.isoformat()))
        else:
            # Non-activated users might still complete 0-2 of the 3 actions
            possible = ["add_payment_method", "create_project", "invite_teammate"]
            random.shuffle(possible)
            n_partial = random.choice([0, 0, 0, 1, 1, 2])  # weighted toward 0
            for ev in possible[:n_partial]:
                offset_days = random.randint(1, 10)
                ev_time = signup_dt + timedelta(days=offset_days)
                events.append((user_id, ev, ev_time.isoformat()))

        # Support tickets (guardrail metric)
        ticket_rate = TREATMENT_TICKET_RATE if variant == "treatment" else BASELINE_TICKET_RATE
        if random.random() < ticket_rate:
            offset_days = random.randint(0, 7)
            ev_time = signup_dt + timedelta(days=offset_days)
            events.append((user_id, "support_ticket", ev_time.isoformat()))

        # 30-day retention (guardrail metric): simulate as a final "active_day"
        # event near day 30 if the user is retained.
        retention_prob = (
            RETENTION_RATE_IF_ACTIVATED if activated else RETENTION_RATE_IF_NOT_ACTIVATED
        )
        if random.random() < retention_prob:
            ev_time = signup_dt + timedelta(days=30)
            events.append((user_id, "active_day", ev_time.isoformat()))

    return users, assignments, events


def load_into_sqlite(users, assignments, events):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    with open(SCHEMA_PATH, "r") as f:
        cur.executescript(f.read())

    cur.executemany("INSERT OR REPLACE INTO users VALUES (?, ?, ?)", users)
    cur.executemany("INSERT OR REPLACE INTO assignments VALUES (?, ?, ?)", assignments)
    cur.executemany(
        "INSERT INTO events (user_id, event_name, event_timestamp) VALUES (?, ?, ?)",
        events,
    )

    conn.commit()
    conn.close()
    print(f"Loaded {len(users)} users, {len(assignments)} assignments, "
          f"{len(events)} events into {DB_PATH}")


if __name__ == "__main__":
    users, assignments, events = generate()
    load_into_sqlite(users, assignments, events)
    print("\nGround truth for later validation:")
    print(f"  Baseline (control) activation rate: {BASELINE_ACTIVATION_RATE:.1%}")
    print(f"  True absolute lift:                 {TRUE_ABSOLUTE_LIFT:.1%}")
    print(f"  Expected treatment activation rate: "
          f"{BASELINE_ACTIVATION_RATE + TRUE_ABSOLUTE_LIFT:.1%}")