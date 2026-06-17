import { useRef, useState } from 'react'
import { googleLoginStart, googleLoginResult } from '../lib/api'

const DEFAULT_API_URL = 'https://api.srvlab.dk/'

function openBrowser(url: string): void {
  const b = (window as unknown as { jarvisDesk?: { openExternal?: (u: string) => Promise<void> } }).jarvisDesk
  void b?.openExternal?.(url)
}

/** Første-gangs setup: log ind med Google ELLER server-URL + token (§12).
 *  Google-login henter Jarvis-tokenet automatisk fra serveren for en forud-
 *  oprettet konto; ingen self-service. Token-feltet er altid tilgængeligt. */
export function SetupScreen({ onSave }: { onSave: (cfg: { apiBaseUrl: string; authToken: string }) => void }) {
  const [url, setUrl] = useState('')
  const [token, setToken] = useState('')
  const [googleBusy, setGoogleBusy] = useState(false)
  const [googleMsg, setGoogleMsg] = useState('')
  const cancelRef = useRef(false)

  const loginWithGoogle = async () => {
    if (googleBusy) return
    const apiBaseUrl = url.trim() || DEFAULT_API_URL
    setGoogleBusy(true); setGoogleMsg('Åbner Google…'); cancelRef.current = false
    try {
      const start = await googleLoginStart(apiBaseUrl)
      if (!start.authorize_url || !start.nonce) {
        setGoogleMsg('Google-login er ikke konfigureret på serveren.'); setGoogleBusy(false); return
      }
      openBrowser(start.authorize_url)
      setGoogleMsg('Log ind i browseren — venter…')
      const nonce = start.nonce
      // Poll resultatet i op til ~2,5 min.
      for (let i = 0; i < 75 && !cancelRef.current; i++) {
        await new Promise((r) => setTimeout(r, 2000))
        const res = await googleLoginResult(apiBaseUrl, nonce)
          .catch((): Awaited<ReturnType<typeof googleLoginResult>> => ({ status: 'pending' }))
        if (res.status === 'ok' && res.token) {
          onSave({ apiBaseUrl, authToken: res.token })
          return
        }
        if (res.status === 'error') {
          setGoogleMsg(res.error === 'no_account'
            ? 'Ingen Jarvis-konto er knyttet til denne Google-konto.'
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
      <h1>Forbind til Jarvis</h1>
      <label>
        Server-URL
        <input aria-label="server" value={url} onChange={(e) => setUrl(e.target.value)} placeholder={DEFAULT_API_URL} />
      </label>

      <button type="button" className="setup-google" onClick={loginWithGoogle} disabled={googleBusy}>
        {googleBusy ? 'Forbinder…' : 'Log ind med Google'}
      </button>
      {googleMsg && <p className="setup-google-msg">{googleMsg}</p>}

      <div className="setup-or">eller med token</div>
      <label>
        Token
        <input aria-label="token" type="password" value={token} onChange={(e) => setToken(e.target.value)} />
      </label>
      <button type="button" onClick={() => onSave({ apiBaseUrl: url.trim() || DEFAULT_API_URL, authToken: token.trim() })}>
        Forbind
      </button>
    </div>
  )
}
