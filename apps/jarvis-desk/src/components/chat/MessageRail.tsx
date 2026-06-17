import { useCallback, useEffect, useRef, useState, type RefObject } from 'react'

export interface RailAnchor { id: string; label: string }

/** Kort uddrag af en besked (content-blokke) til rail-tooltip. */
export function railLabel(content: unknown): string {
  if (!Array.isArray(content)) return 'Besked'
  const t = content
    .map((b) => (b && typeof b === 'object' && (b as { type?: string }).type === 'text' ? (b as { text?: string }).text ?? '' : ''))
    .join('').trim()
  return t.slice(0, 80) || 'Besked'
}

/** Venstre-kant navigations-rail (à la Claude billede 2). Én tick pr. anker
 *  (bruger-besked), placeret proportionelt efter besked-position i transcripten.
 *  Hover → uddrag · klik → scroll til præcis det punkt. Vises i både chat + code.
 *
 *  Måler positioner via [data-rail-id] i scroll-containeren — robust mod re-render
 *  + scroll + resize. Skjuler sig selv ved 0-1 ankre (intet at navigere). */
export function MessageRail({
  containerRef,
  anchors,
}: {
  containerRef: RefObject<HTMLElement | null>
  anchors: RailAnchor[]
}) {
  const [ticks, setTicks] = useState<{ id: string; top: number; label: string }[]>([])
  const railRef = useRef<HTMLDivElement>(null)

  const recompute = useCallback(() => {
    const c = containerRef.current
    if (!c) { setTicks([]); return }
    const total = c.scrollHeight || 1
    const next = anchors.map((a) => {
      const el = c.querySelector<HTMLElement>(`[data-rail-id="${CSS.escape(a.id)}"]`)
      if (!el) return null
      const top = Math.max(0, Math.min(100, (el.offsetTop / total) * 100))
      return { id: a.id, top, label: a.label }
    }).filter(Boolean) as { id: string; top: number; label: string }[]
    setTicks(next)
  }, [anchors, containerRef])

  useEffect(() => {
    const c = containerRef.current
    if (!c) return
    recompute()
    const ro = typeof ResizeObserver !== 'undefined' ? new ResizeObserver(recompute) : null
    ro?.observe(c)
    c.addEventListener('scroll', recompute, { passive: true })
    return () => { ro?.disconnect(); c.removeEventListener('scroll', recompute) }
  }, [recompute, containerRef])

  const jump = (id: string) => {
    const c = containerRef.current
    const el = c?.querySelector<HTMLElement>(`[data-rail-id="${CSS.escape(id)}"]`)
    el?.scrollIntoView({ behavior: 'smooth', block: 'start' })
  }

  if (ticks.length < 2) return null

  return (
    <div className="msg-rail" ref={railRef} aria-label="Spring til besked">
      {ticks.map((t) => (
        <button
          key={t.id}
          type="button"
          className="msg-rail-tick"
          style={{ top: `${t.top}%` }}
          aria-label={`Spring til: ${t.label}`}
          onClick={() => jump(t.id)}
        >
          <span className="msg-rail-tip">{t.label}</span>
        </button>
      ))}
    </div>
  )
}
