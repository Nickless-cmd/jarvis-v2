import { useEffect, useRef } from 'react'
import { Pencil, TerminalSquare } from 'lucide-react'

/** Flydende højreklik-menu på en fil i fil-træet: "Åbn i editor" / "Åbn i
 *  terminal". Lukker ved klik udenfor eller Escape. Positioneres ved markøren. */
export function FileContextMenu({
  x, y, onEditor, onTerminal, onClose,
}: {
  x: number; y: number
  onEditor: () => void
  onTerminal: () => void
  onClose: () => void
}) {
  const ref = useRef<HTMLDivElement>(null)
  useEffect(() => {
    const onDown = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) onClose()
    }
    const onKey = (e: KeyboardEvent) => { if (e.key === 'Escape') onClose() }
    window.addEventListener('mousedown', onDown)
    window.addEventListener('keydown', onKey)
    return () => {
      window.removeEventListener('mousedown', onDown)
      window.removeEventListener('keydown', onKey)
    }
  }, [onClose])

  // Hold menuen inden for vinduet (undgå at den falder ud i bunden/højre kant).
  const left = Math.min(x, window.innerWidth - 180)
  const top = Math.min(y, window.innerHeight - 90)
  return (
    <div ref={ref} className="file-context-menu" style={{ left, top }}>
      <button type="button" className="file-context-item" onClick={() => { onEditor(); onClose() }}>
        <Pencil size={13} /> Åbn i editor
      </button>
      <button type="button" className="file-context-item" onClick={() => { onTerminal(); onClose() }}>
        <TerminalSquare size={13} /> Åbn i terminal
      </button>
    </div>
  )
}
