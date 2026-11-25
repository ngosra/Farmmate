import { useEffect, useState, type FormEvent, type ReactNode } from 'react'
import { confirmPasswordReset, requestPasswordReset } from './api'
import { AuthProvider } from './auth'
import { useAuth } from './useAuth'
import {
  AssistantPage,
  CompliancePage,
  DashboardPage,
  FarmActivitiesPage,
  FarmersPage,
  FarmsPage,
  InspectionsPage,
  InventoryPage,
  ProductionPage,
  NotificationsPage,
  ReportsPage,
  SettingsPage,
  TracePage,
  TrainingPage,
} from './pages'

const ACTIVITY_LINKS = [
  ['/activities', 'Overview'],
  ['/farmers', 'Farmers'],
  ['/farms', 'Land parcels'],
  ['/inspections', 'Inspections'],
  ['/inventory', 'Inputs and seed'],
  ['/production', 'Production and harvest'],
  ['/traceability', 'Traceability'],
  ['/training', 'Training'],
  ['/compliance', 'Certification'],
] as const

function usePath() {
  const [path, setPath] = useState(window.location.pathname)
  useEffect(() => {
    const onPop = () => setPath(window.location.pathname)
    window.addEventListener('popstate', onPop)
    return () => window.removeEventListener('popstate', onPop)
  }, [])
  function go(next: string) {
    window.history.pushState({}, '', next)
    setPath(next)
  }
  return { path, go }
}

function FarmerArt() {
  return (
    <svg viewBox="0 0 320 360" role="img" aria-label="Line drawing of a farmer">
      <g fill="none" stroke="white" strokeWidth="6" strokeLinecap="round" strokeLinejoin="round">
        <path d="M70 118c8-46 58-78 108-62 28 8 48 36 46 66" />
        <path d="M58 132h196c8 18 4 36-10 46H74c-16-10-22-28-16-46z" />
        <circle cx="156" cy="168" r="58" />
        <path d="M132 166c6 8 14 8 20 0M176 166c6 8 14 8 20 0" />
        <path d="M138 196c12 16 32 16 46 0" />
        <path d="M92 230c18 18 40 28 64 28s48-10 66-28" />
        <path d="M78 250c-16 28-18 70-8 96h52l10-46 18 46h46l16-52 22 52h40c8-30 2-68-16-96" />
        <path d="M118 292h28v34c0 16-8 28-22 28s-22-12-22-28v-18" />
        <path d="M206 248v78M96 248v70" />
      </g>
    </svg>
  )
}

function AuthFrame({ children }: { children: ReactNode }) {
  return (
    <main className="auth-split">
      <section className="auth-art"><FarmerArt /></section>
      <section className="auth-panel">{children}</section>
    </main>
  )
}

function LoginScreen({ go }: { go: (path: string) => void }) {
  const { signIn, error } = useAuth()
  const [identifier, setIdentifier] = useState('')
  const [password, setPassword] = useState('')
  const [submitting, setSubmitting] = useState(false)

  async function onSubmit(event: FormEvent) {
    event.preventDefault()
    setSubmitting(true)
    try {
      await signIn(identifier, password)
      go('/')
    } catch {
      setSubmitting(false)
    }
  }

  return (
    <AuthFrame>
      <form className="auth-form" onSubmit={(event) => void onSubmit(event)}>
        <h1>Log In</h1>
        <label className="field">
          Email or FarmerID
          <input autoComplete="username" value={identifier} onChange={(event) => setIdentifier(event.target.value)} required />
        </label>
        <label className="field">
          Password
          <input type="password" autoComplete="current-password" value={password} onChange={(event) => setPassword(event.target.value)} required />
        </label>
        {error ? <p className="alert error">{error}</p> : null}
        <button type="submit" disabled={submitting}>{submitting ? 'Signing in…' : 'Log In'}</button>
        <button type="button" className="text-link" onClick={() => go('/register')}>Not on FarmMate yet? Join now &gt;</button>
        <button type="button" className="text-link" onClick={() => go('/reset')}>Reset password</button>
      </form>
    </AuthFrame>
  )
}

function RegisterScreen({ go }: { go: (path: string) => void }) {
  const { signUp, error } = useAuth()
  const [submitting, setSubmitting] = useState(false)

  async function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const data = new FormData(event.currentTarget)
    setSubmitting(true)
    try {
      await signUp({
        organization_name: String(data.get('organization_name') || ''),
        first_name: String(data.get('first_name') || ''),
        last_name: String(data.get('last_name') || ''),
        email: String(data.get('email') || ''),
        password: String(data.get('password') || ''),
      })
      go('/')
    } catch {
      setSubmitting(false)
    }
  }

  return (
    <AuthFrame>
      <form className="auth-form" onSubmit={(event) => void onSubmit(event)}>
        <h1>Join FarmMate</h1>
        <p className="lede">This creates the organization and its first administrator.</p>
        <label className="field">Organization<input name="organization_name" required /></label>
        <label className="field">First name<input name="first_name" required /></label>
        <label className="field">Last name<input name="last_name" /></label>
        <label className="field">Email<input name="email" type="email" required /></label>
        <label className="field">Password<input name="password" type="password" required /></label>
        {error ? <p className="alert error">{error}</p> : null}
        <button type="submit" disabled={submitting}>{submitting ? 'Creating…' : 'Create organization'}</button>
        <button type="button" className="text-link" onClick={() => go('/login')}>Already onboard? Log in here &gt;</button>
      </form>
    </AuthFrame>
  )
}

