import { useStream } from '../../hooks/useStream'
import { useOnline } from '../../hooks/useOnline'

/** Bund-statusbar: model · status · session. Monospace, dæmpet (locked design).
 *  Viser den model det aktive/seneste run FAKTISK brugte (fra stream), med
 *  fallback til default-modellen før første run. + offline-badge (§6.1). */
export function StatusBar({ model, sessionId }: { model: string; sessionId: string | null }) {
  const { status, activeModel, activeLane } = useStream()
  const online = useOnline()
  const shownModel = activeModel || model
  const shownLane = activeLane || 'primary'
  const STATUS_DA: Record<string, string> = {
    idle: 'inaktiv', working: 'arbejder', done: 'færdig',
    hung: 'hænger', interrupted: 'afbrudt', error: 'fejl',
  }
  return (
    <footer className="statusbar">
      <div className="left">
        <span><span className="dot" />{shownLane} · {shownModel}</span>
        <span>{STATUS_DA[status] ?? status}</span>
        {!online && <span className="statusbar-offline" title="Ingen netforbindelse">● offline</span>}
      </div>
      <div>session: {sessionId?.slice(0, 12) || '–'}</div>
    </footer>
  )
}
