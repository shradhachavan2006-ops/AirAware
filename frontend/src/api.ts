// Typed API client — all backend calls go through here.
//
// In development, BASE is '' (empty) so all requests are same-origin and are
// transparently forwarded to http://127.0.0.1:8000 by the Vite dev-server proxy.
// This avoids CORS entirely and works regardless of which port Vite binds to.
//
// In production, set the VITE_API_BASE_URL env variable to the backend URL.

const BASE = import.meta.env.VITE_API_BASE_URL ?? '';

async function post<T>(path: string, body: FormData | Record<string, unknown>): Promise<T> {
  const url = BASE ? new URL(path, BASE) : new URL(path, window.location.origin);
  const isFormData = body instanceof FormData;
  const res = await fetch(url.toString(), {
    method: 'POST',
    body: isFormData ? body : JSON.stringify(body),
    headers: isFormData ? {} : { 'Content-Type': 'application/json' },
  });
  if (!res.ok) {
    const detail = await res.json().catch(() => ({}));
    throw new Error(detail?.detail ?? `HTTP ${res.status}`);
  }
  return res.json() as Promise<T>;
}

async function del<T>(path: string): Promise<T> {
  const url = BASE ? new URL(path, BASE) : new URL(path, window.location.origin);
  const res = await fetch(url.toString(), { method: 'DELETE' });
  if (!res.ok) {
    const detail = await res.json().catch(() => ({}));
    throw new Error(detail?.detail ?? `HTTP ${res.status}`);
  }
  return res.json() as Promise<T>;
}

async function get<T>(path: string, params?: Record<string, string | string[] | number | null | undefined>): Promise<T> {
  const url = BASE ? new URL(path, BASE) : new URL(path, window.location.origin);

  if (params) {
    for (const [key, value] of Object.entries(params)) {
      if (value === null || value === undefined) continue;
      if (Array.isArray(value)) {
        value.forEach(v => url.searchParams.append(key, String(v)));
      } else {
        url.searchParams.set(key, String(value));
      }
    }
  }
  const res = await fetch(url.toString());
  if (!res.ok) {
    const detail = await res.json().catch(() => ({}));
    throw new Error(detail?.detail ?? `HTTP ${res.status}`);
  }
  return res.json() as Promise<T>;
}

async function download(path: string, params?: Record<string, string | string[] | number | null | undefined>): Promise<void> {
  const url = BASE ? new URL(path, BASE) : new URL(path, window.location.origin);
  if (params) {
    for (const [key, value] of Object.entries(params)) {
      if (value === null || value === undefined) continue;
      if (Array.isArray(value)) {
        value.forEach(v => url.searchParams.append(key, String(v)));
      } else {
        url.searchParams.set(key, String(value));
      }
    }
  }
  const res = await fetch(url.toString());
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  const blob = await res.blob();
  const cd = res.headers.get('content-disposition') ?? '';
  const match = cd.match(/filename="?([^"]+)"?/);
  const filename = match?.[1] ?? 'download.csv';
  const a = document.createElement('a');
  a.href = URL.createObjectURL(blob);
  a.download = filename;
  a.click();
  URL.revokeObjectURL(a.href);
}

// ── Types ──────────────────────────────────────────────────────────────────

export interface MetaCities { cities: string[] }
export interface MetaDateRange { start: string; end: string }

export interface DashboardSummary {
  selected: { city: string; start: string; end: string };
  kpis: {
    latest_pm25: number | null;
    latest_date: string | null;
    period_avg_pm25: number | null;
    period_max_pm25: number | null;
    valid_city_days: number;
  };
  trend_series: { date: string; pm25_mean: number | null; rolling_7d: number | null }[];
  city_summary: { city: string; average_pm25: number; valid_days: number }[];
  recent_observations: Observation[];
}

export interface Observation {
  date: string;
  city: string;
  pm25_mean: number | null;
  station_count: number | null;
  coverage_pct: number | null;
}

export interface ObservationsResponse {
  filters: { city: string | null; start: string | null; end: string | null; limit: number };
  count: number;
  observations: Observation[];
}

export interface TrendsSeries {
  filters: { cities: string[]; start: string | null; end: string | null; metric: string; metric_label: string };
  series: { city: string; data: { date: string; [key: string]: number | string | null }[] }[];
  summary: { city: string; observed_days: number; average: number | null; maximum: number | null }[];
}