function ResetScreen({ go }: { go: (path: string) => void }) {
  const [message, setMessage] = useState('')
  const [error, setError] = useState('')

  async function onRequest(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setError('')
    try {
      const result = await requestPasswordReset(String(new FormData(event.currentTarget).get('email') || ''))
      setMessage(result.detail)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not request a reset.')
    }
  }

  async function onConfirm(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setError('')
    const data = new FormData(event.currentTarget)
    try {
      await confirmPasswordReset(String(data.get('token') || ''), String(data.get('password') || ''))
      setMessage('Password updated. You can sign in.')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not update the password.')
    }
  }

  return (
    <AuthFrame>
      <div className="auth-form">
        <h1>Reset password</h1>
        <p className="lede">If the email matches an account, the reset token is sent to that address.</p>
        <form onSubmit={(event) => void onRequest(event)} className="stack">
          <label className="field">Email<input name="email" type="email" required /></label>
          <button type="submit">Send reset</button>
        </form>
        <form onSubmit={(event) => void onConfirm(event)} className="stack">
          <label className="field">Token<input name="token" required /></label>
          <label className="field">New password<input name="password" type="password" required /></label>
          <button type="submit" className="secondary">Update password</button>
        </form>
        {message ? <p className="alert">{message}</p> : null}
        {error ? <p className="alert error">{error}</p> : null}
        <button type="button" className="text-link" onClick={() => go('/login')}>Back to log in</button>
      </div>
    </AuthFrame>
  )
}

function Shell() {
  const { status, me, signOut, refresh } = useAuth()
  const { path, go } = usePath()

  if (status === 'loading') {
    return <main className="auth-panel"><p className="muted">Checking your session…</p></main>
  }
  if (status !== 'authenticated' || !me) {
    if (path === '/register') return <RegisterScreen go={go} />
    if (path === '/reset') return <ResetScreen go={go} />
    return <LoginScreen go={go} />
  }

  const role = me.organization?.role ?? ''
  const activityOpen = ACTIVITY_LINKS.some(([href]) => href === path)
  let page = <DashboardPage />
  if (path === '/activities') page = <FarmActivitiesPage go={go} />
  else if (path === '/farmers') page = <FarmersPage />
  else if (path === '/farms') page = <FarmsPage />
  else if (path === '/compliance') page = <CompliancePage role={role} />
  else if (path === '/inventory') page = <InventoryPage />
  else if (path === '/production') page = <ProductionPage />
  else if (path === '/traceability') page = <TracePage />
  else if (path === '/inspections') page = <InspectionsPage />
  else if (path === '/training') page = <TrainingPage />
  else if (path === '/reports') page = <ReportsPage />
  else if (path === '/assistant') page = <AssistantPage />
  else if (path === '/notifications') page = <NotificationsPage />
  else if (path === '/settings') page = <SettingsPage role={role} onRefresh={refresh} />

  const hello = me.first_name || me.email

  return (
    <div className="shell">
      <aside className="sidebar">
        <p className="hello">Hello {hello},</p>
        <nav>
          <button type="button" className={path === '/' ? 'nav active' : 'nav'} onClick={() => go('/')}>Dashboard</button>
          <button type="button" className={path === '/reports' ? 'nav active' : 'nav'} onClick={() => go('/reports')}>Reports</button>
          <button type="button" className={activityOpen ? 'nav active' : 'nav'} onClick={() => go('/activities')}>Farm Activities</button>
          {activityOpen ? (
            <div className="side-group">
              {ACTIVITY_LINKS.map(([href, label]) => (
                <button key={href} type="button" className={path === href ? 'nav-sub active' : 'nav-sub'} onClick={() => go(href)}>
                  {label}
                </button>
              ))}
            </div>
          ) : null}
          <button type="button" className={path === '/assistant' ? 'nav active' : 'nav'} onClick={() => go('/assistant')}>FarmMate AI</button>
          <button type="button" className={path === '/settings' ? 'nav active' : 'nav'} onClick={() => go('/settings')}>Settings</button>
        </nav>
        <div className="sidebar-foot">
          <button type="button" className={path === '/notifications' ? 'nav active' : 'nav'} onClick={() => go('/notifications')}>Notifications</button>
          <button type="button" className="nav" onClick={() => void signOut()}>Sign Out</button>
        </div>
      </aside>
      <div className="main">
        <main className="content">{page}</main>
      </div>
    </div>
  )
}

export default function App() {
  return (
    <AuthProvider>
      <Shell />
    </AuthProvider>
  )
}
