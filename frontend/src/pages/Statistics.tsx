import { useEffect, useState } from 'react';
import { api } from '../api';
import type { StatisticsOverview } from '../api';

const CITY_COLORS = ['#16a36a', '#e69b48', '#6488c6', '#e06c6c'];

function KpiCard({ label, value, sub }: { label: string; value: string; sub?: string }) {
  return (
    <div className="kpi-card">
      <div className="kpi-label">{label}</div>
      <div className="kpi-value" style={{ fontSize: '1.25rem' }}>{value}</div>
      {sub && <div className="kpi-sub">{sub}</div>}
    </div>
  );
}

// Custom boxplot using Recharts ComposedChart
function BoxPlotChart({ data }: { data: StatisticsOverview }) {
  const cities = data.city_summary.map(r => r.city);

  // Build chart data for each city
  const chartData = cities.map((city, i) => {
    const bp = data.boxplots[city];
    const color = CITY_COLORS[i % CITY_COLORS.length];
    return { city, bp, color };
  });

  // We render a simple vertical bar per city showing min..max with IQR box
  return (
    <div className="flex gap-8 justify-around items-end" style={{ height: 280, paddingTop: 20 }}>
      {chartData.map(({ city, bp, color }) => {
        const allVals = [bp.lower_fence, bp.q1, bp.median, bp.q3, bp.upper_fence, ...bp.outliers];
        const globalMin = Math.min(...allVals);
        const globalMax = Math.max(...allVals);
        const range = globalMax - globalMin || 1;

        const pct = (v: number) => ((v - globalMin) / range) * 100;
        const h = (v: number) => `${100 - pct(v)}%`;

        return (
          <div key={city} className="flex flex-col items-center" style={{ flex: 1, maxWidth: 90 }}>
            <div className="relative w-full" style={{ height: 240 }}>
              {/* Whisker line */}
              <div style={{
                position: 'absolute', left: '50%', transform: 'translateX(-50%)',
                width: 2, background: color + '60',
                top: h(bp.upper_fence), bottom: `${pct(bp.lower_fence)}%`,
              }} />
              {/* IQR box */}
              <div style={{
                position: 'absolute', left: '15%', right: '15%',
                background: color + '30', border: `2px solid ${color}`,
                borderRadius: 4,
                top: h(bp.q3), bottom: `${pct(bp.q1)}%`,
              }} />
              {/* Median line */}
              <div style={{
                position: 'absolute', left: '12%', right: '12%', height: 2,
                background: color, top: h(bp.median),
              }} />
              {/* Outliers */}
              {bp.outliers.map((v, i) => (
                <div key={i} style={{
                  position: 'absolute', left: '50%', transform: 'translateX(-50%)',
                  width: 6, height: 6, borderRadius: '50%',
                  background: color, top: `calc(${h(v)} - 3px)`,
                }} />
              ))}
            </div>
            <div className="text-xs font-semibold mt-2" style={{ color: '#4a6358' }}>{city}</div>
            <div className="text-xs" style={{ color: '#9aaa9f' }}>Med: {bp.median.toFixed(1)}</div>
          </div>
        );
      })}
    </div>
  );
}

