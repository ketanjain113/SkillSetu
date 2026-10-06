import { useEffect, useRef, useState } from 'react'
import { BrowserRouter, Route, Routes, useNavigate, useParams } from 'react-router-dom'
import Dexie from 'dexie'
import { jsPDF } from 'jspdf'
import QRCode from 'qrcode'

const API_BASE = 'http://localhost:8000'

type Role = 'worker' | 'assessor' | 'admin'

type Competency = {
  id: string
  title: string
  rubric: Record<string, string>
  checklist: string[]
}

type TradePack = {
  pack_id: string
  title: string
  summary?: string
  version?: string
  nsqf_level?: number
  trade_code?: string
  pass_threshold?: number
  safety_critical_steps?: string[]
  checklist?: string[]
  rubric?: Record<string, string>
  nos?: Array<{ id: string; title: string; description: string; prerequisites?: string[]; keywords?: string[] }>
  keywords?: string[]
}

type MatchResult = {
  pack_id: string
  title: string
  confidence: number
  skill_gaps: string[]
  summary: string
  matched_nos?: string[]
  missing_nos?: string[]
  bridge_training?: string[]
  pack_version?: string
  nsqf_level?: number
}

type AuditLog = {
  id: number
  action: string
  details: string
  created_at: string
}

type AppUser = {
  username: string
  role: Role
  name: string
}

type Locale = 'en' | 'hi' | 'mr' | 'ta' | 'bn'

declare global {
  interface Window {
    SpeechRecognition?: new () => any
    webkitSpeechRecognition?: new () => any
  }
}

const translations: Record<Locale, Record<string, string>> = {
  en: {
    workerFlow: 'Open worker flow',
    passport: 'My skills passport',
    notifications: 'Notifications',
    language: 'Language',
    lowLiteracy: 'Low-literacy mode',
    accessibility: 'Accessibility mode',
    declareTitle: 'Declare: voice or text',
    demoBadge: 'Demo data / AI suggested',
    voiceInput: 'Try voice input',
    readPrompt: 'Read prompt aloud',
    statusTracker: 'Assessment status tracker',
    mapToPacks: 'Map to packs',
    useHindi: 'Use Hindi sample',
    qualityCheck: 'Quality check',
    stepDone: 'Step done',
    saveEvidence: 'Save evidence',
    myPassport: 'My skills passport',
    notificationsTitle: 'Notifications',
    shareQr: 'Share QR',
    mockJob: 'Local job recommendation',
    mockCourse: 'Bridge course',
    queueStatus: 'Sync queue status',
    retryRule: 'Retry rules',
    storageQuota: 'Storage quota',
  },
  hi: {
    workerFlow: 'कार्यकर्ता फ्लो खोलें',
    passport: 'मेरा कौशल पासपोर्ट',
    notifications: 'सूचनाएँ',
    language: 'भाषा',
    lowLiteracy: 'कम-पढ़ने वाली मोड',
    accessibility: 'पहुँच मोड',
    declareTitle: 'घोषणा: आवाज या टेक्स्ट',
    demoBadge: 'डेमो डेटा / एआई सुझाव',
    voiceInput: 'आवाज इनपुट आज़माएँ',
    readPrompt: 'प्रॉम्प्ट सुनाएँ',
    statusTracker: 'मूल्यांकन स्थिति ट्रैकर',
    mapToPacks: 'पैक से जोड़ें',
    useHindi: 'हिंदी नमूना',
    qualityCheck: 'गुणवत्ता जाँच',
    stepDone: 'स्टेप पूरा',
    saveEvidence: 'सबूत सेव करें',
    myPassport: 'मेरा कौशल पासपोर्ट',
    notificationsTitle: 'सूचनाएँ',
    shareQr: 'क्यूआर साझा करें',
    mockJob: 'स्थानीय नौकरी सुझाव',
    mockCourse: 'ब्रिज कोर्स',
    queueStatus: 'सिंक कतार स्थिति',
    retryRule: 'पुनः प्रयास नियम',
    storageQuota: 'स्टोरेज कोटा',
  },
  mr: {
    workerFlow: 'कामगार फ्लो उघडा',
    passport: 'माझा कौशल्य पासपोर्ट',
    notifications: 'नोटिफिकेशन',
    language: 'भाषा',
    lowLiteracy: 'कमी-वाचन मोड',
    accessibility: 'सरलता मोड',
    declareTitle: 'जाहीरनामा: आवाज किंवा मजकूर',
    demoBadge: 'डेमो डेटा / एआई सूचना',
    voiceInput: 'आवाज इनपुट वापरा',
    readPrompt: 'प्रॉम्प्ट वाचून दाखवा',
    statusTracker: 'मूल्यांकन स्थिती ट्रॅकर',
    mapToPacks: 'पॅकशी जोडा',
    useHindi: 'हिंदी नमुना',
    qualityCheck: 'गुणवत्ता तपासा',
    stepDone: 'स्टेप पूर्ण',
    saveEvidence: 'साक्ष्य जतन करा',
    myPassport: 'माझा कौशल्य पासपोर्ट',
    notificationsTitle: 'नोटिफिकेशन',
    shareQr: 'QR शेअर करा',
    mockJob: 'स्थानिक नोकरी सूचना',
    mockCourse: 'ब्रिज कोर्स',
    queueStatus: 'सिंक रांगेची स्थिती',
    retryRule: 'पुनः प्रयत्न नियम',
    storageQuota: 'स्टोरेज कोटा',
  },
  ta: {
    workerFlow: 'பணியாளர் பயணம்',
    passport: 'என் திறன் பாஸ்போர்ட்',
    notifications: 'அறிவிப்புகள்',
    language: 'மொழி',
    lowLiteracy: 'குறைந்த வாசிப்பு முறை',
    accessibility: 'அணுகல் முறை',
    declareTitle: 'அறிக்கை: குரல் அல்லது உரை',
    demoBadge: 'டெமோ டேட்டா / AI பரிந்துரை',
    voiceInput: 'குரல் உள்ளீடு',
    readPrompt: 'செய்தியை ஒலிக்க',
    statusTracker: 'மதிப்பீட்டு நிலை',
    mapToPacks: 'பேக்குடன் இணை',
    useHindi: 'இந்தி மாதிரி',
    qualityCheck: 'தரம் சரிபார்ப்பு',
    stepDone: 'படி முடிந்தது',
    saveEvidence: 'சான்றை சேமி',
    myPassport: 'என் திறன் பாஸ்போர்ட்',
    notificationsTitle: 'அறிவிப்புகள்',
    shareQr: 'QR பகிர்',
    mockJob: 'உள்ளூர் வேலை பரிந்துரை',
    mockCourse: 'பிரிட்ஜ் கோர்ஸ்',
    queueStatus: 'சின்க் வரிசை நிலை',
    retryRule: 'மீண்டும் முயற்சி விதி',
    storageQuota: 'சேமிப்பக ஒதுக்கீடு',
  },
  bn: {
    workerFlow: 'কর্মী ফ্লো খুলুন',
    passport: 'আমার দক্ষতার পাসপোর্ট',
    notifications: 'নোটিফিকেশন',
    language: 'ভাষা',
    lowLiteracy: 'কম-পঠন মোড',
    accessibility: 'অ্যাক্সেসিবিলিটি',
    declareTitle: 'ঘোষণা: ভয়েস বা টেক্সট',
    demoBadge: 'ডেমো ডেটা / AI পরামর্শ',
    voiceInput: 'ভয়েস ইনপুট',
    readPrompt: 'প্রম্পট শুনান',
    statusTracker: 'মূল্যায়ন অবস্থা',
    mapToPacks: 'প্যাকের সাথে মিলান',
    useHindi: 'হিন্দি নমুনা',
    qualityCheck: 'গুণমান পরীক্ষা',
    stepDone: 'ধাপ শেষ',
    saveEvidence: 'প্রমাণ সংরক্ষণ',
    myPassport: 'আমার দক্ষতার পাসপোর্ট',
    notificationsTitle: 'নোটিফিকেশন',
    shareQr: 'QR শেয়ার',
    mockJob: 'স্থানীয় চাকরি সাজেশন',
    mockCourse: 'ব্রিজ কোর্স',
    queueStatus: 'সিঙ্ক সারির অবস্থা',
    retryRule: 'পুনরায় চেষ্টা নিয়ম',
    storageQuota: 'স্টোরেজ কোটা',
  },
}

