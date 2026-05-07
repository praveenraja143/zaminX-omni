import { useState, createContext, useContext } from 'react'
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { LOCATION_TRANSLATIONS } from './locations.js'
import Navbar from './components/Navbar.jsx'
import Landing from './pages/Landing.jsx'
import Login from './pages/Login.jsx'
import Search from './pages/Search.jsx'
import Report from './pages/Report.jsx'

export const AppContext = createContext()

export function useApp() { return useContext(AppContext) }

const TRANSLATIONS = {
  en: { app_name:"Zamin X", tagline:"Know your land. Know its truth.", search:"Search Land", login:"Login", register:"Register", dashboard:"Dashboard", owner_name:"Land Owner Name", district:"District", taluk:"Taluk", village:"Village", survey_number:"Survey Number", mobile_number:"Mobile Number", search_button:"Check Land Status", risk_score:"Risk Score", cases_found:"Court Cases Found", no_cases:"No court cases found! Land appears safe.", patta_details:"Patta Details", chitta_details:"Chitta Details", loading:"Searching court records...", error:"Something went wrong. Please try again.", powered_by:"Powered by AI + Blockchain", free_service:"Free Service for Rural India", select_district:"Select District", select_taluk:"Select Taluk", select_village:"Select Village", chargesheet:"Case Summary", ai_summary:"AI Summary", risk_low:"Low Risk - Safe to Buy", risk_medium:"Medium Risk - Proceed with Caution", risk_high:"High Risk - Not Recommended", risk_critical:"Critical Risk - DO NOT BUY", active:"Active", disposed:"Disposed", petitioner:"Petitioner", respondent:"Respondent", next_hearing:"Next Hearing", case_type:"Case Type", blockchain_verified:"Blockchain Verified", Erode:"Erode", Coimbatore:"Coimbatore", Salem:"Salem", Namakkal:"Namakkal", Tiruppur:"Tiruppur" },
  ta: { ...LOCATION_TRANSLATIONS.ta, app_name:"ஜமீன் X", tagline:"உங்கள் நிலத்தை அறியுங்கள். உண்மையை அறியுங்கள்.", search:"நிலம் தேடு", login:"உள்நுழைக", register:"பதிவு செய்க", dashboard:"டாஷ்போர்டு", owner_name:"நில உரிமையாளர் பெயர்", district:"மாவட்டம்", taluk:"வட்டம்", village:"கிராமம்", survey_number:"சர்வே எண்", mobile_number:"கைபேசி எண்", search_button:"நில நிலையை சரிபார்க்கவும்", risk_score:"ஆபத்து மதிப்பெண்", cases_found:"நீதிமன்ற வழக்குகள் கண்டறியப்பட்டன", no_cases:"நீதிமன்ற வழக்குகள் எதுவும் இல்லை! நிலம் பாதுகாப்பானது.", patta_details:"பட்டா விவரங்கள்", chitta_details:"சிட்டா விவரங்கள்", loading:"நீதிமன்ற பதிவுகளைத் தேடுகிறது...", error:"ஏதோ தவறு நடந்தது. மீண்டும் முயற்சிக்கவும்.", powered_by:"AI + பிளாக்செயின் மூலம்", free_service:"கிராமப்புற இந்தியாவுக்கான இலவச சேவை", select_district:"மாவட்டத்தைத் தேர்ந்தெடுங்கள்", select_taluk:"வட்டத்தைத் தேர்ந்தெடுங்கள்", select_village:"கிராமத்தைத் தேர்ந்தெடுங்கள்", chargesheet:"வழக்கு சுருக்கம்", ai_summary:"AI சுருக்கம்", risk_low:"குறைந்த ஆபத்து - வாங்கலாம்", risk_medium:"நடுத்தர ஆபத்து - கவனமாக செயல்படுங்கள்", risk_high:"அதிக ஆபத்து - பரிந்துரைக்கப்படவில்லை", risk_critical:"மிகப்பெரிய ஆபத்து - வாங்க வேண்டாம்", active:"செயலில்", disposed:"முடிவடைந்தது", petitioner:"மனுதாரர்", respondent:"பிரதிவாதி", next_hearing:"அடுத்த விசாரணை", case_type:"வழக்கு வகை", blockchain_verified:"பிளாக்செயின் சரிபார்க்கப்பட்டது", Erode:"ஈரோடு", Coimbatore:"கோயம்புத்தூர்", Salem:"சேலம்", Namakkal:"நாமக்கல்", Tiruppur:"திருப்பூர்" },
  hi: { ...LOCATION_TRANSLATIONS.hi, app_name:"ज़मीन X", tagline:"अपनी ज़मीन जानो। सच्चाई जानो।", search:"भूमि खोजें", login:"लॉगिन", register:"रजिस्टर", dashboard:"डैशबोर्ड", owner_name:"भूमि मालिक का नाम", district:"जिला", taluk:"तालुक", village:"गाँव", survey_number:"सर्वे नंबर", mobile_number:"मोबाइल नंबर", search_button:"भूमि स्थिति जांचें", risk_score:"जोखिम स्कोर", cases_found:"अदालती मामले मिले", no_cases:"कोई अदालती मामला नहीं मिला! जमीन सुरक्षित।", patta_details:"पट्टा विवरण", chitta_details:"चिट्टा विवरण", loading:"अदालत के रिकॉर्ड खोज रहे हैं...", error:"कुछ गलत हो गया। पुनः प्रयास करें।", powered_by:"AI + ब्लॉकचेन द्वारा", free_service:"ग्रामीण भारत के लिए मुफ्त सेवा", select_district:"जिला चुनें", select_taluk:"तालुक चुनें", select_village:"गाँव चुनें", chargesheet:"मामले का सारांश", ai_summary:"AI सारांश", risk_low:"कम जोखिम - खरीदना सुरक्षित", risk_medium:"मध्यम जोखिम - सावधानी से", risk_high:"उच्च जोखिम - अनुशंसित नहीं", risk_critical:"गंभीर जोखिम - न खरीदें", active:"सक्रिय", disposed:"निपटाया गया", petitioner:"याचिकाकर्ता", respondent:"प्रतिवादी", next_hearing:"अगली सुनवाई", case_type:"मामले का प्रकार", blockchain_verified:"ब्लॉकचेन सत्यापित", Erode:"इरोड", Coimbatore:"कोयंबटूर", Salem:"सेलम", Namakkal:"नमक्कल", Tiruppur:"तिरुपुर" },
  ml: { ...LOCATION_TRANSLATIONS.ml, app_name:"സമിൻ X", tagline:"നിങ്ങളുടെ ഭൂമി അറിയൂ. സത്യം അറിയൂ.", search:"ഭൂമി തിരയുക", login:"ലോഗിൻ", register:"രജിസ്റ്റർ", dashboard:"ഡാഷ്ബോർഡ്", owner_name:"ഭൂമി ഉടമയുടെ പേര്", district:"ജില്ല", taluk:"താലൂക്ക്", village:"ഗ്രാമം", survey_number:"സർവേ നമ്പർ", mobile_number:"മൊബൈൽ നമ്പർ", search_button:"ഭൂമി സ്ഥിതി പരിശോധിക്കുക", risk_score:"റിസ്ക് സ്കോർ", cases_found:"കോടതി കേസുകൾ കണ്ടെത്തി", no_cases:"കോടതി കേസുകൾ ഇല്ല! ഭൂമി സുരക്ഷിതം.", patta_details:"പട്ട വിശദാംശങ്ങൾ", chitta_details:"ചിട്ട വിശദാംശങ്ങൾ", loading:"കോടതി രേഖകൾ തിരയുന്നു...", error:"എന്തോ തെറ്റ് സംഭവിച്ചു. വീണ്ടും ശ്രമിക്കുക.", powered_by:"AI + ബ്ലോക്ക്ചെയിൻ", free_service:"ഗ്രാമീണ ഇന്ത്യയ്ക്കുള്ള സൗജന്യ സേവനം", select_district:"ജില്ല തിരഞ്ഞെടുക്കുക", select_taluk:"താലൂക്ക് തിരഞ്ഞെടുക്കുക", select_village:"ഗ്രാമം തിരഞ്ഞെടുക്കുക", chargesheet:"കേസ് സംഗ്രഹം", ai_summary:"AI സംഗ്രഹം", risk_low:"കുറഞ്ഞ റിസ്ക് - വാങ്ങാം", risk_medium:"ഇടത്തരം റിസ്ക് - ജാഗ്രതയോടെ", risk_high:"ഉയർന്ന റിസ്ക് - ശുപാർശ ചെയ്യുന്നില്ല", risk_critical:"ഗുരുതരമായ റിസ്ക് - വാങ്ങരുത്", active:"സജീവം", disposed:"തീർപ്പാക്കി", petitioner:"ഹർജിക്കാരൻ", respondent:"എതിർകക്ഷി", next_hearing:"അടുത്ത വാദം", case_type:"കേസ് തരം", blockchain_verified:"ബ്ലോക്ക്ചെയിൻ പരിശോധിച്ചു", Erode:"ഈറോഡ്", Coimbatore:"കോയമ്പത്തൂർ", Salem:"സേലം", Namakkal:"നാമക്കൽ", Tiruppur:"തിരുപ്പൂർ" },
}

