import { useEffect, useState } from 'react'
import {
  Sparkles,
  Crown,
  User,
  ArrowRight,
  Check,
  Loader2,
  AlertCircle,
} from 'lucide-react'

interface Props {
  open: boolean
  apiBaseUrl: string
  defaultUserName: string
  onComplete: (patch: {
    userName?: string
    userId?: string
    authToken?: string
    authTokenUserId?: string
    authTokenRole?: string
    authTokenExpiresAt?: string
  }) => Promise<void>
  onSkip: () => void
}

type Step = 'welcome' | 'owner' | 'member' | 'done'

/**
 * First-run onboarding modal.
 *
 * Shows up when JarvisX detects an unconfigured installation
 * (no authToken AND default placeholder userId still in config).
 * Guides the user down one of two paths:
 *
 *   Owner path  — "this is my own Jarvis, I'm setting it up"
 *                 Confirms name + keeps the existing userId/config
 *                 (which already points at owner's discord_id from
 *                 the default fallback). One-click continue.
 *
 *   Member path — "owner gave me a token, I'm joining"
 *                 Asks for display name + token, claims via
 *                 /api/auth/whoami-token (public endpoint), saves
 *                 token + claims to local config.
 *
 * Why a modal vs a separate route: a modal preserves the chrome
 * (sidebar, toolbar) so the user sees what they're entering. Routes
 * feel like "you're not in JarvisX yet". Modal says "you're in,
 * just need to introduce yourself".
 *
 * Skip is allowed but discouraged — owners on localhost-only setups
 * with auth disabled don't strictly need to do this dance. We log
 * a "completed" flag in localStorage either way so this only
 * appears once.
 */
export function OnboardingModal({
  open,
  apiBaseUrl,
  defaultUserName,
  onComplete,
  onSkip,
}: Props) {
  const [step, setStep] = useState<Step>('welcome')
  const [name, setName] = useState(defaultUserName || '')
  const [token, setToken] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const baseUrl = apiBaseUrl.replace(/\/$/, '')

  // Reset state when re-opening
  useEffect(() => {
    if (!open) return
    setStep('welcome')
    setName(defaultUserName || '')
    setToken('')
    setError(null)
  }, [open, defaultUserName])

  if (!open) return null

  const handleOwnerContinue = async () => {
    setBusy(true)
    setError(null)
    try {
      await onComplete({ userName: name.trim() || defaultUserName })
      setStep('done')
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e))
    } finally {
      setBusy(false)
    }
  }

  const handleMemberClaim = async () => {
    const trimmed = token.trim()
    if (!trimmed) {
      setError('Token mangler')
      return
    }
    setBusy(true)
    setError(null)
    try {
      const res = await fetch(`${baseUrl}/api/auth/whoami-token`, {
        headers: { Authorization: `Bearer ${trimmed}` },
      })
      const j = await res.json()
      if (!j.valid) {
        throw new Error(j.error || 'token rejected')
      }
      const expIso = j.expires_at
        ? new Date(j.expires_at * 1000).toISOString()
        : undefined
      await onComplete({
        userName: name.trim() || 'member',
        userId: j.user_id,
        authToken: trimmed,
        authTokenUserId: j.user_id,
        authTokenRole: j.role,
        authTokenExpiresAt: expIso,
      })
      setStep('done')
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e))
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="fixed inset-0 z-[10000] flex items-center justify-center bg-bg0/90 backdrop-blur-sm">
      <div className="flex max-h-[90vh] w-[560px] max-w-[92vw] flex-col overflow-hidden rounded-xl border border-line2 bg-bg1 shadow-2xl">
        {step === 'welcome' && (
          <Welcome
            onOwner={() => setStep('owner')}
            onMember={() => setStep('member')}
            onSkip={onSkip}
          />
        )}
        {step === 'owner' && (
          <OwnerStep
            name={name}
            setName={setName}
            busy={busy}
            error={error}
            onBack={() => setStep('welcome')}
            onContinue={handleOwnerContinue}
          />
        )}
        {step === 'member' && (
          <MemberStep
            name={name}
            setName={setName}
            token={token}
            setToken={setToken}
            busy={busy}
            error={error}
            onBack={() => setStep('welcome')}
            onClaim={handleMemberClaim}
          />
        )}
        {step === 'done' && <DoneStep onClose={onSkip} />}
      </div>
    </div>
  )
}