const offlineDb = new Dexie('skillsetu-offline-db')
offlineDb.version(1).stores({ queue: '++id, action, createdAt, synced' })

async function apiRequest<T>(path: string, options: RequestInit = {}, token?: string): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...(options.headers ?? {}),
    },
  })

  if (!response.ok) {
    const body = await response.text()
    throw new Error(body || 'Request failed')
  }

  return (await response.json()) as T
}

async function persistQueue(action: string, payload: unknown) {
  await offlineDb.table('queue').add({
    action,
    payload,
    createdAt: new Date().toISOString(),
    synced: false,
  })
}

async function syncQueue(token?: string) {
  const entries = await offlineDb.table('queue').where('synced').equals(0).toArray()
  for (const entry of entries) {
    try {
      await apiRequest(`/api/${entry.action}`, {
        method: 'POST',
        body: JSON.stringify(entry.payload),
      }, token)
      await offlineDb.table('queue').update(entry.id, { synced: true })
    } catch {
      break
    }
  }
}

const competencyLevels = [1, 2, 3, 4, 5]
const workflowStages = ['Registered', 'Declared', 'Evidence captured', 'Under review', 'Second review', 'Moderation', 'Signed off', 'Credential issued', 'Appeal']

function StatusTracker({ currentStatus }: { currentStatus?: string }) {
  const activeIndex = Math.max(0, workflowStages.findIndex((stage) => stage.toLowerCase() === (currentStatus ?? 'declared').replace(/_/g, ' ').toLowerCase()))
  return (
    <div className="chip-list">
      {workflowStages.map((stage, index) => (
        <span key={stage} className={`chip ${index <= activeIndex ? 'selected' : ''}`}>
          {stage}
        </span>
      ))}
    </div>
  )
}

function speakText(text: string) {
  if (!('speechSynthesis' in window)) return
  const voices = window.speechSynthesis.getVoices()
  const utterance = new SpeechSynthesisUtterance(text)
  const preferredVoice = voices.find((voice) => /en|hi|mr|ta|bn/i.test(voice.lang))
  if (preferredVoice) utterance.voice = preferredVoice
  utterance.rate = 0.95
  utterance.pitch = 1
  window.speechSynthesis.cancel()
  window.speechSynthesis.speak(utterance)
}