export default function App() {
  const [lang, setLang] = useState('en')
  const [user, setUser] = useState(null)
  const [token, setToken] = useState(localStorage.getItem('zx_token') || null)
  const [searchResult, setSearchResult] = useState(null)

  const t = (key) => TRANSLATIONS[lang]?.[key] || TRANSLATIONS.en[key] || key

  const login = (userData, authToken) => {
    setUser(userData)
    setToken(authToken)
    localStorage.setItem('zx_token', authToken)
  }

  const logout = () => {
    setUser(null)
    setToken(null)
    localStorage.removeItem('zx_token')
  }

  const ctx = { lang, setLang, t, user, token, login, logout, searchResult, setSearchResult }

  return (
    <AppContext.Provider value={ctx}>
      <BrowserRouter>
        <Navbar />
        <main className="page-content">
          <Routes>
            <Route path="/" element={<Landing />} />
            <Route path="/login" element={<Login />} />
            <Route path="/search" element={<Search />} />
            <Route path="/report" element={searchResult ? <Report /> : <Navigate to="/search" />} />
            <Route path="*" element={<Navigate to="/" />} />
          </Routes>
        </main>
        <footer className="footer">
          <p>© 2026 Zamin X — Project Minds Guilders, JKKM College of Technology, Erode</p>
          <p style={{marginTop: 4}}>{t('powered_by')} • {t('free_service')}</p>
        </footer>
      </BrowserRouter>
    </AppContext.Provider>
  )
}
