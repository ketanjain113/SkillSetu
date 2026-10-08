import { useEffect, useState } from 'react'
import QRCode from 'qrcode'
import type { Locale } from '../i18n/translations'
import { translations } from '../i18n/translations'

export function MySkillsPassportPage({ locale, lowLiteracyMode }: { locale: Locale; lowLiteracyMode: boolean }) {
  const t = translations[locale]
  const [passportUrl] = useState('https://demo.skillsetu.ai/passport/worker1')
  const [qrDataUrl, setQrDataUrl] = useState('')
  const [qrError, setQrError] = useState('')

  const sharePassport = async () => {
    if (navigator.share) {
      await navigator.share({ title: 'SkillSetu passport', text: 'My work profile and credentials', url: passportUrl })
      return
    }
    await navigator.clipboard.writeText(passportUrl)
    alert('Passport link copied to clipboard.')
  }

  useEffect(() => {
    let cancelled = false
    void QRCode.toDataURL(passportUrl)
      .then((url) => {
        if (!cancelled) setQrDataUrl(url)
      })
      .catch((reason: unknown) => {
        if (!cancelled) setQrError(reason instanceof Error ? reason.message : 'Could not generate passport QR code.')
      })
    return () => { cancelled = true }
  }, [passportUrl])

  return (
    <main className="page-shell">
      <div className="card padded-card">
        <h2>{t.myPassport}</h2>
        <div className="passport-grid">
          <div>
            <p><strong>Credential:</strong> Domestic Electrician – NSQF 4</p>
            <p><strong>Progress:</strong> 72% to NSQF 5</p>
            <p><strong>Next milestone:</strong> Advanced fault-finding and worksite safety review</p>
            <button type="button" className={lowLiteracyMode ? 'large-button' : ''} onClick={() => sharePassport()}>{t.shareQr}</button>
          </div>
          <div className="qr-panel">
            {qrDataUrl ? <img id="passport-qr" alt="QR code for worker passport" src={qrDataUrl} /> : <p className="state-message">{qrError || 'Generating QR code…'}</p>}
          </div>
        </div>
      </div>

      <div className="card padded-card">
        <h3>Recommended bridge courses (demo)</h3>
        <ul className="audit-list">
          <li><strong>{t.mockCourse}:</strong> Advanced fault finding in domestic wiring</li>
          <li><strong>{t.mockCourse}:</strong> Safe worksite supervision and inspection</li>
        </ul>
      </div>

      <div className="card padded-card">
        <h3>{t.mockJob}</h3>
        <ul className="audit-list">
          <li>Junior site technician – local service provider network</li>
          <li>Apprentice supervisor – housing maintenance team</li>
        </ul>
      </div>
    </main>
  )
}

export default MySkillsPassportPage
