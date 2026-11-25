export type Me = {
  id: string
  email: string
  farmer_id: string | null
  first_name: string
  last_name: string
  phone: string
  organization: { id: string; name: string; role: string } | null
  organizations: { id: string; name: string; role: string }[]
}

export type Page<T> = {
  count: number
  results: T[]
}

const API_URL = import.meta.env.VITE_API_URL ?? ''

let accessToken: string | null = null
let organizationId: string | null = null

export function apiUrl(path: string) {
  return `${API_URL}${path}`
}

export function setOrganization(id: string | null) {
  organizationId = id
}

function remember(me: Me) {
  organizationId = me.organization?.id ?? null
  return me
}

function messageFrom(body: unknown, fallback: string) {
  if (!body || typeof body !== 'object') return fallback
  const record = body as Record<string, unknown>
  if (typeof record.detail === 'string') return record.detail
  const parts: string[] = []
  for (const [key, value] of Object.entries(record)) {
    if (Array.isArray(value)) parts.push(`${key}: ${value.join(' ')}`)
    else if (typeof value === 'string') parts.push(`${key}: ${value}`)
    else if (value && typeof value === 'object') parts.push(`${key}: ${JSON.stringify(value)}`)
  }
  return parts.join(' ') || fallback
}

async function readError(response: Response, fallback: string) {
  try {
    return messageFrom(await response.json(), fallback)
  } catch {
    return fallback
  }
}

export async function loginRequest(identifier: string, password: string): Promise<Me> {
  const response = await fetch(apiUrl('/api/v1/auth/login/'), {
    method: 'POST',
    credentials: 'include',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ identifier, password }),
  })
  if (!response.ok) throw new Error(await readError(response, 'Could not sign in.'))
  const body = (await response.json()) as { access: string }
  accessToken = body.access
  return remember(await fetchMe())
}

export async function registerRequest(payload: {
  organization_name: string
  email: string
  password: string
  first_name: string
  last_name: string
}): Promise<Me> {
  const response = await fetch(apiUrl('/api/v1/auth/register/'), {
    method: 'POST',
    credentials: 'include',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })
  if (!response.ok) throw new Error(await readError(response, 'Could not create the organization.'))
  const body = (await response.json()) as { access: string }
  accessToken = body.access
  return remember(await fetchMe())
}

export async function refreshSession(): Promise<Me | null> {
  const response = await fetch(apiUrl('/api/v1/auth/refresh/'), {
    method: 'POST',
    credentials: 'include',
    headers: { 'Content-Type': 'application/json' },
  })
  if (!response.ok) {
    accessToken = null
    return null
  }
  const body = (await response.json()) as { access: string }
  accessToken = body.access
  return remember(await fetchMe())
}

export async function fetchMe(): Promise<Me> {
  const response = await fetch(apiUrl('/api/v1/auth/me/'), {
    credentials: 'include',
    headers: { Authorization: `Bearer ${accessToken ?? ''}` },
  })
  if (!response.ok) throw new Error(await readError(response, 'Could not load your account.'))
  return remember((await response.json()) as Me)
}

export async function logoutRequest() {
  await fetch(apiUrl('/api/v1/auth/logout/'), {
    method: 'POST',
    credentials: 'include',
    headers: {
      Authorization: `Bearer ${accessToken ?? ''}`,
      'Content-Type': 'application/json',
    },
  })
  accessToken = null
  organizationId = null
}

export async function requestPasswordReset(email: string) {
  const response = await fetch(apiUrl('/api/v1/auth/password-reset/'), {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email }),
  })
  if (!response.ok) throw new Error(await readError(response, 'Could not request a reset.'))
  return (await response.json()) as { detail: string }
}

export async function confirmPasswordReset(token: string, password: string) {
  const response = await fetch(apiUrl('/api/v1/auth/password-reset/confirm/'), {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ token, password }),
  })
  if (!response.ok) throw new Error(await readError(response, 'Could not update the password.'))
}

async function authorized(path: string, init: RequestInit, retry: boolean): Promise<Response> {
  const headers = new Headers(init.headers)
  if (accessToken) headers.set('Authorization', `Bearer ${accessToken}`)
  if (organizationId) headers.set('X-Organization-Id', organizationId)
  const response = await fetch(apiUrl(path), { ...init, headers, credentials: 'include' })
  if (response.status === 401 && retry) {
    const me = await refreshSession()
    if (me) return authorized(path, init, false)
  }
  return response
}

export async function api<T>(path: string, init: RequestInit = {}): Promise<T> {
  const response = await authorized(path, init, true)
  if (!response.ok) throw new Error(await readError(response, 'Request failed.'))
  if (response.status === 204) return undefined as T
  const type = response.headers.get('content-type') ?? ''
  if (type.includes('application/json')) return (await response.json()) as T
  return (await response.blob()) as T
}

export function sendJson<T>(path: string, method: string, body: unknown) {
  return api<T>(path, {
    method,
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
}
