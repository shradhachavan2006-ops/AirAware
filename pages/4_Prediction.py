import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from src.ui import apply_theme, chart_layout, load_forecast_data, page_header, require_data

st.set_page_config(page_title="AirAware | Forecast Evaluation", page_icon="🌿", layout="wide")
apply_theme()
city_data = require_data()
page_header("MODEL EVALUATION", "Forecasts under the microscope", "Review historical test-set performance for next-day PM2.5 models. These are retrospective predictions, not live forecasts.")
metrics, predictions = load_forecast_data()
required_metrics = {"city", "model", "MAE", "RMSE", "R2"}
required_predictions = {"city", "model", "date", "actual_pm25", "predicted_pm25"}
if metrics.empty or predictions.empty:
    st.warning("Forecast reports are missing. Run `python -m src.forecast` from the project folder to generate them.")
    st.stop()
if not required_metrics.issubset(metrics.columns) or not required_predictions.issubset(predictions.columns):
    st.error("Forecast report columns do not match the expected schema. Please regenerate the reports.")
    st.stop()
metrics["city"] = metrics["city"].astype(str)
predictions["city"] = predictions["city"].astype(str)
predictions["date"] = pd.to_datetime(predictions["date"], errors="coerce")
cities = sorted(set(metrics["city"].dropna()) & set(predictions["city"].dropna()))
if not cities:
    st.info("No cities have both metrics and prediction records.")
    st.stop()
city = st.selectbox("Choose evaluation city", cities, index=cities.index("Pune") if "Pune" in cities else 0)
city_metrics = metrics[metrics["city"] == city].copy()
city_predictions = predictions[predictions["city"] == city].copy()
if city_metrics.empty or city_predictions.empty:
    st.info("No evaluation results are available for this city.")
    st.stop()

if {"test_start_date", "test_end_date", "test_samples"}.issubset(city_metrics.columns):
    starts = pd.to_datetime(city_metrics["test_start_date"], errors="coerce").dropna()
    ends = pd.to_datetime(city_metrics["test_end_date"], errors="coerce").dropna()
    samples = pd.to_numeric(city_metrics["test_samples"], errors="coerce").max()
    if not starts.empty and not ends.empty:
        st.caption(f"Test window: {starts.min():%d %b %Y} – {ends.max():%d %b %Y} · Up to {int(samples)} samples per model")

preferred = {"Persistence": 0, "RandomForest": 1}
city_metrics["_sort"] = city_metrics["model"].map(preferred).fillna(99)
city_metrics = city_metrics.sort_values("_sort")
st.markdown("### Model scorecard")
cols = st.columns(max(1, len(city_metrics)))
for col, (_, row) in zip(cols, city_metrics.iterrows()):
    with col:
        st.metric(f"{row['model']} · MAE", f"{row['MAE']:.2f} µg/m³" if pd.notna(row["MAE"]) else "—")
        st.caption(f"RMSE {row['RMSE']:.2f} µg/m³" if pd.notna(row["RMSE"]) else "RMSE unavailable")
        st.caption(f"R² {row['R2']:.3f}" if pd.notna(row["R2"]) else "R² unavailable")

st.markdown("### Performance comparison")
show_metrics = city_metrics.drop(columns="_sort").copy()
st.dataframe(show_metrics.round(3), use_container_width=True, hide_index=True)
chart_data = city_predictions.dropna(subset=["date", "actual_pm25", "predicted_pm25"]).copy()
if chart_data.empty:
    st.info("No valid prediction records are available to plot.")
else:
    st.markdown("### Actual vs predicted PM2.5")
    fig = go.Figure()
    actual = chart_data.sort_values("date").drop_duplicates(subset=["date"])
    fig.add_trace(go.Scatter(x=actual["date"], y=actual["actual_pm25"], mode="lines", name="Actual", line=dict(width=3, color="#14532d")))
    palette = {"Persistence":"#16a36a", "RandomForest":"#e69b48"}
    for model_name in chart_data["model"].dropna().unique():
        md = chart_data[chart_data["model"] == model_name].sort_values("date")
        fig.add_trace(go.Scatter(x=md["date"], y=md["predicted_pm25"], mode="lines", name=f"{model_name} prediction", line=dict(width=2, color=palette.get(model_name, "#6488c6"))))
    fig.update_layout(xaxis_title="Test date", yaxis_title="PM2.5 (µg/m³)", hovermode="x unified")
    st.plotly_chart(chart_layout(fig, 450), use_container_width=True)

st.markdown("### Inspect prediction records")
model_names = sorted(city_predictions["model"].dropna().unique())
selected_model = st.selectbox("Model records", model_names)
table = city_predictions[city_predictions["model"] == selected_model].sort_values("date", ascending=False)
st.dataframe(table.round(3), use_container_width=True, hide_index=True)
st.download_button("Download evaluation records", data=table.to_csv(index=False).encode("utf-8"), file_name=f"{city.lower()}_{selected_model.lower()}_evaluation.csv", mime="text/csv")

# Show a useful warning when a model performs worse than the baseline.
pivot = city_metrics.set_index("model")
if "Persistence" in pivot.index and "RandomForest" in pivot.index and pd.notna(pivot.loc["Persistence", "MAE"]) and pd.notna(pivot.loc["RandomForest", "MAE"]):
    if pivot.loc["RandomForest", "MAE"] > pivot.loc["Persistence", "MAE"]:
        st.warning("For this city's saved test set, Random Forest has a higher MAE than the persistence baseline. Do not assume the more complex model is better; investigate feature quality and generalization.")
with st.container(border=True):
    st.markdown("**Important interpretation note**")
    st.write("MAE and RMSE are error measures, so lower is better. R² can be negative when a model performs worse than predicting the test-set mean. These results come from a historical holdout period and do not represent tomorrow's live forecast or an official AQI forecast.")
