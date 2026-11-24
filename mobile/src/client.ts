const API_URL = process.env.EXPO_PUBLIC_API_URL ?? 'http://127.0.0.1:8000'

export type Me = {
  id: string
  email: string
  farmer_id: string | null
  organization: { id: string; name: string; role: string } | null
}

export type Session = {
  access: string
  refresh: string
  me: Me
}

export class OfflineError extends Error {}

export function batchCode(raw: string) {
  const value = raw.trim()
  const marker = 'farmmate:batch:'
  return value.startsWith(marker) ? value.slice(marker.length) : value
}

async function parseError(response: Response) {
  try {
    const body = (await response.json()) as { detail?: string }
    return body.detail || 'Request failed.'
  } catch {
    return 'Request failed.'
  }
}

export async function signIn(identifier: string, password: string): Promise<Session> {
  const response = await fetch(`${API_URL}/api/v1/auth/login/`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-FarmMate-Client': 'mobile',
    },
    body: JSON.stringify({ identifier, password }),
  })
  if (!response.ok) throw new Error(await parseError(response))
  const body = (await response.json()) as { access: string; refresh: string }
  const meResponse = await fetch(`${API_URL}/api/v1/auth/me/`, {
    headers: { Authorization: `Bearer ${body.access}` },
  })
  if (!meResponse.ok) throw new Error('Could not load your account.')
  return { access: body.access, refresh: body.refresh, me: (await meResponse.json()) as Me }
}

export async function api<T>(session: Session, path: string, init: RequestInit = {}): Promise<T> {
  let response: Response
  try {
    response = await fetch(`${API_URL}${path}`, {
      ...init,
      headers: {
        Authorization: `Bearer ${session.access}`,
        'X-FarmMate-Client': 'mobile',
        'X-Organization-Id': session.me.organization?.id ?? '',
        ...(init.body ? { 'Content-Type': 'application/json' } : {}),
        ...init.headers,
      },
    })
  } catch {
    throw new OfflineError('No connection. The record was kept on this phone.')
  }
  if (!response.ok) throw new Error(await parseError(response))
  if (response.status === 204) return undefined as T
  return (await response.json()) as T
}
