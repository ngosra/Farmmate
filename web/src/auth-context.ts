import { createContext } from 'react'
import type { Me } from './api'

export type AuthStatus = 'loading' | 'anonymous' | 'authenticated'

export type AuthState = {
  status: AuthStatus
  me: Me | null
  error: string | null
  signIn: (identifier: string, password: string) => Promise<void>
  signOut: () => Promise<void>
}

export const AuthContext = createContext<AuthState | null>(null)
