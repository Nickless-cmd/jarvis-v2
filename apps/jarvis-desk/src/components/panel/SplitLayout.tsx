import { useEffect, useRef, useState, type ReactNode } from 'react'
import { MAX_WIDTH_FRACTION, MIN_WIDTH } from '../../lib/panelReducer'

const OVERLAY_BELOW_PX = 900

/** Horisontal split: children (main) til venstre, panel til højre, med trækbart
 *  håndtag. Under OVERLAY_BELOW_PX falder panelet tilbage til drawer-overlay. */
export function SplitLayout({
  open,
  width,
  onResize,
  panel,
  children,
}: {
  open: boolean
  width: number
  onResize: (w: number) => void
  panel: ReactNode
  children: ReactNode
}) {
  const rootRef = useRef<HTMLDivElement>(null)
  const [dragging, setDragging] = useState(false)
  const [overlay, setOverlay] = useState(false)

  useEffect(() => {
    const check = () => setOverlay(window.innerWidth < OVERLAY_BELOW_PX)
    check()
    window.addEventListener('resize', check)
    return () => window.removeEventListener('resize', check)
  }, [])

  useEffect(() => {
    if (!dragging) return
    const onMove = (e: MouseEvent) => {
      const root = rootRef.current
      if (!root) return
      const rootW = root.clientWidth
      const fromRight = root.getBoundingClientRect().right - e.clientX
      const clamped = Math.max(MIN_WIDTH, Math.min(fromRight, rootW * MAX_WIDTH_FRACTION))
      onResize(clamped)
    }
    const onUp = () => setDragging(false)
    window.addEventListener('mousemove', onMove)
    window.addEventListener('mouseup', onUp)
    return () => {
      window.removeEventListener('mousemove', onMove)
      window.removeEventListener('mouseup', onUp)
    }
  }, [dragging, onResize])

  const panelWidth = overlay ? undefined : width
  return (
    <div className={`split-root ${open ? 'split-open' : ''} ${overlay ? 'split-overlay' : ''}`} ref={rootRef}>
      <div className="split-main">{children}</div>
      {open && !overlay && (
        <div
          role="separator"
          aria-orientation="vertical"
          className={`split-handle ${dragging ? 'dragging' : ''}`}
          onMouseDown={() => setDragging(true)}
        />
      )}
      {open && (
        <div className="split-panel" style={panelWidth ? { width: panelWidth } : undefined}>
          {panel}
        </div>
      )}
    </div>
  )
}