export interface StatisticsOverview {
  kpis: {
    highest_avg_city: string | null;
    highest_avg_pm25: number | null;
    most_variable_city: string | null;
    most_variable_std: number | null;
    total_valid_measurements: number;
  };
  city_summary: { city: string; mean: number; median: number; std: number; maximum: number; valid_days: number }[];
  boxplots: Record<string, {
    q1: number; median: number; q3: number;
    lower_fence: number; upper_fence: number;
    min_non_outlier: number; max_non_outlier: number;
    outliers: number[];
  }>;
  coverage: {
    city: string; first_date: string; last_date: string;
    available_rows: number; valid_pm25_days: number;
    missing_pm25_rows: number; avg_station_count: number | null;
  }[];
}

export interface EvaluationCities { cities: string[]; models: string[] }

export interface ForecastCities {
  cities: string[];
  max_horizon: number;
  supported_horizons: number[];
  model: string;
  note: string;
}

export interface ForecastPoint {
  date: string;
  predicted_pm25: number;
  horizon_day: number;
}

export interface ForecastChartPoint {
  date: string;
  pm25_mean: number;
  is_forecast: boolean;
  horizon_day?: number;
}

export interface ForecastCity {
  city: string;
  horizon: number;
  latest_observed_date: string;
  latest_observed_pm25: number | null;
  historical_tail: ForecastChartPoint[];
  forecast: ForecastPoint[];
  chart_series: ForecastChartPoint[];
  train_rows: number;
  feature_importance: Record<string, number>;
  model_note: string;
  disclaimer: string;
}

export interface EvaluationCity {
  city: string;
  test_window: { start: string; end: string; max_samples: number | null } | null;
  metrics: Record<string, unknown>[];
  rf_worse_than_persistence: boolean;
  chart_data: {
    actual: { date: string; actual_pm25: number | null }[];
    models: { model: string; data: { date: string; predicted_pm25: number | null }[] }[];
  };
  prediction_records: Record<string, {
    date: string; city: string; model: string;
    actual_pm25: number | null; predicted_pm25: number | null; absolute_error: number | null;
  }[]>;
  disclaimer: string;
}

// ── V2 Types ───────────────────────────────────────────────────────────────

export interface DatasetInfo {
  id: string;
  name: string;
  city_hint: string;
  is_demo: boolean;
  rows: number;
  total_rows: number;
  date_start: string;
  date_end: string;
  has_station_count: boolean;
  has_coverage_pct: boolean;
  uploaded_at: string;
  warnings: string[];
}

export interface DatasetList { datasets: DatasetInfo[] }

export interface DatasetPreview {
  dataset_id: string;
  columns: string[];
  rows: Record<string, unknown>[];
  total_rows: number;
  showing: number;
}

export interface UploadResult {
  dataset: DatasetInfo;
  warnings: string[];
  message: string;
}

export interface QualityProfile {
  dataset_id: string;
  dataset_name: string;
  shape: { rows: number; columns: number };
  valid_pm25_rows: number;
  columns: {
    name: string; dtype: string; total: number;
    null_count: number; null_pct: number; unique_count: number;
    min?: number; max?: number; mean?: number; median?: number; std?: number;
  }[];
  date_gaps: { gap_start: string; gap_end: string; missing_days: number }[];
  total_gap_days: number;
  duplicate_dates: number;
  outliers: {
    count: number;
    bounds: { lower_fence: number; upper_fence: number; method: string };
    examples: { date: string; pm25_mean: number }[];
  };
  quality_issues: { severity: string; field: string; message: string }[];
  quality_score: number;
  preprocessing_recommendations: string[];
}

export interface StatisticsAnalysis {
  dataset_id: string;
  dataset_name: string;
  descriptive: {
    n: number; mean: number; median: number; std: number; sem: number;
    min: number; max: number; q1: number; q3: number; iqr: number;
    skewness: number; kurtosis_excess: number; cv_pct: number;
    interpretation: string;
  };
  normality: {
    test: string; n_tested: number; statistic: number | null;
    p_value: number | null; p_display: string; is_normal: boolean | null;
    conclusion: string;
  };
  ttest_who_annual: TTtestResult;
  ttest_india_naaqs: TTtestResult;
  confidence_interval_95: { level: number; lower: number; upper: number; interpretation: string };
  seasonal_anova: {
    test: string; f_statistic: number | null; p_value: number | null;
    p_display?: string; reject_null?: boolean;
    group_stats: Record<string, { n: number; mean: number; std: number }>;
    kruskal_wallis?: { statistic: number; p_value: number; p_display: string; reject_null: boolean };
    conclusion: string;
  };
  histogram: { bins: number[]; counts: number[]; bin_width: number };
  reference_values: { who_annual_guideline_ug_m3: number; india_naaqs_annual_ug_m3: number; note: string };
}

