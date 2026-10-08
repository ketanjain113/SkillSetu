import { useState } from 'react'
import type { Locale } from '../i18n/translations'
import { translations } from '../i18n/translations'

export function NotificationsPage({ locale, lowLiteracyMode }: { locale: Locale; lowLiteracyMode: boolean }) {
  const t = translations[locale]
  const [notifications, setNotifications] = useState<Array<{ id: number; channel: string; body: string; status: string }>>([
    { id: 1, channel: 'SMS', body: 'Your assessment moved to review.', status: 'queued' },
    { id: 2, channel: 'WhatsApp', body: 'Please complete your evidence check.', status: 'sent' },
  ])

  const sendMockNotification = (channel: 'SMS' | 'WhatsApp') => {
    setNotifications((current) => [
      { id: Date.now(), channel, body: `Demo ${channel} alert: your RPL status has changed.`, status: 'sent' },
      ...current,
    ])
  }

  return (
    <main className="page-shell">
      <div className="card padded-card">
        <h2>{t.notificationsTitle}</h2>
        <div className="inline-actions">
          <button type="button" className={lowLiteracyMode ? 'large-button' : ''} onClick={() => sendMockNotification('SMS')}>Send SMS</button>
          <button type="button" className="ghost-button" onClick={() => sendMockNotification('WhatsApp')}>Send WhatsApp</button>
        </div>
        <ul className="audit-list">
          {notifications.map((item) => (
            <li key={item.id}><strong>{item.channel}</strong> — {item.body} <span className="status-pill">{item.status}</span></li>
          ))}
        </ul>
      </div>
    </main>
  )
}

export default NotificationsPage
