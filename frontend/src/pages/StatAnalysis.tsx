import { useEffect, useState } from 'react';
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, Cell, ReferenceLine,
} from 'recharts';
import { api } from '../api';
import type { StatisticsAnalysis } from '../api';
import { useDatasetId } from '../context/DatasetContext';

// ── Helpers ──────────────────────────────────────────────────────────────────
function fmt(v: number | null | undefined, d = 2) {
  return v == null || Number.isNaN(v) ? '—' : v.toFixed(d);
}

function PBadge({ p, display }: { p: number | null; display: string }) {
  if (p == null) return <span style={{ color: '#9aaa9f' }}>N/A</span>;
  const sig = p < 0.05;
  return (
    <span style={{
      background: sig ? '#dcfce7' : '#fff3cd',
      color: sig ? '#15803d' : '#92400e',
      padding: '2px 8px', borderRadius: 10, fontSize: 11, fontWeight: 700,
    }}>
      {display}
    </span>
  );
}

function StatRow({ label, value, sub }: { label: string; value: string; sub?: string }) {
  return (
    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline',
                  padding: '7px 0', borderBottom: '1px solid #f0f4f1' }}>
      <span style={{ fontSize: 12.5, color: '#4a6358' }}>{label}</span>
      <span style={{ fontSize: 13, fontWeight: 700, color: '#163b2b' }}>
        {value}
        {sub && <span style={{ fontSize: 10.5, fontWeight: 400, color: '#9aaa9f', marginLeft: 4 }}>{sub}</span>}
      </span>
    </div>
  );
}

function TTestCard({ result, title }: {
  result: StatisticsAnalysis['ttest_who_annual'];
  title: string;
}) {
  const sig = result.reject_null;
  return (
    <div style={{
      border: `2px solid ${sig ? '#16a36a' : '#f59e0b'}`,
      borderRadius: 12, padding: '16px 18px',
      background: sig ? '#f0fdf4' : '#fffbeb',
    }}>
      <div style={{ fontWeight: 700, fontSize: 13, color: '#163b2b', marginBottom: 4 }}>{title}</div>
      <div style={{ fontSize: 11.5, color: '#6b7c74', marginBottom: 10 }}>
        H₀: {result.null_hypothesis}
      </div>
      <div className="grid grid-cols-2 gap-2" style={{ marginBottom: 10 }}>
        <div>
          <div style={{ fontSize: 10, color: '#9aaa9f' }}>t-statistic</div>
          <div style={{ fontWeight: 700, fontSize: 14 }}>{fmt(result.t_statistic, 3)}</div>
        </div>
        <div>
          <div style={{ fontSize: 10, color: '#9aaa9f' }}>p-value</div>
          <PBadge p={result.p_value} display={result.p_display} />
        </div>
        <div>
          <div style={{ fontSize: 10, color: '#9aaa9f' }}>Cohen's d</div>
          <div style={{ fontWeight: 700, fontSize: 14 }}>
            {result.cohens_d != null ? fmt(result.cohens_d, 3) : '—'}
            {result.cohens_d != null && (
              <span style={{ fontSize: 10, color: '#9aaa9f', marginLeft: 4 }}>
                ({result.effect_size_label})
              </span>
            )}
          </div>
        </div>
        <div>
          <div style={{ fontSize: 10, color: '#9aaa9f' }}>Decision</div>
          <span style={{
            background: sig ? '#dcfce7' : '#fff3cd', color: sig ? '#15803d' : '#92400e',
            fontSize: 10.5, fontWeight: 700, padding: '2px 8px', borderRadius: 8,
          }}>
            {sig ? 'Reject H₀' : 'Fail to reject H₀'}
          </span>
        </div>
      </div>
      <p style={{ fontSize: 11, color: '#4a6358', lineHeight: 1.6, margin: 0 }}>
        {result.conclusion}
      </p>
    </div>
  );
}

// ── Main component ────────────────────────────────────────────────────────────
type Tab = 'summary' | 'distribution' | 'tests' | 'seasonal';

