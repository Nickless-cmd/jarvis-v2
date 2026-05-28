import { useState } from 'react'
import { Flame, CheckCircle2, AlertCircle, Loader2 } from 'lucide-react'

/**
 * First-run setup screen. Shows when the app config doesn't have a
 * valid `apiBaseUrl` + `authToken` pair yet — i.e. the user just
 * installed JarvisX and hasn't been bootstrapped.
 *
 * Flow:
 *   1. Default apiBaseUrl pre-filled to https://api.srvlab.dk (Bjørn's
 *      production endpoint). User can override for self-hosted or
 *      different Jarvis instances.
 *   2. User pastes the bearer token they were given.
 *   3. We hit /api/auth/whoami-token to validate — confirms the
 *      backend recognizes the token + tells us the user_id + role
 *      we're bound to. No identity is forged: if the backend rejects
 *      the token, we show the error and let them retry.
 *   4. On success we persist apiBaseUrl + authToken + metadata to
 *      ~/.config/jarvisx/config.json (via electron IPC), then reload
 *      so the rest of the app boots fully authenticated.
 *
 * Why not skip-able: without auth the app can't reach a remote Jarvis
 * (auth_required=true rejects unauthenticated requests). Forcing setup
 * is the price of "send Mikkel a JarvisX.exe + token" working at all.
 */
