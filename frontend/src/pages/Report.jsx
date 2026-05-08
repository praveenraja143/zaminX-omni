import { useApp } from '../App.jsx'
import { Link } from 'react-router-dom'

function RiskGauge({ score, level }) {
  const r = 85, circ = 2 * Math.PI * r
  const offset = circ - (score / 100) * circ
  const color = level === 'low' ? '#22c55e' : level === 'medium' ? '#fbbf24' : level === 'high' ? '#fb923c' : '#ef4444'

  return (
    <div className="risk-gauge">
      <svg width="200" height="200">
        <circle cx="100" cy="100" r={r} fill="none" stroke="rgba(255,255,255,0.05)" strokeWidth="12" />
        <circle cx="100" cy="100" r={r} fill="none" stroke={color} strokeWidth="12"
          strokeDasharray={circ} strokeDashoffset={offset}
          strokeLinecap="round" style={{ transition: 'stroke-dashoffset 1.5s ease-out' }} />
      </svg>
      <div style={{ textAlign: 'center' }}>
        <div className="score-text" style={{ color }}>{Math.round(score)}</div>
        <div className="score-label">/100</div>
      </div>
    </div>
  )
}

function InfoGrid({ title, icon, data }) {
  if (!data) return null
  return (
    <div className="glass-card" style={{ marginBottom: 16 }}>
      <h3 style={{ fontSize: 16, marginBottom: 16, display: 'flex', alignItems: 'center', gap: 8 }}>
        {icon} {title}
      </h3>
      <div className="info-grid">
        {Object.entries(data).map(([k, v]) => (
          v && <div key={k} className="info-item">
            <div className="info-label">{k.replace(/_/g, ' ')}</div>
            <div className="info-value">{String(v)}</div>
          </div>
        ))}
      </div>
    </div>
  )
}

function CaseCard({ c, t }) {
  const isActive = c.status === 'active'
  return (
    <div className={`glass-card case-card ${isActive ? 'active' : 'disposed'}`}>
      <div className="case-header">
        <span className="case-number">{c.case_number}</span>
        <span className={`case-status ${isActive ? 'status-active' : 'status-disposed'}`}>
          {isActive ? t('active') : t('disposed')}
        </span>
      </div>
      <div style={{ fontSize: 14, color: 'var(--text-secondary)', marginBottom: 12 }}>
        {c.court_name}
      </div>
      <dl className="case-meta">
        <dt>{t('case_type')}</dt><dd>{c.case_type || 'Civil'}</dd>
        <dt>{t('petitioner')}</dt><dd>{c.petitioner || '—'}</dd>
        <dt>{t('respondent')}</dt><dd>{c.respondent || '—'}</dd>
        <dt>{t('next_hearing')}</dt><dd>{c.next_hearing || '—'}</dd>
        {c.judge_name && <><dt>Judge</dt><dd>{c.judge_name}</dd></>}
        {c.source && <><dt>Source</dt><dd style={{ textTransform: 'capitalize' }}>{c.source.replace('_', ' ')}</dd></>}
      </dl>
      {c.ai_summary && (
        <div className="report-card chargesheet-card">
          <h3>📖 {t('chargesheet')}</h3>
          <div className="ai-summary-content">
            {displaySummary}
          </div>
        </div>
      )}
      {!c.ai_summary && c.headline && (
        <div className="case-summary">
          <div className="label">📄 Details</div>
          {c.headline}
        </div>
      )}
    </div>
  )
}

