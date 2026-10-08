import { useCallback, useEffect, useRef, useState } from 'react'
import { apiRequest } from '../api/client'
import { competencyLevels } from '../api/types'
import type { AuditLog, Competency } from '../api/types'

type OwnScore = { competency_id: string; score: number; ai_draft: number; review_round: number }
type Review = { assessment_id: number; status: string; review_round: number; scores: OwnScore[] }
type QueueItem = { assessment_id: number; status: string; centre: string | null }

export function AssessorScorePage({ token }: { token: string }) {
  const [assessmentId, setAssessmentId] = useState(Number(sessionStorage.getItem('skillsetu-last-assessment-id') ?? 1))
  const assessmentIdRef = useRef(assessmentId)
  const [competencies, setCompetencies] = useState<Competency[]>([])
  const [scores, setScores] = useState<Record<string, number>>({})
  const [reasons, setReasons] = useState<Record<string, string>>({})
  const [explanations, setExplanations] = useState<Record<string, string>>({})
  const [review, setReview] = useState<Review | null>(null)
  const [queue, setQueue] = useState<QueueItem[]>([])
  const [auditLogs, setAuditLogs] = useState<AuditLog[]>([])
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState('')
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')

  const load = useCallback(async (id = assessmentIdRef.current) => {
    setLoading(true)
    setError('')
    try {
      const [rubric, pending, logs, ownReview] = await Promise.all([
        apiRequest<{ competencies: Competency[] }>('/api/competencies', {}, token),
        apiRequest<{ assignments: QueueItem[] }>('/api/reviews/queue', {}, token),
        apiRequest<{ logs: AuditLog[] }>('/api/audit', {}, token),
        apiRequest<Review>(`/api/assessments/${id}/review`, {}, token),
      ])
      setCompetencies(rubric.competencies)
      setQueue(pending.assignments)
      setAuditLogs(logs.logs)
      setReview(ownReview)
      assessmentIdRef.current = id
      setAssessmentId(id)
      sessionStorage.setItem('skillsetu-last-assessment-id', String(id))
      const existing: Record<string, number> = {}
      ownReview.scores.forEach((item) => { existing[item.competency_id] = item.score })
      setScores((current) => ({ ...current, ...existing }))
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Could not load assessor workspace.')
    } finally {
      setLoading(false)
    }
  }, [token])

  useEffect(() => {
    const timer = window.setTimeout(() => void load(), 0)
    return () => window.clearTimeout(timer)
  }, [load])

  const submitScore = async (competency: Competency) => {
    const score = scores[competency.id] ?? 3
    setSaving(competency.id)
    setError('')
    setNotice('')
    try {
      const result = await apiRequest<{
        ai_draft: number
        assessment_status: string
        review_round: number
        second_review_assigned: boolean
        assigned_assessor_id: number | null
      }>('/api/score', {
        method: 'POST',
        body: JSON.stringify({
          assessment_id: assessmentId,
          competency_id: competency.id,
          score,
          explanation: explanations[competency.id]?.trim() || `Assessor judgement for ${competency.title} against the selected rubric descriptor.`,
          override_reason: reasons[competency.id]?.trim() || undefined,
        }),
      }, token)
      setNotice(`Score saved. Your AI draft is now revealed: ${result.ai_draft}/5. Review round ${result.review_round}; workflow status: ${result.assessment_status.replace(/_/g, ' ')}.${result.second_review_assigned ? ` A second assessor has been assigned (ID ${result.assigned_assessor_id}).` : ''}`)
      setReview((current) => current ? {
        ...current,
        status: result.assessment_status,
        review_round: result.review_round,
        scores: [
          ...current.scores.filter((item) => item.competency_id !== competency.id),
          {
            competency_id: competency.id,
            score,
            ai_draft: result.ai_draft,
            review_round: result.review_round,
          },
        ],
      } : current)
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Could not submit score.')
    } finally {
      setSaving('')
    }
  }

  const submitted = new Set(review?.scores.map((item) => item.competency_id) ?? [])

  return (
    <main className="page-shell">
      <section className="card padded-card" data-tour="assessor-score">
        <h1>Assessor scoring</h1>
        <p className="micro-copy">Score independently against the rubric. AI drafts and other assessors’ scores are hidden until your score is submitted.</p>
        <label htmlFor="assessment-id">Assessment ID</label>
        <div className="inline-actions">
          <input id="assessment-id" inputMode="numeric" value={assessmentId} onChange={(event) => {
            const id = Number(event.target.value) || 0
            assessmentIdRef.current = id
            setAssessmentId(id)
          }} />
          <button type="button" className="button-secondary" onClick={() => void load(assessmentId)} disabled={loading}>Load assessment</button>
          {queue.length ? (
            <select aria-label="Assigned second reviews" value={queue.some((item) => item.assessment_id === assessmentId) ? assessmentId : ''} onChange={(event) => {
              const id = Number(event.target.value)
              if (id) { setAssessmentId(id); void load(id) }
            }}>
              <option value="">Assigned reviews ({queue.length})</option>
              {queue.map((item) => <option key={item.assessment_id} value={item.assessment_id}>Assessment #{item.assessment_id} · {item.centre ?? 'different centre'}</option>)}
            </select>
          ) : null}
        </div>
        {review ? <p className="status-pill">Your round: {review.review_round === 2 ? 'independent second review' : 'primary review'} · {review.status.replace(/_/g, ' ')}</p> : null}
        {loading ? <p role="status">Loading review workspace…</p> : null}
        {error ? <p className="error-text" role="alert">{error}</p> : null}
        {notice ? <p className="success-message" role="status">{notice}</p> : null}
      </section>

      {competencies.map((competency) => {
        const existing = review?.scores.find((item) => item.competency_id === competency.id)
        const selectedScore = scores[competency.id] ?? 3
        return (
          <section key={competency.id} className="card padded-card score-card">
            <h2>{competency.title}</h2>
            <p>{competency.rubric[String(selectedScore)]}</p>
            {existing ? (
              <div className="success-message" role="status">
                Your score: {existing.score}/5 · AI draft revealed after submission: {existing.ai_draft}/5
              </div>
            ) : (
              <>
                <div className="rumble-row" role="group" aria-label={`Score ${competency.title}`}>
                  {competencyLevels.map((level) => (
                    <button key={level} type="button" className={`pill-button ${selectedScore === level ? 'selected' : ''}`} aria-pressed={selectedScore === level} onClick={() => setScores((current) => ({ ...current, [competency.id]: level }))}>{level}</button>
                  ))}
                </div>
                <label htmlFor={`explanation-${competency.id}`}>Evidence-based scoring rationale</label>
                <textarea id={`explanation-${competency.id}`} value={explanations[competency.id] ?? ''} onChange={(event) => setExplanations((current) => ({ ...current, [competency.id]: event.target.value }))} placeholder="Describe the evidence and rubric descriptor supporting your score." />
                <label htmlFor={`override-${competency.id}`}>Reason for overriding the hidden AI draft (if required)</label>
                <textarea id={`override-${competency.id}`} value={reasons[competency.id] ?? ''} onChange={(event) => setReasons((current) => ({ ...current, [competency.id]: event.target.value }))} placeholder="The server will require this if your score differs from the AI draft." />
                <button type="button" onClick={() => void submitScore(competency)} disabled={Boolean(saving) || loading}>{saving === competency.id ? 'Submitting…' : 'Submit independent score'}</button>
              </>
            )}
            {submitted.has(competency.id) && existing ? <p className="micro-copy">Your peer assessor’s score remains blind during this review.</p> : null}
          </section>
        )
      })}

      <section className="card padded-card">
        <h2>Your audit activity</h2>
        {auditLogs.length ? <ul className="audit-list">{auditLogs.slice(0, 6).map((entry) => <li key={entry.id}><strong>{entry.action}</strong> {entry.details}</li>)}</ul> : <p className="state-message">No audit entries yet.</p>}
      </section>
    </main>
  )
}

export default AssessorScorePage
