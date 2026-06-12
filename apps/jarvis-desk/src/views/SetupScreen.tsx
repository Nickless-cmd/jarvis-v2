import { useState } from 'react'

// Bjørns produktions-backend. Pre-udfyldt så de fleste brugere bare kan
// klikke videre. Vil man ramme en anden instans (lokal LAN, dev-server)
// sletter man feltet og skriver sin egen URL.
const DEFAULT_API_URL = 'https://api.srvlab.dk/'

/** Første-gangs setup: server-URL + token. Vises når isConfigured=false. */
export function SetupScreen({ onSave }: { onSave: (cfg: { apiBaseUrl: string; authToken: string }) => void }) {
  const [url, setUrl] = useState(DEFAULT_API_URL)
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
      <button type="button" onClick={() => onSave({ apiBaseUrl: url.trim(), authToken: token.trim() })}>
        Forbind
      </button>
    </div>
  )
}
