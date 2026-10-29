# AirAware V2 — Air Quality Analytics & Forecasting Platform

A college Data Science & Analytics project for analysing, statistically testing, and forecasting PM2.5 air quality data across Indian cities. The platform is a **React + FastAPI** full-stack web application supporting built-in demo datasets (Mumbai, Nagpur, Nashik, Pune) **and user-uploaded custom CSV datasets**.

---

## Architecture

```
AirAware/
├── backend/                        # FastAPI backend
│   ├── main.py                     # App factory, CORS, router registration
│   ├── data_loader.py              # CSV loading for legacy city_daily.csv
│   ├── dataset_store.py            # V2 dataset registry (demos + uploads)
│   ├── forecast_engine.py          # In-process RF training + iterative forecasts
│   └── routers/
│       ├── meta.py                 # /meta/cities, /meta/date-range
│       ├── dashboard.py            # /dashboard/summary
│       ├── observations.py         # /observations/recent
│       ├── trends.py               # /trends/series, /trends/download
│       ├── statistics.py           # /statistics/overview (legacy box-plots)
│       ├── evaluation.py           # /evaluation/{city}
│       ├── forecast.py             # /forecast/{city}
│       ├── datasets.py             # /datasets — CRUD, upload, preview
│       ├── quality.py              # /quality/{dataset_id} — profiling + cleaned CSV
│       ├── stat_analysis.py        # /analysis/{dataset_id}/statistics
│       └── regression.py           # /analysis/{dataset_id}/regression
├── frontend/                       # React + TypeScript + Vite + Tailwind
│   └── src/
│       ├── api.ts                  # Typed API client (single source of truth)
│       ├── Layout.tsx              # Sidebar navigation shell (10 pages)
│       ├── App.tsx                 # React Router routes
│       ├── context/
│       │   └── DatasetContext.tsx  # Global active-dataset context (localStorage)
│       └── pages/
│           ├── Overview.tsx        # Dashboard KPIs + trend chart
│           ├── Trends.tsx          # Multi-city historical comparison
│           ├── Statistics.tsx      # Descriptive stats + box plots (legacy)
│           ├── Evaluation.tsx      # Historical holdout model evaluation
│           ├── Forecast.tsx        # Future 7/14-day RF forecast
│           ├── DatasetManager.tsx  # Upload / switch / delete datasets
│           ├── DataQuality.tsx     # Automated quality profiling report
│           ├── StatAnalysis.tsx    # Hypothesis testing + inferential stats
│           ├── Regression.tsx      # Correlation, SLR, MLR studio
│           └── Methodology.tsx     # CRISP-DM, assumptions, ethics
├── data/
│   ├── demo/                       # Built-in demo CSVs (4 cities)
│   ├── processed/city_daily.csv    # Legacy source dataset (1,988 records)
│   └── uploads/                    # User-uploaded CSVs (persisted; gitignored)
├── reports/
│   ├── forecast_metrics.csv
│   └── forecast_predictions.csv
├── tests/                          # pytest suite (228 tests)
│   ├── test_dashboard.py
│   ├── test_dataset_store.py       # V2: dataset store unit tests
│   ├── test_datasets_router.py     # V2: /datasets endpoints
│   ├── test_evaluation.py
│   ├── test_features.py
│   ├── test_forecast.py
│   ├── test_observations.py
│   ├── test_quality_router.py      # V2: /quality endpoints
│   ├── test_regression_router.py   # V2: /analysis/*/regression
│   ├── test_stat_analysis_router.py# V2: /analysis/*/statistics
│   ├── test_statistics.py
│   └── test_trends.py
├── requirements.txt
└── README.md
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
# From AirAware_Improved/ (project root containing .venv/)
.venv\Scripts\Activate.ps1
python -m pip install -r AirAware/requirements.txt
pip install httpx      # required for FastAPI TestClient
```

### React frontend

```powershell
cd AirAware\frontend
npm install
```

---

## Running the application

### 1 — Start the FastAPI backend

Open a terminal in `AirAware_Improved\AirAware\` with the virtual environment active:

```powershell
..\..\.venv\Scripts\Activate.ps1
python -m uvicorn backend.main:app --reload
```

The API will be available at `http://127.0.0.1:8000`.  
Interactive docs: `http://127.0.0.1:8000/docs`

### 2 — Start the React frontend

Open a **second** terminal in `AirAware_Improved\AirAware\frontend\`:

```powershell
node .\node_modules\vite\bin\vite.js
```

> **Note:** Use `node .\node_modules\vite\bin\vite.js` instead of `npm run dev` when your project path contains parentheses (e.g. `DSA (Data Science & Analytics)`), which can confuse the `.cmd` wrapper.

The frontend will be available at `http://localhost:5173`.

---

## Running tests

```powershell
# From AirAware_Improved\AirAware\
..\.venv\Scripts\python -m pytest
```

Expected: **228 passed** (202 existing + 26 V2 tests).

### TypeScript type check

```powershell
cd frontend
node .\node_modules\typescript\bin\tsc -b
```

### Production build

```powershell
cd frontend
node .\node_modules\vite\bin\vite.js build
```

---

## API routes

### Legacy routes (city_daily.csv — 4 cities)

