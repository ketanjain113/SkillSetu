import { useCallback, useEffect, useState } from 'react'
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import { apiRequest } from '../api/client'
import { AsyncState } from '../components/AsyncState'

type RateRow = {
  label: string
  eligible: number
  passed: number
  pass_rate: number | null
  includes_demo_data: boolean
  demo_count?: number
}

type ImpactSummary = {
  funnel: Array<{ stage: string; label: string; count: number }>
  time_per_candidate: {
    assisted: { seconds: number | null; candidate_count: number }
    unassisted: { seconds: number | null; candidate_count: number }
    method: string
  }
  pass_rate_by_trade: RateRow[]
  fairness: Record<string, RateRow[]>
  outcome_method: string
  fairness_method: string
  includes_demo_data: boolean
  completed_assessments: number
}

const colors = ['#18408c', '#ff9933', '#15845d', '#7856a8', '#2b8a9e', '#d1495b']
const fairnessLabels: Record<string, string> = {
  gender: 'Gender',
  region: 'Region',
  language: 'Language',
}

function PercentTooltip({ active, payload }: { active?: boolean; payload?: Array<{ payload: RateRow }> }) {
  if (!active || !payload?.[0]) return null
  const row = payload[0].payload
  return (
    <div className="impact-tooltip">
      <strong>{row.label}</strong>
      <span>{row.passed}/{row.eligible} passed ({row.pass_rate === null ? 'n/a' : `${(row.pass_rate * 100).toFixed(1)}%`})</span>
      {row.includes_demo_data ? <span>Includes seeded demo data</span> : null}
    </div>
  )
}

