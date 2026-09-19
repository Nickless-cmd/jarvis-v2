import { useEffect, useState, type RefObject } from 'react'
import { CornerLeftUp } from 'lucide-react'
import type { ChatMessage } from '../../lib/api'

function tekstAf(m: ChatMessage): string {
  return (m.content ?? []).map((b) => (b.type === 'text' ? b.text : '')).join(' ').replace(/\s+/g, ' ').trim()
}

/**
 * Tilbage til din egen besked, mens du læser svaret på den — Claude Desktops
 * sticky prompt (cc-desktop-chatview.md §10). Et klik ruller blødt tilbage
 * til beskeden: det er navigation, ikke pynt.
 *
 * ET IKON I HEADEREN, ikke en strimmel over samtalen (Bjørn 19/9-2026: «den
 * står i toppen af chatview og det er lidt træls»). Den lå som en boble
 * ovenpå de øverste linjer af svaret — netop dem man læste. Nu står den ved
 * siden af Visning-øjet, kun når din besked er rullet ud af syne, og teksten
 * står i tooltip'en og i knappens navn.
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
      // ÉN søgning i DOM'en, ikke én pr. bruger-besked (profileret 19/9-2026:
      // under streaming rulles der ved hver delta, og 130 querySelector'er i
      // en DOM på 57.000 elementer var 3,5 % af render-tråden).
      const noder = new Map<string, Element>()
      for (const n of el.querySelectorAll('[data-rail-id]')) noder.set(n.getAttribute('data-rail-id') ?? '', n)
      // Bagfra: svaret er den NYESTE bruger-besked der er helt over toppen.
      // Beskederne står i dokument-rækkefølge, så den første bagfra der er over
      // toppen, er den samme som den sidste forfra — men man står næsten
      // altid nær bunden, så det er et par skridt i stedet for alle.
      let fundet: ChatMessage | null = null
      for (let i = brugere.length - 1; i >= 0; i--) {
        const m = brugere[i]!
        const node = noder.get(m.id)
        if (!node) continue
        const r = node.getBoundingClientRect()
        // Uden højde er den ikke lagt ud endnu — et nul-mål er ikke «rullet væk».
        if (r.bottom === r.top) continue
        if (r.bottom < top + 4) { fundet = m; break }
      }
      // Samme besked som før = samme tilstand; ellers renderede kortet om ved
      // hver rulle-frame.
      setVist((f) => (fundet ? (f?.id === fundet.id ? f : { id: fundet.id, tekst: tekstAf(fundet) }) : null))
    }
    const planlaeg = () => { if (!ramme) ramme = requestAnimationFrame(maal) }
    maal()
    el.addEventListener('scroll', planlaeg, { passive: true })
    const ro = typeof ResizeObserver !== 'undefined' ? new ResizeObserver(planlaeg) : null
    ro?.observe(el)
    return () => { el.removeEventListener('scroll', planlaeg); ro?.disconnect(); if (ramme) cancelAnimationFrame(ramme) }
  }, [containerRef, brugere.length, brugere[brugere.length - 1]?.id]) // eslint-disable-line react-hooks/exhaustive-deps

  if (!vist || !vist.tekst) return null
  const kort = vist.tekst.length > 140 ? `${vist.tekst.slice(0, 140)}…` : vist.tekst
  return (
    <button
      type="button"
      className="panel-toggle sticky-prompt"
      data-testid="sticky-prompt"
      aria-label={`Rul til din besked: ${kort}`}
      title={`Rul til din besked:\n${kort}`}
      onClick={() => {
        const node = containerRef.current?.querySelector(`[data-rail-id="${CSS.escape(vist.id)}"]`)
        node?.scrollIntoView({ behavior: 'smooth', block: 'start' })
      }}
    >
      <CornerLeftUp size={15} strokeWidth={1.8} />
    </button>
  )
}
