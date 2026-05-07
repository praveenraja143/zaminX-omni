import { Link } from 'react-router-dom'
import { useApp } from '../App.jsx'

const LANGS = [
  { code: 'en', label: 'EN' },
  { code: 'ta', label: 'தமிழ்' },
  { code: 'hi', label: 'हिंदी' },
  { code: 'ml', label: 'മല' },
]

export default function Navbar() {
  const { lang, setLang, t, user, logout } = useApp()

  return (
    <nav className="navbar">
      <div className="navbar-inner">
        <Link to="/" className="navbar-brand">
          🌾 {t('app_name')} <span>v2.0</span>
        </Link>

        <div className="navbar-links">
          <div className="lang-switcher">
            {LANGS.map(l => (
              <button
                key={l.code}
                className={`lang-btn ${lang === l.code ? 'active' : ''}`}
                onClick={() => setLang(l.code)}
              >
                {l.label}
              </button>
            ))}
          </div>

          <Link to="/search" className="btn btn-primary" style={{ padding: '8px 20px', fontSize: 13 }}>
            🔍 {t('search')}
          </Link>

          {user ? (
            <button onClick={logout} className="btn btn-secondary" style={{ padding: '8px 16px', fontSize: 13 }}>
              {user.name || user.phone}
            </button>
          ) : (
            <Link to="/login" className="btn btn-secondary" style={{ padding: '8px 16px', fontSize: 13 }}>
              {t('login')}
            </Link>
          )}
        </div>
      </div>
    </nav>
  )
}
