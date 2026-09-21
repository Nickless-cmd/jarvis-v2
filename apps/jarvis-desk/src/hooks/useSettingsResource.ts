import { useEffect, useRef, useState } from 'react'
import type { ApiConfig } from '../lib/api'

export type ResourceStatus = 'missing' | 'loading' | 'ready' | 'error'

/** A failed read must never masquerade as an empty list or a disabled setting.
 * A new account/session hides old data immediately; late responses are ignored. */
export function useSettingsResource<T>(
  config: ApiConfig | undefined,
  load: (config: ApiConfig) => Promise<T>,
  scope = '',
) {
  const loader = useRef(load)
  loader.current = load
  const [revision, setRevision] = useState(0)
  const key = JSON.stringify([config?.apiBaseUrl, config?.authToken, scope, revision])
  const available = Boolean(config?.apiBaseUrl && config?.authToken)
  const [result, setResult] = useState<{ key: string; status: ResourceStatus; data: T | null }>({
    key: '', status: 'loading', data: null,
  })
  useEffect(() => {
    if (!available || !config) return
    let active = true
    setResult({ key, status: 'loading', data: null })
    void Promise.resolve().then(() => loader.current(config)).then(
      data => { if (active) setResult({ key, status: 'ready', data }) },
      () => { if (active) setResult({ key, status: 'error', data: null }) },
    )
    return () => { active = false }
    // `key` includes connection, scope and retry. Fresh config objects don't refetch.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [key, available])
  const status: ResourceStatus = !available ? 'missing' : result.key === key ? result.status : 'loading'
  return { status, data: status === 'ready' ? result.data : null, retry: () => setRevision(n => n + 1),
    setData: (data: T) => setResult(previous => previous.key === key ? { key, status: 'ready', data } : previous),
  }
}
