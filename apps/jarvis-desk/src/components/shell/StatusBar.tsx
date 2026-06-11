import { useStream } from '../../hooks/useStream'

/** Bund-statusbar: model · status · session. Monospace, dæmpet (locked design). */
export function StatusBar({ model, sessionId }: { model: string; sessionId: string | null }) {
  const { status } = useStream()
  return (
    <footer className="statusbar">
      <div className="left">
        <span><span className="dot" />primary · {model}</span>
        <span>{status}</span>
      </div>
      <div>session: {sessionId?.slice(0, 12) || '–'}</div>
    </footer>
  )
}
