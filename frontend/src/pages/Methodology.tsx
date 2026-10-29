export default function Methodology() {
  const sections = [
    {
      icon: '🔄',
      title: 'CRISP-DM Lifecycle',
      color: '#16a36a',
      content: `AirAware follows the Cross-Industry Standard Process for Data Mining (CRISP-DM):
        (1) Business Understanding — reduce PM2.5 exposure harm through data-driven insights.
        (2) Data Understanding — daily observations from CPCB monitoring stations.
        (3) Data Preparation — validated, cleaned, feature-engineered time series.
        (4) Modelling — Random Forest Regressor with Persistence baseline.
        (5) Evaluation — MAE, RMSE, R² on a chronological test split (no data leakage).
        (6) Deployment — interactive platform accessible via a browser.`,
    },
    {
      icon: '📊',
      title: 'Data Sources',
      color: '#1e5c8e',
      content: `Data originates from India's Central Pollution Control Board (CPCB) monitoring network.
        PM2.5 concentrations are daily averages across all active monitoring stations in a city.
        The station_count column indicates how many stations contributed to each daily average.
        Coverage gaps may reflect sensor downtime, calibration periods, or data transmission failures.
        Raw data is preserved without modification; cleaned data is produced on demand for analysis.`,
    },
    {
      icon: '🔬',
      title: 'Statistical Methods',
      color: '#7b3f00',
      content: `Descriptive statistics use pandas and NumPy with sample standard deviation (ddof=1).
        Normality is assessed with Shapiro-Wilk (scipy.stats.shapiro) — sensitive with large samples.
        One-sample t-tests (scipy.stats.ttest_1samp) compare city means against WHO and India NAAQS guidelines.
        Effect sizes use Cohen's d = (x̄ − μ₀) / s.
        Confidence intervals use the t-distribution: scipy.stats.t.interval().
        Seasonal ANOVA (scipy.stats.f_oneway) is supplemented by Kruskal-Wallis as a non-parametric check.
        Regression uses scipy.stats.linregress (simple) and sklearn LinearRegression with manually computed OLS p-values.`,
    },
    {
      icon: '🤖',
      title: 'Forecasting Model',
      color: '#4a1942',
      content: `Primary model: Random Forest Regressor (sklearn, 150 estimators).
        Baseline: Persistence (predicts tomorrow = today).
        Features: lag_1, lag_7, rolling_mean_3, rolling_mean_7, day_of_week, month, is_weekend.
        Evaluation uses chronological train/test splitting — no shuffling, no data leakage.
        If Random Forest does not outperform Persistence, this is reported honestly.
        Final production forecasts train on all available data to maximise information.
        Iterative rollout: each forecast day becomes input for the next (prediction uncertainty accumulates).`,
    },
    {
      icon: '⚠️',
      title: 'Limitations & Honest Disclaimers',
      color: '#dc2626',
      content: `PM2.5 city-level averages are NOT population-weighted personal exposure estimates.
        Monitoring station density varies; some areas may be over- or under-represented.
        Short time series (Pune: 330 days) reduce statistical power and forecast reliability.
        Autocorrelation in time series violates the independence assumption of classical hypothesis tests.
        Treat p-values as approximate. Correlation ≠ causation.
        Random Forest has no understanding of physical chemistry or meteorological dynamics.
        Forecasts degrade in accuracy beyond 3–4 days due to error accumulation.
        Seasonal ANOVA results are exploratory, not confirmatory.`,
    },
    {
      icon: '🛡️',
      title: 'Responsible AI & Ethics',
      color: '#0f4c2a',
      content: `Data privacy: No personal information is collected or stored.
        Transparency: All model decisions are explainable via feature importance scores.
        Bias & fairness: Station coverage may favour wealthier or denser urban areas.
        Uncertainty: Confidence intervals and error metrics are reported alongside every prediction.
        Data provenance: Data sources are documented; uploaded data is never shared with third parties.
        Explainability: AirAware aligns with the XAI (Explainable AI) principle — every result links
          to interpretable statistical concepts documented here.`,
    },
    {
      icon: '🐍',
      title: 'Python Ecosystem',
      color: '#2563eb',
      content: `NumPy — numerical arrays, percentiles, matrix operations.
        Pandas — data loading, time-indexed DataFrames, groupby aggregations.
        SciPy (scipy.stats) — hypothesis tests, confidence intervals, distributions.
        Scikit-learn — RandomForestRegressor, LinearRegression, train-test splits.
        FastAPI — typed REST API with automatic OpenAPI documentation (/docs).
        Recharts / React — interactive visualisations in the browser.`,
    },
  ];

  return (
    <div className="p-7 max-w-5xl mx-auto">
      {/* Header */}
      <div className="rounded-2xl mb-8 px-8 py-6" style={{
        background: 'linear-gradient(115deg,#0f4c2a 0%,#1a6b3c 55%,#16a36a 100%)',
        color: '#fff',
      }}>
        <div style={{ color: '#6ee7b7', fontSize: 11, fontWeight: 700, letterSpacing: '0.1em', marginBottom: 4 }}>
          METHODOLOGY & ABOUT
        </div>
        <h1 className="text-2xl font-black mb-2" style={{ color: '#fff', fontFamily: 'Manrope, sans-serif' }}>
          How AirAware Works
        </h1>
        <p style={{ color: 'rgba(255,255,255,0.8)', fontSize: 13, lineHeight: 1.7 }}>
          A transparent account of data sources, statistical methods, modelling decisions,
          limitations and responsible AI principles.
        </p>
      </div>

      {/* CRISP-DM flow diagram */}
      <div className="card mb-6">
        <div className="section-title">CRISP-DM Process Flow</div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 0, overflowX: 'auto', paddingBottom: 4 }}>
          {[
            ['Business\nUnderstanding', '#16a36a'],
            ['Data\nUnderstanding', '#1e5c8e'],
            ['Data\nPreparation', '#7b3f00'],
            ['Modelling', '#4a1942'],
            ['Evaluation', '#dc2626'],
            ['Deployment', '#0f4c2a'],
          ].map(([step, color], i) => (
            <div key={i} style={{ display: 'flex', alignItems: 'center', flexShrink: 0 }}>
              <div style={{
                background: color, color: '#fff',
                borderRadius: 10, padding: '8px 14px',
                fontSize: 11, fontWeight: 700, textAlign: 'center', lineHeight: 1.4,
                whiteSpace: 'pre-line', minWidth: 90,
              }}>
                {step}
              </div>
              {i < 5 && (
                <div style={{ color: '#c9dfd3', fontSize: 18, padding: '0 4px' }}>→</div>
              )}
            </div>
          ))}
        </div>
        <p className="text-xs mt-2" style={{ color: 'var(--color-muted)' }}>
          CRISP-DM is iterative — insights from Evaluation feed back into Business Understanding and Data Preparation.
        </p>
      </div>

      {/* Section cards */}
      <div className="flex flex-col gap-4">
        {sections.map((s, i) => (
          <details key={i} className="card" style={{ borderLeft: `4px solid ${s.color}` }}>
            <summary style={{
              cursor: 'pointer', fontWeight: 700, fontSize: 14, color: '#163b2b',
              display: 'flex', alignItems: 'center', gap: 8, userSelect: 'none',
            }}>
              <span>{s.icon}</span> {s.title}
            </summary>
            <p style={{ marginTop: 12, fontSize: 12.5, color: '#4a6358', lineHeight: 1.85, whiteSpace: 'pre-line' }}>
              {s.content}
            </p>
          </details>
        ))}
      </div>

      {/* Syllabus coverage */}
      <div className="card mt-6">
        <div className="section-title">DSA Syllabus Coverage</div>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))', gap: 8, marginTop: 8 }}>
          {[
            'Data Science Lifecycle & CRISP-DM',
            'Python ecosystem (NumPy, Pandas, SciPy, sklearn)',
            'Data acquisition & cleaning',
            'Feature engineering (lag, rolling)',
            'EDA & data profiling',
            'Descriptive statistics',
            'Probability distributions',
            'Hypothesis testing (t-test, ANOVA)',
            'p-values & confidence intervals',
            'Effect sizes (Cohen\'s d)',
            'Kruskal-Wallis (non-parametric)',
            'Pearson correlation',
            'Simple linear regression',
            'Multiple linear regression (OLS)',
            'Regression diagnostics',
            'Outlier detection (IQR method)',
            'Time-series forecasting',
            'Cross-validation (chronological)',
            'KPI analysis',
            'Data quality scoring',
            'Explainable AI & feature importance',
            'Responsible AI & ethics',
            'Report generation',
          ].map((item, i) => (
            <div key={i} style={{
              background: '#f0fdf4', borderRadius: 8, padding: '6px 12px',
              fontSize: 11.5, color: '#15803d', fontWeight: 500,
              display: 'flex', alignItems: 'center', gap: 6,
            }}>
              <span>✓</span> {item}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
