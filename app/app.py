"""
app.py

Self-serve experiment read-out tool. Loads experiment data (either the
built-in SQLite database or an uploaded CSV matching the analysis_ready
schema), runs the same analysis module used in Phase 4
(src/experiment_analysis.py), and displays primary metric results,
guardrail checks, and a plain-English ship/no-ship recommendation.

Visual design: a "lab report" aesthetic -- ledger-style metric rows,
monospace data figures, and an ink-stamp verdict -- since the content
itself (an experiment read-out) is literally a report being signed off.

Run with: streamlit run app/app.py
"""

import sqlite3
import sys
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
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

# Black and white palette
PAPER = "#FFFFFF"
INK = "#000000"
EVERGREEN = "#2B6E4E"  # Kept for charts and stamps only
RUST = "#A8461F"       # Kept for charts and stamps only
OCHRE = "#C08A1B"      # Kept for charts and stamps only
SLATE = "#666666"      # Grayscale for muted text
HAIRLINE = "#DDDDDD"   # Light gray for borders

st.set_page_config(page_title="A/B Test Analysis Platform", layout="wide")


# ---------------------------------------------------------------------------
# Styling
# ---------------------------------------------------------------------------

CUSTOM_CSS = """
<style>
:root {
    --paper: #FFFFFF;
    --ink: #000000;
    --evergreen: #2B6E4E;
    --rust: #A8461F;
    --ochre: #C08A1B;
    --slate: #666666;
    --hairline: #DDDDDD;
}

html, body, [data-testid="stAppViewContainer"], .main, .block-container {
    background-color: var(--paper) !important;
    color: var(--ink) !important;
    font-family: 'Arial', sans-serif !important;
}

#MainMenu, footer, [data-testid="stToolbar"] { visibility: hidden; }
header[data-testid="stHeader"] { background-color: var(--paper) !important; }

h1, h2, h3 { 
    font-family: 'Arial', sans-serif !important; 
    color: var(--ink) !important;
    font-weight: 700 !important;
}

/* Sidebar: solid black panel */
[data-testid="stSidebar"] {
    background-color: var(--ink) !important;
    border-right: 1px solid #333333;
}
[data-testid="stSidebar"] * { 
    color: #FFFFFF !important;
    font-family: 'Arial', sans-serif !important;
}
[data-testid="stSidebar"] .stRadio [role="radiogroup"] label span:first-child {
    border-color: #FFFFFF !important;
}

/* Masthead */
.report-meta {
    font-family: 'Arial', sans-serif;
    font-size: 0.78rem;
    color: var(--slate);
    letter-spacing: 0.01em;
}
.report-title {
    font-family: 'Arial', sans-serif;
    font-weight: 700;
    font-size: 2.4rem;
    margin: 4px 0 0 0;
    color: var(--ink);
}

/* Ledger-style metric row */
.metric-row {
    display: flex;
    align-items: baseline;
    justify-content: space-between;
    gap: 24px;
    padding: 28px 4px;
    border-top: 1px solid var(--ink);
    border-bottom: 1px solid var(--ink);
    margin: 28px 0 8px 0;
    flex-wrap: wrap;
}
.metric-block { text-align: left; }
.metric-value {
    font-family: 'Arial', sans-serif;
    font-size: 2.1rem;
    font-weight: 700;
    font-variant-numeric: tabular-nums;
    color: var(--ink);
}
.metric-label {
    font-family: 'Arial', sans-serif;
    font-size: 0.82rem;
    color: var(--slate);
    margin-top: 2px;
}
.metric-arrow {
    font-family: 'Arial', sans-serif;
    font-size: 1.6rem;
    color: var(--ink);
    align-self: center;
    font-weight: 700;
}

.section-label {
    font-family: 'Arial', sans-serif;
    font-size: 0.78rem;
    font-weight: 700;
    color: var(--slate);
    margin: 32px 0 12px 0;
    text-transform: uppercase;
    letter-spacing: 0.05em;
}

/* Guardrail list */
.guardrail-row {
    display: flex;
    align-items: center;
    gap: 12px;
    padding: 13px 2px;
    border-bottom: 1px solid var(--hairline);
    font-family: 'Arial', sans-serif;
    font-size: 0.94rem;
}
.dot { 
    width: 9px; 
    height: 9px; 
    border-radius: 50%; 
    flex-shrink: 0; 
}
.dot.pass { 
    background-color: var(--ink);
    border: 1px solid var(--ink);
}
.dot.fail { 
    background-color: #FF0000;
    border: 1px solid #FF0000;
}
.guardrail-status {
    margin-left: auto;
    font-family: 'Arial', sans-serif;
    font-size: 0.76rem;
    font-weight: 700;
    letter-spacing: 0.02em;
    color: var(--slate);
    white-space: nowrap;
}

/* Verdict stamp - the colored exception */
.stamp-wrap {
    display: flex;
    justify-content: center;
    align-items: center;
    flex-direction: column;
    margin: 44px 0 36px 0;
}
.stamp {
    border: 3px solid currentColor;
    border-radius: 4px;
    padding: 14px 34px;
    font-family: 'Arial', sans-serif;
    font-weight: 700;
    font-size: 1.7rem;
    letter-spacing: 0.03em;
    position: relative;
    transform: rotate(-3deg);
    opacity: 0;
    animation: stampIn 0.55s cubic-bezier(0.18, 1.35, 0.4, 1) 0.85s both;
}
.stamp::after {
    content: "";
    position: absolute;
    inset: 4px;
    border: 1px solid currentColor;
    border-radius: 3px;
    opacity: 0.55;
}
.stamp.ship { 
    color: var(--evergreen);
    background-color: #F0F7F2;  /* Light green tint for ship stamp */
}
.stamp.no-ship { 
    color: var(--rust);
    background-color: #FFF0EB;  /* Light red tint for no-ship stamp */
}
.stamp.inconclusive { 
    color: var(--ochre);
    background-color: #FFF8EB;  /* Light yellow tint for inconclusive stamp */
}

.stamp-reason {
    font-family: 'Arial', sans-serif;
    font-size: 0.86rem;
    color: var(--slate);
    max-width: 520px;
    text-align: center;
    margin-top: 14px;
    opacity: 0;
    animation: fadeUp 0.5s ease 1.25s both;
}

@keyframes stampIn {
    0%   { opacity: 0; transform: scale(2.4) rotate(-3deg); }
    55%  { opacity: 1; }
    100% { opacity: 1; transform: scale(1) rotate(-3deg); }
}
@keyframes fadeUp {
    from { opacity: 0; transform: translateY(6px); }
    to   { opacity: 1; transform: translateY(0); }
}

/* Page-load reveal */
.reveal { opacity: 0; animation: feedIn 0.55s ease both; }
.reveal-1 { animation-delay: 0.02s; }
.reveal-2 { animation-delay: 0.20s; }
.reveal-3 { animation-delay: 0.42s; }

@keyframes feedIn {
    from { opacity: 0; transform: translateY(-8px); }
    to   { opacity: 1; transform: translateY(0); }
}

/* File uploader styling */
[data-testid="stFileUploader"] {
    background-color: #FFFFFF !important;
    border: 2px dashed #666666 !important;
    font-family: 'Arial', sans-serif !important;
}
[data-testid="stFileUploader"] * {
    color: #000000 !important;
    font-family: 'Arial', sans-serif !important;
}

/* Radio buttons in sidebar */
[data-testid="stSidebar"] .stRadio [role="radiogroup"] label {
    background-color: transparent !important;
    border: 1px solid #FFFFFF !important;
    font-family: 'Arial', sans-serif !important;
}
[data-testid="stSidebar"] .stRadio [role="radiogroup"] label:hover {
    background-color: #333333 !important;
}
</style>
"""


