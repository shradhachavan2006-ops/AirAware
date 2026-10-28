import { NavLink, Outlet } from 'react-router-dom';

const NAV = [
  { to: '/',            icon: '🏠', label: 'Overview'   },
  { to: '/trends',      icon: '📈', label: 'Trends'     },
  { to: '/statistics',  icon: '📊', label: 'Statistics' },
  { to: '/evaluation',  icon: '🔬', label: 'Evaluation' },
  { to: '/forecast',    icon: '🔮', label: 'Forecast'   },
];

export default function Layout() {
  return (
    <div className="flex min-h-screen" style={{ background: 'var(--color-surface)' }}>
      {/* ── Sidebar ─────────────────────────────────────── */}
      <aside
        className="flex flex-col w-56 shrink-0"
        style={{
          background: 'linear-gradient(180deg, #0f2d1f 0%, #163b28 100%)',
          borderRight: '1px solid rgba(255,255,255,0.07)',
        }}
      >
        {/* Brand */}
        <div className="px-5 pt-7 pb-6">
          <div className="text-white font-black text-xl tracking-tight" style={{ fontFamily: 'Manrope, sans-serif' }}>
            🌿 AirAware
          </div>
          <div className="text-xs mt-1" style={{ color: '#7acba1' }}>
            Air Quality Intelligence
          </div>
        </div>

        <div className="mx-4 mb-4" style={{ height: '1px', background: 'rgba(255,255,255,0.08)' }} />

        {/* Nav links */}
        <nav className="flex-1 px-3 space-y-1">
          {NAV.map(({ to, icon, label }) => (
            <NavLink
              key={to}
              to={to}
              end={to === '/'}
              className={({ isActive }) =>
                `flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm font-medium transition-all ${
                  isActive
                    ? 'text-white'
                    : 'text-[#a8cdb8] hover:text-white hover:bg-white/5'
                }`
              }
              style={({ isActive }) =>
                isActive
                  ? { background: 'rgba(22,163,106,0.22)', color: 'white' }
                  : {}
              }
            >
              <span className="text-base leading-none">{icon}</span>
              <span>{label}</span>
            </NavLink>
          ))}
        </nav>

        {/* Footer note */}
        <div className="px-5 py-5 text-[10px] leading-4" style={{ color: '#4a6e58' }}>
          PM2.5 concentration · µg/m³
          <br />Not AQI. Not medical advice.
        </div>
      </aside>

      {/* ── Main content ────────────────────────────────── */}
      <main className="flex-1 min-w-0 overflow-y-auto">
        <Outlet />
      </main>
    </div>
  );
}
