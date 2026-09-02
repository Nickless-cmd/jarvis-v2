import { Pressable, StyleSheet, Text, View } from 'react-native'
import { tokens } from '../theme/tokens'
import type { StreamErrorInfo, StreamErrorRecoverable } from '../state/StreamContext'

/** "Hvad gjorde systemet" — udledt af recoverable. Dansk, ærlig. */
function systemActionText(recoverable: StreamErrorRecoverable): string | null {
  switch (recoverable) {
    case 'auto':
      return 'Jeg håndterer det automatisk.'
    case 'retry':
      return 'Jeg prøvede igen.'
    case 'degraded':
      return 'Jeg kører videre i nedsat tilstand.'
    case 'user_action':
      return 'Det kræver din handling.'
    case 'permanent':
      return 'Det kan ikke løses automatisk.'
    default:
      return null
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
  stream: 'Forbindelsesproblem',
  ui: 'Visningsfejl'
}

/** Kort titel udledt af kind/severity. */
function titleFor(err: StreamErrorInfo): string {
  if (err.severity === 'critical') return 'Kritisk fejl'
  const family = (err.kind || err.code).split('.')[0] ?? ''
  return FAMILY_DA[family] ?? (err.severity === 'warning' ? 'Advarsel' : 'Der opstod en fejl')
}

const SEVERITY_COLOR: Record<StreamErrorInfo['severity'], string> = {
  info: tokens.color.accent,
  warning: tokens.color.warn,
  error: tokens.color.error,
  critical: tokens.color.error
}

/**
 * Rig fejl-kort (Canonical Error System, Fase 2 — mobil): titel · hvad skete (message) ·
 * hvad systemet gjorde (recoverable) · fix_hint · CTA. Falder pænt tilbage når kun
 * legacy-felter er sat. Spejler apps/jarvis-desk ErrorCard.
 */
export function ErrorCard({
  error,
  onRetry,
  onDismiss
}: {
  error: StreamErrorInfo
  onRetry?: () => void
  onDismiss: () => void
}) {
  const action = systemActionText(error.recoverable)
  const showRetry = error.retryable && !!onRetry
  const accent = SEVERITY_COLOR[error.severity]
  return (
    <View style={[styles.root, { borderLeftColor: accent }]} accessibilityRole="alert">
      <View style={styles.head}>
        <Text style={[styles.title, { color: accent }]}>{titleFor(error)}</Text>
        <Pressable accessibilityRole="button" accessibilityLabel="luk" onPress={onDismiss} style={styles.dismiss}>
          <Text style={styles.dismissText}>×</Text>
        </Pressable>
      </View>
      <Text style={styles.message}>{error.message}</Text>
      {action ? <Text style={styles.action}>{action}</Text> : null}
      {error.fixHint ? <Text style={styles.hint}>{error.fixHint}</Text> : null}
      {error.correlationId ? (
        <Text style={styles.cid}>#{error.correlationId.slice(0, 8)}</Text>
      ) : null}
      {showRetry ? (
        <Pressable accessibilityRole="button" onPress={onRetry} style={styles.retry}>
          <Text style={styles.retryText}>Prøv igen</Text>
        </Pressable>
      ) : null}
    </View>
  )
}

const styles = StyleSheet.create({
  root: {
    paddingHorizontal: tokens.spacing.md,
    paddingVertical: tokens.spacing.sm,
    borderTopColor: tokens.color.line,
    borderTopWidth: 1,
    borderLeftWidth: 3,
    backgroundColor: tokens.color.bg1,
    gap: 2
  },
  head: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between'
  },
  title: {
    fontWeight: '700',
    flex: 1
  },
  message: {
    color: tokens.color.fg1,
    marginTop: 2
  },
  action: {
    color: tokens.color.fg2,
    marginTop: 2,
    fontStyle: 'italic'
  },
  hint: {
    color: tokens.color.fg3,
    marginTop: 2
  },
  cid: {
    color: tokens.color.fg3,
    fontSize: 11,
    marginTop: 4
  },
  retry: {
    alignSelf: 'flex-start',
    marginTop: tokens.spacing.sm,
    minHeight: 38,
    minWidth: 90,
    paddingHorizontal: tokens.spacing.md,
    alignItems: 'center',
    justifyContent: 'center',
    borderRadius: tokens.radius.md,
    borderColor: tokens.color.accent,
    borderWidth: 1
  },
  retryText: {
    color: tokens.color.accent,
    fontWeight: '700'
  },
  dismiss: {
    minHeight: 32,
    minWidth: 32,
    alignItems: 'center',
    justifyContent: 'center'
  },
  dismissText: {
    color: tokens.color.fg3,
    fontSize: 22,
    lineHeight: 24
  }
})