def inject_css():
    st.markdown(CUSTOM_CSS, unsafe_allow_html=True)


def _flatten_html(html: str) -> str:
    """
    Strips leading whitespace from every line of an HTML string.

    Markdown treats any line indented 4+ spaces as a literal code block,
    which disables HTML parsing for that block. Python's natural source
    indentation (especially inside nested loops/functions) easily produces
    4+ leading spaces, causing parts of the HTML to render as raw text
    instead of styled elements. Flattening indentation before passing the
    string to st.markdown avoids this.
    """
    return "\n".join(line.lstrip() for line in html.strip("\n").split("\n"))


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
    st.sidebar.markdown(
        "<div style='font-family:Arial, sans-serif; font-size:0.78rem; "
        "letter-spacing:0.03em; margin-bottom:10px;'>DATA SOURCE</div>",
        unsafe_allow_html=True,
    )
    source = st.sidebar.radio(
        "Choose a dataset",
        ["Built-in experiment", "Upload CSV"],
        label_visibility="collapsed",
    )

    if source == "Built-in experiment":
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
    
    # Validate data types and basic data quality
    try:
        df['user_id'] = df['user_id'].astype(str)
        df['signup_date'] = pd.to_datetime(df['signup_date'])
        df['variant'] = df['variant'].str.lower()
        
        # Validate variant values
        valid_variants = {'control', 'treatment'}
        if not set(df['variant'].unique()).issubset(valid_variants):
            st.error("Variant column should contain only 'control' and 'treatment' values")
            return None
            
        # Validate binary columns
        for col in ['day7_activated', 'retained_30d', 'had_support_ticket']:
            if not set(df[col].unique()).issubset({0, 1}):
                st.error(f"Column '{col}' should contain only 0 and 1 values")
                return None
    except Exception as e:
        st.error(f"Error validating data: {str(e)}")
        return None
    
    return df


# ---------------------------------------------------------------------------
# Report body
# ---------------------------------------------------------------------------

