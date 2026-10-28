# AirAware — Air Quality Intelligence Dashboard

A college Data Science & Analytics project for analysing historical PM2.5 observations across four Indian cities: **Mumbai, Nagpur, Nashik, and Pune**. The primary application is a **React + FastAPI** stack with analytics, statistical insights, historical model evaluation, and **future PM2.5 forecasting**.

---

## Architecture

```
AirAware/
├── app.py                          # Streamlit entry point (preserved for reference)
├── pages/                          # Streamlit multi-page app (reference only)
│   ├── 1_Overview.py
│   ├── 2_Historical_Analysis.py
│   ├── 3_Statistical_Insights.py
│   └── 4_Prediction.py
├── src/                            # Data processing, features, evaluation
│   ├── aggregate_city.py
│   ├── forecast.py                 # Per-city RF evaluation (generates reports/)
│   ├── features.py                 # Feature engineering helpers
│   ├── train_model.py              # Global model trainer
│   └── ui.py                       # Shared Streamlit helpers
├── backend/                        # FastAPI backend (primary)
│   ├── main.py                     # App factory, CORS, router registration
│   ├── data_loader.py              # CSV loading and validation
│   ├── forecast_engine.py          # In-process RF training + iterative future forecasts
│   └── routers/
│       ├── meta.py                 # /meta/cities, /meta/date-range
│       ├── dashboard.py            # /dashboard/summary
│       ├── observations.py         # /observations/recent
│       ├── trends.py               # /trends/series, /trends/download
│       ├── statistics.py           # /statistics/overview
│       ├── evaluation.py           # /evaluation/cities, /evaluation/{city}
│       └── forecast.py             # /forecast/cities, /forecast/{city}, /forecast/{city}/download
├── frontend/                       # React + TypeScript + Vite + Tailwind (primary)
│   └── src/
│       ├── api.ts                  # Typed API client (single source of truth)
│       ├── Layout.tsx              # Sidebar navigation shell (5 pages)
│       ├── App.tsx                 # React Router routes
│       └── pages/
│           ├── Overview.tsx        # Dashboard KPIs + trend chart
│           ├── Trends.tsx          # Multi-city historical comparison
│           ├── Statistics.tsx      # Descriptive stats + box plots
│           ├── Evaluation.tsx      # Historical holdout model evaluation
│           └── Forecast.tsx        # Future 7/14-day RF forecast (new)
├── data/
│   └── processed/city_daily.csv   # Source dataset (1,988 records)
├── reports/
│   ├── forecast_metrics.csv        # Holdout evaluation metrics
│   └── forecast_predictions.csv   # Holdout actual vs predicted
└── tests/                          # pytest suite (202 tests)
    ├── test_dashboard.py
    ├── test_evaluation.py
    ├── test_features.py
    ├── test_forecast.py            # 53 tests for /forecast/* endpoints
    ├── test_observations.py
    ├── test_statistics.py
    └── test_trends.py
```

---

## Prerequisites

| Tool | Version tested |
|------|----------------|
| Python | 3.13 |
| Node.js | 24.x |
| npm | 11.x |

---

## Setup

### Python backend

```powershell
# From the project root
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

### React frontend

```powershell
cd frontend
npm install
```

---

## Running the application

### 1 — Start the FastAPI backend

Open a terminal in the project root with the virtual environment active:

```powershell
.venv\Scripts\Activate.ps1
python -m uvicorn backend.main:app --reload
```

The API will be available at `http://127.0.0.1:8000`.
Interactive docs: `http://127.0.0.1:8000/docs`

### 2 — Start the React frontend

Open a **second** terminal:

```powershell
cd frontend
.\node_modules\.bin\vite.ps1
```

> **Note:** Use `.\node_modules\.bin\vite.ps1` instead of `npm run dev` when your project path contains parentheses (e.g. `DSA (Data Science & Analytics)`), which can confuse the `.cmd` wrapper.

The frontend will be available at `http://localhost:5173`.

### 3 — (Optional) Streamlit fallback

The Streamlit app is preserved for reference only. New features are implemented in React + FastAPI.

```powershell
.venv\Scripts\Activate.ps1
python -m streamlit run app.py
```

---

## Running tests

```powershell
.venv\Scripts\Activate.ps1
python -m pytest tests/ -v
```

Expected: **202 passed** (149 existing + 53 forecast tests).

### TypeScript type check

```powershell
cd frontend
node node_modules/typescript/bin/tsc --noEmit
```

### Production build

```powershell
cd frontend
node node_modules/vite/bin/vite.js build
```

> **Note:** If your path contains parentheses, use `node ...` directly instead of `npm run build` to avoid shell escaping issues.

---

## API routes

