import { useEffect, useState, useCallback } from 'react';
import {
  ComposedChart, Line, ReferenceLine, XAxis, YAxis,
  CartesianGrid, Tooltip, Legend, ResponsiveContainer, Area,
} from 'recharts';
import { api } from '../api';
import type { ForecastCities, ForecastCity, ForecastChartPoint } from '../api';

// ── Palette ──────────────────────────────────────────────────────────────────
const HIST_COLOR   = '#16a36a';  // historical line
const FORE_COLOR   = '#e09b2f';  // forecast line
const FORE_FILL    = '#fef3c7';  // forecast shaded area

// ── Helpers ──────────────────────────────────────────────────────────────────
function fmt(v: number | null | undefined, dec = 1) {
  return v == null ? '—' : v.toFixed(dec);
}

function downloadCSV(rows: Record<string, unknown>[], filename: string) {
  if (!rows.length) return;
  const cols = Object.keys(rows[0]);
  const csv = [
    cols.join(','),
    ...rows.map(r => cols.map(c => r[c] ?? '').join(',')),
  ].join('\n');
  const a = document.createElement('a');
  a.href = 'data:text/csv,' + encodeURIComponent(csv);
  a.download = filename;
  a.click();
}

// ── Feature importance bar ───────────────────────────────────────────────────
function ImportanceBar({ name, value }: { name: string; value: number }) {
  const pct = Math.round(value * 100);
  const label: Record<string, string> = {
    pm25_today:     "Today's PM2.5",
    pm25_lag1:      'Lag 1 day',
    pm25_lag2:      'Lag 2 days',
    pm25_lag3:      'Lag 3 days',
    pm25_lag7:      'Lag 7 days',
    rolling_mean_3: '3-day mean',
    rolling_mean_7: '7-day mean',
  };
  return (
    <div className="mb-2">
      <div className="flex justify-between text-xs mb-0.5" style={{ color: 'var(--color-muted)' }}>
        <span>{label[name] ?? name}</span>
        <span style={{ color: '#16a36a', fontWeight: 700 }}>{pct}%</span>
      </div>
      <div style={{ background: '#e8f0ec', borderRadius: 4, height: 6 }}>
        <div style={{ width: `${pct}%`, height: 6, borderRadius: 4, background: '#16a36a' }} />
      </div>
    </div>
  );
}

// ── Custom tooltip ───────────────────────────────────────────────────────────
function ForecastTooltip({ active, payload, label }: {
  active?: boolean;
  payload?: { payload: ForecastChartPoint; value: number; dataKey: string }[];
  label?: string;
}) {
  if (!active || !payload?.length) return null;
  const pt = payload[0].payload;
  const val = pt.pm25_mean;
  return (
    <div style={{
      background: 'white', border: '1px solid #e0ebe4',
      borderRadius: 10, padding: '10px 14px', fontSize: 12,
      boxShadow: '0 4px 12px rgba(0,0,0,0.08)',
    }}>
      <div style={{ fontWeight: 700, marginBottom: 4, color: '#163b2b' }}>{label}</div>
      {pt.is_forecast ? (
        <>
          <div style={{ color: FORE_COLOR, fontWeight: 600 }}>
            Forecast: {val != null ? val.toFixed(2) : '—'} µg/m³
          </div>
          <div style={{ color: 'var(--color-muted)', fontSize: 10.5, marginTop: 2 }}>
            Day {pt.horizon_day} ahead · Model estimate
          </div>
        </>
      ) : (
        <div style={{ color: HIST_COLOR, fontWeight: 600 }}>
          Observed: {val != null ? val.toFixed(2) : '—'} µg/m³
        </div>
      )}
    </div>
  );
}

