import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { useApp } from '../App.jsx'
import { API_BASE_URL } from '../api_config.js'

export default function Search() {
  const { t, lang, setSearchResult } = useApp()
  const navigate = useNavigate()

  const [districts, setDistricts] = useState([])
  const [taluks, setTaluks] = useState([])
  const [villages, setVillages] = useState([])

  const [form, setForm] = useState({
    owner_name: '', district: '', taluk: '', village: '',
    survey_number: '', mobile_number: '', language: lang,
  })
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    fetch(`${API_BASE_URL}/api/land/districts`).then(r => r.json()).then(d => setDistricts(d.districts || []))
      .catch(() => setDistricts(['Erode', 'Coimbatore', 'Salem', 'Namakkal', 'Tiruppur']))
  }, [])

  // Mock data fallback for when API is unreachable
  const MOCK_DATA = {
    "Erode": { taluks: ["Erode", "Gobichettipalayam", "Bhavani", "Sathyamangalam", "Perundurai", "Anthiyur"], villages: { "Erode": ["Erode Town", "Karungalpalayam", "Veerappanchatram", "Chithode", "Modakkurichi"], "Gobichettipalayam": ["Gobichettipalayam", "Bhavanisagar", "Kasipalayam", "Odasaliyur", "Kadambur"], "Bhavani": ["Bhavani Town", "Kumarapalayam", "Kavundapalayam", "Salangapalayam"], "Sathyamangalam": ["Sathyamangalam", "Thalavadi", "Bannari", "Hasanur"], "Perundurai": ["Perundurai", "Vijayamangalam", "Ingur", "Ellapalayam"], "Anthiyur": ["Anthiyur", "Ammapettai", "Bargur", "Odhimalai"] } },
    "Coimbatore": { taluks: ["Coimbatore North", "Coimbatore South", "Pollachi", "Mettupalayam", "Sulur", "Valparai"], villages: { "Coimbatore North": ["Coimbatore", "Peelamedu", "Singanallur", "Ganapathypuram", "Thudiyalur"], "Coimbatore South": ["R.S. Puram", "Ramanathapuram", "Nanjundapuram", "Vadavalli"], "Pollachi": ["Pollachi", "Anaimalai", "Negamam", "Zamin Uthukuli", "Kinathukadavu"], "Mettupalayam": ["Mettupalayam", "Annur", "Karamadai", "Sirumugai"], "Sulur": ["Sulur", "Irugur", "Perur", "Madukkarai"], "Valparai": ["Valparai", "Aliyar Nagar", "Sholayar"] } },
    "Salem": { taluks: ["Salem", "Mettur", "Omalur", "Attur", "Yercaud", "Sankagiri"], villages: { "Salem": ["Salem Town", "Suramangalam", "Hasthampatti", "Kondalampatti", "Ayothiyapattinam"], "Mettur": ["Mettur", "Mecheri", "Kolathur", "Nangavalli"], "Omalur": ["Omalur", "Thalaivasal", "Kadayampatti", "Valapadi"], "Attur": ["Attur", "Gangavalli", "Pethanaickenpalayam", "Narasingapuram"], "Yercaud": ["Yercaud", "Shevaroy Hills", "Manjakuttai"], "Sankagiri": ["Sankagiri", "Veerapandi", "Edappadi", "Magudanchavadi"] } },
    "Namakkal": { taluks: ["Namakkal", "Rasipuram", "Tiruchengode", "Paramathi-Velur", "Kolli Hills"], villages: { "Namakkal": ["Namakkal Town", "Mohanur", "Erumapalayam", "Puduchatram"], "Rasipuram": ["Rasipuram", "Sendamangalam", "Namagiripettai", "Mangalapuram"], "Tiruchengode": ["Tiruchengode", "Kumarapalayam", "Pallipalayam", "Sankari"], "Paramathi-Velur": ["Paramathi", "Velur", "Jedarpalayam", "Kabilarmalai"], "Kolli Hills": ["Semmedu", "Ariyur Nagar", "Valavanthi Nagar"] } },
    "Tiruppur": { taluks: ["Tiruppur North", "Tiruppur South", "Avinashi", "Palladam", "Dharapuram", "Kangayam", "Udumalaipettai"], villages: { "Tiruppur North": ["Tiruppur", "Angeripalayam", "Mangalam", "Nallur"], "Tiruppur South": ["Avinashi Road", "Perumanallur", "Uthukuli", "Vellakoil"], "Avinashi": ["Avinashi", "Chennimalai", "Gudimangalam"], "Palladam": ["Palladam", "Pongalur", "Madathukulam"], "Dharapuram": ["Dharapuram", "Mulanur", "Kunnathur"], "Kangayam": ["Kangayam", "Vellakovil", "Nathakadaiyur"], "Udumalaipettai": ["Udumalaipettai", "Madathukulam", "Gudalur"] } }
  };

  useEffect(() => {
    if (form.district) {
      fetch(`${API_BASE_URL}/api/land/taluks/${form.district}`)
        .then(r => r.json())
        .then(d => setTaluks(d.taluks || []))
        .catch(() => {
          console.warn("API failed, using fallback taluks");
          setTaluks(MOCK_DATA[form.district]?.taluks || []);
        })
      setForm(f => ({ ...f, taluk: '', village: '' }))
      setVillages([])
    }
  }, [form.district])

  useEffect(() => {
    if (form.district && form.taluk) {
      fetch(`${API_BASE_URL}/api/land/villages/${form.district}/${form.taluk}`)
        .then(r => r.json())
        .then(d => setVillages(d.villages || []))
        .catch(() => {
          console.warn("API failed, using fallback villages");
          setVillages(MOCK_DATA[form.district]?.villages[form.taluk] || []);
        })
      setForm(f => ({ ...f, village: '' }))
    }
  }, [form.taluk])

  useEffect(() => { setForm(f => ({ ...f, language: lang })) }, [lang])

  const update = (field, value) => setForm(f => ({ ...f, [field]: value }))

  const handleSearch = async (e) => {
    e.preventDefault()
    if (!form.district) { setError('Please select a district'); return }
    setError('')
    setLoading(true)

    try {
      const res = await fetch(`${API_BASE_URL}/api/search`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(form),
      })
      const data = await res.json()
      if (!res.ok) { setError(data.detail || 'Search failed'); return }
      setSearchResult(data)
      navigate('/report')
    } catch (err) {
      setError('Connection failed. Make sure the backend server is running on port 8000.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="container search-page">
      {loading && (
        <div className="loading-overlay">
          <div className="spinner"></div>
          <p className="loading-text">{t('loading')}</p>
          <p style={{ color: 'var(--text-muted)', fontSize: 13, marginTop: 8 }}>
            Searching Indian Kanoon, NJDG & court databases...
          </p>
        </div>
      )}

      <div className="search-form-container fade-in">
        <div style={{ textAlign: 'center', marginBottom: 8 }}>
          <span style={{ fontSize: 48 }}>🔍</span>
        </div>
        <h2>{t('search_button')}</h2>
        <p className="subtitle">Enter land details to check for court cases and litigation risk</p>

        {error && <div className="alert alert-error">{error}</div>}

        <form onSubmit={handleSearch} className="glass-card" style={{ padding: 32 }}>
          <div className="form-grid">
            <div className="form-group full-width">
              <label>👤 {t('owner_name')}</label>
              <input type="text" className="form-input"
                placeholder="e.g. Murugesan s/o Ramu"
                value={form.owner_name} onChange={e => update('owner_name', e.target.value)} />
            </div>

            <div className="form-group">
              <label>📍 {t('district')} *</label>
              <select className="form-select" required value={form.district}
                onChange={e => update('district', e.target.value)}>
                <option value="">{t('select_district')}</option>
                {districts.map(d => <option key={d} value={d}>{t(d)}</option>)}
              </select>
            </div>

            <div className="form-group">
              <label>🏘️ {t('taluk')}</label>
              <select className="form-select" value={form.taluk}
                onChange={e => update('taluk', e.target.value)} disabled={!form.district}>
                <option value="">{t('select_taluk')}</option>
                {taluks.map(tk => <option key={tk} value={tk}>{t(tk)}</option>)}
              </select>
            </div>

            <div className="form-group">
              <label>🏡 {t('village')}</label>
              <select className="form-select" value={form.village}
                onChange={e => update('village', e.target.value)} disabled={!form.taluk}>
                <option value="">{t('select_village')}</option>
                {villages.map(v => <option key={v} value={v}>{t(v)}</option>)}
              </select>
            </div>

            <div className="form-group">
              <label>📋 {t('survey_number')}</label>
              <input type="text" className="form-input"
                placeholder="e.g. 123/4A"
                value={form.survey_number} onChange={e => update('survey_number', e.target.value)} />
            </div>

            <div className="form-group full-width">
              <label>📱 {t('mobile_number')}</label>
              <input type="tel" className="form-input"
                placeholder="9876543210"
                value={form.mobile_number} onChange={e => update('mobile_number', e.target.value)} />
            </div>

            <div className="full-width" style={{ marginTop: 8 }}>
              <button type="submit" className="btn btn-primary" disabled={loading}
                style={{ width: '100%', padding: '16px', fontSize: 16 }}>
                {loading ? '⏳ ' + t('loading') : '🔍 ' + t('search_button')}
              </button>
            </div>
          </div>
        </form>

        <div style={{ textAlign: 'center', marginTop: 24, color: 'var(--text-muted)', fontSize: 13 }}>
          <p>🔒 Your data is secure • 🤖 AI-powered analysis • ⚡ Results in seconds</p>
        </div>
      </div>
    </div>
  )
}