export function SetupScreen({ onComplete }: { onComplete: () => void }) {
  const [apiBaseUrl, setApiBaseUrl] = useState('https://api.srvlab.dk')
  const [token, setToken] = useState('')
  const [displayName, setDisplayName] = useState('')
  const [status, setStatus] = useState<
    { kind: 'idle' } |
    { kind: 'validating' } |
    { kind: 'error'; message: string } |
    { kind: 'success'; userId: string; role: string; expiresAt: string }
  >({ kind: 'idle' })

  async function validate() {
    const url = apiBaseUrl.trim().replace(/\/$/, '')
    const tok = token.trim()
    if (!url) {
      setStatus({ kind: 'error', message: 'API URL er påkrævet' })
      return
    }
    if (!tok) {
      setStatus({ kind: 'error', message: 'API token er påkrævet' })
      return
    }
    setStatus({ kind: 'validating' })
    // Route via the Electron main process — the renderer's fetch() would
    // trigger a CORS preflight (file:// → https://...) that FastAPI doesn't
    // handle, manifesting as "Kunne ikke kontakte backend" even when the
    // backend is perfectly reachable. main.ts uses Node's fetch which has
    // no CORS layer.
    if (!window.jarvisx?.validateToken) {
      setStatus({
        kind: 'error',
        message: 'JarvisX-bridge mangler validateToken — geninstaller app-bygget.',
      })
      return
    }
    try {
      const r = await window.jarvisx.validateToken(url, tok)
      if (!r.ok) {
        setStatus({
          kind: 'error',
          message: `Kunne ikke kontakte backend: ${r.error}. Tjek at api URL'en er korrekt og du har netværk.`,
        })
        return
      }
      if (r.http_status >= 400) {
        setStatus({
          kind: 'error',
          message: `Backend afviste tokenen (HTTP ${r.http_status}). Tjek at den er korrekt og ikke udløbet.`,
        })
        return
      }
      if (!r.valid) {
        setStatus({
          kind: 'error',
          message: `Token ikke valid: ${r.error || 'ukendt grund'}`,
        })
        return
      }
      const userId = String(r.user_id || '')
      const role = String(r.role || 'member')
      const expiresAt = r.expires_at
        ? new Date(r.expires_at * 1000).toISOString()
        : ''
      setStatus({ kind: 'success', userId, role, expiresAt })

      // Derive a friendly display name if the user didn't supply one:
      // capitalize a short user_id (e.g. "mikkel" → "Mikkel"), else fall
      // back to "User <last 4 digits>" for snowflake-style ids.
      const fallbackName = displayName.trim() || (() => {
        if (/^[a-zæøåA-ZÆØÅ]{2,20}$/.test(userId)) {
          return userId.charAt(0).toUpperCase() + userId.slice(1)
        }
        return `User ${userId.slice(-4)}`
      })()
      await window.jarvisx.setConfig({
        apiBaseUrl: url,
        userId,
        userName: fallbackName,
        authToken: tok,
        authTokenUserId: userId,
        authTokenRole: role,
        authTokenExpiresAt: expiresAt,
      } as Partial<{ apiBaseUrl: string; userId: string; userName: string; authToken: string; authTokenUserId: string; authTokenRole: string; authTokenExpiresAt: string }>)
      // Give the success screen a moment to be seen, then continue
      setTimeout(onComplete, 1200)
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : String(e)
      setStatus({
        kind: 'error',
        message: `Uventet fejl: ${msg}.`,
      })
    }
  }

  return (
    <div className="flex h-full min-h-0 flex-col items-center justify-center bg-bg0 px-6">
      <div className="w-full max-w-md">
        <div className="mb-6 flex items-center gap-3">
          <Flame size={28} className="text-accent" />
          <div>
            <h1 className="text-lg font-semibold tracking-tight">Velkommen til JarvisX</h1>
            <p className="text-[12px] text-fg3">
              Forbind til din Jarvis-instans for at komme i gang
            </p>
          </div>
        </div>

        <div className="space-y-3">
          <label className="block">
            <span className="text-[11px] uppercase tracking-wider text-fg2">API URL</span>
            <input
              type="url"
              value={apiBaseUrl}
              onChange={(e) => setApiBaseUrl(e.target.value)}
              disabled={status.kind === 'validating'}
              placeholder="https://api.srvlab.dk"
              className="mt-1 w-full rounded border border-line bg-bg1 px-3 py-2 font-mono text-[13px] text-fg outline-none focus:border-accent disabled:opacity-50"
            />
          </label>

          <label className="block">
            <span className="text-[11px] uppercase tracking-wider text-fg2">API Token</span>
            <textarea
              value={token}
              onChange={(e) => setToken(e.target.value)}
              disabled={status.kind === 'validating'}
              placeholder="eyJhbGc..."
              rows={3}
              className="mt-1 w-full resize-none rounded border border-line bg-bg1 px-3 py-2 font-mono text-[11px] text-fg outline-none focus:border-accent disabled:opacity-50"
            />
            <span className="mt-1 block text-[10px] text-fg3">
              Sendt til dig af din Jarvis-administrator. Genereret med{' '}
              <code className="text-fg2">scripts/mint_jarvisx_token.py</code>
            </span>
          </label>

          <label className="block">
            <span className="text-[11px] uppercase tracking-wider text-fg2">
              Dit navn <span className="text-fg3 normal-case">(valgfrit — Jarvis kalder dig dette)</span>
            </span>
            <input
              type="text"
              value={displayName}
              onChange={(e) => setDisplayName(e.target.value)}
              disabled={status.kind === 'validating'}
              placeholder="Fx Mikkel, Bjørn, eller dit kaldenavn"
              maxLength={40}
              className="mt-1 w-full rounded border border-line bg-bg1 px-3 py-2 text-[13px] text-fg outline-none focus:border-accent disabled:opacity-50"
            />
          </label>

          {status.kind === 'error' && (
            <div className="flex items-start gap-2 rounded border border-danger/30 bg-danger/10 p-2.5 text-[12px] text-danger">
              <AlertCircle size={14} className="mt-0.5 flex-shrink-0" />
              <span>{status.message}</span>
            </div>
          )}

          {status.kind === 'success' && (
            <div className="flex items-start gap-2 rounded border border-ok/30 bg-ok/10 p-2.5 text-[12px] text-ok">
              <CheckCircle2 size={14} className="mt-0.5 flex-shrink-0" />
              <div>
                <div className="font-semibold">Forbundet som {status.userId}</div>
                <div className="text-[11px] text-ok/70">
                  Rolle: {status.role}
                  {status.expiresAt && ` · udløber ${status.expiresAt.slice(0, 10)}`}
                </div>
              </div>
            </div>
          )}

          <button
            onClick={validate}
            disabled={status.kind === 'validating' || status.kind === 'success'}
            className="flex w-full items-center justify-center gap-2 rounded bg-accent px-4 py-2 text-[13px] font-semibold text-bg0 hover:bg-accent/90 disabled:opacity-50"
          >
            {status.kind === 'validating' && <Loader2 size={14} className="animate-spin" />}
            {status.kind === 'validating' ? 'Validerer...' : 'Forbind'}
          </button>
        </div>

        <div className="mt-8 text-center text-[10px] text-fg3">
          Bygget af Bjørn ·{' '}
          <a
            href="https://github.com/Nickless-cmd/jarvis-v2"
            className="text-fg2 hover:text-fg underline"
            target="_blank"
            rel="noopener noreferrer"
          >
            github.com/Nickless-cmd/jarvis-v2
          </a>
        </div>
      </div>
    </div>
  )
}
