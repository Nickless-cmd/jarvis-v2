import type { CanonicalError, CanonicalRecoverable } from '../../lib/canonicalError'

/** "Hvad gjorde systemet" — udledt af recoverable. Dansk, ærlig. */
function systemActionText(recoverable: CanonicalRecoverable | undefined): string | null {
  switch (recoverable) {
    case 'auto': return 'Jeg håndterer det automatisk.'
    case 'retry': return 'Jeg prøvede igen.'
    case 'degraded': return 'Jeg kører videre i nedsat tilstand.'
    case 'user_action': return 'Det kræver din handling.'
    case 'permanent': return 'Det kan ikke løses automatisk.'
    default: return null
  }
}

const FAMILY_DA: Record<string, string> = {
  network: 'Forbindelsesproblem',
  auth: 'Adgangsproblem',
  trust: 'Tillidsspørgsmål',
  central: 'Intern proces',
  self: 'Mit svar blev afbrudt',
  model: 'Model-problem',
  provider: 'Udbyder-problem',
  tool: 'Værktøjsfejl',
  workspace: 'Arbejdsområde',
  infra: 'Infrastruktur',
  server: 'Serverfejl',
  protocol: 'Protokolfejl',
  ui: 'Visningsfejl',
}

/** Kort titel udledt af kind/severity. */
function titleFor(err: CanonicalError): string {
  if (err.severity === 'critical') return 'Kritisk fejl'
  const family = (err.kind ?? err.code).split('.')[0] ?? ''
  return FAMILY_DA[family] ?? (err.severity === 'warning' ? 'Advarsel' : 'Der opstod en fejl')
}

/**
 * Rig fejl-kort (Canonical Error System, Fase 2): titel · hvad skete (message) ·
 * hvad systemet gjorde (recoverable) · fix_hint · CTA. Falder pænt tilbage når kun
 * legacy-felter er sat.
 */
export function ErrorCard({
  error,
  onRetry,
  onDismiss,
  onDetails,
}: {
  error: CanonicalError
  onRetry?: () => void
  onDismiss: () => void
  onDetails?: () => void
}) {
  const action = systemActionText(error.recoverable)
  const showRetry = error.retryable && !!onRetry
  return (
    <div className={`errorcard errorcard-sev-${error.severity}`} role="alert">
      <div className="errorcard-head">
        <span className="errorcard-title">{titleFor(error)}</span>
        <button type="button" className="errorcard-dismiss" aria-label="luk" onClick={onDismiss}>
          ×
        </button>
      </div>
      <p className="errorcard-message">{error.message}</p>
      {action && <p className="errorcard-action">{action}</p>}
      {error.fixHint && <p className="errorcard-hint">{error.fixHint}</p>}
      <div className="errorcard-actions">
        {showRetry && (
          <button type="button" className="errorcard-retry" onClick={onRetry}>
            Prøv igen
          </button>
        )}
        {onDetails && (
          <button type="button" className="errorcard-details" onClick={onDetails}>
            Se detaljer
          </button>
        )}
      </div>
    </div>
  )
}
