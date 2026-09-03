"""
app.py

Self-serve experiment read-out tool. Loads experiment data (either the
built-in SQLite database or an uploaded CSV matching the analysis_ready
schema), runs the same analysis module used in Phase 4
(src/experiment_analysis.py), and displays primary metric results,
guardrail checks, and a plain-English ship/no-ship recommendation.

Run with: streamlit run app/app.py
"""

import sqlite3
import sys
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
from experiment_analysis import (
    analyze_binary_metric,
    check_guardrail,
    generate_recommendation,
)

DB_PATH = "data/experiment.db"
MDE_ABSOLUTE = 0.05  # must match reports/pre_registration.md

REQUIRED_COLUMNS = {
    "user_id", "signup_date", "variant",
    "day7_activated", "retained_30d", "had_support_ticket",
}

st.set_page_config(page_title="A/B Test Analysis Platform", layout="wide")


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

@st.cache_data
def load_from_db(path: str) -> pd.DataFrame:
    conn = sqlite3.connect(path)
    df = pd.read_sql("SELECT * FROM analysis_ready", conn)
    conn.close()
    return df


def load_data() -> pd.DataFrame | None:
    st.sidebar.header("Data source")
    source = st.sidebar.radio(
        "Choose a dataset",
        ["Built-in experiment (SQLite)", "Upload CSV"],
    )

    if source == "Built-in experiment (SQLite)":
        if not Path(DB_PATH).exists():
            st.error(
                f"No database found at {DB_PATH}. Run "
                "data/generate_data.py first."
            )
            return None
        return load_from_db(DB_PATH)

    uploaded = st.sidebar.file_uploader("Upload a CSV", type="csv")
    if uploaded is None:
        st.info("Upload a CSV with columns: " + ", ".join(sorted(REQUIRED_COLUMNS)))
        return None

    df = pd.read_csv(uploaded)
    missing = REQUIRED_COLUMNS - set(df.columns)
    if missing:
        st.error(f"Uploaded file is missing required columns: {sorted(missing)}")
        return None
    return df


# ---------------------------------------------------------------------------
# Display helpers
# ---------------------------------------------------------------------------

def render_metric_card(result, title: str):
    col1, col2, col3, col4 = st.columns(4)
    col1.metric(
        "Control rate",
        f"{result.rate_control:.2%}",
        help=f"n={result.n_control}, 95% CI "
             f"({result.ci_control[0]:.2%}, {result.ci_control[1]:.2%})",
    )
    col2.metric(
        "Treatment rate",
        f"{result.rate_treatment:.2%}",
        help=f"n={result.n_treatment}, 95% CI "
             f"({result.ci_treatment[0]:.2%}, {result.ci_treatment[1]:.2%})",
    )
    col3.metric(
        "Absolute lift",
        f"{result.absolute_lift:+.2%}",
        help=f"95% CI ({result.diff_ci[0]:.2%}, {result.diff_ci[1]:.2%})",
    )
    col4.metric(
        "p-value",
        f"{result.p_value:.4f}",
        help="Significant at alpha=0.05" if result.is_significant else "Not significant",
    )


def render_guardrail_panel(checks: list):
    for check in checks:
        if check["failed"]:
            st.error(f"❌ **{check['metric_name']}** — {check['reason']}")
        else:
            st.success(f"✅ **{check['metric_name']}** — {check['reason']}")


def render_trend_chart(df: pd.DataFrame):
    """
    Shows cumulative activation rate by variant over the test period, purely
    for illustration of how the metric evolved. This view is NOT used to
    make an early ship/no-ship call -- the pre-registered decision rule is
    evaluated once on the full, final sample (see pre_registration.md).
    """
    daily = (
        df.groupby(["signup_date", "variant"])["day7_activated"]
        .agg(["sum", "count"])
        .reset_index()
        .sort_values("signup_date")
    )
    daily["cum_sum"] = daily.groupby("variant")["sum"].cumsum()
    daily["cum_count"] = daily.groupby("variant")["count"].cumsum()
    daily["cumulative_rate"] = daily["cum_sum"] / daily["cum_count"]

    fig = px.line(
        daily,
        x="signup_date",
        y="cumulative_rate",
        color="variant",
        title="Cumulative Day-7 Activation Rate Over Time (illustrative only)",
        labels={"cumulative_rate": "Cumulative activation rate", "signup_date": "Signup date"},
    )
    fig.update_yaxes(tickformat=".0%")
    st.plotly_chart(fig, use_container_width=True)
    st.caption(
        "Shown for illustration of trend stability. Per the pre-registered "
        "decision rule, the ship/no-ship recommendation is based on the "
        "full, final sample only -- not on interim trends."
    )


# ---------------------------------------------------------------------------
# Main app
# ---------------------------------------------------------------------------

def main():
    st.title("A/B Test Analysis Platform")
    st.caption(
        "Self-serve experiment read-out for the onboarding flow test. "
        "See reports/hypothesis.md and reports/pre_registration.md for "
        "full experiment design."
    )

    df = load_data()
    if df is None:
        return

    primary = analyze_binary_metric(df, "day7_activated")
    retention = analyze_binary_metric(df, "retained_30d")
    tickets = analyze_binary_metric(df, "had_support_ticket")

    guardrail_checks = [
        check_guardrail(retention, bad_direction="decrease"),
        check_guardrail(tickets, bad_direction="increase"),
    ]

    recommendation = generate_recommendation(
        primary_result=primary,
        mde_absolute=MDE_ABSOLUTE,
        guardrail_checks=guardrail_checks,
    )

    st.header("Primary Metric — Day-7 Activation Rate")
    render_metric_card(primary, "Day-7 Activation")

    st.header("Guardrail Metrics")
    render_guardrail_panel(guardrail_checks)

    st.header("Recommendation")
    decision = recommendation["decision"]
    if decision == "SHIP":
        st.success(f"**{decision}** — {recommendation['reason']}")
    elif decision == "INCONCLUSIVE":
        st.warning(f"**{decision}** — {recommendation['reason']}")
    else:
        st.error(f"**{decision}** — {recommendation['reason']}")

    st.header("Trend Over Time")
    render_trend_chart(df)


if __name__ == "__main__":
    main()
