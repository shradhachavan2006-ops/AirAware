import pandas as pd
import plotly.express as px
import streamlit as st
from src.ui import apply_theme, chart_layout, page_header, require_data

st.set_page_config(page_title="AirAware | Overview", page_icon="🌿", layout="wide")
apply_theme()
df = require_data()
page_header("THE BIG PICTURE", "A clearer view of city air.", "A quick summary of the data coverage and average PM2.5 levels in the included cities.")
valid = df.dropna(subset=["pm25_mean"])
a, b, c, d = st.columns(4)
a.metric("Cities covered", f"{df['city'].nunique():,}")
b.metric("Valid city-days", f"{len(valid):,}")
c.metric("First date", f"{df['date'].min():%d %b %Y}")
d.metric("Latest date", f"{df['date'].max():%d %b %Y}")
summary = valid.groupby("city", as_index=False).agg(days=("pm25_mean", "count"), mean_pm25=("pm25_mean", "mean"), max_pm25=("pm25_mean", "max"), stations_mean=("station_count", "mean"))
left, right = st.columns([1.2, 1])
with left:
    st.markdown("### Average PM2.5 by city")
    fig = px.bar(summary.sort_values("mean_pm25"), x="mean_pm25", y="city", orientation="h", text="mean_pm25", color="mean_pm25", color_continuous_scale=["#bdebd0", "#168553", "#14532d"])
    fig.update_traces(texttemplate="%{text:.1f}", textposition="outside", cliponaxis=False)
    fig.update_layout(xaxis_title="Average PM2.5 (µg/m³)", yaxis_title="", coloraxis_showscale=False)
    st.plotly_chart(chart_layout(fig), use_container_width=True)
with right:
    st.markdown("### Coverage by city")
    st.dataframe(summary.rename(columns={"city":"City", "days":"Valid days", "mean_pm25":"Mean PM2.5", "max_pm25":"Maximum PM2.5", "stations_mean":"Mean stations"}).round(2), use_container_width=True, hide_index=True)
st.caption("City averages are calculated from available daily values. Differences in date coverage and station availability should be considered when interpreting rankings.")
