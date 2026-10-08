import { useCallback, useEffect, useRef, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { apiRequest } from '../api/client'
import type { Competency } from '../api/types'
import { AsyncState } from '../components/AsyncState'

type Comparison = { assessor_id: number; review_round: number; competency_id: string; score: number; ai_draft: number; ai_confidence: number; override_reason: string | null }
type ReviewPacket = {
  assessment_id: number
  status: string
  scores: Comparison[]
  moderation?: { rationale: string; final_scores: Record<string, number>; overrides: Record<string, { final_score: number; reason: string }> } | null
}
type QueueItem = { assessment_id: number; status: string }

export default function ModerationPage({ token }: { token: string }) {
  const [searchParams, setSearchParams] = useSearchParams()
  const [assessmentId, setAssessmentId] = useState(Number(searchParams.get('assessment') ?? sessionStorage.getItem('skillsetu-last-assessment-id') ?? 1))
  const assessmentIdRef = useRef(assessmentId)
  const [competencies, setCompetencies] = useState<Competency[]>([])
  const [queue, setQueue] = useState<QueueItem[]>([])
  const [packet, setPacket] = useState<ReviewPacket | null>(null)
  const [finalScores, setFinalScores] = useState<Record<string, number>>({})
  const [overrideReasons, setOverrideReasons] = useState<Record<string, string>>({})
  const [rationale, setRationale] = useState('')
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')

  const load = useCallback(async (id = assessmentIdRef.current) => {
    setLoading(true)
    setError('')
    try {
      const [rubric, pending] = await Promise.all([
        apiRequest<{ competencies: Competency[] }>('/api/competencies', {}, token),
        apiRequest<{ assessments: QueueItem[] }>('/api/moderation/queue', {}, token),
      ])
      setCompetencies(rubric.competencies)
      setQueue(pending.assessments)
      const targetId = pending.assessments.some((item) => item.assessment_id === id)
        ? id
        : pending.assessments[0]?.assessment_id
      if (targetId === undefined) {
        setPacket(null)
        return
      }
      const review = await apiRequest<ReviewPacket>(`/api/assessments/${targetId}/review`, {}, token)
      id = targetId
      setPacket(review)
      assessmentIdRef.current = id
      setAssessmentId(id)
      setSearchParams({ assessment: String(id) })
      const roundOne = new Map(review.scores.filter((score) => score.review_round === 1).map((score) => [score.competency_id, score.score]))
      const roundTwo = new Map(review.scores.filter((score) => score.review_round === 2).map((score) => [score.competency_id, score.score]))
      setFinalScores((current) => Object.keys(current).length ? current : Object.fromEntries(rubric.competencies.map((item) => [
        item.id,
        Math.round(((roundOne.get(item.id) ?? 3) + (roundTwo.get(item.id) ?? 3)) / 2),
      ])))
    } catch (reason) {
      setPacket(null)
      setError(reason instanceof Error ? reason.message : 'Could not load moderation packet.')
    } finally {
      setLoading(false)
    }
  }, [setSearchParams, token])

  useEffect(() => {
    const timer = window.setTimeout(() => void load(), 0)
    return () => window.clearTimeout(timer)
  }, [load])

  const submit = async () => {
    if (!packet) return
    setSaving(true)
    setError('')
    setNotice('')
    try {
      await apiRequest('/api/moderation', {
        method: 'POST',
        body: JSON.stringify({
          assessment_id: packet.assessment_id,
          rationale,
          final_scores: finalScores,
          override_reasons: overrideReasons,
        }),
      }, token)
      setNotice('Moderation rationale and final scores saved. The assessment is signed off.')
      setPacket((current) => current ? {
        ...current,
        status: 'signed_off',
        moderation: { rationale, final_scores: finalScores, overrides: {} },
      } : current)
      setQueue((current) => current.filter((item) => item.assessment_id !== packet.assessment_id))
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Could not save the moderation decision.')
    } finally {
      setSaving(false)
    }
  }

  return (
    <main className="page-shell">
      <section className="page-heading">
        <p className="eyebrow">REVIEW WORKFLOW</p>
        <h1>Moderation</h1>
        <p>Resolve a significant competency disagreement with a recorded rationale and final score.</p>
      </section>
      <section className="card padded-card" data-tour="moderation-action">
        <label htmlFor="moderation-assessment-id">Assessment ID</label>
        <div className="inline-actions">
          <input id="moderation-assessment-id" inputMode="numeric" value={assessmentId} onChange={(event) => {
            const id = Number(event.target.value) || 0
            assessmentIdRef.current = id
            setAssessmentId(id)
          }} />
          <button type="button" className="button-secondary" onClick={() => void load(assessmentId)} disabled={loading}>Load moderation</button>
          {queue.length ? (
            <select aria-label="Assessments awaiting moderation" value={queue.some((item) => item.assessment_id === assessmentId) ? assessmentId : ''} onChange={(event) => {
              const id = Number(event.target.value)
              if (id) { setAssessmentId(id); setFinalScores({}); void load(id) }
            }}>
              <option value="">Awaiting moderation ({queue.length})</option>
              {queue.map((item) => <option key={item.assessment_id} value={item.assessment_id}>Assessment #{item.assessment_id}</option>)}
            </select>
          ) : null}
        </div>
        <AsyncState loading={loading} error={error} onRetry={() => void load()} />
        {notice ? <p className="success-message" role="status">{notice}</p> : null}
        {packet ? <p className="status-pill">Assessment #{packet.assessment_id} · {packet.status.replace(/_/g, ' ')}</p> : null}
      </section>

      {packet?.status === 'moderation' ? (
        <>
          {competencies.map((competency) => {
            const comparison = packet.scores.filter((score) => score.competency_id === competency.id)
            const first = comparison.find((score) => score.review_round === 1)
            const second = comparison.find((score) => score.review_round === 2)
            const draft = first?.ai_draft ?? second?.ai_draft
            return (
              <section key={competency.id} className="card padded-card">
                <h2>{competency.title}</h2>
                <p>Blind scores: primary {first?.score ?? 'pending'} / 5 · second assessor {second?.score ?? 'pending'} / 5</p>
                <p>AI draft: {draft ?? 'unavailable'} / 5 · confidence: {((first?.ai_confidence ?? second?.ai_confidence ?? 0) * 100).toFixed(0)}%</p>
                <label htmlFor={`final-${competency.id}`}>Moderator final score</label>
                <select id={`final-${competency.id}`} value={finalScores[competency.id] ?? 3} onChange={(event) => setFinalScores((current) => ({ ...current, [competency.id]: Number(event.target.value) }))}>
                  {[1, 2, 3, 4, 5].map((score) => <option key={score} value={score}>{score}</option>)}
                </select>
                <label htmlFor={`reason-${competency.id}`}>Override reason if final score differs from either assessor</label>
                <textarea id={`reason-${competency.id}`} value={overrideReasons[competency.id] ?? ''} onChange={(event) => setOverrideReasons((current) => ({ ...current, [competency.id]: event.target.value }))} />
              </section>
            )
          })}
          <section className="card padded-card">
            <label htmlFor="moderation-rationale">Moderation rationale (required)</label>
            <textarea id="moderation-rationale" value={rationale} onChange={(event) => setRationale(event.target.value)} placeholder="Explain how the evidence and rubric resolve the disagreement." />
            <button data-tour="moderation-submit" type="button" onClick={() => void submit()} disabled={saving || rationale.trim().length < 10}>{saving ? 'Saving decision…' : 'Save rationale and sign off'}</button>
          </section>
        </>
      ) : null}
      {packet?.status === 'signed_off' && packet.moderation ? (
        <section className="card padded-card">
          <h2>Moderation decision recorded</h2>
          <p>{packet.moderation.rationale}</p>
          <ul>{competencies.map((competency) => <li key={competency.id}>{competency.title}: final score {packet.moderation?.final_scores[competency.id]}/5</li>)}</ul>
        </section>
      ) : null}
      {!loading && !queue.length ? (
        <section className="card padded-card">
          <h2>No assessments are awaiting moderation</h2>
          <p>A request appears here after the primary assessor and assigned second assessor have both scored every competency and their scores differ by at least 2 points on any competency.</p>
          <p className="micro-copy">To demonstrate the flow, submit a flagged or sampled assessment for independent review, then enter sufficiently different scores in the two assessor rounds.</p>
        </section>
      ) : null}
    </main>
  )
}
