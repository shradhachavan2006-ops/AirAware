import { useEffect, useState } from 'react';
import {
  ScatterChart, Scatter, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, ReferenceLine, LineChart, Line,
} from 'recharts';
import { api } from '../api';
import type { RegressionAnalysis } from '../api';
import { useDatasetId } from '../context/DatasetContext';

function fmt(v: number | null | undefined, d = 4) {
  return v == null || Number.isNaN(v as number) ? '—' : (v as number).toFixed(d);
}

function SigBadge({ sig }: { sig: string }) {
  const styles: Record<string, React.CSSProperties> = {
    '***': { background: '#dcfce7', color: '#166534' },
    '**':  { background: '#d1fae5', color: '#065f46' },
    '*':   { background: '#fef9c3', color: '#854d0e' },
    'ns':  { background: '#f3f4f6', color: '#6b7280' },
    '—':   { background: '#f3f4f6', color: '#9ca3af' },
  };
  return (
    <span style={{ ...(styles[sig] ?? styles['—']), padding: '2px 8px', borderRadius: 8, fontSize: 11, fontWeight: 700 }}>
      {sig}
    </span>
  );
}

const CORR_COLORS = ['#2563eb', '#0891b2', '#16a34a', '#ca8a04'];

type Tab = 'correlation' | 'simple' | 'multiple';

