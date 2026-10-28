import { useEffect, useState } from 'react';
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid,
  Tooltip, Legend, ResponsiveContainer,
} from 'recharts';
import { api } from '../api';
import type { EvaluationCity, EvaluationCities } from '../api';

const MODEL_COLORS: Record<string, string> = {
  Persistence:   '#14532d',
  RandomForest:  '#e69b48',
};

function fmt(v: unknown, dec = 2) {
  if (v == null || typeof v !== 'number') return '—';
  return v.toFixed(dec);
}

function MetricCard({ model, metrics }: { model: string; metrics: Record<string, unknown> }) {
  const mae  = metrics['MAE']  as number | null;
  const rmse = metrics['RMSE'] as number | null;
  const r2   = metrics['R2']   as number | null;
  const color = MODEL_COLORS[model] ?? '#16a36a';

  return (
    <div className="kpi-card" style={{ borderTop: `3px solid ${color}` }}>
      <div className="kpi-label" style={{ color }}>{model}</div>
      <div className="kpi-value" style={{ fontSize: '1.3rem' }}>
        {mae != null ? mae.toFixed(2) : '—'} <span className="text-xs font-normal" style={{ color: 'var(--color-muted)' }}>µg/m³ MAE</span>
      </div>
      <div className="kpi-sub mt-1">RMSE: {fmt(rmse)} µg/m³</div>
      <div className="kpi-sub">R²: {r2 != null ? r2.toFixed(3) : '—'}{r2 != null && r2 < 0 ? ' ⚠ negative' : ''}</div>
    </div>
  );
}

function downloadCSV(rows: Record<string, unknown>[], filename: string) {
  if (!rows.length) return;
  const cols = Object.keys(rows[0]);
  const csv = [cols.join(','), ...rows.map(r => cols.map(c => r[c] ?? '').join(','))].join('\n');
  const a = document.createElement('a');
  a.href = 'data:text/csv,' + encodeURIComponent(csv);
  a.download = filename;
  a.click();
}