export default function Statistics() {
  const [data, setData] = useState<StatisticsOverview | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.getStatisticsOverview()
      .then(d => { setData(d); setLoading(false); })
      .catch(e => { setError(String(e)); setLoading(false); });
  }, []);

  if (loading) return <div className="p-7"><div className="msg-info">Loading statistics…</div></div>;
  if (error)   return <div className="p-7"><div className="msg-error">{error}</div></div>;
  if (!data)   return null;

  const { kpis, city_summary, coverage } = data;

  return (
    <div className="p-7 max-w-6xl mx-auto">
      {/* Header */}
      <div className="mb-6">
        <div className="text-xs font-bold uppercase tracking-widest mb-1" style={{ color: '#16a36a' }}>DATA-DRIVEN DISCOVERY</div>
        <h1 className="text-2xl font-black" style={{ fontFamily: 'Manrope, sans-serif', color: '#163b2b' }}>
          What the numbers reveal
        </h1>
        <p className="text-sm mt-1" style={{ color: 'var(--color-muted)' }}>
          Distributions, variability, and data quality — without losing sight of coverage limitations.
        </p>
      </div>

      {/* KPIs */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
        <KpiCard
          label="Highest city average"
          value={kpis.highest_avg_city ?? '—'}
          sub={kpis.highest_avg_pm25 != null ? `${kpis.highest_avg_pm25.toFixed(1)} µg/m³` : undefined}
        />
        <KpiCard
          label="Most variable city"
          value={kpis.most_variable_city ?? '—'}
          sub={kpis.most_variable_std != null ? `Std. dev. ${kpis.most_variable_std.toFixed(1)}` : undefined}
        />
        <KpiCard
          label="Valid measurements"
          value={kpis.total_valid_measurements.toLocaleString()}
          sub="Non-NaN PM2.5 rows"
        />
      </div>

      {/* Charts row */}
      <div className="grid grid-cols-1 md:grid-cols-5 gap-5 mb-6">
        {/* Box plot */}
        <div className="card md:col-span-3">
          <div className="section-title">Distribution by city</div>
          <p className="text-xs mb-2" style={{ color: 'var(--color-muted)' }}>
            Box = IQR (Q1–Q3) · line = median · dots = outliers (±1.5×IQR)
          </p>
          <BoxPlotChart data={data} />
        </div>

        {/* Descriptive stats table */}
        <div className="card md:col-span-2">
          <div className="section-title">Descriptive statistics</div>
          <div style={{ overflowX: 'auto' }}>
            <table className="data-table">
              <thead>
                <tr>
                  <th>City</th>
                  <th>Mean</th>
                  <th>Median</th>
                  <th>Std.</th>
                  <th>Max</th>
                  <th>Days</th>
                </tr>
              </thead>
              <tbody>
                {city_summary.map(row => (
                  <tr key={row.city}>
                    <td><b>{row.city}</b></td>
                    <td>{row.mean.toFixed(2)}</td>
                    <td>{row.median.toFixed(2)}</td>
                    <td>{row.std.toFixed(2)}</td>
                    <td>{row.maximum.toFixed(2)}</td>
                    <td>{row.valid_days.toLocaleString()}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <p className="text-xs mt-2" style={{ color: 'var(--color-muted)' }}>
            Standard deviation uses sample formula (ddof=1). Units: µg/m³.
          </p>
        </div>
      </div>

      {/* Coverage table */}
      <div className="card mb-5">
        <div className="section-title">Data coverage and gaps</div>
        <div style={{ overflowX: 'auto' }}>
          <table className="data-table">
            <thead>
              <tr>
                <th>City</th>
                <th>First date</th>
                <th>Last date</th>
                <th>Rows</th>
                <th>Valid PM2.5 days</th>
                <th>Missing PM2.5</th>
                <th>Avg stations</th>
              </tr>
            </thead>
            <tbody>
              {coverage.map(row => (
                <tr key={row.city}>
                  <td><b>{row.city}</b></td>
                  <td>{row.first_date}</td>
                  <td>{row.last_date}</td>
                  <td>{row.available_rows.toLocaleString()}</td>
                  <td>{row.valid_pm25_days.toLocaleString()}</td>
                  <td>
                    {row.missing_pm25_rows > 0
                      ? <span className="pill pill-warn">{row.missing_pm25_rows}</span>
                      : <span className="pill">0</span>
                    }
                  </td>
                  <td>{row.avg_station_count != null ? row.avg_station_count.toFixed(2) : '—'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Interpretation note */}
      <div className="card" style={{ borderLeft: '4px solid #16a36a' }}>
        <div className="section-title text-sm">How to interpret these results</div>
        <p className="text-sm" style={{ color: 'var(--color-muted)', lineHeight: 1.7 }}>
          The mean can be influenced by unusually high values; the median is more robust to extremes.
          Standard deviation describes variability, not whether a city is safe or unsafe.
          City-level station averages are not population-weighted exposure estimates.
          Different date coverage can affect direct comparisons between cities.
        </p>
      </div>
    </div>
  );
}
