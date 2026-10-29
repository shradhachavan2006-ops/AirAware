import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { api } from '../api';
import type { QualityProfile } from '../api';
import { useDatasetId } from '../context/DatasetContext';

function ScoreBadge({ score }: { score: number }) {
  const color = score >= 85 ? '#16a36a' : score >= 60 ? '#d97706' : '#dc2626';
  const label = score >= 85 ? 'Good' : score >= 60 ? 'Fair' : 'Poor';
  return (
    <div style={{
      display: 'inline-flex', alignItems: 'center', gap: 8,
      background: color + '15', border: `2px solid ${color}`,
      borderRadius: 24, padding: '4px 16px',
    }}>
      <div style={{
        width: 10, height: 10, borderRadius: '50%', background: color,
      }} />
      <span style={{ fontWeight: 800, fontSize: 15, color }}>{score}/100</span>
      <span style={{ fontSize: 12, color, fontWeight: 600 }}>{label}</span>
    </div>
  );
}

function SeverityBadge({ severity }: { severity: string }) {
  const styles: Record<string, React.CSSProperties> = {
    error:   { background: '#fee2e2', color: '#dc2626' },
    warning: { background: '#fff3cd', color: '#d97706' },
    info:    { background: '#dbeafe', color: '#1d4ed8' },
  };
  return (
    <span className="pill" style={{ ...(styles[severity] ?? styles.info), fontWeight: 700, fontSize: 10 }}>
      {severity.toUpperCase()}
    </span>
  );
}

