import { useEffect, useState } from 'react';
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip,
  Legend, ResponsiveContainer, BarChart, Bar, Cell,
} from 'recharts';
import { api } from '../api';
import type { DashboardSummary, MetaDateRange } from '../api';

function fmt(v: number | null | undefined, dec = 1) {
  return v == null ? '—' : v.toFixed(dec);
}

export default function Overview() {
  const [cities, setCities] = useState<string[]>([]);
  const [dateRange, setDateRange] = useState<MetaDateRange | null>(null);
  const [city, setCity] = useState('Pune');
  const [start, setStart] = useState('');
  const [end, setEnd] = useState('');
  const [data, setData] = useState<DashboardSummary | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Load metadata once
  useEffect(() => {
    Promise.all([api.getCities(), api.getDateRange()])
      .then(([c, d]) => {
        setCities(c.cities);
        setDateRange(d);
        setStart(d.start);
        setEnd(d.end);
        if (c.cities.includes('Pune')) setCity('Pune');
        else if (c.cities.length) setCity(c.cities[0]);
      })
      .catch(e => setError(String(e)));
  }, []);

  // Fetch dashboard data when filters change
  useEffect(() => {
    if (!city || !start || !end) return;
    setLoading(true);
    setError(null);
    api.getDashboardSummary(city, start, end)
      .then(d => { setData(d); setLoading(false); })
      .catch(e => { setError(String(e)); setLoading(false); });
  }, [city, start, end]);

  const kpis = data?.kpis;

  return (
    <div className="p-7 max-w-6xl mx-auto">
      {/* Hero */}
      <div className="rounded-2xl mb-6 px-8 py-6" style={{
        background: 'linear-gradient(115deg,#103d2a 0%,#176442 64%,#21865b 100%)',
        color: 'white',
        boxShadow: '0 12px 30px rgba(20,83,45,0.13)',
      }}>
        <div className="text-xs font-bold uppercase tracking-widest mb-2" style={{ color: '#7acba1' }}>
          ENVIRONMENTAL INTELLIGENCE · INDIA
        </div>
        <h1 className="text-2xl font-black mb-1" style={{ color: 'white', fontFamily: 'Manrope, sans-serif' }}>
          Air quality, made clearer.
        </h1>
        <p className="text-sm" style={{ color: '#d8eee1' }}>
          Explore daily PM2.5 patterns across Indian cities and understand what the data can—and cannot—tell us.
        </p>
      </div>

      {/* Filters */}
      <div className="card mb-6 flex flex-wrap gap-5 items-end">
        <div>
          <label className="form-label">Focus city</label>
          <select className="form-control w-40" value={city} onChange={e => setCity(e.target.value)}>
            {cities.map(c => <option key={c}>{c}</option>)}
          </select>
        </div>
        <div>
          <label className="form-label">Start date</label>
          <input type="date" className="form-control w-40" value={start}
            min={dateRange?.start} max={end}
            onChange={e => setStart(e.target.value)} />
        </div>
        <div>
          <label className="form-label">End date</label>
          <input type="date" className="form-control w-40" value={end}
            min={start} max={dateRange?.end}
            onChange={e => setEnd(e.target.value)} />
        </div>
      </div>

      {error && <div className="msg-error mb-4">{error}</div>}
      {loading && <div className="msg-info mb-4">Loading…</div>}

      {/* KPI cards */}
      {kpis && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
          <div className="kpi-card">
            <div className="kpi-label">Latest PM2.5</div>
            <div className="kpi-value">{fmt(kpis.latest_pm25)}</div>
            <div className="kpi-sub">µg/m³{kpis.latest_date ? ` · ${kpis.latest_date}` : ''}</div>
          </div>
          <div className="kpi-card">
            <div className="kpi-label">Period average</div>
            <div className="kpi-value">{fmt(kpis.period_avg_pm25)}</div>
            <div className="kpi-sub">µg/m³</div>
          </div>
          <div className="kpi-card">
            <div className="kpi-label">Peak observed</div>
            <div className="kpi-value">{fmt(kpis.period_max_pm25)}</div>
            <div className="kpi-sub">µg/m³</div>
          </div>
          <div className="kpi-card">
            <div className="kpi-label">Valid city-days</div>
            <div className="kpi-value">{kpis.valid_city_days.toLocaleString()}</div>
            <div className="kpi-sub">Non-missing PM2.5 rows</div>
          </div>
        </div>
      )}

      {/* Charts row */}
      {data && (
        <div className="grid grid-cols-1 md:grid-cols-5 gap-5 mb-6">
          {/* Trend chart */}
          <div className="card md:col-span-3">
            <div className="section-title">Daily pollution trend</div>
            <p className="text-xs mb-3" style={{ color: 'var(--color-muted)' }}>
              Daily city average with 7-day rolling mean. Gaps = missing dates.
            </p>
            {data.trend_series.length === 0
              ? <div className="msg-info">No data for this selection.</div>
              : (
                <ResponsiveContainer width="100%" height={280}>
                  <LineChart data={data.trend_series} margin={{ top: 4, right: 8, left: 0, bottom: 0 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#e8f0ec" />
                    <XAxis dataKey="date" tick={{ fontSize: 11, fill: '#6b7c74' }} tickLine={false}
                      interval="preserveStartEnd" />
                    <YAxis tick={{ fontSize: 11, fill: '#6b7c74' }} tickLine={false} axisLine={false}
                      label={{ value: 'µg/m³', angle: -90, position: 'insideLeft', offset: 10, style: { fontSize: 10, fill: '#9aaa9f' } }} />
                    <Tooltip contentStyle={{ fontSize: 12, borderRadius: 8, border: '1px solid #e0ebe4' }}
                      formatter={(v: any) => v == null ? 'N/A' : Number(v).toFixed(2)} />
                    <Legend wrapperStyle={{ fontSize: 12 }} />
                    <Line dataKey="pm25_mean" name="Daily PM2.5" stroke="#16a36a" strokeWidth={1.8}
                      dot={false} connectNulls={false} />
                    <Line dataKey="rolling_7d" name="7-day rolling mean" stroke="#14532d" strokeWidth={2.5}
                      dot={false} connectNulls={false} strokeDasharray="4 2" />
                  </LineChart>
                </ResponsiveContainer>
              )
            }
          </div>

          {/* City snapshot */}
          <div className="card md:col-span-2">
            <div className="section-title">City snapshot</div>
            <p className="text-xs mb-3" style={{ color: 'var(--color-muted)' }}>
              Average PM2.5 across all cities in selected period.
            </p>
            {data.city_summary.length === 0
              ? <div className="msg-info">No data.</div>
              : (
                <ResponsiveContainer width="100%" height={280}>
                  <BarChart
                    data={[...data.city_summary].sort((a, b) => (a.average_pm25 ?? 0) - (b.average_pm25 ?? 0))}
                    layout="vertical"
                    margin={{ top: 4, right: 30, left: 30, bottom: 0 }}
                  >
                    <CartesianGrid strokeDasharray="3 3" stroke="#e8f0ec" horizontal={false} />
                    <XAxis type="number" tick={{ fontSize: 11, fill: '#6b7c74' }} tickLine={false} axisLine={false} />
                    <YAxis type="category" dataKey="city" tick={{ fontSize: 12, fill: '#4a6358' }} tickLine={false} axisLine={false} width={50} />
                    <Tooltip contentStyle={{ fontSize: 12, borderRadius: 8 }}
                      formatter={(v: any) => [`${Number(v).toFixed(1)} µg/m³`, 'Avg PM2.5']} />
                    <Bar dataKey="average_pm25" radius={[0, 6, 6, 0]}>
                      {data.city_summary.map((_, i) => (
                        <Cell key={i} fill={['#bdebd0','#6dc99b','#16a36a','#14532d'][i % 4]} />
                      ))}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              )
            }
          </div>
        </div>
      )}

      {/* Recent observations */}
      {data && (
        <div className="card">
          <div className="section-title">Recent observations</div>
          {data.recent_observations.length === 0
            ? <div className="msg-info">No rows for this selection.</div>
            : (
              <div style={{ overflowX: 'auto' }}>
                <table className="data-table">
                  <thead>
                    <tr>
                      <th>Date</th>
                      <th>City</th>
                      <th>PM2.5 (µg/m³)</th>
                      <th>Stations</th>
                      <th>Coverage (%)</th>
                    </tr>
                  </thead>
                  <tbody>
                    {data.recent_observations.map((row, i) => (
                      <tr key={i}>
                        <td>{row.date}</td>
                        <td>{row.city}</td>
                        <td>{row.pm25_mean != null ? row.pm25_mean.toFixed(2) : '—'}</td>
                        <td>{row.station_count ?? '—'}</td>
                        <td>{row.coverage_pct != null ? row.coverage_pct.toFixed(1) + '%' : '—'}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )
          }
          <p className="text-xs mt-3" style={{ color: 'var(--color-muted)' }}>
            PM2.5 is reported in µg/m³. It should not be interpreted as an AQI score.
            Missing dates and different station counts can affect comparisons.
          </p>
        </div>
      )}
    </div>
  );
}
