import { Outlet, NavLink, useNavigate } from 'react-router-dom';
import { useDataset, DEFAULT_DATASET_NAME } from './context/DatasetContext';

const NAV_GROUPS = [
  {
    label: 'DATA',
    items: [
      { to: '/datasets', icon: '🗂', label: 'Dataset Manager' },
      { to: '/quality',  icon: '🔍', label: 'Data Quality'    },
    ],
  },
  {
    label: 'ANALYSIS',
    items: [
      { to: '/overview',      icon: '🏠', label: 'Overview'         },
      { to: '/trends',        icon: '📈', label: 'Explore & Trends' },
      { to: '/statistics',    icon: '📊', label: 'Statistics'       },
      { to: '/stat-analysis', icon: '🔬', label: 'Hypothesis Tests' },
      { to: '/regression',    icon: '📉', label: 'Regression Studio'},
    ],
  },
  {
    label: 'MODELLING',
    items: [
      { to: '/evaluation', icon: '🏅', label: 'Evaluation' },
      { to: '/forecast',   icon: '🔮', label: 'Forecast'   },
    ],
  },
  {
    label: 'LEARN',
    items: [
      { to: '/methodology', icon: '📖', label: 'Methodology' },
    ],
  },
];

export default function Layout() {
  const { dataset } = useDataset();
  const navigate    = useNavigate();

  const displayName = dataset?.name ?? DEFAULT_DATASET_NAME;
  const isDemo      = dataset?.is_demo ?? true;

  return (
    <div style={{ display: 'flex', minHeight: '100vh', background: 'var(--color-surface)' }}>
      {/* ── Sidebar ──────────────────────────────────────────────────────── */}
      <nav style={{
        width: 228,
        flexShrink: 0,
        background: 'linear-gradient(180deg, #0c2d1c 0%, #14391f 60%, #0f2d1f 100%)',
        display: 'flex',
        flexDirection: 'column',
        padding: '0 0 16px 0',
        overflowY: 'auto',
        overflowX: 'hidden',
        position: 'sticky',
        top: 0,
        height: '100vh',
        zIndex: 10,
      }}>

        {/* Logo */}
        <div style={{ padding: '22px 20px 16px', borderBottom: '1px solid rgba(255,255,255,0.07)' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 9, marginBottom: 4 }}>
            <div style={{
              width: 32, height: 32, borderRadius: 9,
              background: 'linear-gradient(135deg,#16a36a,#0d9488)',
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              fontSize: 18, flexShrink: 0, boxShadow: '0 2px 8px rgba(22,163,106,0.4)',
            }}>🌿</div>
            <div>
              <div style={{ fontWeight: 900, fontSize: 15, color: '#fff', letterSpacing: '-0.02em', fontFamily: 'Manrope, sans-serif' }}>
                AirAware
              </div>
              <div style={{ fontSize: 9, color: 'rgba(255,255,255,0.4)', letterSpacing: '0.05em', marginTop: -1 }}>
                V2 · ANALYTICS PLATFORM
              </div>
            </div>
          </div>
        </div>

        {/* Active Dataset Badge */}
        <div
          style={{
            margin: '12px 12px 4px',
            padding: '10px 12px',
            background: 'rgba(22,163,106,0.12)',
            border: '1px solid rgba(22,163,106,0.25)',
            borderRadius: 10,
            cursor: 'pointer',
            transition: 'background 0.2s',
          }}
          onClick={() => navigate('/datasets')}
          title="Click to change dataset"
        >
          <div style={{ fontSize: 9, color: 'rgba(255,255,255,0.45)', letterSpacing: '0.08em', marginBottom: 3 }}>
            ACTIVE DATASET
          </div>
          <div style={{ fontWeight: 700, fontSize: 12, color: '#6ee7b7', lineHeight: 1.3 }}>
            {displayName}
          </div>
          {dataset && (
            <div style={{ fontSize: 9.5, color: 'rgba(255,255,255,0.4)', marginTop: 2 }}>
              {dataset.rows.toLocaleString()} rows · {dataset.date_start} → {dataset.date_end}
            </div>
          )}
          <div style={{ fontSize: 9, color: 'rgba(255,255,255,0.3)', marginTop: 2 }}>
            {isDemo ? '📁 Demo' : '📤 Upload'} · click to change
          </div>
        </div>

        {/* Navigation groups */}
        <div style={{ flex: 1, padding: '8px 0', marginTop: 4 }}>
          {NAV_GROUPS.map(group => (
            <div key={group.label} style={{ marginBottom: 4 }}>
              <div style={{
                padding: '6px 16px 3px',
                fontSize: 9, fontWeight: 800,
                color: 'rgba(255,255,255,0.3)',
                letterSpacing: '0.12em',
              }}>
                {group.label}
              </div>
              {group.items.map(item => (
                <NavLink
                  key={item.to}
                  to={item.to}
                  style={({ isActive }) => ({
                    display: 'flex',
                    alignItems: 'center',
                    gap: 9,
                    padding: '7px 16px',
                    fontSize: 12.5,
                    fontWeight: isActive ? 700 : 400,
                    color: isActive ? '#6ee7b7' : 'rgba(255,255,255,0.62)',
                    textDecoration: 'none',
                    background: isActive ? 'rgba(22,163,106,0.15)' : 'transparent',
                    borderRadius: 8,
                    margin: '1px 6px',
                    borderLeft: isActive ? '3px solid #16a36a' : '3px solid transparent',
                    transition: 'all 0.15s ease',
                  })}
                >
                  <span style={{ fontSize: 14, lineHeight: 1 }}>{item.icon}</span>
                  {item.label}
                </NavLink>
              ))}
            </div>
          ))}
        </div>

        {/* Footer */}
        <div style={{ padding: '12px 16px 0', borderTop: '1px solid rgba(255,255,255,0.06)' }}>
          <div style={{ fontSize: 9.5, color: 'rgba(255,255,255,0.28)', lineHeight: 1.7 }}>
            PM2.5 data from CPCB · India<br />
            AirAware V2 · DSA Project
          </div>
        </div>
      </nav>

      {/* ── Main content ──────────────────────────────────────────────────── */}
      <main style={{ flex: 1, minWidth: 0, overflowY: 'auto' }}>
        {/* Top bar with dataset indicator */}
        <div style={{
          padding: '10px 28px',
          background: '#fff',
          borderBottom: '1px solid var(--color-border)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          position: 'sticky',
          top: 0,
          zIndex: 5,
          boxShadow: '0 1px 4px rgba(0,0,0,0.04)',
        }}>
          <div style={{ fontSize: 12, color: 'var(--color-muted)' }}>
            Analysing: <b style={{ color: '#163b2b' }}>{displayName}</b>
            {dataset && (
              <span style={{ marginLeft: 8, color: '#9aaa9f' }}>
                {dataset.date_start} → {dataset.date_end}
              </span>
            )}
          </div>
          <button
            className="btn btn-outline"
            onClick={() => navigate('/datasets')}
            style={{ fontSize: 11, padding: '4px 12px' }}
          >
            Change dataset
          </button>
        </div>

        <Outlet />
      </main>
    </div>
  );
}