export default function DataQuality() {
  const datasetId = useDatasetId();
  const navigate = useNavigate();

  const [profile, setProfile] = useState<QualityProfile | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!datasetId) return;
    setLoading(true);
    setError(null);
    api.getQualityProfile(datasetId)
      .then(p => { setProfile(p); setLoading(false); })
      .catch(e => { setError(String(e)); setLoading(false); });
  }, [datasetId]);

  if (loading) return <div className="p-7"><div className="msg-info">Profiling data…</div></div>;
  if (error)   return <div className="p-7"><div className="msg-error">{error}</div></div>;
  if (!profile) return null;

  const pm25Col = profile.columns.find(c => c.name === 'pm25_mean');

  return (
    <div className="p-7 max-w-5xl mx-auto">
      {/* Header */}
      <div className="mb-6">
        <div className="text-xs font-bold uppercase tracking-widest mb-1" style={{ color: '#16a36a' }}>
          DATA QUALITY & PREPARATION
        </div>
        <h1 className="text-2xl font-black" style={{ fontFamily: 'Manrope, sans-serif', color: '#163b2b' }}>
          {profile.dataset_name}
        </h1>
        <p className="text-sm mt-1" style={{ color: 'var(--color-muted)' }}>
          Automated data quality report — shape, gaps, outliers, coverage and preprocessing recommendations.
        </p>
      </div>

      {/* Score + KPI row */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
        <div className="kpi-card" style={{ gridColumn: '1', display: 'flex', flexDirection: 'column', gap: 6 }}>
          <div className="kpi-label">Quality score</div>
          <ScoreBadge score={profile.quality_score} />
        </div>
        <div className="kpi-card">
          <div className="kpi-label">Total rows</div>
          <div className="kpi-value">{profile.shape.rows.toLocaleString()}</div>
          <div className="kpi-sub">{profile.shape.columns} columns</div>
        </div>
        <div className="kpi-card">
          <div className="kpi-label">Valid PM2.5 rows</div>
          <div className="kpi-value">{profile.valid_pm25_rows.toLocaleString()}</div>
          <div className="kpi-sub">
            {pm25Col ? `${pm25Col.null_pct.toFixed(1)}% missing` : ''}
          </div>
        </div>
        <div className="kpi-card">
          <div className="kpi-label">Date gaps</div>
          <div className="kpi-value">{profile.date_gaps.length}</div>
          <div className="kpi-sub">{profile.total_gap_days} total missing days</div>
        </div>
      </div>

      {/* Quality issues */}
      {profile.quality_issues.length > 0 && (
        <div className="card mb-5">
          <div className="section-title">Quality issues detected</div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
            {profile.quality_issues.map((issue, i) => (
              <div key={i} style={{ display: 'flex', gap: 10, alignItems: 'flex-start' }}>
                <SeverityBadge severity={issue.severity} />
                <span className="text-sm" style={{ color: '#4a6358', lineHeight: 1.5 }}>
                  <b>{issue.field}</b>: {issue.message}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Column profiles */}
      <div className="card mb-5">
        <div className="section-title">Column profiles</div>
        <div style={{ overflowX: 'auto' }}>
          <table className="data-table">
            <thead>
              <tr>
                <th>Column</th><th>Type</th><th>Total</th>
                <th>Missing</th><th>Missing %</th><th>Unique</th>
                <th>Min</th><th>Max</th><th>Mean</th><th>Std</th>
              </tr>
            </thead>
            <tbody>
              {profile.columns.map(col => (
                <tr key={col.name}>
                  <td><code style={{ fontSize: 11 }}>{col.name}</code></td>
                  <td style={{ fontSize: 11, color: '#9aaa9f' }}>{col.dtype}</td>
                  <td>{col.total}</td>
                  <td>
                    {col.null_count > 0
                      ? <span className="pill pill-warn">{col.null_count}</span>
                      : <span className="pill">0</span>}
                  </td>
                  <td style={{ color: col.null_pct > 20 ? '#dc2626' : col.null_pct > 5 ? '#d97706' : '#16a36a' }}>
                    {col.null_pct.toFixed(1)}%
                  </td>
                  <td>{col.unique_count}</td>
                  <td>{col.min != null ? col.min.toFixed(2) : '—'}</td>
                  <td>{col.max != null ? col.max.toFixed(2) : '—'}</td>
                  <td>{col.mean != null ? col.mean.toFixed(2) : '—'}</td>
                  <td>{col.std != null ? col.std.toFixed(2) : '—'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Outliers */}
      {profile.outliers.count > 0 && (
        <div className="card mb-5">
          <div className="section-title">PM2.5 outliers ({profile.outliers.count} detected)</div>
          <p className="text-xs mb-3" style={{ color: 'var(--color-muted)' }}>
            Method: {profile.outliers.bounds.method}.
            Lower fence: {profile.outliers.bounds.lower_fence.toFixed(2)} µg/m³ ·
            Upper fence: {profile.outliers.bounds.upper_fence.toFixed(2)} µg/m³
          </p>
          <div style={{ overflowX: 'auto' }}>
            <table className="data-table">
              <thead>
                <tr><th>Date</th><th>PM2.5 (µg/m³)</th></tr>
              </thead>
              <tbody>
                {profile.outliers.examples.map((ex, i) => (
                  <tr key={i}>
                    <td>{ex.date}</td>
                    <td style={{ color: '#dc2626', fontWeight: 600 }}>{ex.pm25_mean.toFixed(2)}</td>
                  </tr>
                ))}
                {profile.outliers.count > 20 && (
                  <tr>
                    <td colSpan={2} style={{ color: '#9aaa9f', fontStyle: 'italic' }}>
                      … and {profile.outliers.count - 20} more
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Date gaps */}
      {profile.date_gaps.length > 0 && (
        <div className="card mb-5">
          <div className="section-title">Date gaps (&gt; 3 consecutive missing days)</div>
          <p className="text-xs mb-3" style={{ color: 'var(--color-muted)' }}>
            These gaps affect lag-based feature engineering for forecasting.
          </p>
          <div style={{ overflowX: 'auto', maxHeight: 240, overflow: 'auto' }}>
            <table className="data-table">
              <thead>
                <tr><th>Gap start</th><th>Gap end</th><th>Missing days</th></tr>
              </thead>
              <tbody>
                {profile.date_gaps.slice(0, 30).map((g, i) => (
                  <tr key={i}>
                    <td>{g.gap_start}</td>
                    <td>{g.gap_end}</td>
                    <td>
                      <span className="pill pill-warn">{g.missing_days}</span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Recommendations + download */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
        <div className="card" style={{ borderLeft: '4px solid #16a36a' }}>
          <div className="section-title text-sm">Preprocessing recommendations</div>
          <ul style={{ paddingLeft: 18, lineHeight: 2, fontSize: 13, color: 'var(--color-muted)' }}>
            {profile.preprocessing_recommendations.map((r, i) => <li key={i}>{r}</li>)}
          </ul>
        </div>
        <div className="card" style={{ borderLeft: '4px solid #1e5c8e' }}>
          <div className="section-title text-sm">Download</div>
          <p className="text-sm mb-4" style={{ color: 'var(--color-muted)' }}>
            Download the cleaned version of this dataset: dates parsed,
            rows sorted by date, duplicate dates removed (last kept),
            non-numeric PM2.5 rows dropped.
            Raw data on disk is never modified.
          </p>
          <div className="flex gap-3 flex-wrap">
            <button
              className="btn btn-primary"
              onClick={() => api.downloadCleanedDataset(datasetId)}
            >
              ⬇ Download cleaned CSV
            </button>
            <button
              className="btn btn-outline"
              onClick={() => navigate('/stat-analysis')}
            >
              Run statistical analysis →
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