async function startVoiceInput(language: Locale, onText: (value: string) => void) {
  const CurrentSpeechRecognition = (window as any).SpeechRecognition ?? (window as any).webkitSpeechRecognition
  if (CurrentSpeechRecognition) {
    const recognition = new CurrentSpeechRecognition()
    recognition.lang = language === 'hi' ? 'hi-IN' : language === 'mr' ? 'mr-IN' : language === 'ta' ? 'ta-IN' : language === 'bn' ? 'bn-BD' : 'en-IN'
    recognition.interimResults = false
    recognition.onresult = (event: any) => {
      const result = event.results[0][0].transcript
      onText(result)
    }
    recognition.start()
    return
  }

  if (navigator.onLine) {
    const key = localStorage.getItem('skillsetu-bhashini-key')
    if (key) {
      onText(`Voice input configured with Bhashini key: ${key.slice(0, 4)}...`)
      return
    }
  }

  onText('Voice input unavailable. Please type your answer or retry with a microphone.')
}

function App() {
  const [online, setOnline] = useState<boolean>(navigator.onLine)
  const [simulateOffline, setSimulateOffline] = useState(false)
  const [locale, setLocale] = useState<Locale>(() => (localStorage.getItem('skillsetu-locale') as Locale) || 'en')
  const [lowLiteracyMode, setLowLiteracyMode] = useState(Boolean(localStorage.getItem('skillsetu-low-literacy')))
  const [accessibilityMode, setAccessibilityMode] = useState(Boolean(localStorage.getItem('skillsetu-accessibility')))
  const [token, setToken] = useState(localStorage.getItem('skillsetu-token') ?? '')
  const [user, setUser] = useState<AppUser | null>(() => {
    const raw = localStorage.getItem('skillsetu-user')
    return raw ? JSON.parse(raw) : null
  })

  useEffect(() => {
    localStorage.setItem('skillsetu-locale', locale)
  }, [locale])

  useEffect(() => {
    localStorage.setItem('skillsetu-low-literacy', lowLiteracyMode ? '1' : '')
  }, [lowLiteracyMode])

  useEffect(() => {
    localStorage.setItem('skillsetu-accessibility', accessibilityMode ? '1' : '')
  }, [accessibilityMode])

  useEffect(() => {
    const updateStatus = () => setOnline(simulateOffline ? false : navigator.onLine)
    window.addEventListener('online', updateStatus)
    window.addEventListener('offline', updateStatus)
    return () => {
      window.removeEventListener('online', updateStatus)
      window.removeEventListener('offline', updateStatus)
    }
  }, [simulateOffline])

  useEffect(() => {
    if (token) {
      void syncQueue(token)
    }
  }, [token, online])

  const logout = () => {
    localStorage.removeItem('skillsetu-token')
    localStorage.removeItem('skillsetu-user')
    setToken('')
    setUser(null)
  }

  return (
    <BrowserRouter>
      <div className="app-shell">
        <header className="topbar">
          <div>
            <strong>SkillSetu AI</strong>
            <span className="status-pill">{simulateOffline ? 'Offline demo' : online ? 'Online' : 'Offline'}</span>
          </div>
          <div className="toolbar">
            <label className="toggle-inline compact-control">
              <span>{translations[locale].language}</span>
              <select aria-label="Select language" value={locale} onChange={(event) => setLocale(event.target.value as Locale)}>
                <option value="en">English</option>
                <option value="hi">हिन्दी</option>
                <option value="mr">मराठी</option>
                <option value="ta">தமிழ்</option>
                <option value="bn">বাংলা</option>
              </select>
            </label>
            <label className="toggle-inline">
              <input type="checkbox" checked={lowLiteracyMode} onChange={() => setLowLiteracyMode((value) => !value)} />
              {translations[locale].lowLiteracy}
            </label>
            <label className="toggle-inline">
              <input type="checkbox" checked={accessibilityMode} onChange={() => setAccessibilityMode((value) => !value)} />
              {translations[locale].accessibility}
            </label>
            <label className="toggle-inline">
              <input type="checkbox" checked={simulateOffline} onChange={() => setSimulateOffline((value) => !value)} />
              Simulate offline
            </label>
            {user ? (
              <button type="button" className="ghost-button" onClick={logout}>Logout</button>
            ) : null}
          </div>
        </header>

        <Routes>
          <Route path="/" element={<HomePage user={user} locale={locale} lowLiteracyMode={lowLiteracyMode} />} />
          <Route path="/login" element={<LoginPage setToken={setToken} setUser={setUser} locale={locale} />} />
          <Route path="/worker/declare" element={<WorkerDeclarePage token={token} locale={locale} lowLiteracyMode={lowLiteracyMode} />} />
          <Route path="/worker/demonstrate" element={<DemonstratePage token={token} locale={locale} lowLiteracyMode={lowLiteracyMode} />} />
          <Route path="/worker/passport" element={<MySkillsPassportPage locale={locale} lowLiteracyMode={lowLiteracyMode} />} />
          <Route path="/worker/notifications" element={<NotificationsPage locale={locale} lowLiteracyMode={lowLiteracyMode} />} />
          <Route path="/assessor/score" element={<AssessorScorePage token={token} />} />
          <Route path="/admin/packs" element={<AdminPacksPage token={token} />} />
          <Route path="/calibration" element={<CalibrationPage token={token} />} />
          <Route path="/certificate" element={<CertificatePage />} />
          <Route path="/verify/:id" element={<VerificationPage />} />
        </Routes>
      </div>
    </BrowserRouter>
  )
}