export default function Report() {
  const { searchResult, t, lang } = useApp()
  const navigate = useNavigate()

  if (!searchResult) return null

  // Use translated content if available, otherwise fallback
  const displaySummary = searchResult.i18n_summaries?.[lang] || searchResult.ai_summary
  const displayRiskReason = searchResult.i18n_risk_summaries?.[lang] || searchResult.risk_assessment?.risk_summary

  const data = searchResult
  const risk = data.risk_assessment || {}
  const riskLevel = risk.risk_level || 'low'
  const riskScore = risk.risk_score || 0
  const cases = data.cases || []
  const land = data.land_record || {}
  const meta = data.search_metadata || {}

  const riskLabel = t(`risk_${riskLevel}`) || riskLevel

  return (
    <div className="container report-page fade-in">
      <div className="report-header">
        <div>
          <h1 style={{ fontSize: 28, fontWeight: 700 }}>📊 Land Litigation Report</h1>
          <p style={{ color: 'var(--text-secondary)', fontSize: 14, marginTop: 4 }}>
            {land.village_name && `${land.village_name}, `}{land.district} — Survey: {land.survey_number || 'N/A'}
          </p>
        </div>
        <div style={{ display: 'flex', gap: 12 }}>
          <Link to="/search" className="btn btn-secondary" style={{ padding: '10px 20px' }}>
            ← New Search
          </Link>
        </div>
      </div>

      <div className="report-grid">
        {/* Main Content */}
        <div>
          {/* AI Overall Summary */}
          {data.ai_summary && (
            <div className="glass-card" style={{ marginBottom: 16, borderLeft: '3px solid var(--gold-500)' }}>
              <h3 style={{ fontSize: 16, marginBottom: 12, display: 'flex', alignItems: 'center', gap: 8 }}>
                🤖 {t('chargesheet')}
              </h3>
              <p style={{ fontSize: 15, lineHeight: 1.8, color: 'var(--text-secondary)' }}>
                {displaySummary}
              </p>
            </div>
          )}

          {/* Risk Factors */}
          {risk.risk_factors && risk.risk_factors.length > 0 && (
            <div className="glass-card" style={{ marginBottom: 16 }}>
              <h3 style={{ fontSize: 16, marginBottom: 12 }}>⚠️ Risk Factors</h3>
              <ul style={{ listStyle: 'none', padding: 0 }}>
                {risk.risk_factors.map((f, i) => (
                  <li key={i} style={{ padding: '8px 0', borderBottom: '1px solid var(--border-glass)', fontSize: 14, color: 'var(--text-secondary)', display: 'flex', alignItems: 'center', gap: 8 }}>
                    <span style={{ color: riskScore > 50 ? 'var(--red-400)' : 'var(--gold-400)' }}>●</span> {f}
                  </li>
                ))}
              </ul>
              {risk.recommendation && (
                <div className="recommendation-box">
                  <p>💡 <strong>Recommendation:</strong> {displayRiskReason}</p>
                </div>
              )}
            </div>
          )}

          {/* Court Cases */}
          <h3 style={{ fontSize: 18, marginBottom: 16, marginTop: 8 }}>
            ⚖️ {t('cases_found')} ({cases.length})
          </h3>

          {cases.length === 0 ? (
            <div className="glass-card" style={{ textAlign: 'center', padding: 40 }}>
              <span style={{ fontSize: 48 }}>✅</span>
              <p style={{ marginTop: 12, fontSize: 18, color: 'var(--green-400)' }}>{t('no_cases')}</p>
            </div>
          ) : (
            cases.map((c, i) => <CaseCard key={i} c={c} t={t} />)
          )}
        </div>

        {/* Sidebar */}
        <div>
          {/* Risk Gauge */}
          <div className="glass-card risk-gauge-container" style={{ marginBottom: 16 }}>
            <h3 style={{ fontSize: 16, marginBottom: 8 }}>{t('risk_score')}</h3>
            <RiskGauge score={riskScore} level={riskLevel} />
            <span className={`risk-level-badge risk-${riskLevel}`}>{riskLabel}</span>
            {risk.is_safe_to_buy !== undefined && (
              <div style={{ marginTop: 12, fontSize: 14, color: risk.is_safe_to_buy ? 'var(--green-400)' : 'var(--red-400)' }}>
                {risk.is_safe_to_buy ? '✅ Safe to proceed' : '⛔ Not recommended'}
              </div>
            )}
          </div>

          {/* Land Record */}
          <InfoGrid title={t('patta_details')} icon="📜" data={data.patta_details} />
          <InfoGrid title={t('chitta_details')} icon="📋" data={data.chitta_details} />

          {/* Blockchain */}
          <div className="glass-card" style={{ marginBottom: 16 }}>
            <h3 style={{ fontSize: 16, marginBottom: 12 }}>🔗 {t('blockchain_verified')}</h3>
            <div className={`blockchain-badge ${data.blockchain_badge?.verified ? 'verified' : 'pending'}`}>
              {data.blockchain_badge?.verified ? '✅ Verified on Polygon' : '⏳ Pending Verification'}
            </div>
            <p style={{ fontSize: 12, color: 'var(--text-muted)', marginTop: 8 }}>
              Chain: Polygon Mumbai Testnet
            </p>
          </div>

          {/* Metadata */}
          <div className="glass-card" style={{ fontSize: 13, color: 'var(--text-muted)' }}>
            <h4 style={{ fontSize: 14, marginBottom: 8, color: 'var(--text-secondary)' }}>Search Info</h4>
            <p>⚡ Response: {meta.response_time_ms}ms</p>
            <p>🌐 Language: {meta.language?.toUpperCase()}</p>
            <p>📅 {meta.searched_at?.split('T')[0]}</p>
            <p>📡 Sources: {meta.data_sources?.join(', ')}</p>
          </div>
        </div>
      </div>
    </div>
  )
}
