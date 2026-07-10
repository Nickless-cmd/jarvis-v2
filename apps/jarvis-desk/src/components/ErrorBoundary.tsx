import { Component, type ErrorInfo, type ReactNode } from 'react'

/** Top-level fejl-hegn. UDEN dette unmounter en render-throw HELE React-træet →
 *  sort skærm uden signal (Bjørn 9. jul). Med dette: vis fejlen + stack + en
 *  genindlæs-knap i stedet, og persistér sidste crash i localStorage så den
 *  overlever et reload og kan aflæses/relayes. */
type State = { error: Error | null; info: string }

const CRASH_KEY = 'jarvis-desk:lastCrash'

/** Inline-variant: isolér en enkelt besked/blok så en render-throw i ÉN besked
 *  ikke river hele appen ned — vis kompakt fejl + log (samme CRASH_KEY). */
export class InlineErrorBoundary extends Component<{ children: ReactNode; label?: string }, State> {
  state: State = { error: null, info: '' }
  static getDerivedStateFromError(error: Error): Partial<State> { return { error } }
  componentDidCatch(error: Error, info: ErrorInfo) {
    const payload = { when: new Date().toISOString(), where: this.props.label || 'message',
      message: String(error?.message || error), stack: String(error?.stack || ''),
      componentStack: String(info?.componentStack || '') }
    try { localStorage.setItem(CRASH_KEY, JSON.stringify(payload)) } catch { /* noop */ }
    // eslint-disable-next-line no-console
    console.error('[jarvis-desk inline crash]', payload.where, payload.message, payload.stack, payload.componentStack)
  }
  render() {
    if (!this.state.error) return this.props.children
    return (
      <div style={{ padding: '8px 12px', borderRadius: 8, background: 'var(--panel, #1a1a1a)', color: 'var(--danger, #ff8080)', fontSize: 12, fontFamily: 'ui-monospace, monospace' }}>
        ⚠ Kunne ikke vise denne besked: {String(this.state.error.message).slice(0, 200)}
      </div>
    )
  }
}

export class ErrorBoundary extends Component<{ children: ReactNode }, State> {
  state: State = { error: null, info: '' }

  static getDerivedStateFromError(error: Error): Partial<State> {
    return { error }
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    const payload = {
      when: new Date().toISOString(),
      message: String(error?.message || error),
      stack: String(error?.stack || ''),
      componentStack: String(info?.componentStack || ''),
    }
    // Persistér + log, så roden kan aflæses efter et reload.
    try { localStorage.setItem(CRASH_KEY, JSON.stringify(payload)) } catch { /* noop */ }
    // eslint-disable-next-line no-console
    console.error('[jarvis-desk crash]', payload.message, payload.stack, payload.componentStack)
    this.setState({ info: payload.componentStack })
  }

  render() {
    const { error, info } = this.state
    if (!error) return this.props.children
    return (
      <div style={{ padding: 24, maxWidth: 900, margin: '40px auto', fontFamily: 'ui-monospace, monospace', color: 'var(--text, #ddd)' }}>
        <h2 style={{ color: 'var(--danger, #ff6b6b)' }}>⚠ Visningen ramte en fejl (men appen kører)</h2>
        <p>Chatten fortsætter server-side. Kopiér fejlen herunder til Claude, og tryk Genindlæs.</p>
        <pre style={{ whiteSpace: 'pre-wrap', background: 'var(--panel, #1a1a1a)', padding: 12, borderRadius: 8, maxHeight: 320, overflow: 'auto', fontSize: 12 }}>
          {String(error.message)}
          {'\n\n'}
          {String(error.stack || '').slice(0, 2000)}
          {info ? `\n\n--- component stack ---\n${info.slice(0, 1500)}` : ''}
        </pre>
        <button
          onClick={() => { this.setState({ error: null, info: '' }); location.reload() }}
          style={{ marginTop: 12, padding: '8px 18px', borderRadius: 8, border: 'none', background: 'var(--accent, #4c8bf5)', color: '#fff', cursor: 'pointer' }}
        >
          Genindlæs
        </button>
      </div>
    )
  }
}
