export type Me = {
  id: string
  email: string
  farmer_id: string | null
  organization: { id: string; name: string; role: string } | null
}

const API_URL = import.meta.env.VITE_API_URL ?? ''

let accessToken: string | null = null

export function apiUrl(path: string) {
  return `${API_URL}${path}`
}

async function errorMessage(response: Response, fallback: string) {
  try {
    const body = (await response.json()) as { detail?: string }
    return body.detail || fallback
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
  if (!response.ok) {
    throw new Error(await errorMessage(response, 'Could not sign in.'))
  }
  const body = (await response.json()) as { access: string }
  accessToken = body.access
  return fetchMe()
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
  return fetchMe()
}

export async function fetchMe(): Promise<Me> {
  const response = await fetch(apiUrl('/api/v1/auth/me/'), {
    credentials: 'include',
    headers: { Authorization: `Bearer ${accessToken ?? ''}` },
  })
  if (!response.ok) {
    throw new Error(await errorMessage(response, 'Could not load your account.'))
  }
  return (await response.json()) as Me
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
}
