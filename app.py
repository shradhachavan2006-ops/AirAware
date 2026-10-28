from pathlib import Path
import pandas as pd
import plotly.express as px
import streamlit as st
from src.ui import apply_theme, chart_layout, page_header, require_data

st.set_page_config(page_title="AirAware | Air Quality Intelligence", page_icon="🌿", layout="wide", initial_sidebar_state="expanded")
st.sidebar.title("🌿 AirAware")
st.sidebar.write("Navigation test")
apply_theme()
df = require_data()

with st.sidebar:
    st.markdown("# 🌿 AirAware")
    st.markdown("**Understand the air. Predict tomorrow.**")
    st.divider()
    st.markdown("### Your dashboard")
    st.markdown("Use the pages above to explore trends, compare cities, inspect statistics, and review model evaluation.")
    st.divider()
    st.markdown("**Data source**")
    st.caption("Processed city-level daily PM2.5 observations included with this project.")
    st.caption(f"Latest available date: {df['date'].max():%d %b %Y}")

page_header("ENVIRONMENTAL INTELLIGENCE · INDIA", "Air quality, made clearer.", "Explore daily PM2.5 patterns across Indian cities and understand what the data can—and cannot—tell us.")

cities = sorted(df["city"].dropna().unique())
filter_col, date_col = st.columns([1, 2])
with filter_col:
    city = st.selectbox("Focus city", cities, index=cities.index("Pune") if "Pune" in cities else 0)
with date_col:
    min_date, max_date = df["date"].min().date(), df["date"].max().date()
    date_range = st.date_input("Analysis period", value=(min_date, max_date), min_value=min_date, max_value=max_date)
if isinstance(date_range, (tuple, list)) and len(date_range) == 2:
    start, end = pd.Timestamp(date_range[0]), pd.Timestamp(date_range[1])
else:
    start = end = pd.Timestamp(date_range)
period_df = df[df["date"].between(start, end)].copy()
city_df = period_df[period_df["city"] == city].sort_values("date")
valid = city_df.dropna(subset=["pm25_mean"])
all_valid = period_df.dropna(subset=["pm25_mean"])
latest = valid.iloc[-1] if not valid.empty else None

st.markdown("### At a glance")
k1, k2, k3, k4 = st.columns(4)
k1.metric("Latest PM2.5", f"{latest['pm25_mean']:.1f} µg/m³" if latest is not None else "—", help="Latest available daily city average inside the selected period.")
k2.metric("Period average", f"{valid['pm25_mean'].mean():.1f} µg/m³" if not valid.empty else "—")
k3.metric("Peak observed", f"{valid['pm25_mean'].max():.1f} µg/m³" if not valid.empty else "—")
k4.metric("Valid city-days", f"{len(valid):,}", help="Number of dates with a non-missing PM2.5 value for the selected city.")
if latest is not None:
    st.caption(f"{city} · latest observation in this selection: {latest['date']:%d %b %Y}. Values represent PM2.5 concentration, not AQI.")

left, right = st.columns([1.55, 1])
with left:
    st.markdown("### Daily pollution trend")
    st.markdown('<div class="section-note">Daily city average with a 7-day rolling mean where enough data exists.</div>', unsafe_allow_html=True)
    if city_df.empty or city_df["pm25_mean"].notna().sum() == 0:
        st.info("No valid PM2.5 observations for this city and period.")
    else:
        chart_df = city_df.copy()
        chart_df["7-day rolling mean"] = chart_df["pm25_mean"].rolling(7, min_periods=3).mean()
        import plotly.graph_objects as go
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=chart_df["date"], y=chart_df["pm25_mean"], mode="lines", name="Daily PM2.5", line=dict(color="#16a36a", width=2), connectgaps=False))
        fig.add_trace(go.Scatter(x=chart_df["date"], y=chart_df["7-day rolling mean"], mode="lines", name="7-day rolling mean", line=dict(color="#14532d", width=3), connectgaps=False))
        fig.update_layout(yaxis_title="PM2.5 (µg/m³)", xaxis_title="Date", hovermode="x unified")
        st.plotly_chart(chart_layout(fig, 390), use_container_width=True)
with right:
    st.markdown("### City snapshot")
    city_summary = all_valid.groupby("city", as_index=False).agg(average_pm25=("pm25_mean", "mean"), valid_days=("pm25_mean", "count"))
    city_summary = city_summary.sort_values("average_pm25", ascending=False)
    if city_summary.empty:
        st.info("No valid city data in this period.")
    else:
        fig = px.bar(city_summary, x="average_pm25", y="city", orientation="h", text="average_pm25", color="average_pm25", color_continuous_scale=["#bdebd0", "#168553", "#14532d"])
        fig.update_traces(texttemplate="%{text:.1f}", textposition="outside", cliponaxis=False)
        fig.update_layout(xaxis_title="Average PM2.5 (µg/m³)", yaxis_title="", coloraxis_showscale=False, yaxis={"categoryorder":"total ascending"})
        st.plotly_chart(chart_layout(fig, 390), use_container_width=True)
        top = city_summary.iloc[0]
        st.caption(f"Highest average in this selected period: **{top['city']}** ({top['average_pm25']:.1f} µg/m³). This is a comparison of available observations, not a population exposure estimate.")

st.markdown("### Recent observations")
if city_df.empty:
    st.info("No rows available for this selection.")
else:
    display_cols = [c for c in ["date", "city", "pm25_mean", "station_count", "coverage_pct"] if c in city_df.columns]
    recent = city_df[display_cols].sort_values("date", ascending=False).head(12).copy()
    recent["date"] = recent["date"].dt.strftime("%d %b %Y")
    st.dataframe(recent, use_container_width=True, hide_index=True, column_config={"pm25_mean": st.column_config.NumberColumn("PM2.5 (µg/m³)", format="%.2f"), "station_count": st.column_config.NumberColumn("Stations", format="%d"), "coverage_pct": st.column_config.NumberColumn("Coverage (%)", format="%.1f%%")})

st.markdown("### Read this data responsibly")
with st.container(border=True):
    a, b, c = st.columns(3)
    a.markdown("**Concentration, not AQI**")
    a.caption("PM2.5 is reported in µg/m³. It should not be interpreted as an AQI score.")
    b.markdown("**Coverage can vary**")
    b.caption("Missing dates and different station counts can affect comparisons between cities.")
    c.markdown("**Analytics, not medical advice**")
    c.caption("Historical patterns and model estimates are not official forecasts or health guidance.")
