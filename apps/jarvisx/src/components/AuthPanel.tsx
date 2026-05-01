import { useEffect, useState } from 'react'
import {
  ShieldCheck,
  ShieldX,
  Copy,
  Check,
  Plus,
  Trash2,
  AlertCircle,
  Loader2,
} from 'lucide-react'

interface TokenClaim {
  valid: boolean
  user_id?: string
  role?: string
  issued_at?: number
  expires_at?: number
  issuer?: string
  error?: string
}

interface IssuedToken {
  token: string
  user_id: string
  role: string
  issued_at: string
  expires_at: string
  ttl_days: number
}

interface AuthState {
  authToken?: string
  authTokenUserId?: string
  authTokenRole?: string
  authTokenExpiresAt?: string
}

interface Props {
  apiBaseUrl: string
  auth: AuthState
  isOwner: boolean
  onChange: (patch: Partial<AuthState>) => Promise<void>
}

/**
 * Authentication management panel inside Settings.
 *
 * Three jobs:
 *   1. Show current token status (whoami-token check on mount)
 *   2. Owner: issue tokens for other users → display as copy-paste-able
 *      string for delivery out-of-band (Discord DM / paper / SMS)
 *   3. Anyone: paste a token into the "claim" field → verify → save it
 *      to local config so subsequent requests carry it
 *
 * Why all three in one place: the threat model is "trust nothing on
 * the wire". A shared backend secret means the owner mints, the
 * recipient claims, and that's the entire trust chain. UI surfaces
 * just need to make those two operations frictionless.
 */