export interface TTtestResult {
  null_hypothesis: string;
  t_statistic: number;
  p_value: number;
  p_display: string;
  degrees_of_freedom: number;
  reject_null: boolean;
  cohens_d: number | null;
  effect_size_label: string;
  conclusion: string;
}

export interface RegressionAnalysis {
  dataset_id: string;
  dataset_name: string;
  n_samples: number;
  features_built: string[];
  target: string;
  correlation: Record<string, {
    r: number | null; r_squared: number | null;
    p_value: number | null; p_display: string;
    significance: string; interpretation: string;
  }>;
  simple_regression: {
    feature: string; feature_label: string; n: number;
    slope: number; intercept: number; r: number; r_squared: number;
    p_value: number; p_display: string; std_error: number; equation: string;
    scatter_data: { x: number; y: number; predicted: number }[];
    residual_data: { fitted: number; residual: number }[];
    interpretation: string;
  };
  multiple_regression: {
    features: string[]; n: number;
    r_squared: number; adjusted_r_squared: number;
    mse: number | null; rmse: number | null;
    coefficients: { feature: string; coefficient: number; p_value: number; p_display: string; significance: string }[];
    actual_vs_predicted: { index: number; actual: number; predicted: number }[];
    interpretation: string;
    significance_note: string;
  };
  methodology_note: string;
}

// ── API calls ──────────────────────────────────────────────────────────────

export const api = {
  getCities: () => get<MetaCities>('/meta/cities'),
  getDateRange: () => get<MetaDateRange>('/meta/date-range'),

  getDashboardSummary: (city: string, start: string, end: string) =>
    get<DashboardSummary>('/dashboard/summary', { city, start, end }),

  getRecentObservations: (params: { city?: string; start?: string; end?: string; limit?: number }) =>
    get<ObservationsResponse>('/observations/recent', params),

  getTrendsSeries: (cities: string[], start: string | null, end: string | null, metric: string) =>
    get<TrendsSeries>('/trends/series', { cities, start, end, metric }),

  downloadTrends: (cities: string[], start: string | null, end: string | null, metric: string) =>
    download('/trends/download', { cities, start, end, metric }),

  getStatisticsOverview: () => get<StatisticsOverview>('/statistics/overview'),

  getEvaluationCities: () => get<EvaluationCities>('/evaluation/cities'),

  getCityEvaluation: (city: string) => get<EvaluationCity>(`/evaluation/${encodeURIComponent(city)}`),

  getForecastCities: () => get<ForecastCities>('/forecast/cities'),

  getCityForecast: (city: string, horizon: number) =>
    get<ForecastCity>(`/forecast/${encodeURIComponent(city)}`, { horizon }),

  downloadForecast: (city: string, horizon: number) =>
    download(`/forecast/${encodeURIComponent(city)}/download`, { horizon }),

  // V2 Dataset endpoints
  listDatasets: () => get<DatasetList>('/datasets'),
  getDataset: (id: string) => get<DatasetInfo>(`/datasets/${encodeURIComponent(id)}`),
  getDatasetPreview: (id: string, rows = 25) =>
    get<DatasetPreview>(`/datasets/${encodeURIComponent(id)}/preview`, { rows }),
  uploadDataset: (file: File, name: string) => {
    const fd = new FormData();
    fd.append('file', file);
    fd.append('name', name);
    return post<UploadResult>('/datasets/upload', fd);
  },
  deleteDataset: (id: string) => del<{ message: string }>(`/datasets/${encodeURIComponent(id)}`),

  // V2 Quality endpoints
  getQualityProfile: (datasetId: string) =>
    get<QualityProfile>(`/quality/${encodeURIComponent(datasetId)}`),
  downloadCleanedDataset: (datasetId: string) =>
    download(`/quality/${encodeURIComponent(datasetId)}/cleaned`),

  // V2 Statistical analysis
  getStatisticsAnalysis: (datasetId: string) =>
    get<StatisticsAnalysis>(`/analysis/${encodeURIComponent(datasetId)}/statistics`),

  // V2 Regression
  getRegressionAnalysis: (datasetId: string) =>
    get<RegressionAnalysis>(`/analysis/${encodeURIComponent(datasetId)}/regression`),
};