DECISION_META = {
    "SHIP": ("ship", "Ship"),
    "DO NOT SHIP": ("no-ship", "Do not ship"),
    "INCONCLUSIVE": ("inconclusive", "Inconclusive"),
}


def render_report_body(primary, guardrail_checks, recommendation):
    # Use black for positive lift, gray for negative in B&W theme
    lift_color = INK if primary.absolute_lift > 0 else SLATE

    guardrail_html = ""
    for check in guardrail_checks:
        status_class = "fail" if check["failed"] else "pass"
        status_text = "Fail" if check["failed"] else "Pass"
        guardrail_html += f"""
        <div class="guardrail-row">
            <span class="dot {status_class}"></span>
            <span><strong>{check['metric_name']}</strong> — {check['reason']}</span>
            <span class="guardrail-status">{status_text}</span>
        </div>"""

    stamp_class, stamp_label = DECISION_META[recommendation["decision"]]

    html = f"""
    <div class="reveal reveal-1">
        <div class="report-meta">Experiment read-out &middot; onboarding flow test</div>
        <h1 class="report-title">A/B Test Analysis</h1>
    </div>

    <div class="reveal reveal-2 metric-row">
        <div class="metric-block">
            <div class="metric-value">{primary.rate_control:.1%}</div>
            <div class="metric-label">Control &middot; n={primary.n_control:,}</div>
        </div>
        <div class="metric-arrow">&rarr;</div>
        <div class="metric-block">
            <div class="metric-value">{primary.rate_treatment:.1%}</div>
            <div class="metric-label">Treatment &middot; n={primary.n_treatment:,}</div>
        </div>
        <div class="metric-block">
            <div class="metric-value" style="color:{lift_color}">{primary.absolute_lift:+.1%}</div>
            <div class="metric-label">Absolute lift &middot; p={primary.p_value:.4f}</div>
        </div>
    </div>

    <div class="reveal reveal-3">
        <div class="section-label">Guardrail metrics</div>
        {guardrail_html}
    </div>

    <div class="stamp-wrap">
        <div class="stamp {stamp_class}">{stamp_label}</div>
        <div class="stamp-reason">{recommendation['reason']}</div>
    </div>
    """
    st.markdown(_flatten_html(html), unsafe_allow_html=True)


def render_trend_chart(df: pd.DataFrame):
    """
    Cumulative activation rate by variant over the test period, shown for
    illustration only -- the ship/no-ship decision is based on the
    pre-registered final sample, not on interim trends (see
    reports/pre_registration.md).
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

    fig = go.Figure()
    # Use different shades of gray/black for the chart to maintain B&W theme
    for variant, color in [("control", "#000000"), ("treatment", "#666666")]:
        sub = daily[daily["variant"] == variant]
        fig.add_trace(go.Scatter(
            x=sub["signup_date"],
            y=sub["cumulative_rate"],
            mode="lines",
            name=variant.capitalize(),
            line=dict(color=color, width=2.5),
        ))

    fig.update_layout(
        paper_bgcolor=PAPER,
        plot_bgcolor=PAPER,
        font=dict(family="Arial, sans-serif", color=INK, size=13),
        title=dict(
            text="Cumulative Day-7 activation rate over time", 
            font=dict(family="Arial, sans-serif", size=18, color=INK)
        ),
        legend=dict(
            orientation="h", 
            yanchor="bottom", 
            y=1.02, 
            xanchor="left", 
            x=0,
            font=dict(family="Arial, sans-serif", color=INK)
        ),
        margin=dict(t=60, l=10, r=10, b=10),
        yaxis=dict(
            tickformat=".0%", 
            gridcolor="rgba(0,0,0,0.10)", 
            zeroline=False,
            linecolor="black",
            linewidth=1,
            tickfont=dict(family="Arial, sans-serif", color=INK)
        ),
        xaxis=dict(
            gridcolor="rgba(0,0,0,0.10)",
            linecolor="black",
            linewidth=1,
            tickfont=dict(family="Arial, sans-serif", color=INK)
        ),
    )
    return fig


# ---------------------------------------------------------------------------
# Main app
# ---------------------------------------------------------------------------

def main():
    inject_css()

    df = load_data()
    if df is None:
        return

    try:
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

        # Create two columns: left for report, right for chart
        col_left, col_right = st.columns([1, 1], gap="large")
        
        # Left column: report body
        with col_left:
            render_report_body(primary, guardrail_checks, recommendation)
        
        # Right column: chart with some vertical spacing
        with col_right:
            st.markdown("<div style='margin-top: 100px;'></div>", unsafe_allow_html=True)
            fig = render_trend_chart(df)
            st.plotly_chart(fig, width="stretch")
            st.caption(
                "Shown for illustration of trend stability. Per the pre-registered "
                "decision rule, the ship/no-ship recommendation is based on the "
                "full, final sample only — not on interim trends."
            )
            
    except Exception as e:
        st.error(f"An error occurred during analysis: {str(e)}")
        st.info("Please check your data format and try again.")


if __name__ == "__main__":
    main()