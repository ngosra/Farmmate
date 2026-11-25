import { createContext } from 'react'
import type { Me } from './api'

export type AuthStatus = 'loading' | 'anonymous' | 'authenticated'

export type AuthState = {
  status: AuthStatus
  me: Me | null
  error: string | null
  signIn: (identifier: string, password: string) => Promise<void>
  signUp: (payload: {
    organization_name: string
    email: string
    password: string
    first_name: string
    last_name: string
  }) => Promise<void>
  signOut: () => Promise<void>
  refresh: () => Promise<void>
}

export const AuthContext = createContext<AuthState | null>(null)
