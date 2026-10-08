import { lazy, Suspense, useCallback, useEffect, useState } from 'react'
import { BrowserRouter, Link, Route, Routes, useNavigate } from 'react-router-dom'
import { syncQueue } from './api/client'
import { signInDemoRole, type DemoRole } from './api/demo'
import type { AppUser } from './api/types'
import type { Locale } from './i18n/translations'
import { translations } from './i18n/translations'
import { DemoRoleSwitcher } from './components/DemoRoleSwitcher'
import { GuidedDemo } from './components/GuidedDemo'
import HomePage from './pages/HomePage'
import LoginPage from './pages/LoginPage'
import WorkerDeclarePage from './pages/WorkerDeclarePage'
import MySkillsPassportPage from './pages/MySkillsPassportPage'
import NotificationsPage from './pages/NotificationsPage'
import AdminPacksPage from './pages/AdminPacksPage'
import DemonstratePage from './pages/DemonstratePage'
import AssessorScorePage from './pages/AssessorScorePage'
import CertificatePage from './pages/CertificatePage'
import VerificationPage from './pages/VerificationPage'
import ModerationPage from './pages/ModerationPage'

const CalibrationPage = lazy(() => import('./pages/CalibrationPage'))
const ImpactDashboardPage = lazy(() => import('./pages/ImpactDashboardPage'))

function LogoutButton({ onLogout }: { onLogout: () => void }) {
  const navigate = useNavigate()

  const handleLogout = () => {
    onLogout()
    navigate('/')
  }

  return <button type="button" className="ghost-button" onClick={handleLogout}>Logout</button>
}

function App() {
  const [online, setOnline] = useState<boolean>(navigator.onLine)
  const [simulateOffline, setSimulateOffline] = useState(false)
  const [locale, setLocale] = useState<Locale>(() => (localStorage.getItem('skillsetu-locale') as Locale) || 'en')
  const [lowLiteracyMode, setLowLiteracyMode] = useState(Boolean(localStorage.getItem('skillsetu-low-literacy')))
  const [accessibilityMode, setAccessibilityMode] = useState(Boolean(localStorage.getItem('skillsetu-accessibility')))
  const [darkMode, setDarkMode] = useState(() => localStorage.getItem('skillsetu-theme') === 'dark')
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
    document.documentElement.dataset.theme = darkMode ? 'dark' : 'light'
    localStorage.setItem('skillsetu-theme', darkMode ? 'dark' : 'light')
  }, [darkMode])

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

  const handleDemoSignIn = useCallback(async (role: DemoRole) => {
    const session = await signInDemoRole(role)
    setToken(session.token)
    setUser(session.user)
  }, [])

  return (
    <BrowserRouter>
      <div className="app-shell">
        <header className="topbar">
          <div>
            <Link className="home-brand" to="/" aria-label="SkillSetu home">
              <strong>SkillSetu AI</strong>
            </Link>
            <span className="status-pill">{simulateOffline ? 'Offline demo' : online ? 'Online' : 'Offline'}</span>
          </div>
          <div className="toolbar">
            {user?.role === 'worker' ? (
              <nav className="role-nav" aria-label="Worker journey">
                <Link className="button-link" to="/worker/declare">Declare skills</Link>
                <Link className="button-link" to="/worker/demonstrate">Demonstrate</Link>
                <Link className="button-link" to="/worker/passport">My passport</Link>
              </nav>
            ) : null}
            {user?.role === 'assessor' ? (
              <nav className="role-nav" aria-label="Assessor workflow">
                <Link className="button-link" to="/assessor/score">Reviews</Link>
                <Link className="button-link" to="/calibration">Calibration</Link>
                <Link className="button-link" to="/impact">Impact</Link>
                <Link className="button-link" to="/certificate">Certificates</Link>
              </nav>
            ) : null}
            {user?.role === 'moderator' ? (
              <nav className="role-nav" aria-label="Moderator workflow">
                <Link className="button-link" to="/moderation">Moderation queue</Link>
                <Link className="button-link" to="/impact">Impact</Link>
              </nav>
            ) : null}
            {user?.role === 'admin' ? (
              <nav className="role-nav" aria-label="Administrator workflow">
                <Link className="button-link" to="/assessor/score">Reviews</Link>
                <Link className="button-link" to="/calibration">Calibration</Link>
                <Link className="button-link" to="/impact">Impact</Link>
                <Link className="button-link" to="/certificate">Certificates</Link>
                <Link className="button-link" to="/admin/packs">Admin tools</Link>
              </nav>
            ) : null}
            <DemoRoleSwitcher currentRole={user?.role} currentUsername={user?.username} onSignIn={handleDemoSignIn} />
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
            <button type="button" className="button-secondary theme-toggle" aria-pressed={darkMode} onClick={() => setDarkMode((value) => !value)}>
              {darkMode ? 'Light mode' : 'Dark mode'}
            </button>
            {user ? (
              <LogoutButton onLogout={logout} />
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
          <Route path="/moderation" element={<ModerationPage token={token} />} />
          <Route path="/admin/packs" element={<AdminPacksPage token={token} isAdmin={user?.role === 'admin'} />} />
          <Route path="/calibration" element={
            <Suspense fallback={<main className="page-shell"><p role="status">Loading calibration dashboard…</p></main>}>
              <CalibrationPage token={token} />
            </Suspense>
          } />
          <Route path="/impact" element={
            <Suspense fallback={<main className="page-shell"><p role="status">Loading impact dashboard…</p></main>}>
              <ImpactDashboardPage token={token} />
            </Suspense>
          } />
          <Route path="/certificate" element={<CertificatePage token={token} />} />
          <Route path="/verify/:id" element={<VerificationPage />} />
        </Routes>
        <GuidedDemo onSignIn={handleDemoSignIn} />
      </div>
    </BrowserRouter>
  )
}

export default App
