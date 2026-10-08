import { useEffect, useState } from 'react'
import { jsPDF } from 'jspdf'
import QRCode from 'qrcode'
import { apiRequest } from '../api/client'
import { AsyncState } from '../components/AsyncState'

type Certificate = {
  assessment_id: number
  credential_id: string
  trade: string
  assessor_signoff: boolean
  signature_verified: boolean
  hash_verified: boolean
  evidence_chain_verified: boolean
  verified: boolean
  public_url: string
  created_at: string
  verifiable_credential: { proof: { type: string } }
  demo_data: boolean
}

export function CertificatePage({ token }: { token: string }) {
  const [assessmentId, setAssessmentId] = useState(sessionStorage.getItem('skillsetu-last-assessment-id') ?? '1')
  const [certificate, setCertificate] = useState<Certificate | null>(null)
  const [qrDataUrl, setQrDataUrl] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')

  useEffect(() => {
    if (!certificate) return
    let cancelled = false
    const verifyUrl = new URL(`/verify/${certificate.assessment_id}`, window.location.origin).toString()
    void QRCode.toDataURL(verifyUrl, { errorCorrectionLevel: 'H', margin: 2, width: 240 })
      .then((url) => { if (!cancelled) setQrDataUrl(url) })
      .catch((reason: unknown) => setError(reason instanceof Error ? reason.message : 'Could not create the certificate QR code.'))
    return () => { cancelled = true }
  }, [certificate])

  const issueCertificate = async () => {
    const id = Number(assessmentId)
    if (!Number.isSafeInteger(id) || id < 1) {
      setError('Enter a valid assessment ID.')
      return
    }
    setLoading(true)
    setError('')
    setNotice('')
    setQrDataUrl('')
    try {
      const response = await apiRequest<Certificate>(`/api/certificate/${id}`, {}, token)
      setCertificate(response)
      sessionStorage.setItem('skillsetu-last-assessment-id', String(id))
      setNotice(response.verified
        ? 'Credential signature and evidence chain verified.'
        : 'Credential issued and signature checked, but full verification did not pass. Review the individual checks before presenting it as verified.')
    } catch (reason) {
      setCertificate(null)
      setQrDataUrl('')
      setError(reason instanceof Error ? reason.message : 'Could not issue or verify this certificate.')
    } finally {
      setLoading(false)
    }
  }

  const downloadPdf = async () => {
    if (!certificate || !qrDataUrl) {
      setError('Issue the certificate and generate its verification QR before downloading.')
      return
    }
    const pdf = new jsPDF({ unit: 'pt', format: 'a4' })
    pdf.setFillColor(24, 64, 140)
    pdf.rect(0, 0, 595, 150, 'F')
    pdf.setTextColor(255, 255, 255)
    pdf.setFontSize(24)
    pdf.text('SkillSetu Demonstration Certificate', 40, 64)
    pdf.setFontSize(12)
    pdf.text('Illustrative credential — not an accredited qualification', 40, 92)
    pdf.setTextColor(23, 43, 77)
    pdf.setFontSize(15)
    pdf.text(`Credential: ${certificate.credential_id}`, 40, 200)
    pdf.text(`Trade: ${certificate.trade}`, 40, 232)
    pdf.text(`Assessment: ${certificate.assessment_id}`, 40, 264)
    pdf.setFontSize(11)
    pdf.text(`Assessor sign-off: ${certificate.assessor_signoff ? 'recorded' : 'not recorded'}`, 40, 305)
    pdf.text(`Ed25519 signature: ${certificate.signature_verified ? 'verified' : 'failed'}`, 40, 327)
    pdf.text(`Credential hash: ${certificate.hash_verified ? 'verified' : 'failed'}`, 40, 349)
    pdf.text(`Evidence chain: ${certificate.evidence_chain_verified ? 'verified' : 'not verified'}`, 40, 371)
    pdf.text(`Overall status: ${certificate.verified ? 'VERIFIED' : 'NOT VERIFIED'}`, 40, 393)
    pdf.addImage(qrDataUrl, 'PNG', 415, 190, 140, 140)
    pdf.setFontSize(9)
    pdf.text(`Scan to check: ${new URL(certificate.public_url, window.location.origin).toString()}`, 40, 440)
    pdf.text('Signature uses a locally managed demo issuer key and is not a production trust credential.', 40, 465, { maxWidth: 515 })
    pdf.save(`skillsetu-certificate-${certificate.assessment_id}.pdf`)
  }

  return (
    <main className="page-shell">
      <header className="page-heading">
        <p className="eyebrow">CREDENTIAL PRESENTATION</p>
        <h1>Certificate and verification</h1>
        <p>Issue or retrieve the signed demo credential for a completed assessment.</p>
      </header>
      <section className="card padded-card">
        <label htmlFor="certificate-assessment-id">Assessment ID</label>
        <div className="inline-actions">
          <input id="certificate-assessment-id" type="number" min="1" value={assessmentId} onChange={(event) => setAssessmentId(event.target.value)} />
          <button type="button" onClick={() => void issueCertificate()} disabled={loading || !token}>{loading ? 'Checking…' : 'Issue and verify'}</button>
        </div>
        <p className="calibration-caption">Requires assessor or administrator access and an assessment already signed off.</p>
        <AsyncState loading={loading} error={error} />
        {notice ? <p className={certificate?.verified ? 'success-message' : 'warning-message'} role="status">{notice}</p> : null}
        {certificate ? (
          <article className="certificate-preview">
            <div>
              <p className="eyebrow">SKILLSETU DEMO CREDENTIAL</p>
              <h2>{certificate.trade}</h2>
              <p>Credential {certificate.credential_id}</p>
              <p>Assessment #{certificate.assessment_id}</p>
              <span className={`certificate-badge ${certificate.verified ? 'certificate-verified' : 'certificate-unverified'}`}>
                {certificate.verified ? 'Verified' : 'Not fully verified'}
              </span>
              {certificate.demo_data ? <span className="calibration-demo-badge">Demo data</span> : null}
              <ul className="certificate-checks">
                <li>Assessor sign-off: {certificate.assessor_signoff ? 'Recorded' : 'Missing'}</li>
                <li>Ed25519 signature: {certificate.signature_verified ? 'Verified' : 'Failed'}</li>
                <li>Credential content hash: {certificate.hash_verified ? 'Verified' : 'Failed'}</li>
                <li>Evidence chain: {certificate.evidence_chain_verified ? 'Verified' : 'Not verified'}</li>
              </ul>
            </div>
            <div className="qr-panel">
              {qrDataUrl ? <img src={qrDataUrl} alt={`QR code linking to verify assessment ${certificate.assessment_id}`} /> : <p role="status">Creating QR code…</p>}
            </div>
            <div className="inline-actions certificate-actions">
              <a className="button-link" href={certificate.public_url}>Open public verification</a>
              <button type="button" className="button-secondary" onClick={() => void downloadPdf()} disabled={!qrDataUrl}>Download PDF</button>
            </div>
            <p className="warning-message certificate-disclaimer">
              This is a demonstration credential. It checks a real Ed25519 signature using the app's local demo issuer key; it is not issued by an accreditation authority or suitable as proof of a formal qualification.
            </p>
          </article>
        ) : null}
      </section>
    </main>
  )
}

export default CertificatePage
