import { type RefObject } from 'react'

export interface RailAnchor { id: string; label: string }

/** Kort uddrag af en besked (content-blokke) til rail-label. */
export function railLabel(content: unknown): string {
  if (!Array.isArray(content)) return 'Besked'
  const t = content
    .map((b) => (b && typeof b === 'object' && (b as { type?: string }).type === 'text' ? (b as { text?: string }).text ?? '' : ''))
    .join('').trim()
  return t.slice(0, 80) || 'Besked'
}

/** Navigations-rail à la Claude (1:1): en lodret indholdsfortegnelse i venstre
 *  kant. I hvile vises kun korte dashes — ét pr. anker (bruger-besked). Når
 *  musen er over rail-zonen folder hele titel-listen ud i et panel; rækken under
 *  markøren fremhæves, og det aktuelle (nederste) anker står fedt. Klik scroller
 *  til beskeden. Vises i både chat + code. Skjuler sig ved 0-1 ankre. */
export function MessageRail({
  containerRef,
  anchors,
}: {
  containerRef: RefObject<HTMLElement | null>
  anchors: RailAnchor[]
}) {
  if (anchors.length < 2) return null

  const jump = (id: string) => {
    const c = containerRef.current
    const el = c?.querySelector<HTMLElement>(`[data-rail-id="${CSS.escape(id)}"]`)
    el?.scrollIntoView({ behavior: 'smooth', block: 'start' })
  }

  const lastId = anchors[anchors.length - 1]?.id

  return (
    <nav className="msg-rail" aria-label="Spring til besked">
      <div className="msg-rail-panel">
        {anchors.map((a) => (
          <button
            key={a.id}
            type="button"
            className={`msg-rail-row ${a.id === lastId ? 'is-active' : ''}`}
            onClick={() => jump(a.id)}
          >
            <span className="msg-rail-dash" aria-hidden />
            <span className="msg-rail-text" title={a.label}>{a.label}</span>
          </button>
        ))}
      </div>
    </nav>
  )
}
