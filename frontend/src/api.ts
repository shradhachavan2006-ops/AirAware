// Typed API client — all backend calls go through here.
//
// In development, BASE is '' (empty) so all requests are same-origin and are
// transparently forwarded to http://127.0.0.1:8000 by the Vite dev-server proxy.
// This avoids CORS entirely and works regardless of which port Vite binds to.
//
// In production, set the VITE_API_BASE_URL env variable to the backend URL.

const BASE = import.meta.env.VITE_API_BASE_URL ?? '';

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
};
