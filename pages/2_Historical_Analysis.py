import pandas as pd
import plotly.express as px
import streamlit as st
from src.ui import apply_theme, chart_layout, page_header, require_data

st.set_page_config(page_title="AirAware | Historical Trends", page_icon="🌿", layout="wide")
apply_theme()
df = require_data()
page_header("EXPLORE THE PAST", "Historical pollution trends", "Compare daily PM2.5 patterns and station coverage over a time period of your choice.")
cities = sorted(df["city"].dropna().unique())
with st.container(border=True):
    c1, c2, c3 = st.columns([1.3, 1, 1])
    selected = c1.multiselect("Cities to compare", cities, default=cities)
    min_date, max_date = df["date"].min().date(), df["date"].max().date()
    dates = c2.date_input("Start date", value=min_date, min_value=min_date, max_value=max_date)
    end_date = c3.date_input("End date", value=max_date, min_value=min_date, max_value=max_date)
if dates > end_date:
    st.warning("Start date must be on or before end date.")
    st.stop()
d = df[df["city"].isin(selected) & df["date"].between(pd.Timestamp(dates), pd.Timestamp(end_date))].copy()
metric_label = st.radio("View metric", ["PM2.5 concentration", "Station count"], horizontal=True)
metric = "pm25_mean" if metric_label == "PM2.5 concentration" else "station_count"
if d.empty or d[metric].notna().sum() == 0:
    st.info("No observations match these filters. Select a different city or date range.")
else:
    fig = px.line(d, x="date", y=metric, color="city", title=f"{metric_label} over time", labels={"date":"Date", "pm25_mean":"PM2.5 (µg/m³)", "station_count":"Stations", "city":"City"})
    fig.update_traces(line=dict(width=2.2), connectgaps=False)
    fig.update_layout(hovermode="x unified")
    st.plotly_chart(chart_layout(fig, 460), use_container_width=True)
    st.markdown("### Summary for selected period")
    summary = d.groupby("city", as_index=False).agg(observed_days=(metric, "count"), average=(metric, "mean"), maximum=(metric, "max"))
    st.dataframe(summary.round(2), use_container_width=True, hide_index=True)
    st.download_button("Download filtered data (CSV)", d.to_csv(index=False).encode("utf-8"), "airaware_filtered_history.csv", "text/csv")
st.caption("Missing observations are left missing and are not treated as zero pollution.")
