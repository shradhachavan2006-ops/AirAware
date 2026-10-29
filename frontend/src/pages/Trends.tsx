import { useEffect, useState } from 'react';
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid,
  Tooltip, Legend, ResponsiveContainer,
} from 'recharts';
import { api } from '../api';
import type { TrendsSeries, MetaDateRange } from '../api';

const CITY_COLORS = ['#16a36a', '#e69b48', '#6488c6', '#e06c6c'];
const METRICS = [
  { value: 'pm25_mean',    label: 'PM2.5 concentration' },
  { value: 'station_count', label: 'Station count'       },
];

export default function Trends() {
  const [allCities, setAllCities] = useState<string[]>([]);
  const [dateRange, setDateRange] = useState<MetaDateRange | null>(null);
  const [selectedCities, setSelectedCities] = useState<string[]>([]);
  const [start, setStart] = useState('');
  const [end, setEnd] = useState('');
  const [metric, setMetric] = useState('pm25_mean');
  const [data, setData] = useState<TrendsSeries | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Load metadata
  useEffect(() => {
    Promise.all([api.getCities(), api.getDateRange()])
      .then(([c, d]) => {
        setAllCities(c.cities);
        setSelectedCities(c.cities);
        setDateRange(d);
        setStart(d.start);
        setEnd(d.end);
      })
      .catch(e => setError(String(e)));
  }, []);

  // Fetch on filter change
  useEffect(() => {
    if (!selectedCities.length || !start || !end) return;
    setLoading(true);
    setError(null);
    api.getTrendsSeries(selectedCities, start, end, metric)
      .then(d => { setData(d); setLoading(false); })
      .catch(e => { setError(String(e)); setLoading(false); });
  }, [selectedCities, start, end, metric]);

  // Merge series into flat chart data
  const chartData = (() => {
    if (!data) return [];
    const dateMap = new Map<string, Record<string, any>>();
    for (const s of data.series) {
      for (const pt of s.data) {
        if (!dateMap.has(pt.date)) dateMap.set(pt.date, { date: pt.date });
        const row = dateMap.get(pt.date)!;
        const val = pt[metric];
        row[s.city] = (val === undefined ? null : (val as number | null));
      }
    }
    return Array.from(dateMap.values()).sort((a, b) =>
      String(a.date) < String(b.date) ? -1 : 1
    );
  })();

  const toggleCity = (c: string) =>
    setSelectedCities(prev =>
      prev.includes(c) ? prev.filter(x => x !== c) : [...prev, c]
    );

  const metricLabel = METRICS.find(m => m.value === metric)?.label ?? metric;
  const yLabel = metric === 'pm25_mean' ? 'µg/m³' : 'Stations';

  return (
    <div className="p-7 max-w-6xl mx-auto">
      {/* Header */}
      <div className="mb-6">
        <div className="text-xs font-bold uppercase tracking-widest mb-1" style={{ color: '#16a36a' }}>EXPLORE THE PAST</div>
        <h1 className="text-2xl font-black" style={{ fontFamily: 'Manrope, sans-serif', color: '#163b2b' }}>
          Historical pollution trends
        </h1>
        <p className="text-sm mt-1" style={{ color: 'var(--color-muted)' }}>
          Compare daily PM2.5 patterns and station coverage over a time period of your choice.
        </p>
      </div>

      {/* Filters */}
      <div className="card mb-6 flex flex-wrap gap-5 items-end">
        <div>
          <label className="form-label">Cities</label>
          <div className="flex flex-wrap gap-2 mt-1">
            {allCities.map((c, i) => (
              <button
                key={c}
                onClick={() => toggleCity(c)}
                className="btn text-xs py-1"
                style={{
                  borderColor: selectedCities.includes(c) ? CITY_COLORS[i % CITY_COLORS.length] : '#dde8e2',
                  background: selectedCities.includes(c) ? CITY_COLORS[i % CITY_COLORS.length] + '18' : 'white',
                  color: selectedCities.includes(c) ? CITY_COLORS[i % CITY_COLORS.length] : '#6b7c74',
                  fontWeight: 600,
                }}
              >
                {c}
              </button>
            ))}
          </div>
        </div>
        <div>
          <label className="form-label">Start date</label>
          <input type="date" className="form-control w-40" value={start}
            min={dateRange?.start} max={end} onChange={e => setStart(e.target.value)} />
        </div>
        <div>
          <label className="form-label">End date</label>
          <input type="date" className="form-control w-40" value={end}
            min={start} max={dateRange?.end} onChange={e => setEnd(e.target.value)} />
        </div>
        <div>
          <label className="form-label">Metric</label>
          <select className="form-control w-48" value={metric} onChange={e => setMetric(e.target.value)}>
            {METRICS.map(m => <option key={m.value} value={m.value}>{m.label}</option>)}
          </select>
        </div>
        <button
          className="btn btn-outline"
          disabled={!selectedCities.length || !start || !end}
          onClick={() => api.downloadTrends(selectedCities, start, end, metric).catch(e => setError(String(e)))}
        >
          ⬇ Download CSV
        </button>
      </div>

      {error && <div className="msg-error mb-4">{error}</div>}
      {loading && <div className="msg-info mb-4">Loading…</div>}

      {/* Chart */}
      {data && (
        <div className="card mb-5">
          <div className="section-title">{metricLabel} over time</div>
          <p className="text-xs mb-3" style={{ color: 'var(--color-muted)' }}>
            Line gaps represent missing observations — values are not connected across gaps.
          </p>
          {chartData.length === 0
            ? <div className="msg-info">No observations match these filters.</div>
            : (
              <ResponsiveContainer width="100%" height={320}>
                <LineChart data={chartData} margin={{ top: 4, right: 8, left: 0, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#e8f0ec" />
                  <XAxis dataKey="date" tick={{ fontSize: 11, fill: '#6b7c74' }} tickLine={false}
                    interval="preserveStartEnd" />
                  <YAxis tick={{ fontSize: 11, fill: '#6b7c74' }} tickLine={false} axisLine={false}
                    label={{ value: yLabel, angle: -90, position: 'insideLeft', offset: 10, style: { fontSize: 10, fill: '#9aaa9f' } }} />
                  <Tooltip contentStyle={{ fontSize: 12, borderRadius: 8, border: '1px solid #e0ebe4' }}
                    formatter={(v: any) => v == null ? 'N/A' : Number(v).toFixed(2)} />
                  <Legend wrapperStyle={{ fontSize: 12 }} />
                  {selectedCities.map((c, i) => (
                    <Line key={c} dataKey={c} name={c} stroke={CITY_COLORS[i % CITY_COLORS.length]}
                      strokeWidth={2} dot={false} connectNulls={false} />
                  ))}
                </LineChart>
              </ResponsiveContainer>
            )
          }
        </div>
      )}

      {/* Summary table */}
      {data && data.summary.length > 0 && (
        <div className="card">
          <div className="section-title">Summary for selected period</div>
          <div style={{ overflowX: 'auto' }}>
            <table className="data-table">
              <thead>
                <tr>
                  <th>City</th>
                  <th>Observed days</th>
                  <th>Average {metric === 'pm25_mean' ? '(µg/m³)' : ''}</th>
                  <th>Maximum {metric === 'pm25_mean' ? '(µg/m³)' : ''}</th>
                </tr>
              </thead>
              <tbody>
                {data.summary.map(row => (
                  <tr key={row.city}>
                    <td><b>{row.city}</b></td>
                    <td>{row.observed_days.toLocaleString()}</td>
                    <td>{row.average != null ? row.average.toFixed(2) : '—'}</td>
                    <td>{row.maximum != null ? row.maximum.toFixed(2) : '—'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <p className="text-xs mt-3" style={{ color: 'var(--color-muted)' }}>
            Missing observations are left missing and are not treated as zero pollution.
          </p>
        </div>
      )}
    </div>
  );
}