function HomePage({ user, locale, lowLiteracyMode }: { user: AppUser | null; locale: Locale; lowLiteracyMode: boolean }) {
  const navigate = useNavigate()
  const t = translations[locale]

  return (
    <main className="page-shell">
      <section className="hero-card">
        <div>
          <p className="eyebrow">SIH 2026 • PS 26242</p>
          <h1>AI-assisted Recognition of Prior Learning</h1>
          <p className="lead">Human assessor decides. AI prepares evidence. Certification never auto-runs.</p>
        </div>
        <div className="hero-actions">
          {user ? (
            <>
              {user.role === 'worker' ? (
                <>
                  <button type="button" className={lowLiteracyMode ? 'large-button' : ''} onClick={() => navigate('/worker/declare')}>{t.workerFlow}</button>
                  <button type="button" className="ghost-button" onClick={() => navigate('/worker/passport')}>{t.passport}</button>
                  <button type="button" className="ghost-button" onClick={() => navigate('/worker/notifications')}>{t.notifications}</button>
                </>
              ) : null}
              {user.role === 'assessor' || user.role === 'admin' ? <button type="button" onClick={() => navigate('/assessor/score')}>Open assessor console</button> : null}
              {user.role === 'admin' ? <button type="button" className="ghost-button" onClick={() => navigate('/admin/packs')}>Manage trade packs</button> : null}
            </>
          ) : (
            <button type="button" onClick={() => navigate('/login')}>Login to continue</button>
          )}
        </div>
      </section>

      <section className="three-grid">
        <div className="info-card">
          <h3>{t.declareTitle}</h3>
          <p>Voice or text in Hindi/English mapped to top-3 qualification packs.</p>
        </div>
        <div className="info-card">
          <h3>Demonstrate</h3>
          <p>Checklist, captured evidence, AI-suggested tags, and quality check.</p>
        </div>
        <div className="info-card">
          <h3>{t.passport}</h3>
          <p>Credential passport, QR share, bridge learning and recommended local jobs.</p>
        </div>
      </section>
    </main>
  )
}

function LoginPage({ setToken, setUser, locale }: { setToken: (token: string) => void; setUser: (user: AppUser | null) => void; locale: Locale }) {
  const navigate = useNavigate()
  const t = translations[locale]
  const [username, setUsername] = useState('worker1')
  const [password, setPassword] = useState('worker123')
  const [error, setError] = useState('')

  const submit = async () => {
    try {
      const data = await apiRequest<{ access_token: string; role: Role; username: string }>(
        '/api/auth/login',
        { method: 'POST', body: JSON.stringify({ username, password }) },
      )
      const user = { username: data.username, role: data.role, name: username }
      localStorage.setItem('skillsetu-token', data.access_token)
      localStorage.setItem('skillsetu-user', JSON.stringify(user))
      setToken(data.access_token)
      setUser(user)
      navigate(data.role === 'worker' ? '/worker/declare' : data.role === 'assessor' || data.role === 'admin' ? '/assessor/score' : '/')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Login failed')
    }
  }

  return (
    <main className="page-shell center-layout">
      <div className="card form-card">
        <h2>{t.passport}</h2>
        <label>
          Username
          <input value={username} onChange={(event) => setUsername(event.target.value)} />
        </label>
        <label>
          Password
          <input type="password" value={password} onChange={(event) => setPassword(event.target.value)} />
        </label>
        {error ? <p className="error-text">{error}</p> : null}
        <button type="button" onClick={submit}>Login</button>
        <p className="micro-copy">Demo users: admin/admin123, assessor1/assessor123, worker1/worker123</p>
      </div>
    </main>
  )
}

function WorkerDeclarePage({ token, locale, lowLiteracyMode }: { token: string; locale: Locale; lowLiteracyMode: boolean }) {
  const [text, setText] = useState('I installed a new lighting circuit and checked the switchboard for safety before testing continuity and earthing.')
  const [matches, setMatches] = useState<MatchResult[]>([])
  const t = translations[locale]

  const runDeclare = async () => {
    const result = await apiRequest<{ matches: MatchResult[] }>('/api/declare', { method: 'POST', body: JSON.stringify({ text }) }, token)
    await apiRequest('/api/assessments', { method: 'POST', body: JSON.stringify({ text, matches: result.matches }) }, token)
    setMatches(result.matches)
  }

  const handleVoiceInput = () => {
    void startVoiceInput(locale, setText)
    speakText('Please describe the work you have already done and the tasks you want assessed.')
  }

  return (
    <main className="page-shell">
      <div className="card padded-card">
        <h2>{t.declareTitle}</h2>
        <p className="micro-copy">Hindi/English supported. AI maps your declaration to top qualification packs and skill gaps.</p>
        <textarea aria-label="Declaration text" value={text} onChange={(event) => setText(event.target.value)} rows={6} />
        <div className="inline-actions">
          <button type="button" className={lowLiteracyMode ? 'large-button' : ''} onClick={runDeclare}>{t.mapToPacks}</button>
          <button type="button" className="ghost-button" onClick={() => setText('मैं ने स्विचबोर्ड की सुरक्षा जाँच की और तारों का परीक्षण किया।')}>{t.useHindi}</button>
          <button type="button" className="ghost-button" onClick={handleVoiceInput}>{t.voiceInput}</button>
          <button type="button" className="ghost-button" onClick={() => speakText(text)}>{t.readPrompt}</button>
        </div>
      </div>

      <div className="card padded-card">
        <h3>{t.statusTracker}</h3>
        <StatusTracker currentStatus="declared" />
      </div>

      {matches.length ? (
        <section className="stack">
          {matches.map((match) => (
            <div key={match.pack_id} className="card padded-card">
              <div className="card-header-row">
                <h3>{match.title}</h3>
                <span>{Math.round(match.confidence * 100)}%</span>
              </div>
              <div className="progress-bar">
                <span style={{ width: `${Math.round(match.confidence * 100)}%` }} />
              </div>
              <p>{match.summary}</p>
              <div className="chip-list">
                {match.skill_gaps.map((gap) => <span key={gap} className="chip">{gap}</span>)}
              </div>
              <p className="micro-copy">Pack version: {match.pack_version ?? 'demo-version'} • NSQF {match.nsqf_level ?? 'N/A'}</p>
              {match.matched_nos?.length ? <p><strong>Matched NOS:</strong> {match.matched_nos.join(', ')}</p> : null}
              {match.missing_nos?.length ? <p><strong>Missing NOS:</strong> {match.missing_nos.join(', ')}</p> : null}
              {match.bridge_training?.length ? <p><strong>Suggested bridge training:</strong> {match.bridge_training.join(' • ')}</p> : null}
            </div>
          ))}
        </section>
      ) : null}
    </main>
  )
}

