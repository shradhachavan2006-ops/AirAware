import { useEffect, useState, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { api } from '../api';
import type { DatasetInfo } from '../api';
import { useDataset } from '../context/DatasetContext';

const CITY_GRADIENTS: Record<string, string> = {
  Pune:    'linear-gradient(135deg,#1b4332 0%,#2d6a4f 100%)',
  Mumbai:  'linear-gradient(135deg,#1a3a5c 0%,#2980b9 100%)',
  Nagpur:  'linear-gradient(135deg,#4a1942 0%,#9b2c8a 100%)',
  Nashik:  'linear-gradient(135deg,#7b3f00 0%,#d4820a 100%)',
  Custom:  'linear-gradient(135deg,#2d3748 0%,#4a5568 100%)',
};

const CITY_ICONS: Record<string, string> = {
  Pune:'🌿', Mumbai:'🌊', Nagpur:'🍊', Nashik:'🍇', Custom:'📂',
};

function gradient(city: string) {
  return CITY_GRADIENTS[city] ?? CITY_GRADIENTS.Custom;
}
function icon(city: string) {
  return CITY_ICONS[city] ?? '📂';
}

function DemoCard({ info, active, onSelect }: {
  info: DatasetInfo;
  active: boolean;
  onSelect: () => void;
}) {
  return (
    <button
      id={`dataset-card-${info.id.replace(':', '-')}`}
      onClick={onSelect}
      style={{
        background: active ? gradient(info.city_hint) : '#fff',
        border: `2px solid ${active ? 'transparent' : '#dde8e2'}`,
        borderRadius: 16,
        padding: '20px 22px',
        textAlign: 'left',
        cursor: 'pointer',
        transition: 'all 0.2s ease',
        boxShadow: active ? '0 6px 24px rgba(0,0,0,0.18)' : '0 2px 6px rgba(0,0,0,0.05)',
        transform: active ? 'translateY(-2px)' : 'none',
        position: 'relative',
        overflow: 'hidden',
      }}
    >
      {active && (
        <div style={{
          position: 'absolute', top: 10, right: 12,
          background: 'rgba(255,255,255,0.25)', borderRadius: 20,
          padding: '2px 10px', fontSize: 11, color: '#fff', fontWeight: 700,
        }}>
          ACTIVE ✓
        </div>
      )}
      <div style={{ fontSize: 28, marginBottom: 8 }}>{icon(info.city_hint)}</div>
      <div style={{ fontWeight: 800, fontSize: 15, color: active ? '#fff' : '#163b2b', marginBottom: 2 }}>
        {info.city_hint}
      </div>
      <div style={{ fontSize: 12, color: active ? 'rgba(255,255,255,0.75)' : '#6b7c74', marginBottom: 8 }}>
        Demo dataset
      </div>
      <div style={{ fontSize: 11, color: active ? 'rgba(255,255,255,0.8)' : '#9aaa9f', lineHeight: 1.7 }}>
        <div>{info.rows.toLocaleString()} valid observations</div>
        <div>{info.date_start} → {info.date_end}</div>
      </div>
    </button>
  );
}

function UploadCard({ onUpload }: { onUpload: (file: File, name: string) => void }) {
  const [dragging, setDragging] = useState(false);
  const fileRef = useRef<HTMLInputElement>(null);

  function handleFile(file: File) {
    const autoName = file.name.replace(/\.csv$/i, '');
    onUpload(file, autoName);
  }

  return (
    <div
      style={{
        border: `2px dashed ${dragging ? '#16a36a' : '#c9dfd3'}`,
        borderRadius: 16,
        padding: '28px 24px',
        background: dragging ? '#f0fdf4' : '#fafcfb',
        textAlign: 'center',
        transition: 'all 0.2s',
        cursor: 'pointer',
      }}
      onDragOver={e => { e.preventDefault(); setDragging(true); }}
      onDragLeave={() => setDragging(false)}
      onDrop={e => {
        e.preventDefault();
        setDragging(false);
        const file = e.dataTransfer.files[0];
        if (file) handleFile(file);
      }}
      onClick={() => fileRef.current?.click()}
    >
      <div style={{ fontSize: 36, marginBottom: 8 }}>📤</div>
      <div style={{ fontWeight: 700, color: '#163b2b', marginBottom: 4 }}>Upload your own CSV</div>
      <div style={{ fontSize: 12, color: '#6b7c74', marginBottom: 14 }}>
        Drag &amp; drop or click to browse
      </div>
      <input
        ref={fileRef}
        type="file"
        accept=".csv"
        style={{ display: 'none' }}
        onChange={e => { const f = e.target.files?.[0]; if (f) handleFile(f); e.target.value = ''; }}
        onClick={e => e.stopPropagation()}
      />
      <div style={{ fontSize: 11, color: '#9aaa9f', lineHeight: 1.8 }}>
        <strong>Required columns:</strong> date (YYYY-MM-DD), pm25_mean (µg/m³)<br />
        <strong>Optional:</strong> station_count, coverage_pct, city<br />
        Maximum 10 MB · CSV format
      </div>
    </div>
  );
}

function UploadRow({ info, active, onSelect, onDelete }: {
  info: DatasetInfo;
  active: boolean;
  onSelect: () => void;
  onDelete: () => void;
}) {
  return (
    <div style={{
      display: 'flex', alignItems: 'center', gap: 12,
      padding: '12px 16px', borderRadius: 10,
      background: active ? '#f0fdf4' : '#fff',
      border: `1.5px solid ${active ? '#16a36a' : '#e1ece5'}`,
      marginBottom: 8,
    }}>
      <div style={{ fontSize: 22 }}>{icon(info.city_hint)}</div>
      <div style={{ flex: 1 }}>
        <div style={{ fontWeight: 700, fontSize: 13, color: '#163b2b' }}>{info.name}</div>
        <div style={{ fontSize: 11, color: '#9aaa9f' }}>
          {info.rows.toLocaleString()} rows · {info.date_start} → {info.date_end}
          {info.city_hint !== 'Custom' && ` · ${info.city_hint}`}
        </div>
        {info.warnings.length > 0 && (
          <div style={{ fontSize: 10.5, color: '#d97706', marginTop: 2 }}>
            ⚠ {info.warnings[0]}
          </div>
        )}
      </div>
      {active && (
        <span style={{
          background: '#dcfce7', color: '#15803d',
          fontSize: 10, fontWeight: 700, padding: '2px 8px', borderRadius: 12,
        }}>ACTIVE</span>
      )}
      <button
        onClick={onSelect}
        className="btn btn-primary"
        style={{ fontSize: 11, padding: '4px 12px' }}
      >
        Use
      </button>
      <button
        onClick={e => { e.stopPropagation(); onDelete(); }}
        style={{
          background: 'none', border: '1px solid #fca5a5', borderRadius: 6,
          color: '#dc2626', padding: '4px 8px', cursor: 'pointer', fontSize: 12,
        }}
        title="Delete upload"
      >
        ✕
      </button>
    </div>
  );
}

export default function DatasetManager() {
  const { dataset, setDataset } = useDataset();
  const navigate = useNavigate();

  const [datasets, setDatasets] = useState<DatasetInfo[]>([]);
  const [uploading, setUploading] = useState(false);
  const [uploadMsg, setUploadMsg] = useState<{ type: 'success'|'error'|'warn'; text: string } | null>(null);
  const [loading, setLoading] = useState(true);

  function loadDatasets() {
    api.listDatasets()
      .then(d => { setDatasets(d.datasets); setLoading(false); })
      .catch(e => { console.error(e); setLoading(false); });
  }

  useEffect(() => { loadDatasets(); }, []);

  async function handleUpload(file: File, name: string) {
    setUploading(true);
    setUploadMsg(null);
    try {
      const result = await api.uploadDataset(file, name);
      setUploadMsg({
        type: result.warnings.length ? 'warn' : 'success',
        text: result.message + (result.warnings.length
          ? ' Warnings: ' + result.warnings.join('; ')
          : ''),
      });
      loadDatasets();
      // Auto-select the new dataset
      setDataset(result.dataset);
    } catch (e: unknown) {
      setUploadMsg({ type: 'error', text: String(e) });
    } finally {
      setUploading(false);
    }
  }

  async function handleDelete(id: string) {
    if (!window.confirm('Delete this dataset?')) return;
    try {
      await api.deleteDataset(id);
      if (dataset?.id === id) setDataset(datasets.find(d => d.id === 'demo:pune')!);
      loadDatasets();
    } catch (e) {
      alert(String(e));
    }
  }

  function selectAndGo(info: DatasetInfo) {
    setDataset(info);
    navigate('/overview');
  }

  const demos   = datasets.filter(d => d.is_demo);
  const uploads = datasets.filter(d => !d.is_demo);

  return (
    <div className="p-7 max-w-5xl mx-auto">
      {/* Header */}
      <div className="rounded-2xl mb-8 px-8 py-6" style={{
        background: 'linear-gradient(115deg,#0f4c2a 0%,#1a6b3c 55%,#16a36a 100%)',
        color: '#fff', boxShadow: '0 12px 30px rgba(15,76,42,0.2)',
      }}>
        <div className="text-xs font-bold uppercase tracking-widest mb-1" style={{ color: '#6ee7b7' }}>
          AIRAWARE V2 · DATA SCIENCE PLATFORM
        </div>
        <h1 className="text-2xl font-black mb-2" style={{ color: '#fff', fontFamily: 'Manrope, sans-serif' }}>
          Dataset Manager
        </h1>
        <p style={{ color: 'rgba(255,255,255,0.8)', fontSize: 13 }}>
          Choose a built-in city demo or upload your own daily PM2.5 CSV.
          All analysis pages use the active dataset — no data mixing occurs.
        </p>
      </div>

      {/* Status messages */}
      {uploading && <div className="msg-info mb-4">Uploading and validating…</div>}
      {uploadMsg && (
        <div
          className={uploadMsg.type === 'error' ? 'msg-error' : 'msg-info'}
          style={{ marginBottom: 16, background: uploadMsg.type === 'warn' ? '#fffbeb' : undefined,
                   borderColor: uploadMsg.type === 'warn' ? '#d97706' : undefined }}
        >
          {uploadMsg.type === 'warn' && '⚠ '}{uploadMsg.text}
        </div>
      )}

      {/* Demo datasets */}
      <div className="mb-8">
        <div className="section-title mb-4">Built-in demo datasets</div>
        {loading ? (
          <div className="msg-info">Loading datasets…</div>
        ) : (
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))', gap: 16 }}>
            {demos.map(info => (
              <DemoCard
                key={info.id}
                info={info}
                active={dataset?.id === info.id}
                onSelect={() => selectAndGo(info)}
              />
            ))}
          </div>
        )}
      </div>

      {/* Upload zone */}
      <div className="mb-8">
        <div className="section-title mb-4">Upload a custom dataset</div>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 20 }}>
          <UploadCard onUpload={handleUpload} />
          {/* Schema reference */}
          <div className="card" style={{ fontSize: 12, color: 'var(--color-muted)' }}>
            <div className="section-title text-sm mb-3">CSV Schema Reference</div>
            <table className="data-table" style={{ fontSize: 11 }}>
              <thead>
                <tr><th>Column</th><th>Required</th><th>Format</th></tr>
              </thead>
              <tbody>
                <tr><td><code>date</code></td><td>✅ Yes</td><td>YYYY-MM-DD</td></tr>
                <tr><td><code>pm25_mean</code></td><td>✅ Yes</td><td>float, µg/m³</td></tr>
                <tr><td><code>station_count</code></td><td>Optional</td><td>integer</td></tr>
                <tr><td><code>coverage_pct</code></td><td>Optional</td><td>0–100 float</td></tr>
                <tr><td><code>city</code></td><td>Optional</td><td>string</td></tr>
              </tbody>
            </table>
            <div style={{ marginTop: 12, lineHeight: 1.8, fontSize: 11 }}>
              <b>One row per day.</b> Duplicate dates are de-duplicated (last kept).
              Missing <code>pm25_mean</code> values are allowed but excluded from analysis.
              Raw uploaded data is never modified on disk.
            </div>
          </div>
        </div>
      </div>

      {/* Uploaded datasets */}
      {uploads.length > 0 && (
        <div>
          <div className="section-title mb-4">Your uploads ({uploads.length})</div>
          {uploads.map(info => (
            <UploadRow
              key={info.id}
              info={info}
              active={dataset?.id === info.id}
              onSelect={() => selectAndGo(info)}
              onDelete={() => handleDelete(info.id)}
            />
          ))}
        </div>
      )}
    </div>
  );
}
