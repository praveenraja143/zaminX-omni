import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useApp } from '../App.jsx'
import { API_BASE_URL } from '../api_config.js'

const API = `${API_BASE_URL}/api/auth`

export default function Login() {
  const { t, login } = useApp()
  const navigate = useNavigate()
  const [isRegister, setIsRegister] = useState(false)
  const [phone, setPhone] = useState('')
  const [name, setName] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  const handleSubmit = async (e) => {
    e.preventDefault()
    setError('')
    setLoading(true)

    try {
      const endpoint = isRegister ? `${API}/register` : `${API}/login`
      const body = isRegister
        ? { phone, name, password, language: 'en' }
        : { phone, password }

      const res = await fetch(endpoint, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      })

      const data = await res.json()

      if (!res.ok) {
        setError(data.detail || 'Authentication failed')
        return
      }

      login(data.user, data.token)
      navigate('/search')
    } catch (err) {
      setError('Connection failed. Is the backend running?')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="auth-page">
      <div className="glass-card auth-card fade-in">
        <div style={{ textAlign: 'center', marginBottom: 8 }}>
          <span style={{ fontSize: 48 }}>🌾</span>
        </div>
        <h2>{isRegister ? t('register') : t('login')}</h2>
        <p className="subtitle">{t('tagline')}</p>

        {error && <div className="alert alert-error">{error}</div>}

        <form onSubmit={handleSubmit}>
          {isRegister && (
            <div className="form-group">
              <label>{t('owner_name')}</label>
              <input
                type="text" className="form-input"
                placeholder="Enter your name"
                value={name} onChange={e => setName(e.target.value)}
              />
            </div>
          )}

          <div className="form-group">
            <label>{t('mobile_number')}</label>
            <input
              type="tel" className="form-input" required
              placeholder="9876543210"
              value={phone} onChange={e => setPhone(e.target.value)}
            />
          </div>

          <div className="form-group">
            <label>Password</label>
            <input
              type="password" className="form-input" required
              placeholder="••••••••"
              value={password} onChange={e => setPassword(e.target.value)}
              minLength={4}
            />
          </div>

          <button type="submit" className="btn btn-primary" disabled={loading}
            style={{ width: '100%', marginTop: 8 }}>
            {loading ? '...' : (isRegister ? t('register') : t('login'))}
          </button>
        </form>

        <div className="auth-toggle">
          {isRegister ? (
            <span>Already have an account? <a href="#" onClick={(e) => { e.preventDefault(); setIsRegister(false) }}>{t('login')}</a></span>
          ) : (
            <span>New user? <a href="#" onClick={(e) => { e.preventDefault(); setIsRegister(true) }}>{t('register')}</a></span>
          )}
        </div>
      </div>
    </div>
  )
}