| Method | Route | Description |
|--------|-------|-------------|
| GET | `/health` | Health check |
| GET | `/meta/cities` | List of available cities |
| GET | `/meta/date-range` | Dataset date range |
| GET | `/dashboard/summary` | Overview KPIs, trend series, city snapshot, recent rows |
| GET | `/observations/recent` | Filterable recent observations |
| GET | `/trends/series` | Multi-city time series for PM2.5 or station count |
| GET | `/trends/download` | Filtered dataset as CSV download |
| GET | `/statistics/overview` | Descriptive stats, box-plot data, coverage table |
| GET | `/evaluation/cities` | Cities with historical evaluation data |
| GET | `/evaluation/{city}` | Full holdout model evaluation for one city |
| GET | `/forecast/cities` | Cities available for future forecasting |
| GET | `/forecast/{city}?horizon=7` | 7 or 14-day future PM2.5 forecast + historical tail |
| GET | `/forecast/{city}/download?horizon=7` | Future forecast as CSV download |

All date parameters use inclusive `YYYY-MM-DD` bounds.

---

## Pages

| Page | Route | What it shows |
|------|-------|---------------|
| Overview | `/` | City + date filter · KPI cards · trend chart · city comparison · recent observations |
| Trends | `/trends` | Multi-city line chart · metric toggle · summary table · CSV download |
| Statistics | `/statistics` | Box plots · descriptive stats · coverage table · interpretation note |
| Evaluation | `/evaluation` | Historical holdout score cards · actual vs predicted chart · prediction records · CSV download |
| **Forecast** | `/forecast` | **City selector · 7/14-day RF forecast · combined chart · table · feature importance · CSV download** |

---

## Forecast page — how it works

The **Forecast page** (`/forecast`) provides genuine future PM2.5 predictions for each city:

1. **Training**: A RandomForest model is trained on **all available historical data** for the selected city (no test holdout — the holdout evaluation is on the separate Evaluation page).
2. **Features**: Today's PM2.5, lags at 1/2/3/7 days, 3-day rolling mean, 7-day rolling mean — identical to `src/forecast.py`.
3. **Iterative rollout**: Each future step is predicted using the model output from the previous step (no look-ahead into real observations).
4. **Output**: 7 or 14 daily predictions starting from `latest_observed_date + 1 day`.
5. **Caching**: Models are cached in-process and invalidated when new data is loaded.

### Forecast limitations

- RandomForest cannot extrapolate beyond its training distribution.
- Uncertainty grows with forecast horizon (no prediction intervals are returned).
- No meteorological inputs (wind speed, temperature, precipitation) are used.
- These estimates are for academic demonstration — not official AQI forecasts.

---

## Dataset and model notes

- **Source dataset**: `data/processed/city_daily.csv` — 1,988 city-daily records, columns: `city`, `date`, `pm25_mean`, `station_count`, `coverage_pct`.
- **Date range**: 2025-02-19 to 2026-10-13.
- **PM2.5 values are reported in µg/m³** — not AQI.
- **Evaluation results** (`reports/forecast_metrics.csv`, `reports/forecast_predictions.csv`) represent **historical holdout performance** of Persistence and RandomForest models. They are distinct from the Forecast page's future predictions and should not be interpreted as live forecasts.
- A negative R² on the Evaluation page means the model performed worse than predicting the test-set mean. This is displayed accurately and not hidden.
- Missing PM2.5 values are preserved as gaps in charts and excluded from aggregates.

### Chronological split (Evaluation page)
- Training: earliest 80% of samples per city.
- Testing: latest 20% of samples.
- No data leakage: rolling features reference only observations up to the forecast origin date.

### Model comparisons (Evaluation page)
| City | RF better than Persistence? |
|------|-----------------------------|
| Mumbai | ❌ No (RF MAE 22.2 vs Persistence 3.5) |
| Nagpur | ✅ Yes (RF MAE 4.3 vs Persistence 4.6) |
| Nashik | ❌ Marginally (RF MAE 4.2 vs Persistence 4.0) |
| Pune | ❌ No (RF MAE 5.0 vs Persistence 4.0) |

For Mumbai in particular, RandomForest performs dramatically worse than persistence, likely due to distributional shift between the training and test periods.

---

## Limitations

1. **End-to-end browser test**: The frontend builds and type-checks correctly. Live API integration requires manual verification in a browser with both servers running.
2. **Forecast model per city**: The Forecast page trains models on-demand (cached). The first request per city may take ~15–30 seconds.
3. **Chunk size**: The production bundle is ~703 kB gzip (205 kB). Code-splitting could reduce it further.
4. **No authentication**: Academic demonstration only. Do not expose publicly without access controls.
