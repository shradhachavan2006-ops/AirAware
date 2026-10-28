
"""Shared presentation helpers for the AirAware Streamlit dashboard."""

from pathlib import Path

import pandas as pd
import streamlit as st


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_PATH = PROJECT_ROOT / "data" / "processed" / "city_daily.csv"
METRICS_PATH = PROJECT_ROOT / "reports" / "forecast_metrics.csv"
PREDICTIONS_PATH = PROJECT_ROOT / "reports" / "forecast_predictions.csv"


def apply_theme() -> None:
    """Apply the AirAware visual theme without hiding Streamlit navigation."""

    st.markdown(
        """
        <style>
        @import url(
            'https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&'
            'family=Manrope:wght@500;600;700;800&display=swap'
        );

        :root {
            --forest: #14532d;
            --green: #16a36a;
            --mint: #e8f7ef;
            --ink: #172b25;
            --muted: #65756f;
        }

        html, body, [class*="css"] {
            font-family: 'DM Sans', sans-serif;
        }

        .stApp {
            background: linear-gradient(
                180deg, #f7fbf8 0%, #f5f8f7 100%
            );
            color: var(--ink);
        }

        [data-testid="stHeader"] {
            background: rgba(247, 251, 248, 0.92);
        }

        /* Sidebar: style it, but do not force its collapsed state open. */
        [data-testid="stSidebar"] {
            background: #102f25 !important;
            border-right: 1px solid rgba(255, 255, 255, 0.08);
        }

        [data-testid="stSidebar"] > div {
            background: #102f25 !important;
        }

        [data-testid="stSidebar"] * {
            color: #eef8f1;
        }

        [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p {
            color: #c4d9ce;
        }

        [data-testid="stSidebar"] hr {
            border-color: rgba(255, 255, 255, 0.16);
        }

        /* Keep Streamlit's sidebar expand/collapse control accessible. */
        [data-testid="stSidebarCollapsedControl"] {
            display: flex !important;
            visibility: visible !important;
            opacity: 1 !important;
            pointer-events: auto !important;
        }

        h1, h2, h3 {
            font-family: 'Manrope', 'DM Sans', sans-serif !important;
            letter-spacing: -0.035em;
            color: #163b2b;
        }

        h1 {
            font-weight: 800 !important;
        }

        h2 {
            font-weight: 750 !important;
        }

        [data-testid="stMetric"] {
            background: #fff;
            border: 1px solid #e1ece5;
            padding: 18px 20px;
            border-radius: 18px;
            box-shadow: 0 5px 18px rgba(25, 65, 45, 0.045);
            min-height: 124px;
        }

        [data-testid="stMetricLabel"] {
            color: #64766d !important;
            font-size: 0.86rem !important;
            font-weight: 600 !important;
        }

        [data-testid="stMetricValue"] {
            color: #164c31 !important;
            font-family: 'Manrope', sans-serif;
            font-weight: 800;
        }

        [data-testid="stMetricDelta"] {
            font-size: 0.78rem !important;
        }

        [data-testid="stVerticalBlockBorderWrapper"] {
            border-radius: 18px;
            border-color: #e0ebe4;
            background: #fff;
        }

        div[data-testid="stPlotlyChart"] {
            background: #fff;
            border: 1px solid #e4ede7;
            border-radius: 18px;
            padding: 8px 8px 0;
        }

        div[data-testid="stDataFrame"] {
            border: 1px solid #e0ebe4;
            border-radius: 14px;
            overflow: hidden;
        }

        .hero {
            padding: 28px 30px;
            border-radius: 22px;
            background: linear-gradient(
                115deg, #103d2a 0%, #176442 64%, #21865b 100%
            );
            color: white;
            margin: 4px 0 24px;
            box-shadow: 0 12px 30px rgba(20, 83, 45, 0.13);
        }

        .hero h1 {
            color: white !important;
            font-size: 2.1rem !important;
            margin: 0 0 8px 0;
        }

        .hero p {
            color: #d8eee1;
            margin: 0;
            font-size: 1rem;
        }

        .eyebrow {
            text-transform: uppercase;
            letter-spacing: 0.15em;
            font-size: 0.72rem;
            font-weight: 700;
            color: #7acba1;
            margin-bottom: 10px;
        }

        .section-note {
            color: #718078;
            font-size: 0.9rem;
            margin-top: -8px;
        }

        .pill {
            display: inline-block;
            background: #e7f7ed;
            color: #17633c;
            padding: 5px 10px;
            border-radius: 999px;
            font-size: 0.75rem;
            font-weight: 700;
        }

        .small-muted {
            color: #74827b;
            font-size: 0.82rem;
        }

        .stButton > button,
        .stDownloadButton > button {
            border-radius: 10px;
            border: 1px solid #c9dfd1;
            font-weight: 700;
        }

        @media (max-width: 768px) {
            .hero {
                padding: 22px;
            }

            .hero h1 {
                font-size: 1.65rem !important;
            }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


@st.cache_data(show_spinner=False)
def load_city_data() -> pd.DataFrame:
    """Load and validate the processed city-level daily dataset."""

    if not DATA_PATH.exists():
        return pd.DataFrame()

    df = pd.read_csv(DATA_PATH)

    required = {"city", "date", "pm25_mean"}
    if not required.issubset(df.columns):
        return pd.DataFrame()

    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df["pm25_mean"] = pd.to_numeric(
        df["pm25_mean"], errors="coerce"
    )

    if "station_count" not in df.columns:
        df["station_count"] = pd.NA

    if "coverage_pct" not in df.columns:
        df["coverage_pct"] = pd.NA

    df = df.dropna(
        subset=["city", "date", "pm25_mean"]
    ).sort_values(["city", "date"])

    return df


def load_forecast_data():
    """Load saved forecast metrics and predictions if available."""

    metrics = (
        pd.read_csv(METRICS_PATH)
        if METRICS_PATH.exists()
        else pd.DataFrame()
    )

    predictions = (
        pd.read_csv(PREDICTIONS_PATH)
        if PREDICTIONS_PATH.exists()
        else pd.DataFrame()
    )

    if not predictions.empty and "date" in predictions.columns:
        predictions["date"] = pd.to_datetime(
            predictions["date"], errors="coerce"
        )

    return metrics, predictions


def page_header(kicker: str, title: str, subtitle: str) -> None:
    """Render the shared page hero."""

    st.markdown(
        f"""
        <div class="hero">
            <div class="eyebrow">{kicker}</div>
            <h1>{title}</h1>
            <p>{subtitle}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def chart_layout(fig, height: int = 390):
    """Apply consistent formatting to Plotly charts."""

    fig.update_layout(
        template="plotly_white",
        height=height,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(
            family="DM Sans, sans-serif",
            color="#53645b",
            size=12,
        ),
        margin=dict(l=18, r=18, t=48, b=18),
        title=dict(
            font=dict(
                family="Manrope, sans-serif",
                size=16,
                color="#183d2b",
            ),
            x=0.02,
        ),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1,
        ),
        hoverlabel=dict(
            bgcolor="#143c2b",
            font_color="white",
        ),
    )

    fig.update_xaxes(
        showgrid=False,
        linecolor="#e3ece6",
        zeroline=False,
    )

    fig.update_yaxes(
        gridcolor="#edf2ee",
        zeroline=False,
        title_font_color="#718078",
    )

    return fig


def require_data() -> pd.DataFrame:
    """Stop with a helpful message if the dataset is unavailable."""

    df = load_city_data()

    if df.empty:
        st.error(
            "AirAware could not load a valid processed dataset."
        )
        st.markdown(
            f"Expected file: `{DATA_PATH.relative_to(PROJECT_ROOT)}`"
        )
        st.info(
            "From the project folder, run "
            "`python -m src.aggregate_city` after checking "
            "the raw observations."
        )
        st.stop()

    return df
