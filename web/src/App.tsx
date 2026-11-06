import { useEffect, useState, type FormEvent } from 'react'
import { AuthProvider } from './auth'
import { useAuth } from './useAuth'
import type { Me } from './api'

const NAV = [
  { path: '/', label: 'Dashboard' },
  { path: '/reports', label: 'Reports' },
  { path: '/activities', label: 'Farm Activities' },
  { path: '/settings', label: 'Settings' },
] as const

const ROLE_LABELS: Record<string, string> = {
  org_admin: 'Organization admin',
  manager: 'Manager',
  farmer: 'Farmer',
  inspector: 'Inspector',
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

function LoginScreen({ onSuccess }: { onSuccess: () => void }) {
  const { signIn, error } = useAuth()
  const [identifier, setIdentifier] = useState('')
  const [password, setPassword] = useState('')
  const [submitting, setSubmitting] = useState(false)

  async function onSubmit(event: FormEvent) {
    event.preventDefault()
    setSubmitting(true)
    try {
      await signIn(identifier, password)
      onSuccess()
    } catch {
      setSubmitting(false)
    }
  }

  return (
    <main className="login-page">
      <form className="login-card" onSubmit={onSubmit}>
        <Wordmark />
        <h1>Sign in</h1>
        <p className="lede">Manager console for farms, certification, and traceability.</p>
        <label>
          Email or FarmerID
          <input
            autoComplete="username"
            value={identifier}
            onChange={(event) => setIdentifier(event.target.value)}
            required
          />
        </label>
        <label>
          Password
          <input
            type="password"
            autoComplete="current-password"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            required
          />
        </label>
        {error ? <p className="form-error">{error}</p> : null}
        <button type="submit" disabled={submitting}>
          {submitting ? 'Signing in…' : 'Sign in'}
        </button>
        <p className="admin-note">
          Farmers are added by an administrator. Contact your administrator for access.
        </p>
      </form>
    </main>
  )
}

function EmptyState({ title, body }: { title: string; body: string }) {
  return (
    <section className="empty">
      <h2>{title}</h2>
      <p>{body}</p>
    </section>
  )
}

function Dashboard({ me }: { me: Me }) {
  const role = me.organization ? ROLE_LABELS[me.organization.role] ?? me.organization.role : null
  return (
    <section>
      <h1>Dashboard</h1>
      <p className="lede">
        Signed in as {me.email}
        {me.farmer_id ? ` · ${me.farmer_id}` : ''}
        {me.organization ? ` · ${me.organization.name}` : ''}
        {role ? ` · ${role}` : ''}
      </p>
      <EmptyState
        title="No farm records yet"
        body="Farmers, fields, and harvests will show up here as those phases are added."
      />
    </section>
  )
}

function Shell() {
  const { status, me, signOut } = useAuth()
  const { path, go } = usePath()

  if (status === 'loading') {
    return (
      <main className="login-page">
        <p className="loading">Checking your session…</p>
      </main>
    )
  }

  if (status !== 'authenticated' || !me) {
    return <LoginScreen onSuccess={() => go('/')} />
  }

  let page = <Dashboard me={me} />
  if (path === '/reports') {
    page = (
      <EmptyState
        title="Reports"
        body="Yield, certification, and batch reports are not available in this scaffold yet."
      />
    )
  } else if (path === '/activities') {
    page = (
      <EmptyState
        title="Farm Activities"
        body="Production records and field work are not available in this scaffold yet."
      />
    )
  } else if (path === '/settings') {
    page = (
      <EmptyState
        title="Settings"
        body="Organization settings are not available in this scaffold yet."
      />
    )
  }

  return (
    <div className="shell">
      <aside className="sidebar">
        <Wordmark />
        <nav>
          {NAV.map((item) => (
            <button
              key={item.path}
              type="button"
              className={path === item.path || (item.path === '/' && path === '') ? 'nav active' : 'nav'}
              onClick={() => go(item.path)}
            >
              {item.label}
            </button>
          ))}
        </nav>
      </aside>
      <div className="main">
        <header className="topbar">
          <span>{me.organization?.name ?? 'No organization'}</span>
          <button type="button" className="ghost" onClick={() => void signOut()}>
            Sign out
          </button>
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