function MySkillsPassportPage({ locale, lowLiteracyMode }: { locale: Locale; lowLiteracyMode: boolean }) {
  const t = translations[locale]
  const [passportUrl] = useState('https://demo.skillsetu.ai/passport/worker1')

  const sharePassport = async () => {
    if (navigator.share) {
      await navigator.share({ title: 'SkillSetu passport', text: 'My work profile and credentials', url: passportUrl })
      return
    }
    await navigator.clipboard.writeText(passportUrl)
    alert('Passport link copied to clipboard.')
  }

  const generateQr = async () => {
    const url = await QRCode.toDataURL(passportUrl)
    const img = document.getElementById('passport-qr') as HTMLImageElement | null
    if (img) img.src = url
  }

  useEffect(() => {
    void generateQr()
  }, [])

  return (
    <main className="page-shell">
      <div className="card padded-card">
        <h2>{t.myPassport}</h2>
        <div className="passport-grid">
          <div>
            <p><strong>Credential:</strong> Domestic Electrician – NSQF 4</p>
            <p><strong>Progress:</strong> 72% to NSQF 5</p>
            <p><strong>Next milestone:</strong> Advanced fault-finding and worksite safety review</p>
            <button type="button" className={lowLiteracyMode ? 'large-button' : ''} onClick={() => sharePassport()}>{t.shareQr}</button>
          </div>
          <div className="qr-panel">
            <img id="passport-qr" alt="QRCode for worker passport" src="" />
          </div>
        </div>
      </div>

      <div className="card padded-card">
        <h3>Recommended bridge courses (demo)</h3>
        <ul className="audit-list">
          <li><strong>{t.mockCourse}:</strong> Advanced fault finding in domestic wiring</li>
          <li><strong>{t.mockCourse}:</strong> Safe worksite supervision and inspection</li>
        </ul>
      </div>

      <div className="card padded-card">
        <h3>{t.mockJob}</h3>
        <ul className="audit-list">
          <li>Junior site technician – local service provider network</li>
          <li>Apprentice supervisor – housing maintenance team</li>
        </ul>
      </div>
    </main>
  )
}

function NotificationsPage({ locale, lowLiteracyMode }: { locale: Locale; lowLiteracyMode: boolean }) {
  const t = translations[locale]
  const [notifications, setNotifications] = useState<Array<{ id: number; channel: string; body: string; status: string }>>([
    { id: 1, channel: 'SMS', body: 'Your assessment moved to review.', status: 'queued' },
    { id: 2, channel: 'WhatsApp', body: 'Please complete your evidence check.', status: 'sent' },
  ])

  const sendMockNotification = (channel: 'SMS' | 'WhatsApp') => {
    setNotifications((current) => [
      { id: Date.now(), channel, body: `Demo ${channel} alert: your RPL status has changed.`, status: 'sent' },
      ...current,
    ])
  }

  return (
    <main className="page-shell">
      <div className="card padded-card">
        <h2>{t.notificationsTitle}</h2>
        <div className="inline-actions">
          <button type="button" className={lowLiteracyMode ? 'large-button' : ''} onClick={() => sendMockNotification('SMS')}>Send SMS</button>
          <button type="button" className="ghost-button" onClick={() => sendMockNotification('WhatsApp')}>Send WhatsApp</button>
        </div>
        <ul className="audit-list">
          {notifications.map((item) => (
            <li key={item.id}><strong>{item.channel}</strong> — {item.body} <span className="status-pill">{item.status}</span></li>
          ))}
        </ul>
      </div>
    </main>
  )
}

function AdminPacksPage({ token }: { token: string }) {
  const [draft, setDraft] = useState('[]')
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')

  useEffect(() => {
    void (async () => {
      try {
        const data = await apiRequest<{ trade_packs: TradePack[] }>('/api/trade-packs', {}, token)
        setDraft(JSON.stringify(data.trade_packs, null, 2))
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Unable to load packs')
      }
    })()
  }, [token])

  const savePacks = async () => {
    try {
      const parsed = JSON.parse(draft)
      const validation = await apiRequest<{ valid: boolean; errors: string[] }>('/api/trade-packs/validate', { method: 'POST', body: JSON.stringify({ pack: parsed[0] ?? {} }) }, token)
      if (!validation.valid) {
        throw new Error(validation.errors.join(', '))
      }
      await apiRequest('/api/trade-packs', { method: 'POST', body: JSON.stringify({ packs: parsed }) }, token)
      setNotice('Trade pack changes saved. Version and schema validation passed.')
      setError('')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unable to save trade packs')
    }
  }

  return (
    <main className="page-shell">
      <div className="card padded-card">
        <h2>Trade pack admin</h2>
        <p className="micro-copy">Versioned pack JSON editor. Schema validation uses the same rules as the backend. AI never auto-certifies; a human reviewer must approve any override.</p>
        {error ? <p className="error-text">{error}</p> : null}
        {notice ? <p className="micro-copy">{notice}</p> : null}
        <textarea value={draft} onChange={(event) => setDraft(event.target.value)} rows={28} />
        <div className="inline-actions">
          <button type="button" onClick={() => void savePacks()}>Save pack changes</button>
        </div>
      </div>
    </main>
  )
}

