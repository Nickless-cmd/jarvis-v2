import { Component, type ErrorInfo, type ReactNode } from 'react'
import { Pressable, ScrollView, StyleSheet, Text, View } from 'react-native'
import { tokens } from '../theme/tokens'
import { ErrorCard } from './ErrorCard'
import type { StreamErrorInfo } from '../state/StreamContext'

/** Sidste render-crash — holdes i modul-scope så den overlever en remount af
 *  boundary'et og kan aflæses/relayes (mobil har ingen localStorage). */
export interface LastCrash {
  when: string
  where: string
  message: string
  stack: string
  componentStack: string
}
let lastCrash: LastCrash | null = null
export function getLastCrash(): LastCrash | null {
  return lastCrash
}

type Props = {
  children: ReactNode
  /** Etiket til log/telemetri (fx 'app', 'chat'). */
  label?: string
  /** Kompakt fallback (ErrorCard) i stedet for fuld-skærm. Til isolering af én
   *  delvis-visning (fx besked-listen) uden at tage hele skærmen. */
  compact?: boolean
}
type State = { error: Error | null; componentStack: string }

/** Top-level fejl-hegn. UDEN dette unmounter en render-throw HELE React-træet →
 *  sort skærm uden signal (samme bug som desk, Bjørn 9. jul). Med dette: vis en
 *  fejl + en "prøv igen"-knap i stedet, og gem sidste crash i modul-scope så den
 *  kan aflæses/relayes. */
export class ErrorBoundary extends Component<Props, State> {
  override state: State = { error: null, componentStack: '' }

  static getDerivedStateFromError(error: Error): Partial<State> {
    return { error }
  }

  override componentDidCatch(error: Error, info: ErrorInfo) {
    const payload: LastCrash = {
      when: new Date().toISOString(),
      where: this.props.label || 'app',
      message: String(error?.message || error),
      stack: String(error?.stack || ''),
      componentStack: String(info?.componentStack || '')
    }
    lastCrash = payload
    // eslint-disable-next-line no-console
    console.error('[jarvis-mobile crash]', payload.where, payload.message, payload.stack, payload.componentStack)
    this.setState({ componentStack: payload.componentStack })
  }

  reset = () => this.setState({ error: null, componentStack: '' })

  override render() {
    const { error, componentStack } = this.state
    if (!error) return this.props.children

    if (this.props.compact) {
      const info: StreamErrorInfo = {
        code: 'ui',
        kind: 'ui.render',
        severity: 'error',
        message: 'Denne visning ramte en fejl, men appen kører videre.',
        fixHint: String(error.message).slice(0, 200),
        retryable: true,
        correlationId: '',
        recoverable: 'retry',
        scope: 'ui'
      }
      return <ErrorCard error={info} onRetry={this.reset} onDismiss={this.reset} />
    }

    return (
      <View style={styles.root}>
        <Text style={styles.title}>Visningen ramte en fejl</Text>
        <Text style={styles.body}>
          Appen kører stadig, og chatten fortsætter på serveren. Tryk Prøv igen — eller kopiér fejlen herunder til Claude.
        </Text>
        <ScrollView style={styles.pre} contentContainerStyle={styles.preContent}>
          <Text style={styles.preText}>
            {String(error.message)}
            {'\n\n'}
            {String(error.stack || '').slice(0, 2000)}
            {componentStack ? `\n\n--- component stack ---\n${componentStack.slice(0, 1500)}` : ''}
          </Text>
        </ScrollView>
        <Pressable accessibilityRole="button" onPress={this.reset} style={styles.retry}>
          <Text style={styles.retryText}>Prøv igen</Text>
        </Pressable>
      </View>
    )
  }
}

const styles = StyleSheet.create({
  root: {
    flex: 1,
    padding: tokens.spacing.lg,
    backgroundColor: tokens.color.bg0,
    gap: tokens.spacing.sm
  },
  title: {
    color: tokens.color.error,
    fontWeight: '700',
    fontSize: 18
  },
  body: {
    color: tokens.color.fg2
  },
  pre: {
    flexGrow: 0,
    maxHeight: 320,
    backgroundColor: tokens.color.bg1,
    borderRadius: tokens.radius.md,
    borderColor: tokens.color.line,
    borderWidth: 1
  },
  preContent: {
    padding: tokens.spacing.md
  },
  preText: {
    color: tokens.color.fg2,
    fontFamily: 'monospace',
    fontSize: 12
  },
  retry: {
    alignSelf: 'flex-start',
    marginTop: tokens.spacing.sm,
    minHeight: 44,
    minWidth: 120,
    paddingHorizontal: tokens.spacing.lg,
    alignItems: 'center',
    justifyContent: 'center',
    borderRadius: tokens.radius.md,
    backgroundColor: tokens.color.accent
  },
  retryText: {
    color: tokens.color.bg0,
    fontWeight: '700'
  }
})
