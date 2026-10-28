# AirAware — Air Quality Intelligence Dashboard

A college Data Science & Analytics project for analysing historical PM2.5 observations across four Indian cities: **Mumbai, Nagpur, Nashik, and Pune**.

---

## Architecture

```
AirAware/
├── app.py                          # Streamlit entry point (preserved fallback)
├── pages/                          # Streamlit multi-page app
│   ├── 1_Overview.py
│   ├── 2_Historical_Analysis.py
│   ├── 3_Statistical_Insights.py
│   └── 4_Prediction.py
├── src/                            # Data processing, features, forecasting
│   ├── aggregate_city.py
│   ├── forecast.py
│   ├── features.py
│   ├── train_model.py
│   └── ui.py                       # Shared Streamlit helpers
├── backend/                        # FastAPI backend
│   ├── main.py                     # App factory, CORS, router registration
│   ├── data_loader.py              # CSV loading and validation
│   └── routers/
│       ├── meta.py                 # /meta/cities, /meta/date-range
│       ├── dashboard.py            # /dashboard/summary
│       ├── observations.py         # /observations/recent
│       ├── trends.py               # /trends/series, /trends/download
│       ├── statistics.py           # /statistics/overview
│       └── evaluation.py           # /evaluation/cities, /evaluation/{city}
├── frontend/                       # React + TypeScript + Vite + Tailwind
│   └── src/
│       ├── api.ts                  # Typed API client (single source of truth)
│       ├── Layout.tsx              # Sidebar navigation shell
│       ├── App.tsx                 # React Router routes
│       └── pages/
│           ├── Overview.tsx
│           ├── Trends.tsx
│           ├── Statistics.tsx
│           └── Evaluation.tsx
├── data/
│   └── processed/city_daily.csv   # Source dataset (1,988 records)
├── reports/
│   ├── forecast_metrics.csv        # Holdout evaluation metrics
│   └── forecast_predictions.csv   # Holdout actual vs predicted
└── tests/                          # pytest suite (149 tests)
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

Expected: **149 passed**.

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
| GET | `/evaluation/cities` | Cities with evaluation data |
| GET | `/evaluation/{city}` | Full model evaluation for one city |

All date parameters use inclusive `YYYY-MM-DD` bounds.

---

## Pages

| Page | Route | What it shows |
|------|-------|---------------|
| Overview | `/` | City + date filter · KPI cards · trend chart · city comparison · recent observations |
| Trends | `/trends` | Multi-city line chart · metric toggle · summary table · CSV download |
| Statistics | `/statistics` | Box plots · descriptive stats · coverage table · interpretation note |
| Evaluation | `/evaluation` | Model score cards · actual vs predicted chart · prediction records · CSV download |

---

## Dataset and model notes

- **Source dataset**: `data/processed/city_daily.csv` — 1,988 city-daily records, columns: `city`, `date`, `pm25_mean`, `station_count`, `coverage_pct`.
- **Date range**: 2025-02-19 to 2026-10-13.
- **PM2.5 values are reported in µg/m³** — not AQI.
- **Evaluation results** (`reports/forecast_metrics.csv`, `reports/forecast_predictions.csv`) represent **historical holdout performance** of Persistence and RandomForest models. They are not live forecasts and should not be interpreted as predictions of tomorrow's air quality.
- A negative R² means the model performed worse than simply predicting the test-set mean. This is displayed accurately and not hidden.
- Missing PM2.5 values are preserved as gaps in charts and excluded from aggregates.

---

## Limitations and remaining manual checks

1. **End-to-end browser test**: The frontend was verified to build and type-check correctly. Live API integration (all four pages loading real data, CSV downloads, filter behavior) requires manual verification in a browser with both servers running.
2. **Chunk size**: The production bundle is ~674 kB (gzip: ~199 kB). For a college demo this is acceptable; code-splitting could reduce it further if needed.
3. **No authentication**: This project is for academic demonstration only. Do not expose publicly without adding appropriate access controls.