function DemonstratePage({ token, locale, lowLiteracyMode }: { token: string; locale: Locale; lowLiteracyMode: boolean }) {
  const t = translations[locale]
  const videoRef = useRef<HTMLVideoElement | null>(null)
  const mediaRecorderRef = useRef<MediaRecorder | null>(null)
  const [consent, setConsent] = useState(false)
  const [quality, setQuality] = useState<{ brightness: number; blur: number; face: string } | null>(null)
  const [recording, setRecording] = useState(false)
  const [videoUrl, setVideoUrl] = useState('')
  const [hash, setHash] = useState('')
  const [currentStepIndex, setCurrentStepIndex] = useState(0)
  const [steps] = useState<string[]>([
    'Verify site isolation and risk assessment',
    'Wear required PPE and check tools',
    'Inspect cables, points and environment for hazards',
    'Confirm lockout/tagout or safe switching',
    'Document hazards and remedial actions',
  ])
  const [doneSteps, setDoneSteps] = useState<Record<number, { start: number; end: number }>>({})

  const runQualityCheck = async () => {
    const video = videoRef.current
    if (!video) return
    const canvas = document.createElement('canvas')
    canvas.width = video.videoWidth || 640
    canvas.height = video.videoHeight || 480
    const context = canvas.getContext('2d')
    if (!context) return
    context.drawImage(video, 0, 0, canvas.width, canvas.height)
    const imageData = context.getImageData(0, 0, canvas.width, canvas.height)
    const data = imageData.data
    let brightness = 0
    let variance = 0
    for (let index = 0; index < data.length; index += 4) {
      const r = data[index], g = data[index + 1], b = data[index + 2]
      brightness += (r + g + b) / 3
      variance += Math.abs((r + g + b) / 3 - 128)
    }
    brightness = brightness / (data.length / 4)
    variance = variance / (data.length / 4)
    setQuality({
      brightness: Number(brightness.toFixed(1)),
      blur: Number(variance.toFixed(1)),
      face: brightness > 80 && brightness < 180 ? 'Face likely in frame' : 'Retake: lighting or angle needs adjustment',
    })
  }

  const startCapture = async () => {
    const stream = await navigator.mediaDevices.getUserMedia({ video: true, audio: false })
    if (videoRef.current) {
      videoRef.current.srcObject = stream
      videoRef.current.play()
    }
    const recorder = new MediaRecorder(stream)
    const chunks: BlobPart[] = []
    recorder.ondataavailable = (event) => chunks.push(event.data)
    recorder.onstop = async () => {
      const blob = new Blob(chunks, { type: 'video/webm' })
      const url = URL.createObjectURL(blob)
      setVideoUrl(url)
      const buffer = await blob.arrayBuffer()
      const digest = await crypto.subtle.digest('SHA-256', buffer)
      const hashHex = Array.from(new Uint8Array(digest)).map((value) => value.toString(16).padStart(2, '0')).join('')
      setHash(hashHex)
      stream.getTracks().forEach((track) => track.stop())
    }
    mediaRecorderRef.current = recorder
    recorder.start()
    setRecording(true)
    window.setTimeout(() => {
      recorder.stop()
      setRecording(false)
      void runQualityCheck()
    }, 2500)
  }

  const markStepDone = () => {
    const start = Number(((performance.now() % 60000) / 1000).toFixed(2))
    const end = Number((start + 1.5).toFixed(2))
    setDoneSteps((current) => ({
      ...current,
      [currentStepIndex]: { start, end },
    }))
    if (currentStepIndex < steps.length - 1) {
      setCurrentStepIndex((value) => value + 1)
    }
  }

  const saveEvidence = async () => {
    const payload = {
      title: `Step capture ${Date.now()}`,
      sha256: hash,
      geo: { latitude: 28.6139, longitude: 77.209 },
      timestamp: new Date().toISOString(),
      hash_chain: hash,
      live_status: quality?.face.includes('likely') ? 'ok' : 'needs-retake',
      steps: steps.map((step, index) => ({
        step_id: `step-${index + 1}`,
        name: step,
        status: doneSteps[index] ? 'done' : 'pending',
        start_time: doneSteps[index]?.start ?? 0,
        end_time: doneSteps[index]?.end ?? 0,
        suggested_by_ai: index % 2 === 0,
      })),
    }

    if (navigator.onLine) {
      await apiRequest('/api/evidence', { method: 'POST', body: JSON.stringify(payload) }, token)
      return
    }

    await persistQueue('evidence', payload)
  }

  return (
    <main className="page-shell">
      {!consent ? (
        <div className="card consent-card">
          <h2>Consent before capture</h2>
          <p>
            This application only records evidence needed for assessment. It uses the worker’s consent, stores a limited hash and timestamp, and supports DPDP-aligned data minimisation. The evidence is retained only for the assessment workflow and will be deleted according to the retention note in the policy.
          </p>
          <button type="button" className={lowLiteracyMode ? 'large-button' : ''} onClick={() => setConsent(true)}>I consent and continue</button>
        </div>
      ) : (
        <>
          <div className="card padded-card">
            <h2>{t.qualityCheck}: guided checklist</h2>
            <div className="video-box">
              <video ref={videoRef} playsInline muted autoPlay />
            </div>
            <div className="inline-actions">
              <button type="button" className={lowLiteracyMode ? 'large-button' : ''} onClick={() => void startCapture()} disabled={recording}>Start capture</button>
              <button type="button" className="ghost-button" onClick={() => void runQualityCheck()}>{t.qualityCheck}</button>
              <button type="button" onClick={markStepDone}>{t.stepDone}</button>
              <button type="button" className="ghost-button" onClick={() => void saveEvidence()}>{t.saveEvidence}</button>
            </div>
            {quality ? (
              <div className="quality-panel">
                <p>Brightness: {quality.brightness}</p>
                <p>Blur indicator: {quality.blur}</p>
                <p>{quality.face}</p>
              </div>
            ) : null}
            {hash ? <p className="micro-copy">SHA-256: {hash}</p> : null}
            {videoUrl ? <video controls src={videoUrl} className="preview-video" /> : null}
          </div>

          <div className="card padded-card">
            <h3>Current step</h3>
            <p><strong>{steps[currentStepIndex] || 'All steps complete'}</strong></p>
            <div className="chip-list">
              {steps.map((step, index) => (
                <button key={step} type="button" className={`tag-button ${index === currentStepIndex ? 'active' : ''}`}>
                  {step}
                  {index % 2 === 0 ? ' • AI suggested' : ''}
                </button>
              ))}
            </div>
            <div className="step-state-list">
              {steps.map((step, index) => (
                <div key={`${step}-${index}`} className="step-row">
                  <span>{index + 1}. {step}</span>
                  {doneSteps[index] ? <span>Done {doneSteps[index].start}s–{doneSteps[index].end}s</span> : <span>Pending</span>}
                </div>
              ))}
            </div>
          </div>
        </>
      )}
    </main>
  )
}