function Welcome({
  onOwner,
  onMember,
  onSkip,
}: {
  onOwner: () => void
  onMember: () => void
  onSkip: () => void
}) {
  return (
    <>
      <header className="flex items-center gap-3 border-b border-line/60 px-6 py-4">
        <div className="flex h-9 w-9 flex-shrink-0 items-center justify-center rounded-md bg-gradient-to-br from-accent to-accent2 font-semibold text-bg0">
          J
        </div>
        <div>
          <h2 className="text-base font-semibold">Velkommen til JarvisX</h2>
          <p className="text-[11px] text-fg3">
            Lad os introducere dig — det tager 30 sekunder
          </p>
        </div>
      </header>

      <div className="flex flex-col gap-3 p-6">
        <p className="text-[12px] leading-relaxed text-fg2">
          JarvisX er Bjørns Jarvis V2 i en native desktop-shell. Før du
          kan bruge den skal vi vide hvem du er.
        </p>

        <button
          onClick={onOwner}
          className="group flex items-start gap-3 rounded-lg border border-line2 bg-bg2/40 p-4 text-left transition-colors hover:border-accent/40 hover:bg-bg2"
        >
          <Crown size={18} className="mt-0.5 flex-shrink-0 text-accent" />
          <div className="flex-1">
            <div className="text-sm font-semibold text-fg">
              Jeg er ejeren — det her er min egen Jarvis
            </div>
            <div className="mt-1 text-[11px] leading-relaxed text-fg3">
              Du satte den her server op. Du har fuld kontrol — pin identitet,
              issue tokens til andre, ændre alt i Indstillinger.
            </div>
          </div>
          <ArrowRight
            size={14}
            className="mt-1 flex-shrink-0 text-fg3 opacity-0 transition-opacity group-hover:opacity-100"
          />
        </button>

        <button
          onClick={onMember}
          className="group flex items-start gap-3 rounded-lg border border-line2 bg-bg2/40 p-4 text-left transition-colors hover:border-accent/40 hover:bg-bg2"
        >
          <User size={18} className="mt-0.5 flex-shrink-0 text-accent2" />
          <div className="flex-1">
            <div className="text-sm font-semibold text-fg">
              Jeg har fået en invite-token fra ejeren
            </div>
            <div className="mt-1 text-[11px] leading-relaxed text-fg3">
              Ejeren gav dig en token (via Discord, papir, SMS — uanset
              hvordan). Paste den her, så claimer vi den og du er inde.
            </div>
          </div>
          <ArrowRight
            size={14}
            className="mt-1 flex-shrink-0 text-fg3 opacity-0 transition-opacity group-hover:opacity-100"
          />
        </button>
      </div>

      <footer className="flex items-center justify-between border-t border-line/60 px-6 py-3 text-[11px] text-fg3">
        <span className="flex items-center gap-2">
          <Sparkles size={11} className="text-accent" />
          Du kan ændre alt senere i Indstillinger
        </span>
        <button
          onClick={onSkip}
          className="text-fg3 underline-offset-2 hover:text-fg2 hover:underline"
        >
          Spring over
        </button>
      </footer>
    </>
  )
}

function OwnerStep({
  name,
  setName,
  busy,
  error,
  onBack,
  onContinue,
}: {
  name: string
  setName: (v: string) => void
  busy: boolean
  error: string | null
  onBack: () => void
  onContinue: () => void
}) {
  return (
    <>
      <header className="flex items-center gap-3 border-b border-line/60 px-6 py-4">
        <Crown size={16} className="text-accent" />
        <h2 className="text-base font-semibold">Owner setup</h2>
      </header>

      <div className="flex flex-col gap-3 p-6">
        <p className="text-[12px] leading-relaxed text-fg2">
          Vi bruger din eksisterende config — du er allerede registreret i{' '}
          <code className="text-fg">users.json</code> som owner. Bekræft bare
          dit navn, så fortsætter vi.
        </p>
        <label className="flex flex-col gap-1.5">
          <span className="text-[10px] font-semibold uppercase tracking-wider text-fg3">
            Display-navn
          </span>
          <input
            autoFocus
            value={name}
            onChange={(e) => setName(e.target.value)}
            className="rounded border border-line bg-bg0 px-3 py-2 text-sm text-fg outline-none focus:border-accent/60"
          />
        </label>
        {error && (
          <div className="flex items-start gap-2 rounded border border-danger/30 bg-danger/10 px-3 py-2 text-[11px] text-danger">
            <AlertCircle size={11} className="mt-0.5 flex-shrink-0" />
            {error}
          </div>
        )}
      </div>

      <footer className="flex items-center justify-between border-t border-line/60 px-6 py-3">
        <button
          onClick={onBack}
          disabled={busy}
          className="text-[11px] text-fg3 hover:text-fg2 disabled:opacity-50"
        >
          ← Tilbage
        </button>
        <button
          onClick={onContinue}
          disabled={busy}
          className="flex items-center gap-1.5 rounded-md bg-accent px-4 py-1.5 text-[12px] font-semibold text-bg0 hover:bg-accent/90 disabled:opacity-50"
        >
          {busy ? <Loader2 size={11} className="animate-spin" /> : <Check size={11} />}
          Bekræft og fortsæt
        </button>
      </footer>
    </>
  )
}

