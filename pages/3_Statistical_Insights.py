import pandas as pd
import plotly.express as px
import streamlit as st
from src.ui import apply_theme, chart_layout, page_header, require_data

st.set_page_config(page_title="AirAware | Statistical Insights", page_icon="🌿", layout="wide")
apply_theme()
df = require_data()
page_header("DATA-DRIVEN DISCOVERY", "What the numbers reveal", "Explore distributions, variability, and data quality without losing sight of coverage limitations.")
valid = df.dropna(subset=["pm25_mean"]).copy()
if valid.empty:
    st.warning("There are no valid PM2.5 values to analyze.")
    st.stop()
city_summary = valid.groupby("city", as_index=False).agg(mean=("pm25_mean", "mean"), median=("pm25_mean", "median"), std=("pm25_mean", "std"), maximum=("pm25_mean", "max"), days=("pm25_mean", "count"))
most_variable = city_summary.sort_values("std", ascending=False).iloc[0]
highest = city_summary.sort_values("mean", ascending=False).iloc[0]
a, b, c = st.columns(3)
a.metric("Highest city average", str(highest["city"]), f"{highest['mean']:.1f} µg/m³")
b.metric("Most variable city", str(most_variable["city"]), f"Std. dev. {most_variable['std']:.1f}")
c.metric("Valid measurements", f"{len(valid):,}")
left, right = st.columns([1.1, 1])
with left:
    st.markdown("### Distribution by city")
    fig = px.box(valid, x="city", y="pm25_mean", color="city", points="outliers", labels={"city":"City", "pm25_mean":"PM2.5 (µg/m³)"})
    fig.update_layout(showlegend=False)
    st.plotly_chart(chart_layout(fig, 420), use_container_width=True)
with right:
    st.markdown("### Descriptive statistics")
    st.dataframe(city_summary.rename(columns={"city":"City", "mean":"Mean", "median":"Median", "std":"Std. dev.", "maximum":"Maximum", "days":"Valid days"}).round(2), use_container_width=True, hide_index=True)

st.markdown("### Data coverage and gaps")
coverage = df.groupby("city").agg(first_date=("date", "min"), last_date=("date", "max"), available_rows=("date", "count"), valid_pm25_days=("pm25_mean", "count"), avg_station_count=("station_count", "mean")).reset_index()
coverage["missing_pm25_rows"] = coverage["available_rows"] - coverage["valid_pm25_days"]
coverage = coverage.rename(columns={"city":"City", "first_date":"First date", "last_date":"Last date", "available_rows":"Rows", "valid_pm25_days":"Valid PM2.5 days", "avg_station_count":"Average stations", "missing_pm25_rows":"Missing PM2.5"})
st.dataframe(coverage, use_container_width=True, hide_index=True, column_config={"First date":st.column_config.DateColumn(format="DD MMM YYYY"), "Last date":st.column_config.DateColumn(format="DD MMM YYYY"), "Average stations":st.column_config.NumberColumn(format="%.2f")})
with st.expander("How to interpret these results"):
    st.write("The mean can be influenced by unusually high values; the median is more robust to extremes. Standard deviation describes variability, not whether a city is safe or unsafe. City-level station averages are not population-weighted exposure estimates. Different date coverage can affect direct comparisons.")
