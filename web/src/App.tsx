import { useEffect, useState, type FormEvent } from 'react'
import { confirmPasswordReset, requestPasswordReset } from './api'
import { AuthProvider } from './auth'
import { useAuth } from './useAuth'
import {
  AssistantPage,
  CompliancePage,
  DashboardPage,
  FarmersPage,
  FarmsPage,
  InspectionsPage,
  InventoryPage,
  ProductionPage,
  ReportsPage,
  SettingsPage,
  TracePage,
  TrainingPage,
} from './pages'

const NAV = [
  ['/', 'Dashboard'],
  ['/farmers', 'Farmers'],
  ['/farms', 'Farms'],
  ['/compliance', 'Compliance'],
  ['/inventory', 'Inventory'],
  ['/production', 'Production'],
  ['/traceability', 'Traceability'],
  ['/inspections', 'Inspections'],
  ['/training', 'Training'],
  ['/reports', 'Reports'],
  ['/assistant', 'Assistant'],
  ['/settings', 'Settings'],
] as const

const ROLE_LABELS: Record<string, string> = {
  org_admin: 'Organization admin',
  field_officer: 'Field officer',
  manager: 'Farm manager',
  farmer: 'Farmer',
  inspector: 'Inspector',
  certification_officer: 'Certification officer',
}

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

function Wordmark() {
  return (
    <span className="wordmark">
      <span className="mark" aria-hidden="true" />
      FarmMate
    </span>
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
    <main className="login-page">
      <form className="login-card" onSubmit={(event) => void onSubmit(event)}>
        <Wordmark />
        <h1>Sign in</h1>
        <p className="lede">Farm records, compliance, and traceability for your organization.</p>
        <label className="field">
          Email or FarmerID
          <input autoComplete="username" value={identifier} onChange={(event) => setIdentifier(event.target.value)} required />
        </label>
        <label className="field">
          Password
          <input type="password" autoComplete="current-password" value={password} onChange={(event) => setPassword(event.target.value)} required />
        </label>
        {error ? <p className="alert error">{error}</p> : null}
        <button type="submit" disabled={submitting}>{submitting ? 'Signing in…' : 'Sign in'}</button>
        <p className="muted">
          <button type="button" className="text-link" onClick={() => go('/register')}>Register an organization</button>
          {' · '}
          <button type="button" className="text-link" onClick={() => go('/reset')}>Reset password</button>
        </p>
      </form>
    </main>
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
    <main className="login-page">
      <form className="login-card" onSubmit={(event) => void onSubmit(event)}>
        <Wordmark />
        <h1>Register an organization</h1>
        <p className="lede">This creates the first administrator. Farmers are added after you sign in.</p>
        <label className="field">Organization<input name="organization_name" required /></label>
        <label className="field">First name<input name="first_name" required /></label>
        <label className="field">Last name<input name="last_name" /></label>
        <label className="field">Email<input name="email" type="email" required /></label>
        <label className="field">Password<input name="password" type="password" required /></label>
        {error ? <p className="alert error">{error}</p> : null}
        <button type="submit" disabled={submitting}>{submitting ? 'Creating…' : 'Create organization'}</button>
        <button type="button" className="text-link" onClick={() => go('/login')}>Back to sign in</button>
      </form>
    </main>
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
    <main className="login-page">
      <div className="login-card">
        <Wordmark />
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
        <button type="button" className="text-link" onClick={() => go('/login')}>Back to sign in</button>
      </div>
    </main>
  )
}

function Shell() {
  const { status, me, signOut, refresh } = useAuth()
  const { path, go } = usePath()

  if (status === 'loading') {
    return <main className="login-page"><p className="muted">Checking your session…</p></main>
  }
  if (status !== 'authenticated' || !me) {
    if (path === '/register') return <RegisterScreen go={go} />
    if (path === '/reset') return <ResetScreen go={go} />
    return <LoginScreen go={go} />
  }

  const role = me.organization?.role ?? ''
  let page = <DashboardPage />
  if (path === '/farmers') page = <FarmersPage />
  else if (path === '/farms') page = <FarmsPage />
  else if (path === '/compliance') page = <CompliancePage role={role} />
  else if (path === '/inventory') page = <InventoryPage />
  else if (path === '/production') page = <ProductionPage />
  else if (path === '/traceability') page = <TracePage />
  else if (path === '/inspections') page = <InspectionsPage />
  else if (path === '/training') page = <TrainingPage />
  else if (path === '/reports') page = <ReportsPage />
  else if (path === '/assistant') page = <AssistantPage />
  else if (path === '/settings') page = <SettingsPage role={role} onRefresh={refresh} />

  return (
    <div className="shell">
      <aside className="sidebar">
        <Wordmark />
        <nav>
          {NAV.map(([href, label]) => (
            <button key={href} type="button" className={path === href ? 'nav active' : 'nav'} onClick={() => go(href)}>
              {label}
            </button>
          ))}
        </nav>
      </aside>
      <div className="main">
        <header className="topbar">
          <span>
            {me.organization?.name ?? 'No organization'}
            {role ? ` · ${ROLE_LABELS[role] ?? role}` : ''}
          </span>
          <button type="button" className="ghost" onClick={() => void signOut()}>Sign out</button>
        </header>
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