// ── Main component ───────────────────────────────────────────────────────────
export default function Forecast() {
  const [meta, setMeta]       = useState<ForecastCities | null>(null);
  const [city, setCity]       = useState('');
  const [horizon, setHorizon] = useState<7 | 14>(7);
  const [data, setData]       = useState<ForecastCity | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError]     = useState<string | null>(null);

  // Load available cities once
  useEffect(() => {
    api.getForecastCities()
      .then(m => {
        setMeta(m);
        const initial = m.cities.includes('Pune') ? 'Pune' : (m.cities[0] ?? '');
        setCity(initial);
      })
      .catch(e => setError(String(e)));
  }, []);

  // Fetch forecast when city or horizon changes
  const fetchForecast = useCallback(() => {
    if (!city) return;
    setLoading(true);
    setError(null);
    api.getCityForecast(city, horizon)
      .then(d => { setData(d); setLoading(false); })
      .catch(e => { setError(String(e)); setLoading(false); });
  }, [city, horizon]);

  useEffect(() => { fetchForecast(); }, [fetchForecast]);

  // Chart data: split to colour historical vs forecast differently
  // We use two Line components sharing the same data array; each reads only
  // the matching segment via a conditional value accessor.
  const chartData = data?.chart_series ?? [];

  // Find the separator index (first forecast point)
  const splitIdx = chartData.findIndex(p => p.is_forecast);
  const splitDate = splitIdx >= 0 ? chartData[splitIdx].date : null;

  // Table rows for forecast
  const tableRows = data?.forecast ?? [];

  // Feature importance sorted descending
  const importanceEntries = data
    ? Object.entries(data.feature_importance).sort(([, a], [, b]) => b - a)
    : [];

  return (
    <div className="p-7 max-w-6xl mx-auto">
      {/* ── Header ─────────────────────────────────────────── */}
      <div className="rounded-2xl mb-6 px-8 py-6" style={{
        background: 'linear-gradient(115deg,#1a3a5c 0%,#1e5c8e 60%,#2980b9 100%)',
        color: 'white', boxShadow: '0 12px 30px rgba(26,58,92,0.18)',
      }}>
        <div className="text-xs font-bold uppercase tracking-widest mb-2" style={{ color: '#90caf9' }}>
          PM2.5 FUTURE FORECAST · RANDOMFOREST
        </div>
        <h1 className="text-2xl font-black mb-1" style={{ color: 'white', fontFamily: 'Manrope, sans-serif' }}>
          What comes next?
        </h1>
        <p className="text-sm" style={{ color: '#bbdefb' }}>
          7 or 14-day PM2.5 estimates beyond the latest observed date.
          Based on historical lag and rolling-mean features — not meteorological inputs.
        </p>
      </div>

      {/* ── Controls ──────────────────────────────────────── */}
      <div className="card mb-6 flex flex-wrap gap-5 items-end">
        <div>
          <label className="form-label" htmlFor="forecast-city-select">City</label>
          <select
            id="forecast-city-select"
            className="form-control w-44"
            value={city}
            onChange={e => setCity(e.target.value)}
          >
            {(meta?.cities ?? []).map(c => <option key={c}>{c}</option>)}
          </select>
        </div>
        <div>
          <label className="form-label">Forecast horizon</label>
          <div className="flex gap-2 mt-1">
            {[7, 14].map(h => (
              <button
                key={h}
                id={`horizon-btn-${h}`}
                className={`btn ${horizon === h ? 'btn-primary' : 'btn-outline'}`}
                onClick={() => setHorizon(h as 7 | 14)}
              >
                {h} days
              </button>
            ))}
          </div>
        </div>
        {data && (
          <div className="text-sm ml-auto" style={{ color: 'var(--color-muted)' }}>
            Latest obs: <b style={{ color: '#163b2b' }}>{data.latest_observed_date}</b>
            {data.latest_observed_pm25 != null && (
              <> · <b style={{ color: '#16a36a' }}>{data.latest_observed_pm25.toFixed(1)} µg/m³</b></>
            )}
          </div>
        )}
      </div>

      {error && <div className="msg-error mb-4">{error}</div>}
      {loading && <div className="msg-info mb-4">Training model and generating forecast… this may take a few seconds.</div>}

      {data && !loading && (
        <>
          {/* ── KPI row ─────────────────────────────────── */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
            <div className="kpi-card" style={{ borderTop: '3px solid #1e5c8e' }}>
              <div className="kpi-label">Latest observed</div>
              <div className="kpi-value">{fmt(data.latest_observed_pm25)}</div>
              <div className="kpi-sub">µg/m³ · {data.latest_observed_date}</div>
            </div>
            <div className="kpi-card" style={{ borderTop: `3px solid ${FORE_COLOR}` }}>
              <div className="kpi-label">Day-1 forecast</div>
              <div className="kpi-value" style={{ color: FORE_COLOR }}>
                {fmt(tableRows[0]?.predicted_pm25)}
              </div>
              <div className="kpi-sub">µg/m³ · {tableRows[0]?.date ?? '—'}</div>
            </div>
            <div className="kpi-card" style={{ borderTop: `3px solid ${FORE_COLOR}` }}>
              <div className="kpi-label">{horizon}-day mean</div>
              <div className="kpi-value" style={{ color: FORE_COLOR }}>
                {tableRows.length
                  ? fmt(tableRows.reduce((s, r) => s + r.predicted_pm25, 0) / tableRows.length)
                  : '—'}
              </div>
              <div className="kpi-sub">µg/m³ forecast average</div>
            </div>
            <div className="kpi-card" style={{ borderTop: '3px solid #16a36a' }}>
              <div className="kpi-label">Training samples</div>
              <div className="kpi-value">{data.train_rows.toLocaleString()}</div>
              <div className="kpi-sub">daily observations used</div>
            </div>
          </div>

          {/* ── Main chart ──────────────────────────────── */}
          <div className="card mb-5">
            <div className="flex justify-between items-start mb-1">
              <div>
                <div className="section-title mb-0">Historical trend + {horizon}-day forecast</div>
                <p className="text-xs mt-1" style={{ color: 'var(--color-muted)' }}>
                  Green = observed PM2.5 (last 30 days). Amber = model forecast (starts{' '}
                  {splitDate ? `${splitDate}` : 'from next day'}).
                  Vertical line marks the forecast boundary.
                </p>
              </div>
              <button
                id="download-forecast-btn"
                className="btn btn-outline"
                onClick={() => api.downloadForecast(city, horizon)}
              >
                ⬇ Download CSV
              </button>
            </div>

            {chartData.length === 0 ? (
              <div className="msg-info mt-3">No data to display.</div>
            ) : (
              <ResponsiveContainer width="100%" height={340}>
                <ComposedChart data={chartData} margin={{ top: 8, right: 12, left: 0, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#e8f0ec" />
                  <XAxis
                    dataKey="date"
                    tick={{ fontSize: 10.5, fill: '#6b7c74' }}
                    tickLine={false}
                    interval="preserveStartEnd"
                  />
                  <YAxis
                    tick={{ fontSize: 10.5, fill: '#6b7c74' }}
                    tickLine={false}
                    axisLine={false}
                    label={{ value: 'µg/m³', angle: -90, position: 'insideLeft', offset: 10, style: { fontSize: 10, fill: '#9aaa9f' } }}
                  />
                  <Tooltip content={<ForecastTooltip />} />
                  <Legend wrapperStyle={{ fontSize: 12 }} />

                  {/* Forecast shading area */}
                  <Area
                    dataKey={(pt: ForecastChartPoint) => pt.is_forecast ? pt.pm25_mean : null}
                    name="Forecast range"
                    fill={FORE_FILL}
                    stroke="none"
                    connectNulls={false}
                    legendType="none"
                    activeDot={false}
                    isAnimationActive={false}
                  />

                  {/* Historical line */}
                  <Line
                    dataKey={(pt: ForecastChartPoint) => pt.is_forecast ? null : pt.pm25_mean}
                    name="Historical PM2.5"
                    stroke={HIST_COLOR}
                    strokeWidth={2}
                    dot={false}
                    connectNulls={false}
                    activeDot={{ r: 4 }}
                    isAnimationActive={false}
                  />

                  {/* Forecast line */}
                  <Line
                    dataKey={(pt: ForecastChartPoint) => pt.is_forecast ? pt.pm25_mean : null}
                    name="Forecast (RF)"
                    stroke={FORE_COLOR}
                    strokeWidth={2.5}
                    strokeDasharray="6 3"
                    dot={{ r: 3, fill: FORE_COLOR }}
                    connectNulls={false}
                    activeDot={{ r: 5 }}
                    isAnimationActive={false}
                  />

                  {/* Vertical boundary line */}
                  {splitDate && (
                    <ReferenceLine
                      x={splitDate}
                      stroke="#94a3b8"
                      strokeDasharray="4 2"
                      label={{ value: 'Forecast start', position: 'insideTopRight', fontSize: 10, fill: '#64748b' }}
                    />
                  )}
                </ComposedChart>
              </ResponsiveContainer>
            )}
          </div>

          {/* ── Two-column layout: table + feature importance ── */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-5 mb-5">
            {/* Forecast table */}
            <div className="card md:col-span-2">
              <div className="flex justify-between items-center mb-3">
                <div className="section-title mb-0">Forecast table</div>
                <button
                  id="download-table-btn"
                  className="btn btn-outline"
                  onClick={() => downloadCSV(
                    tableRows.map(r => ({
                      city: data.city,
                      date: r.date,
                      predicted_pm25: r.predicted_pm25,
                      horizon_day: r.horizon_day,
                    })),
                    `${data.city.toLowerCase()}_forecast_${horizon}d.csv`,
                  )}
                >
                  ⬇ Download
                </button>
              </div>
              <div style={{ overflowX: 'auto' }}>
                <table className="data-table" id="forecast-table">
                  <thead>
                    <tr>
                      <th>Date</th>
                      <th>Day ahead</th>
                      <th>Forecast PM2.5 (µg/m³)</th>
                    </tr>
                  </thead>
                  <tbody>
                    {tableRows.map((row, i) => (
                      <tr key={i}>
                        <td>{row.date}</td>
                        <td>
                          <span className="pill" style={{ background: '#fff3e0', color: '#795548' }}>
                            Day {row.horizon_day}
                          </span>
                        </td>
                        <td style={{ fontWeight: 600, color: FORE_COLOR }}>
                          {row.predicted_pm25.toFixed(2)}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>

            {/* Feature importance */}
            <div className="card">
              <div className="section-title">Feature importance</div>
              <p className="text-xs mb-3" style={{ color: 'var(--color-muted)' }}>
                Relative contribution of each input feature to the RandomForest predictions.
              </p>
              {importanceEntries.map(([name, val]) => (
                <ImportanceBar key={name} name={name} value={val} />
              ))}
            </div>
          </div>

          {/* ── Model note + disclaimer ─────────────────── */}
          <div className="card mb-5" style={{ borderLeft: '4px solid #1e5c8e' }}>
            <div className="section-title text-sm">Model note</div>
            <p className="text-sm" style={{ color: 'var(--color-muted)', lineHeight: 1.7 }}>
              {data.model_note}
            </p>
          </div>

          <div className="card" style={{ borderLeft: '4px solid #e09b2f' }}>
            <div className="section-title text-sm">⚠ Interpretation &amp; limitations</div>
            <p className="text-sm" style={{ color: 'var(--color-muted)', lineHeight: 1.7 }}>
              {data.disclaimer}
            </p>
            <ul className="text-xs mt-2" style={{ color: 'var(--color-muted)', lineHeight: 1.8, paddingLeft: 16 }}>
              <li>Uncertainty grows with horizon — Day-7 predictions are less reliable than Day-1.</li>
              <li>Seasonal patterns or sudden pollution events are not captured without meteorological inputs.</li>
              <li>This model is retrained on all available historical data — it is distinct from the
                  evaluation model on the Evaluation page, which uses a held-out test split.</li>
              <li>Values represent µg/m³ PM2.5 concentration estimates, not AQI scores.</li>
            </ul>
          </div>
        </>
      )}
    </div>
  );
}
