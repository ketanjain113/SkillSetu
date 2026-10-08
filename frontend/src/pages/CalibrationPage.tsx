import { useCallback, useEffect, useState } from 'react'
import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  ComposedChart,
  Line,
  LineChart,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import { apiRequest } from '../api/client'
import { AsyncState } from '../components/AsyncState'

type Metric = {
  metric: string
  value: number | null
  ci?: [number, number] | null
  method: string
  interpretation: string
}

type AssessorSummary = {
  assessor_key: string
  label: string
  severity: number
  leniency: number
  central_tendency: number
  drift: number
  n: number
}

type ReportCard = {
  assessor_name: string
  severity: number
  leniency_bias: number
  halo_effect: number
  drift: number
  recommendations: string[]
  coaching_note: string
}

type AnchorClip = {
  clip_id: string
  title: string
  mean_score: number
  consensus: number
}

type CalibrationSummary = {
  demo_data: boolean
  includes_demo_data: boolean
  data_label: string
  sample_count: number
  metrics: Metric[]
  assessor_severity: AssessorSummary[]
  alpha_over_time: Array<{ month: string; alpha: number; ci_low: number; ci_high: number; ci_band: number }>
  drift_over_time: Array<Record<string, string | number>>
  drift_threshold: number
  drift_alerts: Array<{ assessor_key: string; label: string; drift: number }>
  report_cards: ReportCard[]
  anchor_clips: AnchorClip[]
  assistance_comparison: {
    assisted: { mean_peer_consensus_error: number | null; n: number }
    unassisted: { mean_peer_consensus_error: number | null; n: number }
    interpretation: string
  }
  method_note: string
  viewer: { role: string; report_is_private: boolean }
}

const severityColor = '#18408c'
const assessorColors = ['#18408c', '#ff9933', '#15845d', '#7856a8', '#d1495b', '#2b8a9e', '#a06a00', '#53657d']
const metricLabels: Record<string, string> = {
  krippendorff_alpha_ordinal: "Krippendorff's alpha (ordinal)",
  weighted_cohens_kappa: 'Quadratic weighted kappa',
  icc_absolute_agreement: 'ICC(2,1) absolute agreement',
}

function metricValue(value: number | null) {
  return value === null ? '—' : value.toFixed(3)
}

