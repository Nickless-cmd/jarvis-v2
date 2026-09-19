import { useEffect, useState, type RefObject } from 'react'
import type { ChatMessage } from '../../lib/api'

function tekstAf(m: ChatMessage): string {
  return (m.content ?? []).map((b) => (b.type === 'text' ? b.text : '')).join(' ').replace(/\s+/g, ' ').trim()
}

/**
 * Din egen besked holdt fast i toppen, mens du læser svaret på den — Claude
 * Desktops sticky prompt (cc-desktop-chatview.md §10). Et klik ruller blødt
 * tilbage til beskeden: det er navigation, ikke pynt.
 *
 * Vises når den seneste af DINE beskeder over læsefeltet er scrollet helt ud
 * af syne. Beskederne findes via `data-rail-id`, som begge visninger allerede
 * sætter på hver besked (MessageRail bruger samme ankre).
 */
export function StickyPrompt({ containerRef, beskeder }: {
  containerRef: RefObject<HTMLElement | null>
  beskeder: ChatMessage[]
}) {
  const [vist, setVist] = useState<{ id: string; tekst: string } | null>(null)
  const brugere = beskeder.filter((m) => m.role === 'user')

  useEffect(() => {
    const el = containerRef.current
    if (!el) return
    let ramme = 0
    const maal = () => {
      ramme = 0
      const top = el.getBoundingClientRect().top
      let fundet: ChatMessage | null = null
      for (const m of brugere) {
        const node = el.querySelector(`[data-rail-id="${CSS.escape(m.id)}"]`)
        if (!node) continue
        const r = node.getBoundingClientRect()
        // Uden højde er den ikke lagt ud endnu — et nul-mål er ikke «rullet væk».
        if (r.bottom === r.top) continue
        // Helt ude af syne OVER toppen → kandidat. Den seneste af dem vinder.
        if (r.bottom < top + 4) fundet = m
        else break
      }
      setVist(fundet ? { id: fundet.id, tekst: tekstAf(fundet) } : null)
    }
    const planlaeg = () => { if (!ramme) ramme = requestAnimationFrame(maal) }
    maal()
    el.addEventListener('scroll', planlaeg, { passive: true })
    const ro = typeof ResizeObserver !== 'undefined' ? new ResizeObserver(planlaeg) : null
    ro?.observe(el)
    return () => { el.removeEventListener('scroll', planlaeg); ro?.disconnect(); if (ramme) cancelAnimationFrame(ramme) }
  }, [containerRef, brugere.length, brugere[brugere.length - 1]?.id]) // eslint-disable-line react-hooks/exhaustive-deps

  if (!vist || !vist.tekst) return null
  return (
    <div className="sticky-prompt-clip">
      <button
        type="button"
        className="sticky-prompt"
        data-testid="sticky-prompt"
        aria-label="Rul til din besked"
        onClick={() => {
          const node = containerRef.current?.querySelector(`[data-rail-id="${CSS.escape(vist.id)}"]`)
          node?.scrollIntoView({ behavior: 'smooth', block: 'start' })
        }}
      >
        {vist.tekst}
      </button>
    </div>
  )
}
