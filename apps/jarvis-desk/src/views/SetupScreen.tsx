import { useState } from 'react'

// Bjørns produktions-backend. Vises som PLACEHOLDER (ikke forudfyldt værdi) så
// de fleste brugere bare kan klikke Forbind → vi falder tilbage til default'en.
// Vil man ramme en anden instans (lokal LAN, dev-server) skriver man bare sin
// egen URL i det tomme felt. Forudfyldt værdi gav før concatenation-bug:
// brugerens input blev appendet på default'en (https://api.srvlab.dk/http://…).
const DEFAULT_API_URL = 'https://api.srvlab.dk/'

/** Første-gangs setup: server-URL + token. Vises når isConfigured=false. */
export function SetupScreen({ onSave }: { onSave: (cfg: { apiBaseUrl: string; authToken: string }) => void }) {
  const [url, setUrl] = useState('')
  const [token, setToken] = useState('')
  return (
    <div className="setup">
      <h1>Forbind til Jarvis</h1>
      <label>
        Server-URL
        <input aria-label="server" value={url} onChange={(e) => setUrl(e.target.value)} placeholder={DEFAULT_API_URL} />
      </label>
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
