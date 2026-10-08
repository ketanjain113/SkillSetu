import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { apiRequest } from '../api/client'
import type { AppUser, Role } from '../api/types'
import type { Locale } from '../i18n/translations'
import { translations } from '../i18n/translations'

export function LoginPage({ setToken, setUser, locale }: { setToken: (token: string) => void; setUser: (user: AppUser | null) => void; locale: Locale }) {
  const navigate = useNavigate()
  const t = translations[locale]
  const [username, setUsername] = useState('worker1')
  const [password, setPassword] = useState('worker123')
  const [error, setError] = useState('')

  const submit = async () => {
    try {
      const data = await apiRequest<{ access_token: string; role: Role; username: string }>(
        '/api/auth/login',
        { method: 'POST', body: JSON.stringify({ username, password }) },
      )
      const user = { username: data.username, role: data.role, name: username }
      localStorage.setItem('skillsetu-token', data.access_token)
      localStorage.setItem('skillsetu-user', JSON.stringify(user))
      setToken(data.access_token)
      setUser(user)
      navigate(data.role === 'worker' ? '/worker/declare' : data.role === 'assessor' || data.role === 'admin' ? '/assessor/score' : '/')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Login failed')
    }
  }

  return (
    <main className="page-shell center-layout">
      <div className="card form-card">
        <h2>{t.passport}</h2>
        <label>
          Username
          <input value={username} onChange={(event) => setUsername(event.target.value)} />
        </label>
        <label>
          Password
          <input type="password" value={password} onChange={(event) => setPassword(event.target.value)} />
        </label>
        {error ? <p className="error-text">{error}</p> : null}
        <button type="button" onClick={submit}>Login</button>
        <p className="micro-copy">Demo users: admin/admin123, assessor1/assessor123, worker1/worker123</p>
      </div>
    </main>
  )
}

export default LoginPage
