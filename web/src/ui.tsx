import { useCallback, useEffect, useState, type FormEvent, type ReactNode } from 'react'
import { api } from './api'

export function useLoad<T>(path: string | null) {
  const [data, setData] = useState<T | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(Boolean(path))

  const reload = useCallback(async () => {
    if (!path) {
      setData(null)
      setLoading(false)
      return
    }
    setLoading(true)
    setError(null)
    try {
      setData(await api<T>(path))
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not load this page.')
    } finally {
      setLoading(false)
    }
  }, [path])

  useEffect(() => {
    void reload()
  }, [reload])

  return { data, error, loading, reload, setError }
}

export function PageHead({ title, lede }: { title: string; lede: string }) {
  return (
    <div className="page-head">
      <div>
        <h1>{title}</h1>
        <p className="lede">{lede}</p>
      </div>
    </div>
  )
}

export function Banner({ error }: { error: string | null }) {
  if (!error) return null
  return <p className="alert error">{error}</p>
}

export function Empty({ title, body }: { title: string; body: string }) {
  return (
    <section className="empty">
      <h2>{title}</h2>
      <p className="muted">{body}</p>
    </section>
  )
}

export function num(value: string | number | null | undefined) {
  if (value === null || value === undefined || value === '') return '—'
  const parsed = Number(value)
  if (Number.isNaN(parsed)) return String(value)
  return parsed.toLocaleString(undefined, { maximumFractionDigits: 2 })
}

export function Badge({ value }: { value: string }) {
  const tone =
    value === 'verified' || value === 'certified' || value === 'active' || value === 'pass'
      ? 'ok'
      : value === 'missing' || value === 'open' || value === 'preparing'
        ? 'warn'
        : value === 'prohibited' || value === 'fail' || value === 'suspended'
          ? 'danger'
          : ''
  return <span className={tone ? `badge ${tone}` : 'badge'}>{value.replaceAll('_', ' ')}</span>
}

export async function submitJson(
  event: FormEvent,
  action: () => Promise<void>,
  setError: (message: string | null) => void,
) {
  event.preventDefault()
  setError(null)
  try {
    await action()
  } catch (err) {
    setError(err instanceof Error ? err.message : 'Could not save that record.')
  }
}

export function results<T>(page: { results: T[] } | null) {
  return page?.results ?? []
}

export function LoadNote({ loading, children }: { loading: boolean; children: ReactNode }) {
  if (loading) return <p className="muted">Loading records…</p>
  return children
}

export { api }
