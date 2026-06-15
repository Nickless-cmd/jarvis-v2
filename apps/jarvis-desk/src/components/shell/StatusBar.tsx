import { useStream } from '../../hooks/useStream'

/** Bund-statusbar: model · status · session. Monospace, dæmpet (locked design).
 *  Viser den model det aktive/seneste run FAKTISK brugte (fra stream), med
 *  fallback til default-modellen før første run. */
export function StatusBar({ model, sessionId }: { model: string; sessionId: string | null }) {
  const { status, activeModel, activeLane } = useStream()
  const shownModel = activeModel || model
  const shownLane = activeLane || 'primary'
  return (
    <footer className="statusbar">
      <div className="left">
        <span><span className="dot" />{shownLane} · {shownModel}</span>
        <span>{status}</span>
      </div>
      <div>session: {sessionId?.slice(0, 12) || '–'}</div>
    </footer>
  )
}