| Method | Route | Description |
|--------|-------|-------------|
| GET | `/health` | Health check |
| GET | `/meta/cities` | List of available cities |
| GET | `/meta/date-range` | Dataset date range |
| GET | `/dashboard/summary` | Overview KPIs, trend series, city snapshot, recent rows |
| GET | `/observations/recent` | Filterable recent observations |
| GET | `/trends/series` | Multi-city PM2.5 or station-count time series |
| GET | `/trends/download` | Filtered dataset as CSV download |
| GET | `/statistics/overview` | Descriptive stats, box-plot data, coverage table |
| GET | `/evaluation/cities` | Cities with historical evaluation data |
| GET | `/evaluation/{city}` | Holdout model evaluation for one city |
| GET | `/forecast/cities` | Cities available for future forecasting |
| GET | `/forecast/{city}` | 7 or 14-day future PM2.5 forecast |
| GET | `/forecast/{city}/download` | Future forecast as CSV download |

### V2 routes (per-dataset — any uploaded CSV)

| Method | Route | Description |
|--------|-------|-------------|
| GET | `/datasets` | List all datasets (demo + uploads) |
| POST | `/datasets/upload` | Upload a CSV dataset |
| GET | `/datasets/{id}` | Dataset metadata |
| GET | `/datasets/{id}/preview` | First N rows as JSON |
| DELETE | `/datasets/{id}` | Delete an uploaded dataset |
| GET | `/quality/{id}` | Full data quality profile |
| GET | `/quality/{id}/cleaned` | Download cleaned CSV |
| GET | `/analysis/{id}/statistics` | Inferential statistics + hypothesis tests |
| GET | `/analysis/{id}/regression` | Correlation, SLR, and MLR analysis |

All date parameters use inclusive `YYYY-MM-DD` bounds.

---

## Pages

| Page | Route | Description |
|------|-------|-------------|
| Overview | `/overview` | KPI cards · trend chart · city comparison · recent observations |
| Explore & Trends | `/trends` | Multi-city line chart · metric toggle · summary table · CSV download |
| Statistics | `/statistics` | Box plots · descriptive stats · coverage table |
| Hypothesis Tests | `/stat-analysis` | Shapiro-Wilk · t-tests vs WHO/NAAQS · CI · seasonal ANOVA |
| Regression Studio | `/regression` | Pearson correlation · SLR scatter + residuals · MLR coefficients |
| Evaluation | `/evaluation` | Historical holdout score cards · actual vs predicted chart |
| Forecast | `/forecast` | 7/14-day RF forecast · feature importance · CSV download |
| Dataset Manager | `/datasets` | Upload CSVs · switch active dataset · delete uploads |
| Data Quality | `/quality` | Quality score · column profiles · outliers · gap detection |
| Methodology | `/methodology` | CRISP-DM · statistical methods · ethical disclaimers |

---

## V2 Dataset Schema

User-uploaded CSVs must follow this schema:

| Column | Type | Required | Notes |
|--------|------|----------|-------|
| `date` | date | ✅ | `YYYY-MM-DD` preferred; other parseable formats accepted |
| `pm25_mean` | float | ✅ | Daily mean PM2.5 in µg/m³ |
| `station_count` | int | ❌ | Number of monitoring stations contributing |
| `coverage_pct` | float | ❌ | Data coverage percentage (0–100) |
| `city` | string | ❌ | City name (used for display only) |

Maximum file size: **10 MB**. Minimum valid rows after cleaning: **10**.

---

## Statistical Methods

### Normality — Shapiro-Wilk
$$W\text{-statistic},\ p\text{-value}\ (\alpha = 0.05).\ n > 5000 \Rightarrow \text{sampled to 5000}$$

### One-sample t-test (vs WHO / NAAQS)
$$t = \frac{\bar{x} - \mu_0}{s / \sqrt{n}},\quad d = \frac{\bar{x} - \mu_0}{s}\ \text{(Cohen's}\ d\text{)}$$

### 95% Confidence Interval
$$\bar{x} \pm t_{0.025,\ n-1} \cdot \frac{s}{\sqrt{n}}$$

### OLS Multiple Regression p-values
$$SE = \sqrt{MSE \cdot \text{diag}((X^T X)^{-1})},\quad t_i = \hat\beta_i / SE_i$$

---

## Forecasting Model

The **Forecast page** (`/forecast`) provides genuine future PM2.5 predictions:

1. **Training**: RandomForest Regressor (150 estimators) trained on **all available historical data**.
2. **Features**: `lag_1`, `lag_2`, `lag_3`, `lag_7`, `rolling_mean_3`, `rolling_mean_7`, `day_of_week`, `month`, `is_weekend`.
3. **Iterative rollout**: Each future step uses the previous step's output (no look-ahead).
4. **Output**: 7 or 14 daily predictions from `latest_observed_date + 1 day`.
5. **Caching**: Models are cached in-process per city.

> ⚠️ Forecast uncertainty grows with horizon. No meteorological inputs are used. For academic demonstration only.

---

## Model Evaluation Results (Evaluation page)

| City | RF better than Persistence? |
|------|------------------------------|
| Mumbai | ❌ No (RF MAE 22.2 vs Persistence 3.5) |
| Nagpur | ✅ Yes (RF MAE 4.3 vs Persistence 4.6) |
| Nashik | ❌ Marginally (RF MAE 4.2 vs Persistence 4.0) |
| Pune | ❌ No (RF MAE 5.0 vs Persistence 4.0) |

A negative R² means the model performed worse than the test-set mean — displayed accurately, not hidden.

---

## Limitations

1. **End-to-end browser test**: Both servers must be running for live API integration.
2. **Forecast model per city**: First request per city may take ~15–30 seconds (on-demand training).
3. **Bundle size**: Production bundle ~769 kB uncompressed (~221 kB gzip). Code-splitting could reduce it.
4. **No authentication**: Academic demonstration only — do not expose publicly without access controls.
5. **Time-series autocorrelation**: Violates classical hypothesis-test independence assumptions — treat p-values as approximate.
