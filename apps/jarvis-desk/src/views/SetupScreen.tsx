import { useRef, useState } from 'react'
import { googleLoginStart, googleLoginResult } from '../lib/api'

// Produktions-backend er HARDCODED — ingen server-URL i login-skærmen (Bjørn
// 2026-06-17). Vil man ramme en anden instans sættes det via config/env, ikke i UI.
const API_URL = 'https://api.srvlab.dk/'

function openBrowser(url: string): void {
  const b = (window as unknown as { jarvisDesk?: { openExternal?: (u: string) => Promise<void> } }).jarvisDesk
  void b?.openExternal?.(url)
}

/** Første-gangs login: Google ELLER token (§12). Google-login henter Jarvis-
 *  tokenet automatisk fra serveren for en forud-oprettet konto. Server-URL er
 *  hardcoded — kun login-metode vælges her. */
export function SetupScreen({ onSave }: { onSave: (cfg: { apiBaseUrl: string; authToken: string }) => void }) {
  const [token, setToken] = useState('')
  const [googleBusy, setGoogleBusy] = useState(false)
  const [googleMsg, setGoogleMsg] = useState('')
  const cancelRef = useRef(false)

  const loginWithGoogle = async () => {
    if (googleBusy) return
    setGoogleBusy(true); setGoogleMsg('Åbner Google…'); cancelRef.current = false
    try {
      const start = await googleLoginStart(API_URL)
      if (!start.authorize_url || !start.nonce) {
        setGoogleMsg('Google-login er ikke konfigureret på serveren.'); setGoogleBusy(false); return
      }
      openBrowser(start.authorize_url)
      setGoogleMsg('Log ind i browseren — venter…')
      const nonce = start.nonce
      for (let i = 0; i < 75 && !cancelRef.current; i++) {
        await new Promise((r) => setTimeout(r, 2000))
        const res = await googleLoginResult(API_URL, nonce)
          .catch((): Awaited<ReturnType<typeof googleLoginResult>> => ({ status: 'pending' }))
        if (res.status === 'ok' && res.token) {
          onSave({ apiBaseUrl: API_URL, authToken: res.token })
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
      setGoogleMsg('Kunne ikke nå serveren.'); setGoogleBusy(false)
    }
  }

  return (
    <div className="setup">
      <h1>Log ind på J.A.R.V.I.S.</h1>

      <button type="button" className="setup-google" onClick={loginWithGoogle} disabled={googleBusy}>
        {googleBusy ? 'Forbinder…' : 'Log ind med Google'}
      </button>
      {googleMsg && <p className="setup-google-msg">{googleMsg}</p>}

      <div className="setup-or">eller med token</div>
      <label>
        Token
        <input aria-label="token" type="password" value={token} onChange={(e) => setToken(e.target.value)} />
      </label>
      <button type="button" onClick={() => onSave({ apiBaseUrl: API_URL, authToken: token.trim() })}>
        Forbind
      </button>
    </div>
  )
}
