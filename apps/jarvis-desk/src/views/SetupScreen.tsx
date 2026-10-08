import { useEffect, useRef, useState } from 'react'
import { googleLoginStart, googleLoginResult } from '../lib/api'

// Produktions-backend er HARDCODED — ingen server-URL i login-skærmen (Bjørn
// 2026-06-17). Vil man ramme en anden instans sættes det via config/env, ikke i UI.
const DESK_API_URL = 'https://api.srvlab.dk/'

function apiUrl(): string {
  return (window as Window & { jarvisDesk?: unknown }).jarvisDesk
    ? DESK_API_URL
    : new URL('/', window.location.origin).toString()
}

function openBrowser(url: string): void {
  const b = (window as unknown as { jarvisDesk?: { openExternal?: (u: string) => Promise<void> } }).jarvisDesk
  if (b?.openExternal) void b.openExternal(url)
}

/** Første-gangs login: Google ELLER token (§12). Google-login henter Jarvis-
 *  tokenet automatisk fra serveren for en forud-oprettet konto. Server-URL er
 *  hardcoded — kun login-metode vælges her. */
export function SetupScreen({ onSave }: { onSave: (cfg: { apiBaseUrl: string; authToken: string }) => void }) {
  const [token, setToken] = useState('')
  const [googleBusy, setGoogleBusy] = useState(false)
  const [googleMsg, setGoogleMsg] = useState('')
  const cancelRef = useRef(false)
  useEffect(() => () => { cancelRef.current = true }, [])

  const loginWithGoogle = async () => {
    if (googleBusy) return
    setGoogleBusy(true); setGoogleMsg('Åbner Google…'); cancelRef.current = false
    // Browser popups must be opened during the click, before the async API call.
    const isWeb = !(window as Window & { jarvisDesk?: unknown }).jarvisDesk
    const popup = isWeb ? window.open('about:blank', '_blank') : null
    if (popup) popup.opener = null
    try {
      const base = apiUrl()
      const start = await googleLoginStart(base)
      if (!start.authorize_url || !start.nonce) {
        popup?.close()
        setGoogleMsg('Google-login er ikke konfigureret på serveren.'); setGoogleBusy(false); return
      }
      if (isWeb && !popup) {
        setGoogleMsg('Browseren blokerede login-vinduet. Tillad popups og prøv igen.')
        setGoogleBusy(false)
        return
      }
      if (popup) popup.location.href = start.authorize_url
      else openBrowser(start.authorize_url)
      setGoogleMsg('Log ind i browseren — venter…')
      const nonce = start.nonce
      for (let i = 0; i < 75 && !cancelRef.current; i++) {
        await new Promise((r) => setTimeout(r, 2000))
        const res = await googleLoginResult(base, nonce)
          .catch((): Awaited<ReturnType<typeof googleLoginResult>> => ({ status: 'pending' }))
        if (res.status === 'ok' && res.token) {
          popup?.close()
          onSave({ apiBaseUrl: base, authToken: res.token })
          return
        }
        if (res.status === 'error') {
          setGoogleMsg(res.error === 'no_account'
            ? 'Ingen J.A.R.V.I.S.-konto er knyttet til denne Google-konto.'
            : 'Google-login mislykkedes.')
          setGoogleBusy(false); return
        }
      }
      setGoogleMsg('Timeout — prøv igen.'); setGoogleBusy(false)
    } catch {
      popup?.close()
      setGoogleMsg('Kunne ikke nå serveren.'); setGoogleBusy(false)
    }
  }

  return (
    <div className="setup">
      <h1>Velkommen til Jarvis</h1>
      <p>Tal med Jarvis, arbejd med kode, og følg dine opgaver ét sted.</p>
      <p className="settings-hint">Log ind for at hente dine samtaler og indstillinger. Bagefter får du en kort introduktion.</p>

      <button type="button" className="setup-google" onClick={loginWithGoogle} disabled={googleBusy}>
        {googleBusy ? 'Forbinder…' : 'Log ind med Google'}
      </button>
      {googleMsg && <p className="setup-google-msg">{googleMsg}</p>}

      <details className="settings-details"><summary>Log ind med et adgangstoken</summary>
      <label>
        Token
        <input autoComplete="off" aria-label="token" type="password" value={token} onChange={(e) => setToken(e.target.value)} />
      </label>
      <button type="button" disabled={!token.trim()} onClick={() => onSave({ apiBaseUrl: apiUrl(), authToken: token.trim() })}>
        Forbind
      </button>
      </details>
    </div>
  )
}