export function AuthPanel({ apiBaseUrl, auth, isOwner, onChange }: Props) {
  const baseUrl = apiBaseUrl.replace(/\/$/, '')
  const [status, setStatus] = useState<TokenClaim | null>(null)
  const [statusLoading, setStatusLoading] = useState(false)

  // Issue form state (owner-only)
  const [issueUserId, setIssueUserId] = useState('')
  const [issueRole, setIssueRole] = useState<'owner' | 'member' | 'guest'>('member')
  const [issueTtl, setIssueTtl] = useState(30)
  const [issuing, setIssuing] = useState(false)
  const [issued, setIssued] = useState<IssuedToken | null>(null)
  const [issueError, setIssueError] = useState<string | null>(null)
  const [copied, setCopied] = useState(false)

  // Claim form state (anyone)
  const [claimToken, setClaimToken] = useState('')
  const [claiming, setClaiming] = useState(false)
  const [claimError, setClaimError] = useState<string | null>(null)

  // Verify the currently-stored token on mount + whenever it changes
  useEffect(() => {
    if (!auth.authToken) {
      setStatus(null)
      return
    }
    let cancelled = false
    setStatusLoading(true)
    fetch(`${baseUrl}/api/auth/whoami-token`, {
      headers: { Authorization: `Bearer ${auth.authToken}` },
    })
      .then((r) => r.json())
      .then((j) => {
        if (!cancelled) setStatus(j)
      })
      .catch((e) => {
        if (!cancelled) setStatus({ valid: false, error: String(e) })
      })
      .finally(() => {
        if (!cancelled) setStatusLoading(false)
      })
    return () => {
      cancelled = true
    }
  }, [auth.authToken, baseUrl])

  const handleIssue = async () => {
    if (!issueUserId.trim()) return
    setIssuing(true)
    setIssued(null)
    setIssueError(null)
    try {
      const res = await fetch(`${baseUrl}/api/auth/issue`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          user_id: issueUserId.trim(),
          role: issueRole,
          ttl_days: issueTtl,
        }),
      })
      if (!res.ok) {
        const body = await res.json().catch(() => null)
        throw new Error(body?.detail || `HTTP ${res.status}`)
      }
      const j = (await res.json()) as IssuedToken
      setIssued(j)
      setIssueUserId('')
    } catch (e) {
      setIssueError(e instanceof Error ? e.message : String(e))
    } finally {
      setIssuing(false)
    }
  }

  const handleCopyIssued = () => {
    if (!issued) return
    navigator.clipboard.writeText(issued.token).then(() => {
      setCopied(true)
      setTimeout(() => setCopied(false), 1800)
    })
  }

  const handleClaim = async () => {
    const token = claimToken.trim()
    if (!token) return
    setClaiming(true)
    setClaimError(null)
    try {
      const res = await fetch(`${baseUrl}/api/auth/whoami-token`, {
        headers: { Authorization: `Bearer ${token}` },
      })
      const j = (await res.json()) as TokenClaim
      if (!j.valid) {
        throw new Error(j.error || 'token rejected')
      }
      // Token verifies — save it locally
      const expIso = j.expires_at
        ? new Date(j.expires_at * 1000).toISOString()
        : undefined
      await onChange({
        authToken: token,
        authTokenUserId: j.user_id,
        authTokenRole: j.role,
        authTokenExpiresAt: expIso,
      })
      setClaimToken('')
    } catch (e) {
      setClaimError(e instanceof Error ? e.message : String(e))
    } finally {
      setClaiming(false)
    }
  }

  const handleClearToken = async () => {
    if (!confirm('Fjern din gemte token? Du skal claime en ny for at forblive autentificeret når backend kræver auth.')) return
    await onChange({
      authToken: '',
      authTokenUserId: '',
      authTokenRole: '',
      authTokenExpiresAt: '',
    })
    setStatus(null)
  }

  const tokenIsValid = status?.valid === true
  const expiresAt = auth.authTokenExpiresAt
    ? new Date(auth.authTokenExpiresAt)
    : null

  return (
    <section className="flex flex-col gap-4 rounded-lg border border-line bg-bg1 p-5">
      <header className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          {tokenIsValid ? (
            <ShieldCheck size={14} className="text-ok" />
          ) : (
            <ShieldX size={14} className="text-fg3" />
          )}
          <h3 className="text-sm font-semibold">Authentication</h3>
          {statusLoading && <Loader2 size={11} className="animate-spin text-fg3" />}
        </div>
      </header>

      {/* Current token status */}
      <div className="rounded-md border border-line/60 bg-bg0/40 px-3 py-2.5">
        {auth.authToken ? (
          <>
            <div className="mb-1 flex items-center gap-2 text-[11px]">
              {tokenIsValid ? (
                <span className="flex items-center gap-1 rounded bg-ok/15 px-1.5 py-0.5 font-semibold uppercase tracking-wider text-ok">
                  <Check size={9} /> gyldig
                </span>
              ) : (
                <span className="flex items-center gap-1 rounded bg-danger/15 px-1.5 py-0.5 font-semibold uppercase tracking-wider text-danger">
                  <AlertCircle size={9} /> ugyldig
                </span>
              )}
              <span className="font-mono text-fg2">
                {status?.user_id || auth.authTokenUserId || '?'}
              </span>
              <span className="text-fg3">·</span>
              <span className="font-mono text-fg2">{status?.role || auth.authTokenRole}</span>
            </div>
            {expiresAt && (
              <div className="font-mono text-[10px] text-fg3">
                udløber {expiresAt.toLocaleString()}
              </div>
            )}
            {!tokenIsValid && status?.error && (
              <div className="mt-2 font-mono text-[10px] text-danger">
                {status.error}
              </div>
            )}
            <button
              onClick={handleClearToken}
              className="mt-2 flex items-center gap-1 rounded border border-line2 px-2 py-1 text-[10px] text-fg3 hover:border-danger/40 hover:text-danger"
            >
              <Trash2 size={10} /> Fjern token
            </button>
          </>
        ) : (
          <div className="text-[11px] text-fg3">
            Ingen token gemt. Backend tillader X-JarvisX-User fallback når{' '}
            <code className="text-fg2">JARVISX_AUTH_REQUIRED</code> ikke er sat — brug{' '}
            kun det på localhost.
          </div>
        )}
      </div>

      {/* Claim form (anyone) */}
      <div className="flex flex-col gap-2">
        <label className="text-[11px] font-semibold uppercase tracking-wider text-fg3">
          Claim token
        </label>
        <p className="text-[11px] leading-relaxed text-fg3">
          Hvis owneren har givet dig en token, paste den her. Den verificeres mod
          backend og gemmes lokalt — efterfølgende requests sender den som
          Bearer-header.
        </p>
        <div className="flex gap-2">
          <input
            type="password"
            placeholder="eyJhbGciOi…"
            value={claimToken}
            onChange={(e) => setClaimToken(e.target.value)}
            className="flex-1 rounded border border-line bg-bg0 px-3 py-1.5 font-mono text-[11px] text-fg outline-none focus:border-accent/60"
          />
          <button
            onClick={handleClaim}
            disabled={claiming || !claimToken.trim()}
            className="flex items-center gap-1 rounded bg-accent px-3 py-1.5 text-[11px] font-semibold text-bg0 hover:bg-accent/90 disabled:opacity-40"
          >
            {claiming ? <Loader2 size={11} className="animate-spin" /> : <Check size={11} />}
            Claim
          </button>
        </div>
        {claimError && (
          <div className="rounded border border-danger/30 bg-danger/10 px-3 py-1.5 font-mono text-[10px] text-danger">
            {claimError}
          </div>
        )}
      </div>

      {/* Issue form (owner-only) */}
      {isOwner && (
        <div className="flex flex-col gap-2 rounded-md border border-warn/30 bg-warn/5 p-3">
          <label className="flex items-center gap-2 text-[11px] font-semibold uppercase tracking-wider text-warn">
            <Plus size={11} /> Issue token (owner-only)
          </label>
          <p className="text-[11px] leading-relaxed text-fg3">
            Mint en token til en anden bruger. Du leverer den selv ud-af-bånd
            (Discord DM, papir, SMS) — vi sender den ikke gennem nogen
            tredjepart.
          </p>
          <div className="flex flex-col gap-2 md:flex-row">
            <input
              placeholder="user_id (fx discord_id)"
              value={issueUserId}
              onChange={(e) => setIssueUserId(e.target.value)}
              className="flex-1 rounded border border-line bg-bg0 px-3 py-1.5 font-mono text-[11px] text-fg outline-none focus:border-accent/60"
            />
            <select
              value={issueRole}
              onChange={(e) =>
                setIssueRole(e.target.value as 'owner' | 'member' | 'guest')
              }
              className="rounded border border-line bg-bg0 px-2 py-1.5 text-[11px] text-fg outline-none focus:border-accent/60"
            >
              <option value="member">member</option>
              <option value="owner">owner</option>
              <option value="guest">guest</option>
            </select>
            <input
              type="number"
              min={1}
              max={365}
              value={issueTtl}
              onChange={(e) => setIssueTtl(parseInt(e.target.value) || 30)}
              title="TTL i dage (1..365)"
              className="w-20 rounded border border-line bg-bg0 px-2 py-1.5 font-mono text-[11px] text-fg outline-none focus:border-accent/60"
            />
            <button
              onClick={handleIssue}
              disabled={issuing || !issueUserId.trim()}
              className="flex items-center gap-1 rounded bg-warn px-3 py-1.5 text-[11px] font-semibold text-bg0 hover:bg-warn/90 disabled:opacity-40"
            >
              {issuing ? <Loader2 size={11} className="animate-spin" /> : <Plus size={11} />}
              Issue
            </button>
          </div>
          {issueError && (
            <div className="rounded border border-danger/30 bg-danger/10 px-3 py-1.5 font-mono text-[10px] text-danger">
              {issueError}
            </div>
          )}
          {issued && (
            <div className="mt-1 flex flex-col gap-2 rounded border border-ok/30 bg-ok/5 p-3">
              <div className="flex items-center justify-between text-[10px]">
                <span className="font-semibold uppercase tracking-wider text-ok">
                  Token til {issued.user_id} ({issued.role}, {issued.ttl_days}d)
                </span>
                <button
                  onClick={handleCopyIssued}
                  className="flex items-center gap-1 rounded border border-line2 bg-bg2 px-2 py-1 text-fg2 hover:text-accent"
                >
                  {copied ? <Check size={10} /> : <Copy size={10} />}
                  {copied ? 'kopieret' : 'kopiér'}
                </button>
              </div>
              <pre className="overflow-x-auto rounded bg-bg0 p-2 font-mono text-[10px] text-fg2">
                {issued.token}
              </pre>
              <div className="text-[10px] text-fg3">
                Udløber {new Date(issued.expires_at).toLocaleString()}. Send den
                via en kanal du stoler på — den fungerer som adgangsnøgle.
              </div>
            </div>
          )}
        </div>
      )}
    </section>
  )
}