export default function CalibrationPage({ token }: { token: string }) {
  const [summary, setSummary] = useState<CalibrationSummary | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  const load = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      setSummary(await apiRequest<CalibrationSummary>('/api/calibration', {}, token))
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Calibration data could not be loaded.')
    } finally {
      setLoading(false)
    }
  }, [token])

  useEffect(() => {
    const timer = window.setTimeout(() => void load(), 0)
    return () => window.clearTimeout(timer)
  }, [load])

  const metrics = summary?.metrics ?? []
  const alpha = metrics.find((metric) => metric.metric === 'krippendorff_alpha_ordinal')
  const kappa = metrics.find((metric) => metric.metric === 'weighted_cohens_kappa')
  const icc = metrics.find((metric) => metric.metric === 'icc_absolute_agreement')
  const driftSeries = summary?.assessor_severity.map((item) => item.assessor_key) ?? []

  return (
    <main className="page-shell calibration-page">
      <header className="page-heading">
        <p className="eyebrow">ASSESSMENT QUALITY</p>
        <h1>Calibration dashboard</h1>
        <p>Agreement and scoring patterns calculated from persisted assessor score records.</p>
      </header>

      <AsyncState loading={loading} error={error} onRetry={() => void load()} />
      {summary ? (
        <>
          <section className="calibration-data-note" aria-live="polite">
            <strong>{summary.data_label}</strong>
            <span>{summary.sample_count.toLocaleString()} stored score records</span>
            {summary.demo_data || summary.includes_demo_data
              ? <span className="calibration-demo-badge">Seeded numbers are demo data</span>
              : null}
          </section>

          <section className="metric-grid" aria-label="Agreement metrics" data-tour="calibration-metrics">
            {[alpha, kappa, icc].map((metric) => metric ? (
              <article className="metric-card metric-green" key={metric.metric}>
                <span className="metric-label">{metricLabels[metric.metric] ?? metric.metric}</span>
                <strong>{metricValue(metric.value)}</strong>
                <span className="metric-note">
                  {metric.ci ? `95% CI ${metric.ci[0].toFixed(3)}–${metric.ci[1].toFixed(3)}` : metric.interpretation}
                </span>
                <span className="calibration-method">{metric.method}</span>
              </article>
            ) : null)}
          </section>

          <section className="grid-two">
            <article className="card calibration-chart-card">
              <h2>Ordinal agreement over time</h2>
              <p className="calibration-caption">Monthly alpha with item-bootstrap 95% confidence interval.</p>
              {summary.alpha_over_time.length ? (
                <div className="calibration-chart">
                  <ResponsiveContainer width="100%" height="100%">
                    <AreaChart data={summary.alpha_over_time} margin={{ top: 10, right: 18, bottom: 4, left: -12 }}>
                      <CartesianGrid strokeDasharray="3 3" />
                      <XAxis dataKey="month" tick={{ fontSize: 11 }} />
                      <YAxis domain={[-1, 1]} tick={{ fontSize: 11 }} />
                      <Tooltip formatter={(value) => Number(value).toFixed(3)} />
                      <Area dataKey="ci_low" stackId="interval" stroke="none" fill="transparent" />
                      <Area dataKey="ci_band" stackId="interval" stroke="none" fill="#ff9933" fillOpacity={0.22} />
                      <Line dataKey="alpha" type="monotone" stroke={severityColor} strokeWidth={2.5} dot={{ r: 3 }} />
                    </AreaChart>
                  </ResponsiveContainer>
                </div>
              ) : <p className="empty-state">Not enough overlapping assessor ratings to chart agreement over time.</p>}
            </article>

            <article className="card calibration-chart-card">
              <h2>Assessor severity</h2>
              <p className="calibration-caption">Item-adjusted score residual; positive values indicate stricter ratings.</p>
              {summary.assessor_severity.length ? <div className="calibration-chart">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={summary.assessor_severity} margin={{ top: 8, right: 16, bottom: 4, left: -12 }}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="label" tick={{ fontSize: 10 }} interval={0} />
                    <YAxis tick={{ fontSize: 11 }} />
                    <Tooltip formatter={(value) => Number(value).toFixed(3)} />
                    <ReferenceLine y={0} stroke="#64748b" />
                    <Bar dataKey="severity" name="Severity (stricter)" fill={severityColor} radius={[5, 5, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </div> : <p className="empty-state">Severity requires stored scores with at least one peer rating per assessor.</p>}
            </article>
          </section>

          <section className="grid-two">
            <article className="card calibration-chart-card">
              <h2>Leniency and central tendency</h2>
              <p className="calibration-caption">Positive leniency means more generous-than-peer scores; higher central tendency means a narrower score range.</p>
              {summary.assessor_severity.length ? <div className="calibration-chart">
                <ResponsiveContainer width="100%" height="100%">
                  <ComposedChart data={summary.assessor_severity} margin={{ top: 8, right: 22, bottom: 4, left: -12 }}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="label" tick={{ fontSize: 10 }} interval={0} />
                    <YAxis yAxisId="scores" tick={{ fontSize: 11 }} />
                    <YAxis yAxisId="range" orientation="right" domain={[0, 1]} tick={{ fontSize: 11 }} />
                    <Tooltip formatter={(value) => Number(value).toFixed(3)} />
                    <ReferenceLine yAxisId="scores" y={0} stroke="#64748b" />
                    <Bar yAxisId="scores" dataKey="leniency" name="Leniency" fill="#ff9933" radius={[5, 5, 0, 0]} />
                    <Line yAxisId="range" dataKey="central_tendency" name="Central tendency" stroke="#15845d" strokeWidth={2.5} />
                  </ComposedChart>
                </ResponsiveContainer>
              </div> : <p className="empty-state">Scoring patterns are unavailable until assessors have overlapping stored scores.</p>}
            </article>

            <article className="card calibration-chart-card">
              <h2>Scoring drift</h2>
              <p className="calibration-caption">Change from each assessor's first recorded month. Alert threshold: ±{summary.drift_threshold.toFixed(2)} points.</p>
              {summary.drift_alerts.length ? (
                <ul className="calibration-alert-list" aria-label="Drift threshold alerts">
                  {summary.drift_alerts.map((alert) => <li key={alert.assessor_key}>{alert.label}: {alert.drift.toFixed(2)} point drift</li>)}
                </ul>
              ) : null}
              {summary.drift_over_time.length ? <div className="calibration-chart">
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={summary.drift_over_time} margin={{ top: 8, right: 14, bottom: 4, left: -12 }}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="month" tick={{ fontSize: 10 }} />
                    <YAxis tick={{ fontSize: 11 }} />
                    <Tooltip />
                    <ReferenceLine y={summary.drift_threshold} stroke="#d1495b" strokeDasharray="5 4" />
                    <ReferenceLine y={-summary.drift_threshold} stroke="#d1495b" strokeDasharray="5 4" />
                    {driftSeries.map((key, index) => (
                      <Line key={key} dataKey={key} name={`Assessor ${index + 1}`} type="monotone" stroke={assessorColors[index % assessorColors.length]} dot={false} connectNulls />
                    ))}
                  </LineChart>
                </ResponsiveContainer>
              </div> : <p className="empty-state">Drift needs dated score records across multiple periods.</p>}
            </article>
          </section>

          <section className="grid-two">
            <article className="card calibration-chart-card">
              <h2>AI-assisted and unassisted scoring</h2>
              <p className="calibration-caption">{summary.assistance_comparison.interpretation}</p>
              {summary.assistance_comparison.assisted.n + summary.assistance_comparison.unassisted.n > 0 ? <div className="calibration-chart calibration-chart-short">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={[
                    { group: 'AI-assisted', error: summary.assistance_comparison.assisted.mean_peer_consensus_error, n: summary.assistance_comparison.assisted.n },
                    { group: 'Unassisted', error: summary.assistance_comparison.unassisted.mean_peer_consensus_error, n: summary.assistance_comparison.unassisted.n },
                  ]} margin={{ top: 8, right: 18, bottom: 4, left: -8 }}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="group" />
                    <YAxis />
                    <Tooltip formatter={(value) => value === null ? 'No observations' : Number(value).toFixed(3)} />
                    <Bar dataKey="error" name="Mean absolute peer-consensus difference" fill="#15845d" radius={[5, 5, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </div> : <p className="empty-state">No assisted or unassisted score records are available to compare.</p>}
              {summary.assistance_comparison.assisted.n + summary.assistance_comparison.unassisted.n > 0
                ? <p className="calibration-caption">AI-assisted n={summary.assistance_comparison.assisted.n}; unassisted n={summary.assistance_comparison.unassisted.n}. Descriptive comparison only; not causal.</p>
                : null}
            </article>

            <article className="card calibration-report-card">
              <h2>{summary.viewer.report_is_private ? 'Your private coaching report' : 'Assessor coaching reports'}</h2>
              <p className="calibration-caption">Private coaching feedback, not a punitive rating.</p>
              {summary.report_cards.length ? summary.report_cards.map((report) => (
                <div className="calibration-coaching" key={report.assessor_name}>
                  {!summary.viewer.report_is_private ? <h3>{report.assessor_name}</h3> : null}
                  <dl>
                    <div><dt>Relative severity</dt><dd>{report.severity.toFixed(3)}</dd></div>
                    <div><dt>Leniency</dt><dd>{report.leniency_bias.toFixed(3)}</dd></div>
                    <div><dt>Central tendency</dt><dd>{report.halo_effect.toFixed(3)}</dd></div>
                    <div><dt>Observed drift</dt><dd>{report.drift.toFixed(3)}</dd></div>
                  </dl>
                  <ul>{report.recommendations.map((recommendation) => <li key={recommendation}>{recommendation}</li>)}</ul>
                  <p>{report.coaching_note}</p>
                  <h4>Recommended anchor clips</h4>
                  {summary.anchor_clips.length ? (
                    <ul className="anchor-list">
                      {summary.anchor_clips.slice(0, 3).map((clip) => (
                        <li key={clip.clip_id}>
                          <strong>{clip.title}</strong>
                          <span>{clip.clip_id} · consensus {clip.consensus.toFixed(2)} · mean score {clip.mean_score.toFixed(2)}</span>
                        </li>
                      ))}
                    </ul>
                  ) : <p>No anchor recommendations are available yet.</p>}
                  {summary.demo_data || summary.includes_demo_data
                    ? <p className="calibration-caption">Anchor references are generated from seeded score records; demo clips are not video assets.</p>
                    : null}
                </div>
              )) : <p className="empty-state">A coaching report will appear after you have stored assessor scores.</p>}
            </article>
          </section>

          <details className="card calibration-methods">
            <summary>Methods and limitations</summary>
            <p>{summary.method_note}</p>
            <ul>
              {metrics.map((metric) => <li key={metric.metric}><strong>{metricLabels[metric.metric] ?? metric.metric}:</strong> {metric.interpretation}</li>)}
            </ul>
            <p>All metrics use stored ScoreRecord entries and matched assessment-competency items. Bootstrap intervals are reproducible item-resampling percentile intervals.</p>
          </details>
        </>
      ) : null}
    </main>
  )
}
