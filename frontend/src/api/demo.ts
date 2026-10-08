import { apiRequest } from './client'
import type { AppUser, Role } from './types'

export const DEMO_MODE = import.meta.env.VITE_DEMO_MODE === 'true'

export type DemoRole = Role | 'assessor2'

const demoAccounts: Record<DemoRole, { username: string; password: string }> = {
  worker: { username: 'worker1', password: 'worker123' },
  assessor: { username: 'assessor1', password: 'assessor123' },
  assessor2: { username: 'assessor2', password: 'assessor123' },
  moderator: { username: 'moderator1', password: 'moderator123' },
  admin: { username: 'admin', password: 'admin123' },
}

export async function signInDemoRole(role: DemoRole): Promise<{ token: string; user: AppUser }> {
  if (!DEMO_MODE) {
    throw new Error('Demo role switching is disabled.')
  }

  const account = demoAccounts[role]
  const response = await apiRequest<{ access_token: string; role: Role; username: string }>('/api/auth/login', {
    method: 'POST',
    body: JSON.stringify(account),
  })
  const user: AppUser = { username: response.username, role: response.role, name: response.username }
  localStorage.setItem('skillsetu-token', response.access_token)
  localStorage.setItem('skillsetu-user', JSON.stringify(user))
  return { token: response.access_token, user }
}