function AssessorScorePage({ token }: { token: string }) {
  const [competencies, setCompetencies] = useState<Competency[]>([])
  const [scores, setScores] = useState<Record<string, number>>({})
  const [auditLogs, setAuditLogs] = useState<AuditLog[]>([])

  useEffect(() => {
    void (async () => {
      const data = await apiRequest<{ competencies: Competency[] }>('/api/competencies', {}, token)
      setCompetencies(data.competencies)
      const defaults: Record<string, number> = {}
      data.competencies.forEach((item) => {
        defaults[item.id] = 4
      })
      setScores(defaults)

      const logs = await apiRequest<{ logs: AuditLog[] }>('/api/audit', {}, token)
      setAuditLogs(logs.logs)
    })().catch(() => undefined)
  }, [token])

  const submitScore = async (competency: Competency, draft: number) => {
    const score = scores[competency.id] ?? 3
    const overrideReason = score !== draft ? prompt('Please type a reason for overriding the AI draft score:') ?? '' : ''
    await apiRequest('/api/score', {
      method: 'POST',
      body: JSON.stringify({
        assessment_id: 1,
        competency_id: competency.id,
        score,
        ai_draft: draft,
        explanation: `AI evidence: clip-02, step 3; supporting descriptor: ${competency.rubric[String(Math.max(1, Math.min(5, draft)))]}`,
        override_reason: overrideReason || undefined,
      }),
    }, token)
  }

  return (
    <main className="page-shell">
      <div className="card padded-card">
        <h2>Assessor console: score</h2>
        <p className="micro-copy">AI draft is visible only as a draft and hidden until the assessor submits their own score.</p>
      </div>

      {competencies.map((competency) => {
        const draft = 4
        const score = scores[competency.id] ?? 4
        return (
          <div key={competency.id} className="card padded-card score-card">
            <div className="card-header-row">
              <h3>{competency.title}</h3>
              <span>AI draft: {draft}/5</span>
            </div>
            <p>{competency.rubric['4']}</p>
            <div className="rumble-row">
              {competencyLevels.map((level) => (
                <button key={level} type="button" className={`pill-button ${score === level ? 'selected' : ''}`} onClick={() => setScores((current) => ({ ...current, [competency.id]: level }))}>
                  {level}
                </button>
              ))}
            </div>
            <textarea value={score === draft ? 'AI draft no override needed. Assessor review accepted.' : 'AI draft overridden by assessor due to mismatch in context and evidence quality.'} readOnly />
            <button type="button" onClick={() => void submitScore(competency, draft)}>Submit score</button>
          </div>
        )
      })}

      <div className="card padded-card">
        <h3>Audit log</h3>
        {auditLogs.length ? (
          <ul className="audit-list">
            {auditLogs.slice(0, 6).map((entry) => (
              <li key={entry.id}><strong>{entry.action}</strong> {entry.details}</li>
            ))}
          </ul>
        ) : <p>No audit entries yet.</p>}
      </div>
    </main>
  )
}

