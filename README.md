# AirAware — Air Quality Intelligence Dashboard

AirAware is a Streamlit dashboard for exploring city-level daily PM2.5 observations and reviewing historical next-day forecasting model evaluations. The project uses Python, Pandas, Plotly, and scikit-learn.

## What is included

- **Overview dashboard:** KPI cards, daily PM2.5 trend, rolling average, city comparison, and recent observations.
- **Overview page:** city coverage summary and average PM2.5 comparisons.
- **Historical analysis:** filter cities and dates, compare PM2.5 or station counts, and export filtered data.
- **Statistical insights:** distributions, descriptive statistics, and coverage summaries.
- **Forecast evaluation:** saved test-set MAE/RMSE/R², actual-vs-predicted charts, record inspection, and CSV download.
- **Data processing and model code:** cleaning, city-day aggregation, feature engineering, and chronological model evaluation.

## Run on Windows

Open Command Prompt or PowerShell in the `AirAware` project folder and run:

```powershell
python -m venv .venv
.venv\Scripts\activate
python -m pip install -r requirements.txt
streamlit run app.py
```

The dashboard opens in your browser. Use the multipage navigation in the sidebar to visit Historical Analysis, Statistical Insights, and Forecast Evaluation.

## Data files

The dashboard reads `data/processed/city_daily.csv`, which should contain `city`, `date`, and `pm25_mean`. It also supports `station_count` and `coverage_pct` when those columns are present. The supplied processed dataset and forecast reports are retained in this package.

To rebuild city-day aggregates from the raw observations, run:

```powershell
python -m src.aggregate_city
```

To regenerate the saved model evaluation reports, run:

```powershell
python -m src.forecast
```

Check the scripts and your data before rerunning processing so that your source observations and preprocessing decisions remain documented.

## Interpreting the results

- PM2.5 values are concentrations in **µg/m³**, not AQI values.
- A city-level average of monitoring stations is not necessarily a population-weighted exposure estimate.
- Missing dates represent unavailable observations; they must not be interpreted as zero pollution.
- Forecast Evaluation displays historical test-set predictions, not a live prediction for tomorrow. MAE and RMSE are errors (lower is better); R² can be negative.
- Differences in station counts and date coverage can affect comparisons between cities.
- This dashboard is for educational analysis and is not official AQI guidance or medical advice.

## Tests

Run the feature-engineering tests from the project folder:

```powershell
pytest tests
```

`src/sample_daily_api.py` is an optional manual OpenAQ API sample script. It requires an `OPENAQ_API_KEY` environment variable and is not part of the automated test suite.
