import { useState } from 'react'

/** Første-gangs setup: server-URL + token. Vises når isConfigured=false. */
export function SetupScreen({ onSave }: { onSave: (cfg: { apiBaseUrl: string; authToken: string }) => void }) {
  const [url, setUrl] = useState('')
  const [token, setToken] = useState('')
  return (
    <div className="setup">
      <h1>Forbind til Jarvis</h1>
      <label>
        Server-URL
        <input aria-label="server" value={url} onChange={(e) => setUrl(e.target.value)} placeholder="http://10.0.0.39" />
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