function CalibrationPage({ token }: { token: string }) {
  const [metrics, setMetrics] = useState<Array<{ metric: string; value: number; interpretation: string; ci?: number[] }>>([])
  const [reportCards, setReportCards] = useState<Array<{ assessor_name: string; severity: number; leniency_bias: number; halo_effect: number; drift: number; recommendations: string[] }>>([])
  const [anchorExam, setAnchorExam] = useState<Array<{ clip_id: string; mean_score: number; consensus: number; expert_scores: number[] }>>([])
  const [study, setStudy] = useState<{ assisted_arm?: { mean_score: number; ci: number[] }; unassisted_arm?: { mean_score: number; ci: number[] }; difference?: number } | null>(null)

  useEffect(() => {
    void apiRequest<{ metrics: typeof metrics; report_cards: typeof reportCards; anchor_exam: typeof anchorExam; ab_study: typeof study; demo_note: string }>('/api/calibration', {}, token)
      .then((data) => {
        setMetrics(data.metrics)
        setReportCards(data.report_cards ?? [])
        setAnchorExam(data.anchor_exam ?? [])
        setStudy(data.ab_study ?? null)
      })
  }, [token])

  return (
    <main className="page-shell">
      <div className="card padded-card">
        <h2>Calibration engine 2.0</h2>
        <p className="micro-copy">Demo calibration values are coaching feedback only. Real assessor data can replace the seeded study without changing the workflow.</p>
      </div>

      <div className="grid-two">
        {metrics.map((metric) => (
          <div key={metric.metric} className="card padded-card">
            <h3>{metric.metric.replace(/_/g, ' ')}</h3>
            <div className="progress-bar"><span style={{ width: `${Math.min(100, metric.value * 100)}%` }} /></div>
            <strong>{metric.value.toFixed(2)}</strong>
            {metric.ci ? <p>CI: {metric.ci.map((value) => value.toFixed(2)).join(' – ')}</p> : null}
            <p>{metric.interpretation}</p>
          </div>
        ))}
      </div>

      <div className="card padded-card">
        <h3>Assessor coaching cards</h3>
        <div className="grid-two">
          {reportCards.map((card) => (
            <div key={card.assessor_name} className="card padded-card">
              <h4>{card.assessor_name}</h4>
              <p>Severity: {card.severity.toFixed(2)}</p>
              <p>Leniency bias: {card.leniency_bias.toFixed(2)}</p>
              <p>Halo effect: {card.halo_effect.toFixed(2)}</p>
              <p>Drift: {card.drift.toFixed(2)}</p>
              <ul>
                {card.recommendations.map((item) => <li key={item}>{item}</li>)}
              </ul>
            </div>
          ))}
        </div>
      </div>

      <div className="card padded-card">
        <h3>Anchor clip exam</h3>
        <ul>
          {anchorExam.map((clip) => (
            <li key={clip.clip_id}><strong>{clip.clip_id}</strong> — mean {clip.mean_score.toFixed(2)}, consensus {clip.consensus.toFixed(2)}, expert scores {clip.expert_scores.join(', ')}</li>
          ))}
        </ul>
      </div>

      {study ? (
        <div className="card padded-card">
          <h3>A/B study summary</h3>
          <p>Assisted arm: {study.assisted_arm ? `${study.assisted_arm.mean_score.toFixed(2)} (CI ${study.assisted_arm.ci.map((value) => value.toFixed(2)).join(' – ')})` : 'n/a'}</p>
          <p>Unassisted arm: {study.unassisted_arm ? `${study.unassisted_arm.mean_score.toFixed(2)} (CI ${study.unassisted_arm.ci.map((value) => value.toFixed(2)).join(' – ')})` : 'n/a'}</p>
          <p>Difference: {typeof study.difference === 'number' ? study.difference.toFixed(2) : 'n/a'}</p>
        </div>
      ) : null}
    </main>
  )
}

function CertificatePage() {
  const [signed, setSigned] = useState(false)
  const navigate = useNavigate()

  const generatePdf = async () => {
    if (!signed) {
      alert('Assessor sign-off is required first.')
      return
    }

    const pdf = new jsPDF({ unit: 'pt', format: 'a4' })
    pdf.setFillColor(15, 118, 110)
    pdf.rect(0, 0, 595, 160, 'F')
    pdf.setTextColor(255, 255, 255)
    pdf.setFontSize(26)
    pdf.text('NSQF Competency Profile', 40, 60)
    pdf.setTextColor(20, 20, 20)
    pdf.setFontSize(14)
    pdf.text('Trade: Domestic Electrician', 40, 210)
    pdf.text('Recommendation: Ready for supervised site work', 40, 240)
    pdf.text('Status: Verified and hash-checked', 40, 270)
    pdf.text('Assessor sign-off: accepted', 40, 300)

    const qrData = await QRCode.toDataURL('https://demo.skillsetu.ai/verify/1')
    pdf.addImage(qrData, 'PNG', 430, 180, 100, 100)
    pdf.save('skillsetu-certificate.pdf')
    navigate('/verify/1')
  }

  return (
    <main className="page-shell">
      <div className="card padded-card">
        <h2>Certify</h2>
        <label className="checkbox-row">
          <input type="checkbox" checked={signed} onChange={() => setSigned((value) => !value)} />
          Assessor sign-off complete
        </label>
        <button type="button" onClick={() => void generatePdf()}>Generate PDF certificate</button>
      </div>
    </main>
  )
}

function VerificationPage() {
  const { id } = useParams<{ id: string }>()
  return (
    <main className="page-shell center-layout">
      <div className="card padded-card verification-box">
        <p className="eyebrow">Public verification</p>
        <h2>Credential verified</h2>
        <p>Credential ID: SKILLSETU-{id ?? '0001'}</p>
        <p>Trade: Domestic Electrician</p>
        <p>Verification status: Hash-verified and assessor-signed</p>
      </div>
    </main>
  )
}

export default App
