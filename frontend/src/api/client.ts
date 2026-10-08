import Dexie from 'dexie'

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000'

const offlineDb = new Dexie('skillsetu-offline-db')
offlineDb.version(1).stores({ queue: '++id, action, createdAt, synced' })

export async function apiRequest<T>(path: string, options: RequestInit = {}, token?: string): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...(options.headers ?? {}),
    },
  })

  if (!response.ok) {
    const body = await response.text()
    throw new Error(body || 'Request failed')
  }

  return (await response.json()) as T
}

export async function persistQueue(action: string, payload: unknown) {
  await offlineDb.table('queue').add({
    action,
    payload,
    createdAt: new Date().toISOString(),
    synced: false,
  })
}

export async function syncQueue(token?: string) {
  const entries = await offlineDb.table('queue').where('synced').equals(0).toArray()
  for (const entry of entries) {
    try {
      await apiRequest(`/api/${entry.action}`, {
        method: 'POST',
        body: JSON.stringify(entry.payload),
      }, token)
      await offlineDb.table('queue').update(entry.id, { synced: true })
    } catch {
      break
    }
  }
}
