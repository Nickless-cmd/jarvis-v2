import { useState } from 'react'
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
/** Redningshandlinger i fejløjeblikket. Hver enkelt vises KUN når den er
 *  ægte i situationen — en knap der ikke kan gøre noget er værre end ingen
 *  knap, fordi den koster et klik og et håb. */
export interface Redning {
  /** Prøv igen med en stærkere model. Kun meningsfuld for member-tier
   *  (standard → pro); for owner er «stærkere» ikke defineret, og et gæt
   *  kunne lige så godt vælge en dårligere model. */
  onStaerkere?: () => void
  /** Rul sidste redigeringsrunde tilbage. Kun når sessionen HAR checkpoints.
   *  Returnerer den linje kortet skal vise bagefter — så resultatet ikke skal
   *  trådes gennem hele viewet for at blive synligt. */
  onFortryd?: () => Promise<string>
  /** Skift til «spørg før ændringer». Kun når man står i trust. */
  onSpoergFoerst?: () => void
}

export function ErrorCard({
  error,
  onRetry,
  onDismiss,
  onDetails,
  redning,
}: {
  error: CanonicalError
  onRetry?: () => void
  onDismiss: () => void
  onDetails?: () => void
  redning?: Redning
}) {
  const [ruller, setRuller] = useState(false)
  const [kvittering, setKvittering] = useState('')
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
        {redning?.onStaerkere && (
          <button type="button" className="errorcard-alt" onClick={redning.onStaerkere}>
            Prøv med Pro
          </button>
        )}
        {redning?.onFortryd && (
          <button
            type="button"
            className="errorcard-alt"
            disabled={ruller}
            onClick={() => {
              setRuller(true)
              redning.onFortryd!()
                .then(setKvittering)
                .catch(() => setKvittering('Kunne ikke fortryde'))
                .finally(() => setRuller(false))
            }}
          >
            {ruller ? 'Fortryder…' : 'Fortryd sidste ændringer'}
          </button>
        )}
        {redning?.onSpoergFoerst && (
          <button type="button" className="errorcard-alt" onClick={redning.onSpoergFoerst}>
            Spørg før ændringer
          </button>
        )}
        {onDetails && (
          <button type="button" className="errorcard-details" onClick={onDetails}>
            Se detaljer
          </button>
        )}
      </div>
      {kvittering && <p className="errorcard-kvittering">{kvittering}</p>}
    </div>
  )
}
