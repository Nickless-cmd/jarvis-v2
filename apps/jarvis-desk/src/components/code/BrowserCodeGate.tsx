import { useCallback, useEffect, useState, type ReactNode } from 'react'
import { useSettings } from '../../hooks/useSettings'
import type { ApiConfig } from '../../lib/api'
import {
  anmodOmBrowserAdgang,
  hentBrowserAnmodningStatus,
  hentEnheder,
} from '../../lib/enheder'

const REQUEST_KEY = 'jarvis-desk:browser-code-request'

type Phase = 'checking' | 'pending' | 'denied' | 'expired' | 'error' | 'allowed'

function browserName(): string {
  const platform = String(navigator.platform || 'denne enhed').trim()
  return `Browser på ${platform}`
}

export function BrowserCodeGate({ config, children }: { config: ApiConfig; children: ReactNode }) {
  const { update } = useSettings()
  const [phase, setPhase] = useState<Phase>('checking')
  const [requestId, setRequestId] = useState(() => {
    try { return localStorage.getItem(REQUEST_KEY) || '' } catch { return '' }
  })
  const [error, setError] = useState('')

  const requestAccess = useCallback(async () => {
    setPhase('checking'); setError('')
    const overview = await hentEnheder(config)
    if (!overview.ok) { setPhase('error'); setError(overview.fejl); return }
    if (!overview.data.kraev_aktivt || overview.data.denne.kode_tilladt) {
      setPhase('allowed')
      return
    }
    const created = await anmodOmBrowserAdgang(config, browserName())
    if (!created.ok) { setPhase('error'); setError(created.fejl); return }
    const id = String(created.data.request_id || '')
    try { localStorage.setItem(REQUEST_KEY, id) } catch { /* request still lives server-side */ }
    setRequestId(id)
    setPhase('pending')
  }, [config.apiBaseUrl, config.authToken])

  useEffect(() => {
    if (phase !== 'checking') return
    if (!requestId) { void requestAccess(); return }
    setPhase('pending')
  }, [phase, requestId, requestAccess])

  useEffect(() => {
    if (!requestId || phase !== 'pending') return
    let alive = true
    const poll = async () => {
      const result = await hentBrowserAnmodningStatus(config, requestId)
      if (!alive) return
      if (!result.ok) { setPhase('error'); setError(result.fejl); return }
      const state = result.data.state
      if (state === 'approved' && result.data.token) {
        try { localStorage.removeItem(REQUEST_KEY) } catch { /* harmless */ }
        await update({ authToken: result.data.token })
        if (alive) setPhase('allowed')
      } else if (state === 'denied' || state === 'expired') {
        try { localStorage.removeItem(REQUEST_KEY) } catch { /* harmless */ }
        setRequestId('')
        setPhase(state)
      }
    }
    void poll()
    const timer = window.setInterval(() => { void poll() }, 2000)
    return () => { alive = false; window.clearInterval(timer) }
  }, [config.apiBaseUrl, config.authToken, phase, requestId, update])

  if (phase === 'allowed') return <>{children}</>
  return (
    <section className="browser-code-gate" role="status" aria-live="polite">
      <div className="browser-code-gate-card">
        <h2>Godkend Code Mode i Jarvis Desk</h2>
        {phase === 'checking' ? <p>Kontrollerer denne browser…</p> : null}
        {phase === 'pending' ? (
          <p>Anmodningen er sendt. Åbn Jarvis Desk på din betroede computer og vælg <strong>Godkend</strong>. Denne side åbner automatisk bagefter.</p>
        ) : null}
        {phase === 'denied' ? <p>Jarvis Desk afviste anmodningen.</p> : null}
        {phase === 'expired' ? <p>Anmodningen udløb, før den blev godkendt.</p> : null}
        {phase === 'error' ? <p className="enheder-fejl">{error || 'Godkendelsen kunne ikke gennemføres.'}</p> : null}
        {(phase === 'denied' || phase === 'expired' || phase === 'error') ? (
          <button type="button" className="account-google-btn" onClick={() => {
            try { localStorage.removeItem(REQUEST_KEY) } catch { /* harmless */ }
            setRequestId(''); void requestAccess()
          }}>Send ny anmodning</button>
        ) : null}
        <p className="account-google-hint">Der bruges ingen TOTP-kode. Godkendelsen kommer fra den Desk-installation, der allerede er tilføjet.</p>
      </div>
    </section>
  )
}