export default function Regression() {
  const datasetId = useDatasetId();

  const [data, setData]     = useState<RegressionAnalysis | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError]   = useState<string | null>(null);
  const [tab, setTab]       = useState<Tab>('correlation');

  useEffect(() => {
    if (!datasetId) return;
    setLoading(true);
    setError(null);
    api.getRegressionAnalysis(datasetId)
      .then(d => { setData(d); setLoading(false); })
      .catch(e => { setError(String(e)); setLoading(false); });
  }, [datasetId]);

  if (loading) return <div className="p-7"><div className="msg-info">Building regression model…</div></div>;
  if (error)   return <div className="p-7"><div className="msg-error">{error}</div></div>;
  if (!data)   return null;

  const { correlation, simple_regression: slr, multiple_regression: mlr } = data;

  const features = Object.keys(correlation);
  const corrMax = Math.max(...Object.values(correlation).map(c => Math.abs(c.r ?? 0)));

  return (
    <div className="p-7 max-w-5xl mx-auto">
      {/* Header */}
      <div className="mb-6">
        <div className="text-xs font-bold uppercase tracking-widest mb-1" style={{ color: '#16a36a' }}>
          REGRESSION STUDIO
        </div>
        <h1 className="text-2xl font-black" style={{ fontFamily: 'Manrope, sans-serif', color: '#163b2b' }}>
          Regression Analysis
          <span style={{ fontSize: 14, fontWeight: 400, color: '#9aaa9f', marginLeft: 10 }}>
            {data.dataset_name}
          </span>
        </h1>
        <p className="text-sm mt-1" style={{ color: 'var(--color-muted)' }}>
          Target: <b>next-day PM2.5</b> (µg/m³). Features are lag and rolling-mean values built
          without look-ahead. n = {data.n_samples.toLocaleString()} complete rows.
        </p>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 mb-6" style={{ borderBottom: '2px solid #e1ece5' }}>
        {([
          ['correlation', '🔗 Correlation'],
          ['simple', '📈 Simple Regression'],
          ['multiple', '📉 Multiple Regression'],
        ] as [Tab, string][]).map(([t, label]) => (
          <button key={t} onClick={() => setTab(t)} style={{
            background: 'none', border: 'none', cursor: 'pointer',
            padding: '10px 16px', fontSize: 12.5, fontWeight: tab === t ? 700 : 500,
            color: tab === t ? '#16a36a' : '#6b7c74',
            borderBottom: tab === t ? '3px solid #16a36a' : '3px solid transparent',
            marginBottom: -2, transition: 'all 0.15s',
          }}>
            {label}
          </button>
        ))}
      </div>

      {/* ── CORRELATION ────────────────────────────────────────────────────── */}
      {tab === 'correlation' && (
        <div className="flex flex-col gap-5">
          <div className="card">
            <div className="section-title">Pearson correlation with next-day PM2.5</div>
            <p className="text-xs mb-4" style={{ color: 'var(--color-muted)' }}>
              How strongly each feature is linearly associated with tomorrow's PM2.5.
              Correlation coefficient r ranges from −1 (perfect negative) to +1 (perfect positive).
            </p>

            {/* Visual correlation bars */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: 10, marginBottom: 16 }}>
              {features.map((f, i) => {
                const c = correlation[f];
                const r = c.r ?? 0;
                const barPct = Math.abs(r) / (corrMax || 1) * 85;
                return (
                  <div key={f} style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                    <div style={{ width: 120, fontSize: 11, color: '#4a6358', textAlign: 'right', flexShrink: 0 }}>
                      {f.replace(/_/g, ' ')}
                    </div>
                    <div style={{ flex: 1, height: 22, background: '#f0f4f1', borderRadius: 4, overflow: 'hidden' }}>
                      <div style={{
                        width: `${barPct}%`, height: '100%',
                        background: CORR_COLORS[i % CORR_COLORS.length],
                        opacity: 0.75, borderRadius: 4,
                        transition: 'width 0.4s ease',
                      }} />
                    </div>
                    <div style={{ width: 48, fontSize: 12, fontWeight: 700, color: '#163b2b', textAlign: 'right' }}>
                      {fmt(r, 3)}
                    </div>
                    <div style={{ width: 60 }}>
                      <SigBadge sig={c.significance} />
                    </div>
                  </div>
                );
              })}
            </div>

            {/* Correlation table */}
            <div style={{ overflowX: 'auto' }}>
              <table className="data-table">
                <thead>
                  <tr><th>Feature</th><th>r</th><th>r²</th><th>p-value</th><th>Sig.</th><th>Interpretation</th></tr>
                </thead>
                <tbody>
                  {features.map(f => {
                    const c = correlation[f];
                    return (
                      <tr key={f}>
                        <td><code style={{ fontSize: 11 }}>{f}</code></td>
                        <td style={{ fontWeight: 700 }}>{fmt(c.r, 4)}</td>
                        <td>{fmt(c.r_squared, 4)}</td>
                        <td>{c.p_display}</td>
                        <td><SigBadge sig={c.significance} /></td>
                        <td style={{ fontSize: 11, color: '#6b7c74' }}>{c.interpretation}</td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
            <p className="text-xs mt-2" style={{ color: 'var(--color-muted)' }}>
              *** p &lt; 0.001 · ** p &lt; 0.01 · * p &lt; 0.05 · ns = not significant
            </p>
          </div>

          <div className="card" style={{ fontSize: 12, color: '#4a6358', lineHeight: 1.7 }}>
            <b>Note:</b> Pearson correlation measures linear association only.
            High autocorrelation in time-series data (today's PM2.5 predicting tomorrow's)
            is expected and does not imply a causal mechanism.
            Correlation ≠ causation.
          </div>
        </div>
      )}

      {/* ── SIMPLE REGRESSION ─────────────────────────────────────────────── */}
      {tab === 'simple' && (
        <div className="flex flex-col gap-5">
          {/* Equation banner */}
          <div style={{
            background: 'linear-gradient(115deg,#0f4c2a,#2d6a4f)',
            borderRadius: 12, padding: '16px 20px', color: '#fff',
          }}>
            <div style={{ fontSize: 11, color: '#6ee7b7', marginBottom: 4 }}>REGRESSION EQUATION</div>
            <div style={{ fontFamily: 'monospace', fontSize: 18, fontWeight: 700 }}>
              {slr.equation}
            </div>
            <div style={{ fontSize: 12, color: 'rgba(255,255,255,0.7)', marginTop: 4 }}>
              R² = {fmt(slr.r_squared, 4)} · p {slr.p_display} · SE(slope) = {fmt(slr.std_error, 6)}
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
            {/* Scatter plot */}
            <div className="card">
              <div className="section-title">Scatter: lag_1 vs next-day PM2.5</div>
              <p className="text-xs mb-2" style={{ color: 'var(--color-muted)' }}>
                Green line = regression fit. Dashed = identity (perfect prediction).
              </p>
              <ResponsiveContainer width="100%" height={240}>
                <ScatterChart margin={{ top: 4, right: 12, left: 0, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#e8f0ec" />
                  <XAxis dataKey="x" name="lag_1 (today)" type="number"
                    tick={{ fontSize: 10 }} label={{ value: 'Today PM2.5', position: 'insideBottom', offset: -4, fontSize: 10 }} />
                  <YAxis dataKey="y" name="actual next-day" type="number"
                    tick={{ fontSize: 10 }} tickLine={false} axisLine={false} />
                  <Tooltip cursor={false} contentStyle={{ fontSize: 11, borderRadius: 8 }}
                    formatter={(v: any, name: any) => [Number(v).toFixed(2), String(name)]} />
                  <Scatter data={slr.scatter_data.map(p => ({ x: p.x, y: p.y }))}
                    fill="#16a36a" fillOpacity={0.45} r={3} />
                  {/* Regression line via Line layer trick using reference lines */}
                </ScatterChart>
              </ResponsiveContainer>
              {/* Simple regression line as a LineChart overlay on the same data */}
              <ResponsiveContainer width="100%" height={120}>
                <LineChart
                  data={[...slr.scatter_data].sort((a, b) => a.x - b.x)}
                  margin={{ top: 0, right: 12, left: 0, bottom: 0 }}
                >
                  <XAxis dataKey="x" hide />
                  <YAxis hide />
                  <Line dataKey="predicted" stroke="#16a36a" strokeWidth={2} dot={false} name="Predicted" />
                </LineChart>
              </ResponsiveContainer>
              <p style={{ fontSize: 11, color: '#9aaa9f', marginTop: -8 }}>Predicted line (sorted by lag_1)</p>
            </div>

            {/* Residuals */}
            <div className="card">
              <div className="section-title">Residual plot (fitted vs residual)</div>
              <p className="text-xs mb-2" style={{ color: 'var(--color-muted)' }}>
                Well-behaved residuals should scatter randomly around zero (red dashed line).
              </p>
              <ResponsiveContainer width="100%" height={240}>
                <ScatterChart margin={{ top: 4, right: 12, left: 0, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#e8f0ec" />
                  <XAxis dataKey="fitted" name="Fitted" type="number"
                    tick={{ fontSize: 10 }} label={{ value: 'Fitted values', position: 'insideBottom', offset: -4, fontSize: 10 }} />
                  <YAxis dataKey="residual" name="Residual" type="number"
                    tick={{ fontSize: 10 }} tickLine={false} axisLine={false} />
                  <ReferenceLine y={0} stroke="#dc2626" strokeDasharray="4 2" />
                  <Tooltip cursor={false} contentStyle={{ fontSize: 11, borderRadius: 8 }}
                    formatter={(v: any, name: any) => [Number(v).toFixed(2), String(name)]} />
                  <Scatter data={slr.residual_data} fill="#6488c6" fillOpacity={0.5} r={3} />
                </ScatterChart>
              </ResponsiveContainer>
            </div>
          </div>

          <div className="card" style={{ borderLeft: '4px solid #16a36a' }}>
            <div className="section-title text-sm">Interpretation</div>
            <p style={{ fontSize: 12.5, color: '#4a6358', lineHeight: 1.7 }}>
              {slr.interpretation}
            </p>
          </div>
        </div>
      )}

      {/* ── MULTIPLE REGRESSION ───────────────────────────────────────────── */}
      {tab === 'multiple' && (
        <div className="flex flex-col gap-5">
          {/* R² cards */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div className="kpi-card">
              <div className="kpi-label">R²</div>
              <div className="kpi-value">{fmt(mlr.r_squared, 4)}</div>
              <div className="kpi-sub">Variance explained</div>
            </div>
            <div className="kpi-card">
              <div className="kpi-label">Adjusted R²</div>
              <div className="kpi-value">{fmt(mlr.adjusted_r_squared, 4)}</div>
            </div>
            <div className="kpi-card">
              <div className="kpi-label">RMSE</div>
              <div className="kpi-value">{fmt(mlr.rmse, 2)}</div>
              <div className="kpi-sub">µg/m³</div>
            </div>
            <div className="kpi-card">
              <div className="kpi-label">n samples</div>
              <div className="kpi-value">{mlr.n.toLocaleString()}</div>
            </div>
          </div>

          {/* Coefficient table */}
          <div className="card">
            <div className="section-title">OLS coefficient table</div>
            <p className="text-xs mb-3" style={{ color: 'var(--color-muted)' }}>
              SE and p-values computed via design-matrix formula: SE = √(MSE · diag((X'X)⁻¹)).
              Two-tailed t-tests. Features: {mlr.features.join(', ')}.
            </p>
            <div style={{ overflowX: 'auto' }}>
              <table className="data-table">
                <thead>
                  <tr><th>Term</th><th>Coefficient</th><th>p-value</th><th>Sig.</th></tr>
                </thead>
                <tbody>
                  {mlr.coefficients.map(coef => (
                    <tr key={coef.feature}>
                      <td><code style={{ fontSize: 11 }}>{coef.feature}</code></td>
                      <td style={{ fontWeight: 600 }}>{fmt(coef.coefficient, 6)}</td>
                      <td>{coef.p_display}</td>
                      <td><SigBadge sig={coef.significance} /></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <p className="text-xs mt-2" style={{ color: 'var(--color-muted)' }}>
              {mlr.significance_note}
            </p>
          </div>

          {/* Actual vs predicted */}
          <div className="card">
            <div className="section-title">Actual vs predicted (sample)</div>
            <ResponsiveContainer width="100%" height={260}>
              <LineChart data={mlr.actual_vs_predicted} margin={{ top: 4, right: 12, left: 0, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#e8f0ec" />
                <XAxis dataKey="index" tick={{ fontSize: 10 }} label={{ value: 'Sample index', position: 'insideBottom', offset: -4, fontSize: 10 }} />
                <YAxis tick={{ fontSize: 10 }} tickLine={false} axisLine={false}
                  label={{ value: 'PM2.5 (µg/m³)', angle: -90, position: 'insideLeft', offset: 8, style: { fontSize: 10 } }} />
                <Tooltip contentStyle={{ fontSize: 11, borderRadius: 8 }}
                  formatter={(v: any) => [Number(v).toFixed(2) + ' µg/m³']} />
                <Line dataKey="actual" stroke="#163b2b" strokeWidth={1.5} dot={false} name="Actual" />
                <Line dataKey="predicted" stroke="#16a36a" strokeWidth={1.5} dot={false} name="Predicted" strokeDasharray="4 2" />
              </LineChart>
            </ResponsiveContainer>
          </div>

          <div className="card" style={{ borderLeft: '4px solid #16a36a' }}>
            <div className="section-title text-sm">Interpretation</div>
            <p style={{ fontSize: 12.5, color: '#4a6358', lineHeight: 1.7 }}>
              {mlr.interpretation}
            </p>
            <p className="text-xs mt-3" style={{ color: 'var(--color-muted)', lineHeight: 1.7 }}>
              <b>Methodology:</b> {data.methodology_note}
            </p>
          </div>
        </div>
      )}
    </div>
  );
}
