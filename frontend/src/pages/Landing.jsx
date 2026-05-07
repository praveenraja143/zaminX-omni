import { Link } from 'react-router-dom'
import { useApp } from '../App.jsx'

export default function Landing() {
  const { t } = useApp()

  const features = [
    { icon: '⚖️', title: 'Court Case Search', desc: 'Search NJDG, Indian Kanoon & Madras HC for land-related cases instantly.' },
    { icon: '🤖', title: 'AI Analysis', desc: 'Groq Llama 3.3 analyzes legal text and gives you simple risk summaries.' },
    { icon: '📊', title: 'Risk Score', desc: 'Get a 0-100 risk score with clear factors explaining the risk level.' },
    { icon: '📜', title: 'Patta & Chitta', desc: 'Auto-fetch land ownership records from TN government portal.' },
    { icon: '🔗', title: 'Blockchain Verified', desc: 'All search results are anchored on Polygon for tamper-proof records.' },
    { icon: '🌐', title: 'Multilingual', desc: 'Works in English, Tamil, Hindi & Malayalam for all rural users.' },
  ]

  return (
    <div>
      <section className="hero">
        <div className="container">
          <h1 className="fade-in">
            <span className="gold">{t('app_name')}</span>
            <br />
            Land Litigation Intelligence
          </h1>
          <p className="fade-in-delay-1">{t('tagline')}</p>
          <div className="fade-in-delay-2" style={{ display: 'flex', gap: 16, justifyContent: 'center', flexWrap: 'wrap' }}>
            <Link to="/search" className="btn btn-primary" style={{ fontSize: 17, padding: '16px 40px' }}>
              🔍 {t('search_button')}
            </Link>
            <Link to="/login" className="btn btn-secondary" style={{ fontSize: 17, padding: '16px 40px' }}>
              {t('login')} / {t('register')}
            </Link>
          </div>
        </div>
      </section>

      <section className="container">
        <div style={{ textAlign: 'center', marginBottom: 20 }}>
          <p style={{ color: 'var(--text-muted)', fontSize: 14, letterSpacing: 2, textTransform: 'uppercase' }}>
            Supported Districts
          </p>
          <div style={{ display: 'flex', gap: 12, justifyContent: 'center', marginTop: 12, flexWrap: 'wrap' }}>
            {['Erode', 'Coimbatore', 'Salem', 'Namakkal', 'Tiruppur'].map(d => (
              <span key={d} style={{
                padding: '6px 16px', borderRadius: 'var(--radius-full)',
                background: 'var(--bg-glass)', border: '1px solid var(--border-glass)',
                fontSize: 13, color: 'var(--gold-400)',
              }}>{d}</span>
            ))}
          </div>
        </div>

        <div className="features-grid" style={{ marginTop: 40, marginBottom: 60 }}>
          {features.map((f, i) => (
            <div key={i} className={`glass-card feature-card fade-in-delay-${Math.min(i + 1, 3)}`}>
              <span className="feature-icon">{f.icon}</span>
              <h3>{f.title}</h3>
              <p>{f.desc}</p>
            </div>
          ))}
        </div>

        <div className="glass-card" style={{ textAlign: 'center', padding: 40, marginBottom: 40 }}>
          <h2 style={{ fontSize: 24, marginBottom: 12 }}>How It Works</h2>
          <div style={{ display: 'flex', gap: 32, justifyContent: 'center', flexWrap: 'wrap', marginTop: 24 }}>
            {[
              { step: '1', title: 'Enter Details', desc: 'Owner name, district, taluk, village, survey number' },
              { step: '2', title: 'AI Searches', desc: 'Scans Indian Kanoon, NJDG & court databases' },
              { step: '3', title: 'Get Report', desc: 'Risk score, case details, AI summary in your language' },
            ].map(s => (
              <div key={s.step} style={{ textAlign: 'center', maxWidth: 220 }}>
                <div style={{
                  width: 48, height: 48, borderRadius: '50%', margin: '0 auto 12px',
                  display: 'flex', alignItems: 'center', justifyContent: 'center',
                  background: 'linear-gradient(135deg, var(--gold-500), var(--gold-600))',
                  color: '#000', fontWeight: 800, fontSize: 20,
                }}>{s.step}</div>
                <h4 style={{ marginBottom: 6 }}>{s.title}</h4>
                <p style={{ fontSize: 13, color: 'var(--text-secondary)' }}>{s.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>
    </div>
  )
}
