import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { DEMO_MODE, type DemoRole } from '../api/demo'

type DemoRoleSwitcherProps = {
  currentRole?: DemoRole
  currentUsername?: string
  onSignIn: (role: DemoRole) => Promise<void>
}

const roles: Array<{ id: DemoRole; label: string }> = [
  { id: 'worker', label: 'Worker' },
  { id: 'assessor', label: 'Assessor' },
  { id: 'assessor2', label: 'Second assessor' },
  { id: 'moderator', label: 'Moderator' },
  { id: 'admin', label: 'Admin' },
]

export function DemoRoleSwitcher({ currentRole, currentUsername, onSignIn }: DemoRoleSwitcherProps) {
  const navigate = useNavigate()
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  const selectedRole = currentRole === 'assessor' && currentUsername === 'assessor2' ? 'assessor2' : currentRole

  if (!DEMO_MODE) return null

  const switchRole = async (role: DemoRole) => {
    setBusy(true)
    setError('')
    try {
      await onSignIn(role)
      const destination = {
        worker: '/worker/declare',
        assessor: '/assessor/score',
        assessor2: '/assessor/score',
        moderator: '/moderation',
        admin: '/admin/packs',
      } satisfies Record<DemoRole, string>
      navigate(destination[role])
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Could not switch demo role.')
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="demo-role-control">
      <label className="demo-role-label" htmlFor="demo-role">Demo role</label>
      <select
        id="demo-role"
        aria-label="Switch demo role"
        value={selectedRole ?? ''}
        disabled={busy}
        onChange={(event) => void switchRole(event.target.value as DemoRole)}
      >
        <option value="" disabled>Select role</option>
        {roles.map((role) => <option key={role.id} value={role.id}>{role.label}</option>)}
      </select>
      {busy ? <span className="visually-hidden" role="status">Switching role…</span> : null}
      {error ? <span className="demo-role-error" role="alert">{error}</span> : null}
    </div>
  )
}