export default function Evaluation() {
  const [meta, setMeta] = useState<EvaluationCities | null>(null);
  const [city, setCity] = useState('');
  const [cityData, setCityData] = useState<EvaluationCity | null>(null);
  const [selectedModel, setSelectedModel] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.getEvaluationCities()
      .then(m => {
        setMeta(m);
        const initial = m.cities.includes('Pune') ? 'Pune' : m.cities[0] ?? '';
        setCity(initial);
      })
      .catch(e => setError(String(e)));
  }, []);

  useEffect(() => {
    if (!city) return;
    setLoading(true);
    setError(null);
    api.getCityEvaluation(city)
      .then(d => {
        setCityData(d);
        setSelectedModel(d.metrics[0]?.['model'] as string ?? '');
        setLoading(false);
      })
      .catch(e => { setError(String(e)); setLoading(false); });
  }, [city]);

  // Merge actual + all model predictions into flat chart data
  const chartData = (() => {
    if (!cityData) return [];
    const map = new Map<string, Record<string, number | null>>();
    for (const pt of cityData.chart_data.actual) {
      map.set(pt.date, { date: pt.date, Actual: pt.actual_pm25 });
    }
    for (const ms of cityData.chart_data.models) {
      for (const pt of ms.data) {
        if (!map.has(pt.date)) map.set(pt.date, { date: pt.date, Actual: null });
        map.get(pt.date)![ms.model] = pt.predicted_pm25;
      }
    }
    return Array.from(map.values()).sort((a, b) => String(a.date) < String(b.date) ? -1 : 1);
  })();

  const modelNames = cityData ? Object.keys(cityData.prediction_records) : [];
  const tableRows = selectedModel && cityData ? cityData.prediction_records[selectedModel] ?? [] : [];

  return (
    <div className="p-7 max-w-6xl mx-auto">
      {/* Header */}
      <div className="mb-6">
        <div className="text-xs font-bold uppercase tracking-widest mb-1" style={{ color: '#16a36a' }}>MODEL EVALUATION</div>
        <h1 className="text-2xl font-black" style={{ fontFamily: 'Manrope, sans-serif', color: '#163b2b' }}>
          Forecasts under the microscope
        </h1>
        <p className="text-sm mt-1" style={{ color: 'var(--color-muted)' }}>
          Historical test-set performance for next-day PM2.5 models. These are retrospective predictions, not live forecasts.
        </p>
      </div>

      {error && <div className="msg-error mb-4">{error}</div>}

      {/* City selector */}
      <div className="card mb-6 flex flex-wrap gap-5 items-end">
        <div>
          <label className="form-label">Evaluation city</label>
          <select className="form-control w-44" value={city} onChange={e => setCity(e.target.value)}>
            {(meta?.cities ?? []).map(c => <option key={c}>{c}</option>)}
          </select>
        </div>
        {cityData?.test_window && (
          <div className="text-sm" style={{ color: 'var(--color-muted)' }}>
            Test window: <b>{cityData.test_window.start}</b> – <b>{cityData.test_window.end}</b>
            {cityData.test_window.max_samples != null && ` · up to ${cityData.test_window.max_samples} samples`}
          </div>
        )}
      </div>

      {loading && <div className="msg-info mb-4">Loading…</div>}

      {/* Model scorecard */}
      {cityData && (
        <>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6">
            {cityData.metrics.map((m, i) => (
              <MetricCard key={i} model={m['model'] as string} metrics={m} />
            ))}
          </div>

          {/* RF worse warning */}
          {cityData.rf_worse_than_persistence && (
            <div className="msg-warn mb-5">
              For this city's saved test set, Random Forest has a higher MAE than the persistence baseline.
              Do not assume the more complex model is better; investigate feature quality and generalization.
            </div>
          )}

          {/* Actual vs predicted chart */}
          <div className="card mb-5">
            <div className="section-title">Actual vs predicted PM2.5</div>
            {chartData.length === 0
              ? <div className="msg-info">No valid prediction records available.</div>
              : (
                <ResponsiveContainer width="100%" height={320}>
                  <LineChart data={chartData} margin={{ top: 4, right: 8, left: 0, bottom: 0 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#e8f0ec" />
                    <XAxis dataKey="date" tick={{ fontSize: 11, fill: '#6b7c74' }} tickLine={false} interval="preserveStartEnd" />
                    <YAxis tick={{ fontSize: 11, fill: '#6b7c74' }} tickLine={false} axisLine={false}
                      label={{ value: 'µg/m³', angle: -90, position: 'insideLeft', offset: 10, style: { fontSize: 10, fill: '#9aaa9f' } }} />
                    <Tooltip contentStyle={{ fontSize: 12, borderRadius: 8, border: '1px solid #e0ebe4' }}
                      formatter={(v: number | null) => v == null ? 'N/A' : v.toFixed(2)} />
                    <Legend wrapperStyle={{ fontSize: 12 }} />
                    <Line dataKey="Actual" stroke="#14532d" strokeWidth={2.5} dot={false} connectNulls={false} />
                    {cityData.chart_data.models.map(ms => (
                      <Line key={ms.model} dataKey={ms.model}
                        stroke={MODEL_COLORS[ms.model] ?? '#6488c6'}
                        strokeWidth={2} dot={false} connectNulls={false} strokeDasharray="4 2" />
                    ))}
                  </LineChart>
                </ResponsiveContainer>
              )
            }
          </div>

          {/* Per-model records */}
          <div className="card mb-5">
            <div className="flex justify-between items-center mb-3">
              <div className="section-title mb-0">Prediction records</div>
              <div className="flex gap-3 items-center">
                <select className="form-control w-40" value={selectedModel}
                  onChange={e => setSelectedModel(e.target.value)}>
                  {modelNames.map(m => <option key={m}>{m}</option>)}
                </select>
                <button className="btn btn-outline"
                  onClick={() => downloadCSV(tableRows as Record<string, unknown>[], `${city.toLowerCase()}_${selectedModel.toLowerCase()}_evaluation.csv`)}>
                  ⬇ Download
                </button>
              </div>
            </div>
            <div style={{ overflowX: 'auto', maxHeight: 280, overflowY: 'auto' }}>
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Date</th>
                    <th>Actual (µg/m³)</th>
                    <th>Predicted (µg/m³)</th>
                    <th>Abs. error</th>
                  </tr>
                </thead>
                <tbody>
                  {tableRows.map((row, i) => (
                    <tr key={i}>
                      <td>{row.date}</td>
                      <td>{row.actual_pm25 != null ? row.actual_pm25.toFixed(3) : '—'}</td>
                      <td>{row.predicted_pm25 != null ? row.predicted_pm25.toFixed(3) : '—'}</td>
                      <td>{row.absolute_error != null ? row.absolute_error.toFixed(3) : '—'}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          {/* Disclaimer */}
          <div className="card" style={{ borderLeft: '4px solid #e69b48' }}>
            <div className="section-title text-sm">Important interpretation note</div>
            <p className="text-sm" style={{ color: 'var(--color-muted)', lineHeight: 1.7 }}>
              MAE and RMSE are error measures — lower is better. R² can be negative when a model performs
              worse than predicting the test-set mean. {cityData.disclaimer}
            </p>
          </div>
        </>
      )}
    </div>
  );
}
