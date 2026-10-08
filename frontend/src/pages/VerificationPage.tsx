import { useParams } from 'react-router-dom'
import { useEffect, useState } from 'react'
import { apiRequest } from '../api/client'
import { AsyncState } from '../components/AsyncState'

type Verification = {
  credential_id: string
  status: string
  trade: string
  hash_verified: boolean
  signature_verified: boolean
  evidence_chain_verified: boolean
  verified: boolean
  assessor_signoff: boolean
  note: string
  demo_data?: boolean
}

export function VerificationPage() {
  const { id } = useParams<{ id: string }>()
  const [verification, setVerification] = useState<Verification | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    if (!id) return
    void apiRequest<Verification>(`/api/public/verify/${encodeURIComponent(id)}`)
      .then(setVerification)
      .catch((reason: unknown) => setError(reason instanceof Error ? reason.message : 'Could not verify this credential.'))
      .finally(() => setLoading(false))
  }, [id])

  return (
    <main className="page-shell center-layout">
      <div className="card padded-card verification-box" data-tour="public-verification">
        <p className="eyebrow">Public verification</p>
        <AsyncState loading={Boolean(id) && loading} error={error || (!id ? 'Credential ID is missing.' : '')} />
        {verification ? (
          <>
            <h2>{verification.verified ? 'Credential verified' : 'Credential not verified'}</h2>
            <span className={`certificate-badge ${verification.verified ? 'certificate-verified' : 'certificate-unverified'}`}>
              {verification.verified ? 'Verified' : 'Verification failed'}
            </span>
            <p>Credential ID: {verification.credential_id}</p>
            <p>Trade: {verification.trade}</p>
            <p>Ed25519 signature check: {verification.signature_verified ? 'Passed' : 'Failed'}</p>
            <p>Credential hash check: {verification.hash_verified ? 'Passed' : 'Failed'}</p>
            <p>Evidence chain check: {verification.evidence_chain_verified ? 'Passed' : 'Failed / no evidence saved'}</p>
            <p>Assessor sign-off: {verification.assessor_signoff ? 'Recorded' : 'Not recorded'}</p>
            {verification.demo_data ? <span className="calibration-demo-badge">Demo data</span> : null}
            <p className="micro-copy">{verification.note}</p>
          </>
        ) : null}
      </div>
    </main>
  )
}

export default VerificationPage
