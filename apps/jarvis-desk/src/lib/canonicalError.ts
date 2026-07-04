/**
 * Canonical error-type for desk — spejler backendens central_error_envelope
 * (ErrorEnvelope.to_client_event(), core/services/central_error_envelope.py).
 *
 * Fase 2 af Canonical Error System: ÉN sandhed for hvordan en fejl ser ud,
 * fra backend-envelope → SSE system_event(kind='error') → desk-rendering.
 *
 * Protokol-indpakning: backendens to_client_event() ({type:'error',...}) ankommer
 * IKKE som top-level event, men som payload i et
 *   system_event { kind: 'error', payload: { ...to_client_event() } }
 * parseCanonicalError() tager netop den payload.
 */

export type CanonicalSeverity = 'info' | 'warning' | 'error' | 'critical'

export type CanonicalRecoverable =
  | 'auto' | 'retry' | 'user_action' | 'degraded' | 'permanent'

export type CanonicalScope =
  | 'global' | 'session' | 'run' | 'tool' | 'component'

export interface CanonicalError {
  code: string
  severity: CanonicalSeverity
  message: string
  retryable: boolean
  fixHint: string
  correlationId: string
  kind?: string
  recoverable?: CanonicalRecoverable
  scope?: CanonicalScope
  origin?: 'stream' | 'client'
  receivedAt: number
}

const SEVERITIES: readonly CanonicalSeverity[] = ['info', 'warning', 'error', 'critical']
const RECOVERABILITIES: readonly CanonicalRecoverable[] = [
  'auto', 'retry', 'user_action', 'degraded', 'permanent',
]
const SCOPES: readonly CanonicalScope[] = [
  'global', 'session', 'run', 'tool', 'component',
]

function asSeverity(v: unknown): CanonicalSeverity {
  const s = String(v ?? 'error')
  return (SEVERITIES as readonly string[]).includes(s) ? (s as CanonicalSeverity) : 'error'
}
function asRecoverable(v: unknown): CanonicalRecoverable | undefined {
  const s = String(v ?? '')
  return (RECOVERABILITIES as readonly string[]).includes(s) ? (s as CanonicalRecoverable) : undefined
}
function asScope(v: unknown): CanonicalScope | undefined {
  const s = String(v ?? '')
  return (SCOPES as readonly string[]).includes(s) ? (s as CanonicalScope) : undefined
}

/**
 * Parse en to_client_event()-payload (indersiden af system_event kind='error')
 * til en CanonicalError. Robust: ukendte/manglende felter → fornuftige defaults,
 * aldrig kast. `origin` default 'stream'.
 */
export function parseCanonicalError(
  payload: Record<string, unknown> | null | undefined,
  origin: 'stream' | 'client' = 'stream',
): CanonicalError {
  const p = payload ?? {}
  return {
    code: String(p.code ?? p.kind ?? 'ui.unknown'),
    severity: asSeverity(p.severity),
    message: String(p.message ?? 'Noget gik galt. Det er fanget af systemet.'),
    retryable: Boolean(p.retryable ?? true),
    fixHint: String(p.fix_hint ?? ''),
    correlationId: String(p.correlation_id ?? ''),
    kind: p.kind ? String(p.kind) : undefined,
    recoverable: asRecoverable(p.recoverable),
    scope: asScope(p.scope),
    origin,
    receivedAt: Date.now(),
  }
}

/** Har fejlen en kanonisk kind? Vælger ErrorCard (rig) frem for ErrorBanner (simpel). */
export function isCanonical(err: CanonicalError): boolean {
  return typeof err.kind === 'string' && err.kind.length > 0
}