export default function ImpactDashboardPage({ token }: { token: string }) {
  const [summary, setSummary] = useState<ImpactSummary | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  const load = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      setSummary(await apiRequest<ImpactSummary>('/api/dashboard/impact', {}, token))
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Impact data could not be loaded.')
    } finally {
      setLoading(false)
    }
  }, [token])

  useEffect(() => {
    const timer = window.setTimeout(() => void load(), 0)
    return () => window.clearTimeout(timer)
  }, [load])

  return (
    <main className="page-shell impact-page">
      <header className="page-heading">
        <p className="eyebrow">PROGRAMME IMPACT</p>
        <h1>Impact dashboard</h1>
        <p>Workflow completion, timing and descriptive subgroup views. This dashboard is not an official impact or fairness evaluation.</p>
      </header>
      <AsyncState loading={loading} error={error} onRetry={() => void load()} />
      {summary ? (
        <>
          <div className="calibration-data-note">
            <strong>{summary.includes_demo_data ? 'Includes synthetic demo data' : 'Stored assessment records'}</strong>
            <span>{summary.completed_assessments} completed, scored assessments in pass-rate views.</span>
          </div>

          <section className="grid-two">
            <article className="card impact-chart-card">
              <h2>Assessment stage funnel</h2>
              <p className="calibration-caption">Cumulative counts through the current workflow stage; later stages include earlier-stage assessments.</p>
              {summary.funnel.some((item) => item.count > 0) ? (
                <div className="impact-chart">
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={summary.funnel} layout="vertical" margin={{ top: 4, right: 22, bottom: 4, left: 12 }}>
                      <CartesianGrid strokeDasharray="3 3" />
                      <XAxis type="number" allowDecimals={false} />
                      <YAxis type="category" dataKey="label" width={132} tick={{ fontSize: 11 }} />
                      <Tooltip />
                      <Bar dataKey="count" name="Assessments" fill="#18408c" radius={[0, 5, 5, 0]} />
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              ) : <p className="empty-state">No assessments are available yet.</p>}
            </article>

            <article className="card impact-chart-card">
              <h2>Time per candidate</h2>
              <p className="calibration-caption">{summary.time_per_candidate.method}</p>
              <div className="impact-chart impact-chart-short">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={[
                    { group: 'AI-assisted', seconds: summary.time_per_candidate.assisted.seconds, candidates: summary.time_per_candidate.assisted.candidate_count },
                    { group: 'Unassisted', seconds: summary.time_per_candidate.unassisted.seconds, candidates: summary.time_per_candidate.unassisted.candidate_count },
                  ]} margin={{ top: 8, right: 16, bottom: 4, left: -8 }}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="group" />
                    <YAxis />
                    <Tooltip formatter={(value, _name, item) => [
                      value === null ? 'No observations' : `${Math.round(Number(value) / 60)} min`,
                      `Candidates (n=${item.payload.candidates})`,
                    ]} />
                    <Bar dataKey="seconds" name="Elapsed time per candidate" radius={[5, 5, 0, 0]}>
                      {[0, 1].map((index) => <Cell key={index} fill={colors[index]} />)}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              </div>
              <p className="calibration-caption">Timing comparison is descriptive and not a causal estimate of AI impact.</p>
            </article>
          </section>

          <section className="grid-two">
            <article className="card impact-chart-card">
              <h2>Pass-rate proxy by trade</h2>
              <p className="calibration-caption">{summary.outcome_method}</p>
              {summary.pass_rate_by_trade.length ? (
                <div className="impact-chart">
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={summary.pass_rate_by_trade} margin={{ top: 8, right: 16, bottom: 48, left: -8 }}>
                      <CartesianGrid strokeDasharray="3 3" />
                      <XAxis dataKey="label" angle={-28} textAnchor="end" interval={0} height={64} tick={{ fontSize: 10 }} />
                      <YAxis domain={[0, 1]} tickFormatter={(value) => `${Math.round(value * 100)}%`} />
                      <Tooltip content={<PercentTooltip />} />
                      <Bar dataKey="pass_rate" name="Pass rate proxy" fill="#15845d" radius={[5, 5, 0, 0]} />
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              ) : <p className="empty-state">No completed, scored assessments are available for trade comparison.</p>}
              <ul className="impact-counts">
                {summary.pass_rate_by_trade.map((item) => <li key={item.label}>{item.label}: {item.passed}/{item.eligible} passed ({item.eligible} eligible){item.includes_demo_data ? ' · demo data' : ''}</li>)}
              </ul>
            </article>

            <article className="card impact-fairness-card">
              <h2>Fairness view</h2>
              <p className="calibration-caption">{summary.fairness_method}</p>
              <div className="fairness-panels">
                {Object.entries(summary.fairness).map(([dimension, rows]) => (
                  <section className="fairness-panel" key={dimension}>
                    <h3>{fairnessLabels[dimension] ?? dimension}</h3>
                    {rows.length ? (
                      <>
                        <div className="impact-chart impact-chart-fairness">
                          <ResponsiveContainer width="100%" height="100%">
                            <BarChart data={rows} margin={{ top: 6, right: 10, bottom: 26, left: -16 }}>
                              <CartesianGrid strokeDasharray="3 3" />
                              <XAxis dataKey="label" angle={-20} textAnchor="end" interval={0} height={44} tick={{ fontSize: 9 }} />
                              <YAxis domain={[0, 1]} tickFormatter={(value) => `${Math.round(value * 100)}%`} tick={{ fontSize: 9 }} />
                              <Tooltip content={<PercentTooltip />} />
                              <Bar dataKey="pass_rate" name="Pass rate proxy" fill="#7856a8" radius={[4, 4, 0, 0]} />
                            </BarChart>
                          </ResponsiveContainer>
                        </div>
                        <ul className="impact-counts">
                          {rows.map((row) => <li key={row.label}>{row.label}: {row.passed}/{row.eligible}{row.includes_demo_data ? ' · synthetic group' : ''}</li>)}
                        </ul>
                      </>
                    ) : <p className="empty-state">No completed assessments with {fairnessLabels[dimension]?.toLowerCase()} data.</p>}
                  </section>
                ))}
              </div>
            </article>
          </section>
          <p className="warning-message">Fairness subgroup rates are descriptive, often based on small groups, and contain synthetic seeded demographics. Do not use them to infer discrimination, compare worker capability, or make individual decisions.</p>
        </>
      ) : null}
    </main>
  )
}
