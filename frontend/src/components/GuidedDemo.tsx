import { useEffect, useLayoutEffect, useRef, useState } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import { DEMO_MODE, type DemoRole } from '../api/demo'

type TourStep = {
  title: string
  description: string
  path: string
  target: string
  role?: DemoRole
}

type TargetRect = { target: string; top: number; left: number; width: number; height: number }

const steps: TourStep[] = [
  { title: 'Welcome to SkillSetu', description: 'Start with the live programme dashboard. The counters are aggregated by the API; the agreement score is seeded demo data.', path: '/', target: 'dashboard-counters' },
  { title: 'Declare prior skills', description: 'As a worker, describe experience and map it to a trade pack. Select Map to packs before continuing to create an assessment for the later review steps.', path: '/worker/declare', target: 'declaration-form', role: 'worker' },
  { title: 'Record evidence', description: 'Review consent, the guided evidence checklist, and the capture controls. Camera access is optional for this walkthrough.', path: '/worker/demonstrate', target: 'evidence-capture', role: 'worker' },
  { title: 'Assessor scoring', description: 'Switch to the assessor workspace to review competency rubrics and submit a score.', path: '/assessor/score', target: 'assessor-score', role: 'assessor' },
  { title: 'Second review', description: 'A different-centre assessor scores the same competencies independently. Peer scores stay blind while scoring.', path: '/assessor/score', target: 'assessor-score', role: 'assessor2' },
  { title: 'Moderation', description: 'The moderator compares both submitted scores and the AI draft only after a two-point competency disagreement.', path: '/moderation', target: 'moderation-action', role: 'moderator' },
  { title: 'Certificate', description: 'Review the certificate screen. Issuance remains a demo interaction and requires an assessor sign-off.', path: '/certificate', target: 'certificate-signoff', role: 'assessor' },
  { title: 'Public verification', description: 'Open the public verification view and inspect the example credential status.', path: '/verify/1', target: 'public-verification' },
  { title: 'Calibration dashboard', description: 'Explore agreement, calibration summaries, and coaching data calculated from stored scores. Seeded demo records are labelled.', path: '/calibration', target: 'calibration-metrics', role: 'assessor' },
  { title: 'Walkthrough complete', description: 'Return to the dashboard to explore the demo at your own pace.', path: '/', target: 'dashboard-counters' },
]

export function GuidedDemo({ onSignIn }: { onSignIn: (role: DemoRole) => Promise<void> }) {
  const navigate = useNavigate()
  const location = useLocation()
  const [open, setOpen] = useState(false)
  const [index, setIndex] = useState(0)
  const [targetRect, setTargetRect] = useState<TargetRect | null>(null)
  const [cardHeight, setCardHeight] = useState(240)
  const [error, setError] = useState('')
  const cardRef = useRef<HTMLElement>(null)

  const step = steps[index]

  useEffect(() => {
    if (!open) return
    let cancelled = false
    void (async () => {
      try {
        if (step.role) await onSignIn(step.role)
        if (!cancelled) navigate(step.path)
      } catch (reason) {
        if (!cancelled) setError(reason instanceof Error ? reason.message : 'Unable to open this demo step.')
      }
    })()
    return () => { cancelled = true }
  }, [index, navigate, onSignIn, open, step.path, step.role])

  useEffect(() => {
    if (!open) return
    let attempts = 0
    let timer = 0
    const measure = () => {
      const element = document.querySelector<HTMLElement>(`[data-tour="${step.target}"]`)
      if (element) {
        element.scrollIntoView({ block: 'nearest', behavior: 'instant' })
        const rect = element.getBoundingClientRect()
        setTargetRect({ target: step.target, top: rect.top, left: rect.left, width: rect.width, height: rect.height })
        return
      }
      if (attempts < 20) {
        attempts += 1
        timer = window.setTimeout(measure, 100)
      } else {
        setTargetRect(null)
      }
    }
    timer = window.setTimeout(measure, 50)
    const onResize = () => measure()
    window.addEventListener('resize', onResize)
    return () => {
      window.clearTimeout(timer)
      window.removeEventListener('resize', onResize)
    }
  }, [index, location.pathname, open, step.target])

  useLayoutEffect(() => {
    if (open && cardRef.current) setCardHeight(cardRef.current.offsetHeight)
  }, [error, index, open])

  if (!DEMO_MODE) return null

  const advance = (nextIndex: number) => {
    setError('')
    if (nextIndex < 0 || nextIndex >= steps.length) {
      setOpen(false)
      return
    }
    setIndex(nextIndex)
  }

  const activeTargetRect = targetRect?.target === step.target ? targetRect : null
  const spotlightStyle = activeTargetRect
    ? { top: activeTargetRect.top - 6, left: activeTargetRect.left - 6, width: activeTargetRect.width + 12, height: activeTargetRect.height + 12 }
    : undefined
  const tooltipTop = activeTargetRect && window.innerHeight - activeTargetRect.top - activeTargetRect.height >= cardHeight + 30
    ? activeTargetRect.top + activeTargetRect.height + 18
    : activeTargetRect && activeTargetRect.top >= cardHeight + 30
      ? activeTargetRect.top - cardHeight - 18
      : Math.max(20, window.innerHeight / 2 - 110)

  return (
    <>
      <button className="guided-demo-launcher" type="button" onClick={() => { setError(''); setIndex(0); setOpen(true) }}>
        Guided demo
      </button>
      {open ? (
        <div className="tour-layer" aria-live="polite">
          <div className="tour-scrim" />
          {spotlightStyle ? <div className="tour-spotlight" style={spotlightStyle} /> : null}
          <section ref={cardRef} className="tour-card" style={{ top: tooltipTop }} role="dialog" aria-modal="true" aria-labelledby="tour-title">
            <div className="tour-progress">
              <span>GUIDED DEMO</span>
              <span>{index + 1} / {steps.length}</span>
            </div>
            <h2 id="tour-title">{step.title}</h2>
            <p>{step.description}</p>
            {error ? <p className="error-text" role="alert">{error}</p> : null}
            <div className="tour-actions">
              <button type="button" className="button-secondary" onClick={() => advance(index - 1)} disabled={index === 0}>Back</button>
              <button type="button" onClick={() => advance(index + 1)}>{index === steps.length - 1 ? 'Finish' : 'Next'}</button>
              <button type="button" className="tour-close" onClick={() => setOpen(false)}>Exit tour</button>
            </div>
          </section>
        </div>
      ) : null}
    </>
  )
}
