import { useCallback, useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { apiRequest } from '../api/client'
import type { AppUser } from '../api/types'
import type { Locale } from '../i18n/translations'
import { translations } from '../i18n/translations'
import { AsyncState } from '../components/AsyncState'

type DashboardSummary = {
  candidate_count: number
  assessment_count: number
  assessment_stage_counts: Record<string, number>
  average_time_per_candidate_seconds: number | null
  krippendorff_alpha: number | null
  metrics_are_demo_data: boolean
}

const stages = [
  ['registered', 'Registered'],
  ['declared', 'Declared'],
  ['evidence_captured', 'Evidence captured'],
  ['under_review', 'Under review'],
  ['second_review', 'Second review'],
  ['moderation', 'Moderation'],
  ['signed_off', 'Signed off'],
  ['credential_issued', 'Credential issued'],
  ['appeal', 'Appeal'],
]

function formatDuration(seconds: number | null) {
  if (seconds === null) return '—'
  if (seconds < 60) return '<1 min'
  const minutes = Math.round(seconds / 60)
  if (minutes < 60) return `${minutes} min`
  const hours = Math.floor(minutes / 60)
  const remainingMinutes = minutes % 60
  if (hours < 24) return remainingMinutes ? `${hours}h ${remainingMinutes}m` : `${hours}h`
  const days = Math.floor(hours / 24)
  return `${days}d ${hours % 24}h`
}

export function HomePage({ user, locale, lowLiteracyMode }: { user: AppUser | null; locale: Locale; lowLiteracyMode: boolean }) {
  const navigate = useNavigate()
  const t = translations[locale]
  const [summary, setSummary] = useState<DashboardSummary | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  const loadDashboard = useCallback(async () => {
    try {
      setSummary(await apiRequest<DashboardSummary>('/api/dashboard'))
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Dashboard data is unavailable.')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { void Promise.resolve().then(loadDashboard) }, [loadDashboard])

  const refreshDashboard = async () => {
    setLoading(true)
    setError('')
    await loadDashboard()
  }

  return (
    <main className="page-shell">
      <section className="hero-card">
        <div>
          <p className="eyebrow">RECOGNITION OF PRIOR LEARNING</p>
          <h1>Skills you already have. Recognition you can build on.</h1>
          <p className="lead">SkillSetu supports a human-led assessment journey from a worker’s experience to reviewed evidence and a verifiable demo credential.</p>
        </div>
        <div className="hero-actions">
          {user?.role === 'worker' ? (
            <>
              <button type="button" className={lowLiteracyMode ? 'large-button' : ''} onClick={() => navigate('/worker/declare')}>{t.workerFlow}</button>
              <button type="button" className="button-secondary" onClick={() => navigate('/worker/passport')}>{t.passport}</button>
            </>
          ) : null}
          {user?.role === 'assessor' ? <button type="button" onClick={() => navigate('/assessor/score')}>Open assessor workspace</button> : null}
          {user?.role === 'moderator' ? <button type="button" onClick={() => navigate('/moderation')}>Open review queue</button> : null}
          {user?.role === 'admin' ? <button type="button" onClick={() => navigate('/admin/packs')}>Manage trade packs</button> : null}
          {!user ? <button type="button" onClick={() => navigate('/login')}>Sign in</button> : null}
        </div>
      </section>

      <section className="dashboard-section" data-tour="dashboard-counters" aria-labelledby="dashboard-heading">
        <div className="section-heading">
          <div>
            <p className="eyebrow">PROGRAMME OVERVIEW</p>
            <h2 id="dashboard-heading">Assessment dashboard</h2>
          </div>
          {!loading && !error ? <span className="live-indicator"><span /> Live from API</span> : null}
        </div>
        <AsyncState loading={loading} error={error} onRetry={() => void refreshDashboard()} />
        {summary ? (
          <>
            <div className="metric-grid">
              <article className="metric-card metric-primary">
                <span className="metric-label">Candidates</span>
                <strong>{summary.candidate_count.toLocaleString()}</strong>
                <span className="metric-note">In the demo registry</span>
              </article>
              <article className="metric-card">
                <span className="metric-label">Assessments</span>
                <strong>{summary.assessment_count.toLocaleString()}</strong>
                <span className="metric-note">Across all workflow stages</span>
              </article>
              <article className="metric-card">
                <span className="metric-label">Avg. time per candidate</span>
                <strong>{formatDuration(summary.average_time_per_candidate_seconds)}</strong>
                <span className="metric-note">Elapsed since first assessment</span>
              </article>
              <article className="metric-card metric-green">
                <span className="metric-label">Current alpha</span>
                <strong>{summary.krippendorff_alpha === null ? '—' : summary.krippendorff_alpha.toFixed(2)}</strong>
                <span className="metric-note">{summary.krippendorff_alpha === null
                  ? 'Needs overlapping assessor scores'
                  : summary.metrics_are_demo_data ? 'Seeded calibration value' : 'Calculated from assessments'}</span>
              </article>
            </div>
            <div className="card padded-card stage-card">
              <div className="card-header-row">
                <div>
                  <h3>Assessments by stage</h3>
                  <p className="micro-copy">Live counts from the assessment workflow.</p>
                </div>
                <button type="button" className="button-secondary" onClick={() => navigate(user?.role === 'moderator' ? '/moderation' : '/assessor/score')}>Review assessments</button>
                {user && ['assessor', 'admin', 'moderator'].includes(user.role)
                  ? <button type="button" className="button-secondary" onClick={() => navigate('/impact')}>Open impact dashboard</button>
                  : null}
              </div>
              {summary.assessment_count > 0 ? (
                <div className="stage-grid">
                  {stages.map(([key, label]) => (
                    <div className="stage-item" key={key}>
                      <span>{label}</span>
                      <strong>{summary.assessment_stage_counts[key] ?? 0}</strong>
                    </div>
                  ))}
                </div>
              ) : <p className="state-message">No assessments yet. Start with a worker declaration to create the first record.</p>}
            </div>
          </>
        ) : null}
      </section>

      <section className="three-grid">
        <article className="info-card">
          <span className="feature-number">01</span>
          <h3>{t.declareTitle}</h3>
          <p>Workers describe skills in their own words and review suggested qualification packs.</p>
        </article>
        <article className="info-card">
          <span className="feature-number">02</span>
          <h3>Demonstrate and review</h3>
          <p>Build an evidence record and let a human assessor review each competency.</p>
        </article>
        <article className="info-card">
          <span className="feature-number">03</span>
          <h3>{t.passport}</h3>
          <p>Explore the demo skills passport and credential-verification journey.</p>
        </article>
      </section>
      <p className="dashboard-disclaimer">Prototype data only. AI suggestions and calibration metrics do not make certification decisions.</p>
    </main>
  )
}

export default HomePage