export default function StatAnalysis() {
  const datasetId = useDatasetId();

  const [data, setData]   = useState<StatisticsAnalysis | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError]   = useState<string | null>(null);
  const [tab, setTab]       = useState<Tab>('summary');

  useEffect(() => {
    if (!datasetId) return;
    setLoading(true);
    setError(null);
    api.getStatisticsAnalysis(datasetId)
      .then(d => { setData(d); setLoading(false); })
      .catch(e => { setError(String(e)); setLoading(false); });
  }, [datasetId]);

  if (loading) return <div className="p-7"><div className="msg-info">Running statistical analysis…</div></div>;
  if (error)   return <div className="p-7"><div className="msg-error">{error}</div></div>;
  if (!data)   return null;

  const { descriptive, normality, ttest_who_annual, ttest_india_naaqs,
          confidence_interval_95: ci, seasonal_anova: anova,
          histogram, reference_values } = data;

  // Histogram chart data
  const histData = histogram.counts.map((count, i) => ({
    bin: `${histogram.bins[i].toFixed(0)}–${histogram.bins[i + 1]?.toFixed(0) ?? ''}`,
    count,
    start: histogram.bins[i],
  }));
  const WHO_THRESHOLD = reference_values.who_annual_guideline_ug_m3;
  const NAAQS_THRESHOLD = reference_values.india_naaqs_annual_ug_m3;

  // Seasonal data for bar chart
  const seasonalData = Object.entries(anova.group_stats).map(([q, s]) => ({
    quarter: q.replace(' (', '\n('), mean: s.mean, n: s.n, std: s.std,
  }));

  return (
    <div className="p-7 max-w-5xl mx-auto">
      {/* Header */}
      <div className="mb-6">
        <div className="text-xs font-bold uppercase tracking-widest mb-1" style={{ color: '#16a36a' }}>
          INFERENTIAL STATISTICS
        </div>
        <h1 className="text-2xl font-black" style={{ fontFamily: 'Manrope, sans-serif', color: '#163b2b' }}>
          Statistical Analysis
          <span style={{ fontSize: 14, fontWeight: 400, color: '#9aaa9f', marginLeft: 10 }}>
            {data.dataset_name}
          </span>
        </h1>
        <p className="text-sm mt-1" style={{ color: 'var(--color-muted)' }}>
          Descriptive statistics, normality tests, WHO guideline comparisons, confidence intervals and seasonal ANOVA.
        </p>
      </div>

      {/* Tab nav */}
      <div className="flex gap-1 mb-6" style={{ borderBottom: '2px solid #e1ece5', paddingBottom: 0 }}>
        {([
          ['summary', '📋 Summary'],
          ['distribution', '📊 Distribution'],
          ['tests', '🔬 Hypothesis Tests'],
          ['seasonal', '📅 Seasonal ANOVA'],
        ] as [Tab, string][]).map(([t, label]) => (
          <button
            key={t}
            onClick={() => setTab(t)}
            style={{
              background: 'none', border: 'none', cursor: 'pointer',
              padding: '10px 16px', fontSize: 12.5, fontWeight: tab === t ? 700 : 500,
              color: tab === t ? '#16a36a' : '#6b7c74',
              borderBottom: tab === t ? '3px solid #16a36a' : '3px solid transparent',
              marginBottom: -2, transition: 'all 0.15s',
            }}
          >
            {label}
          </button>
        ))}
      </div>

      {/* ── SUMMARY TAB ──────────────────────────────────────────────────────── */}
      {tab === 'summary' && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
          <div className="card">
            <div className="section-title">Descriptive statistics (PM2.5 µg/m³)</div>
            <StatRow label="n (valid observations)" value={descriptive.n.toLocaleString()} />
            <StatRow label="Mean" value={fmt(descriptive.mean)} sub="µg/m³" />
            <StatRow label="Median" value={fmt(descriptive.median)} sub="µg/m³" />
            <StatRow label="Std. deviation (sample)" value={fmt(descriptive.std)} sub="µg/m³" />
            <StatRow label="SEM" value={fmt(descriptive.sem, 4)} sub="µg/m³" />
            <StatRow label="Min" value={fmt(descriptive.min)} sub="µg/m³" />
            <StatRow label="Max" value={fmt(descriptive.max)} sub="µg/m³" />
            <StatRow label="Q1 (25th percentile)" value={fmt(descriptive.q1)} />
            <StatRow label="Q3 (75th percentile)" value={fmt(descriptive.q3)} />
            <StatRow label="IQR (Q3 − Q1)" value={fmt(descriptive.iqr)} />
            <StatRow label="Skewness" value={fmt(descriptive.skewness, 4)} />
            <StatRow label="Excess kurtosis" value={fmt(descriptive.kurtosis_excess, 4)} />
            <StatRow label="Coefficient of variation" value={`${fmt(descriptive.cv_pct, 1)}%`} />
          </div>
          <div className="flex flex-col gap-4">
            {/* Confidence interval */}
            <div className="card" style={{ borderLeft: '4px solid #16a36a' }}>
              <div className="section-title text-sm">95% Confidence interval (mean)</div>
              <div style={{ fontSize: 20, fontWeight: 800, color: '#16a36a', margin: '6px 0' }}>
                [{fmt(ci.lower)} — {fmt(ci.upper)}] µg/m³
              </div>
              <p style={{ fontSize: 11.5, color: '#6b7c74', lineHeight: 1.6 }}>
                {ci.interpretation}
              </p>
            </div>
            {/* Normality */}
            <div className="card" style={{ borderLeft: `4px solid ${normality.is_normal ? '#16a36a' : '#f59e0b'}` }}>
              <div className="section-title text-sm">Normality ({normality.test})</div>
              <div style={{ marginBottom: 6 }}>
                <PBadge p={normality.p_value} display={normality.p_display} />
                <span style={{ marginLeft: 8, fontSize: 12, fontWeight: 600,
                               color: normality.is_normal ? '#16a36a' : '#d97706' }}>
                  {normality.is_normal === null ? 'N/A' : normality.is_normal ? 'Normal' : 'Not normal'}
                </span>
              </div>
              <p style={{ fontSize: 11.5, color: '#6b7c74', lineHeight: 1.6 }}>
                {normality.conclusion}
              </p>
            </div>
            {/* Interpretation note */}
            <div className="card">
              <div className="section-title text-sm">Distribution interpretation</div>
              <p style={{ fontSize: 12, color: '#6b7c74', lineHeight: 1.7 }}>
                {descriptive.interpretation}
              </p>
            </div>
          </div>
        </div>
      )}

      {/* ── DISTRIBUTION TAB ─────────────────────────────────────────────────── */}
      {tab === 'distribution' && (
        <div className="card">
          <div className="section-title">PM2.5 concentration distribution</div>
          <p className="text-xs mb-3" style={{ color: 'var(--color-muted)' }}>
            Each bar represents {fmt(histogram.bin_width, 1)} µg/m³ bin width.
            Reference lines show WHO annual guideline ({WHO_THRESHOLD} µg/m³) and
            India NAAQS ({NAAQS_THRESHOLD} µg/m³).
          </p>
          <ResponsiveContainer width="100%" height={320}>
            <BarChart data={histData} margin={{ top: 4, right: 12, left: 0, bottom: 24 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#e8f0ec" />
              <XAxis
                dataKey="start"
                type="number"
                domain={['dataMin', 'dataMax']}
                tickFormatter={(v: number) => v.toFixed(0)}
                tick={{ fontSize: 10, fill: '#6b7c74' }}
                label={{ value: 'PM2.5 (µg/m³)', position: 'insideBottom', offset: -16, fontSize: 11 }}
              />
              <YAxis tick={{ fontSize: 10, fill: '#6b7c74' }} tickLine={false} axisLine={false} />
              <Tooltip
                formatter={(v: any) => [v, 'Count']}
                labelFormatter={(v: any) => `${Number(v).toFixed(0)}–${(Number(v) + histogram.bin_width).toFixed(0)} µg/m³`}
                contentStyle={{ fontSize: 12, borderRadius: 8 }}
              />
              <ReferenceLine x={WHO_THRESHOLD} stroke="#16a36a" strokeDasharray="4 2"
                label={{ value: 'WHO', position: 'top', fontSize: 10, fill: '#16a36a' }} />
              <ReferenceLine x={NAAQS_THRESHOLD} stroke="#d97706" strokeDasharray="4 2"
                label={{ value: 'NAAQS', position: 'top', fontSize: 10, fill: '#d97706' }} />
              <Bar dataKey="count" radius={[3, 3, 0, 0]}>
                {histData.map((entry, i) => (
                  <Cell key={i} fill={entry.start > NAAQS_THRESHOLD ? '#dc2626' : entry.start > WHO_THRESHOLD ? '#d97706' : '#16a36a'} fillOpacity={0.75} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
          <div className="flex gap-4 mt-2 text-xs" style={{ color: 'var(--color-muted)' }}>
            <span>🟢 Below WHO {WHO_THRESHOLD} µg/m³</span>
            <span>🟡 Below NAAQS {NAAQS_THRESHOLD} µg/m³</span>
            <span>🔴 Above NAAQS</span>
          </div>
        </div>
      )}

      {/* ── HYPOTHESIS TESTS TAB ─────────────────────────────────────────────── */}
      {tab === 'tests' && (
        <div className="flex flex-col gap-5">
          <div className="card" style={{ borderLeft: '4px solid #1e5c8e' }}>
            <div className="section-title text-sm">About one-sample t-tests</div>
            <p style={{ fontSize: 12, color: '#6b7c74', lineHeight: 1.7 }}>
              A one-sample t-test tests whether the population mean differs from a reference value (µ₀).
              H₀: μ = μ₀. The test statistic t = (x̄ − μ₀) / (s / √n).
              p &lt; 0.05 indicates the difference is statistically significant at the 5% level.
              Cohen's d = (x̄ − μ₀) / s measures practical effect size.
            </p>
          </div>
          <TTestCard result={ttest_who_annual} title="Test 1: vs WHO 2021 Annual Guideline (15 µg/m³)" />
          <TTestCard result={ttest_india_naaqs} title="Test 2: vs India NAAQS Annual Standard (40 µg/m³)" />
          <div className="card" style={{ fontSize: 11, color: 'var(--color-muted)', lineHeight: 1.8 }}>
            <b>Limitations:</b> Statistical significance ≠ practical importance. A very large sample can produce
            significant results for practically trivial differences. Always interpret alongside effect size (Cohen's d).
            These tests assume observations are approximately independent — in a time series,
            consecutive days are autocorrelated, so treat p-values as approximate.
          </div>
        </div>
      )}

      {/* ── SEASONAL ANOVA TAB ───────────────────────────────────────────────── */}
      {tab === 'seasonal' && (
        <div className="flex flex-col gap-5">
          <div className="card">
            <div className="section-title">One-way ANOVA: seasonal PM2.5 differences</div>
            <p className="text-xs mb-4" style={{ color: 'var(--color-muted)' }}>
              H₀: All quarterly means are equal. H₁: At least one quarterly mean differs.
              Groups: Q1 (Jan–Mar), Q2 (Apr–Jun), Q3 (Jul–Sep), Q4 (Oct–Dec).
            </p>
            {anova.f_statistic != null ? (
              <>
                <div className="grid grid-cols-3 gap-4 mb-4">
                  <div className="kpi-card">
                    <div className="kpi-label">F-statistic</div>
                    <div className="kpi-value">{fmt(anova.f_statistic, 3)}</div>
                  </div>
                  <div className="kpi-card">
                    <div className="kpi-label">p-value (ANOVA)</div>
                    <div style={{ marginTop: 4 }}>
                      <PBadge p={anova.p_value} display={anova.p_display ?? '—'} />
                    </div>
                  </div>
                  {anova.kruskal_wallis && (
                    <div className="kpi-card">
                      <div className="kpi-label">Kruskal-Wallis H</div>
                      <div className="kpi-value">{fmt(anova.kruskal_wallis.statistic, 3)}</div>
                      <div className="kpi-sub">
                        <PBadge p={anova.kruskal_wallis.p_value} display={anova.kruskal_wallis.p_display} />
                      </div>
                    </div>
                  )}
                </div>
                <ResponsiveContainer width="100%" height={260}>
                  <BarChart data={seasonalData} margin={{ top: 4, right: 12, left: 0, bottom: 0 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#e8f0ec" />
                    <XAxis dataKey="quarter" tick={{ fontSize: 11, fill: '#6b7c74' }} />
                    <YAxis tick={{ fontSize: 11, fill: '#6b7c74' }} tickLine={false} axisLine={false}
                      label={{ value: 'Mean PM2.5 (µg/m³)', angle: -90, position: 'insideLeft', offset: 8, style: { fontSize: 10 } }} />
                    <Tooltip
                      formatter={(v: any, _: any, props: any) => [
                        `${Number(v).toFixed(2)} µg/m³ (n=${props?.payload?.n}, std=${props?.payload?.std?.toFixed(1)})`,
                        'Mean PM2.5',
                      ]}
                      contentStyle={{ fontSize: 12, borderRadius: 8 }}
                    />
                    <Bar dataKey="mean" radius={[4, 4, 0, 0]}>
                      {seasonalData.map((_, i) => (
                        <Cell key={i} fill={['#16a36a', '#6488c6', '#e09b2f', '#e06c6c'][i % 4]} fillOpacity={0.8} />
                      ))}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
                <p className="text-sm mt-3" style={{ color: '#4a6358', lineHeight: 1.7 }}>
                  {anova.conclusion}
                </p>
              </>
            ) : (
              <div className="msg-info">{anova.conclusion}</div>
            )}
          </div>
          <div className="card" style={{ fontSize: 11.5, color: 'var(--color-muted)', lineHeight: 1.8 }}>
            <b>Limitations:</b> ANOVA assumes (1) independent observations within groups,
            (2) approximate normality within each group, (3) equal variances (homoscedasticity).
            PM2.5 time-series data violates independence — treat results as exploratory,
            not confirmatory. Kruskal-Wallis is a non-parametric alternative that does not
            assume normality.
          </div>
        </div>
      )}
    </div>
  );
}
