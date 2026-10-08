import { useState } from 'react'
import { Link } from 'react-router-dom'
import { apiRequest } from '../api/client'
import type { MatchResult } from '../api/types'
import type { Locale } from '../i18n/translations'
import { translations } from '../i18n/translations'
import { StatusTracker } from '../components/StatusTracker'
import { speakText, startVoiceInput } from '../api/voice'

export function WorkerDeclarePage({ token, locale, lowLiteracyMode }: { token: string; locale: Locale; lowLiteracyMode: boolean }) {
  const [text, setText] = useState('I installed a new lighting circuit and checked the switchboard for safety before testing continuity and earthing.')
  const [matches, setMatches] = useState<MatchResult[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const t = translations[locale]

  const runDeclare = async () => {
    setLoading(true)
    setError('')
    try {
      const result = await apiRequest<{ matches: MatchResult[] }>('/api/declare', { method: 'POST', body: JSON.stringify({ text }) }, token)
      const assessment = await apiRequest<{ id: number; status: string }>('/api/assessments', { method: 'POST', body: JSON.stringify({ text, matches: result.matches }) }, token)
      sessionStorage.setItem('skillsetu-last-assessment-id', String(assessment.id))
      if (result.matches[0]?.title) sessionStorage.setItem('skillsetu-trade', result.matches[0].title)
      setMatches(result.matches)
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Unable to submit this declaration.')
    } finally {
      setLoading(false)
    }
  }

  const handleVoiceInput = () => {
    void startVoiceInput(locale, setText)
    speakText('Please describe the work you have already done and the tasks you want assessed.')
  }

  return (
    <main className="page-shell">
      <div className="card padded-card" data-tour="declaration-form">
        <h2>{t.declareTitle}</h2>
        <p className="micro-copy">Hindi/English supported. AI maps your declaration to top qualification packs and skill gaps.</p>
        <textarea aria-label="Declaration text" value={text} onChange={(event) => setText(event.target.value)} rows={6} />
        <div className="inline-actions">
          <button type="button" className={lowLiteracyMode ? 'large-button' : ''} onClick={() => void runDeclare()} disabled={loading}>{loading ? 'Finding matches…' : t.mapToPacks}</button>
          <button type="button" className="ghost-button" onClick={() => setText('मैं ने स्विचबोर्ड की सुरक्षा जाँच की और तारों का परीक्षण किया।')}>{t.useHindi}</button>
          <button type="button" className="ghost-button" onClick={handleVoiceInput}>{t.voiceInput}</button>
          <button type="button" className="ghost-button" onClick={() => speakText(text)}>{t.readPrompt}</button>
        </div>
        {error ? <p className="error-text" role="alert">{error}</p> : null}
      </div>

      <div className="card padded-card">
        <h3>{t.statusTracker}</h3>
        <StatusTracker currentStatus="declared" />
      </div>

      {matches.length ? (
        <section className="stack">
          <div className="card padded-card worker-next-step">
            <div>
              <p className="eyebrow">NEXT STEP</p>
              <h3>Your declaration is saved. Continue to evidence.</h3>
              <p className="micro-copy">Open Demonstrate to record or review evidence for this assessment.</p>
            </div>
            <Link className="button-link worker-next-link" to="/worker/demonstrate">Continue to Demonstrate</Link>
          </div>
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
      ) : <div className="card"><p className="state-message">Your suggested trade packs will appear here after you map your declaration.</p></div>}
    </main>
  )
}

export default WorkerDeclarePage
