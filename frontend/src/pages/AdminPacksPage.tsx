import { useEffect, useState } from 'react'
import { apiRequest } from '../api/client'
import type { TradePack } from '../api/types'

export function AdminPacksPage({ token, isAdmin }: { token: string; isAdmin: boolean }) {
  const [draft, setDraft] = useState('[]')
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')
  const [tamperBusy, setTamperBusy] = useState(false)
  const [chainReport, setChainReport] = useState<{ valid: boolean; verified_count: number; total_count: number; broken_links: Array<{ id: number; reason: string | null }> } | null>(null)
  const [chainError, setChainError] = useState('')

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

  const simulateTampering = async () => {
    setTamperBusy(true)
    setChainError('')
    setNotice('')
    try {
      const result = await apiRequest<{ evidence_id: number; simulated: boolean; message: string }>(
        '/api/evidence/simulate-tampering',
        { method: 'POST' },
        token,
      )
      setNotice(`${result.message} Demo evidence ID: ${result.evidence_id}.`)
      await verifyChain()
    } catch (reason) {
      setChainError(reason instanceof Error ? reason.message : 'Could not run the tamper demo.')
    } finally {
      setTamperBusy(false)
    }
  }

  const verifyChain = async () => {
    setChainError('')
    try {
      setChainReport(await apiRequest<{ valid: boolean; verified_count: number; total_count: number; broken_links: Array<{ id: number; reason: string | null }> }>('/api/evidence/verify-chain', { method: 'POST' }, token))
    } catch (reason) {
      setChainError(reason instanceof Error ? reason.message : 'Could not verify the evidence chain.')
    }
  }

  return (
    <main className="page-shell">
      {isAdmin ? <section className="card padded-card tamper-demo-card">
        <p className="eyebrow">ADMIN DEMONSTRATION ONLY</p>
        <h2>Evidence-chain tamper demo</h2>
        <p>Creates a clearly marked synthetic evidence entry, edits its stored proof after hashing, and leaves the altered link visible to the verifier. It never edits a worker evidence record.</p>
        <div className="inline-actions">
          <button type="button" className="button-secondary" onClick={() => void simulateTampering()} disabled={tamperBusy || !token}>
            {tamperBusy ? 'Simulating…' : 'Simulate tampering'}
          </button>
          <button type="button" onClick={() => void verifyChain()} disabled={!token}>Verify chain</button>
        </div>
        {notice ? <p className="success-message" role="status">{notice}</p> : null}
        {chainError ? <p className="error-text" role="alert">{chainError}</p> : null}
        {chainReport ? (
          <div className={chainReport.valid ? 'success-message' : 'warning-message'} role="status">
            <strong>{chainReport.valid ? 'Chain verified' : 'Broken evidence link detected'}</strong>
            <p>{chainReport.verified_count} of {chainReport.total_count} links verified.</p>
            {chainReport.broken_links.length ? (
              <ul>
                {chainReport.broken_links.map((item) => <li key={item.id}>Evidence #{item.id}: {item.reason ?? 'invalid link'}</li>)}
              </ul>
            ) : null}
          </div>
        ) : null}
      </section> : null}
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

export default AdminPacksPage