function MemberStep({
  name,
  setName,
  token,
  setToken,
  busy,
  error,
  onBack,
  onClaim,
}: {
  name: string
  setName: (v: string) => void
  token: string
  setToken: (v: string) => void
  busy: boolean
  error: string | null
  onBack: () => void
  onClaim: () => void
}) {
  return (
    <>
      <header className="flex items-center gap-3 border-b border-line/60 px-6 py-4">
        <User size={16} className="text-accent2" />
        <h2 className="text-base font-semibold">Claim invite-token</h2>
      </header>

      <div className="flex flex-col gap-3 p-6">
        <p className="text-[12px] leading-relaxed text-fg2">
          Paste den token ejeren gav dig. Vi verificerer den mod backend
          og gemmer den lokalt — efterfølgende requests sender den
          automatisk så du er autentificeret.
        </p>

        <label className="flex flex-col gap-1.5">
          <span className="text-[10px] font-semibold uppercase tracking-wider text-fg3">
            Display-navn
          </span>
          <input
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="Mikkel"
            className="rounded border border-line bg-bg0 px-3 py-2 text-sm text-fg outline-none focus:border-accent/60"
          />
        </label>

        <label className="flex flex-col gap-1.5">
          <span className="text-[10px] font-semibold uppercase tracking-wider text-fg3">
            Invite-token
          </span>
          <textarea
            autoFocus
            value={token}
            onChange={(e) => setToken(e.target.value)}
            rows={4}
            placeholder="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9…"
            className="resize-none rounded border border-line bg-bg0 px-3 py-2 font-mono text-[11px] text-fg outline-none focus:border-accent/60"
          />
        </label>

        {error && (
          <div className="flex items-start gap-2 rounded border border-danger/30 bg-danger/10 px-3 py-2 text-[11px] text-danger">
            <AlertCircle size={11} className="mt-0.5 flex-shrink-0" />
            {error}
          </div>
        )}
      </div>

      <footer className="flex items-center justify-between border-t border-line/60 px-6 py-3">
        <button
          onClick={onBack}
          disabled={busy}
          className="text-[11px] text-fg3 hover:text-fg2 disabled:opacity-50"
        >
          ← Tilbage
        </button>
        <button
          onClick={onClaim}
          disabled={busy || !token.trim()}
          className="flex items-center gap-1.5 rounded-md bg-accent px-4 py-1.5 text-[12px] font-semibold text-bg0 hover:bg-accent/90 disabled:opacity-50"
        >
          {busy ? <Loader2 size={11} className="animate-spin" /> : <Check size={11} />}
          Claim og fortsæt
        </button>
      </footer>
    </>
  )
}

function DoneStep({ onClose }: { onClose: () => void }) {
  return (
    <>
      <div className="flex flex-col items-center gap-3 px-6 py-10 text-center">
        <div className="flex h-12 w-12 items-center justify-center rounded-full bg-ok/15 text-ok">
          <Check size={24} />
        </div>
        <h2 className="text-base font-semibold">Klar til at starte</h2>
        <p className="max-w-[380px] text-[12px] leading-relaxed text-fg3">
          Du er sat op. F1 viser keyboard-genveje, Ctrl+1..8 hopper mellem
          views, Ctrl+J åbner terminal-drawer. Velkommen.
        </p>
      </div>
      <footer className="flex items-center justify-end border-t border-line/60 px-6 py-3">
        <button
          onClick={onClose}
          className="rounded-md bg-accent px-4 py-1.5 text-[12px] font-semibold text-bg0 hover:bg-accent/90"
        >
          Lad os gå
        </button>
      </footer>
    </>
  )
}
