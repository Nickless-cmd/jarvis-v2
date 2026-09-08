import { useEffect, useState, type RefObject } from 'react'

export interface RailAnchor {
  id: string
  label: string
  /** Turen endte i en fejl. Markeres i skinnen, så «hvor gik det galt» kan
   *  besvares uden at scrolle hele samtalen igennem. */
  fejl?: boolean
}

/**
 * Navigations-skinne: en lodret indholdsfortegnelse i venstre kant.
 *
 * **Omskrevet 8/9-2026.** Bjørn: «det er rimelig useriøst lige nu og
 * ufunktionelt». Han havde ret, og grunden var konkret: skinnen markerede
 * ALTID den sidste besked som aktiv — `is-active` var hardkodet til
 * `anchors[anchors.length - 1]`. Den fortalte altså ikke hvor man var; den
 * fortalte hvor samtalen sluttede, hvilket man i forvejen ved. En
 * indholdsfortegnelse uden position er en liste.
 *
 * Nu følger markeringen scroll-positionen (IntersectionObserver på de faktiske
 * beskeder), og en tur der endte i fejl får en rød streg. Så svarer skinnen på
 * de to spørgsmål man har når man scroller i en lang samtale: hvor er jeg, og
 * hvor gik det galt.
 *
 * I hvile vises kun streger; hover folder titlerne ud. Klik scroller.
 */
export function MessageRail({
  containerRef,
  anchors,
}: {
  containerRef: RefObject<HTMLElement | null>
  anchors: RailAnchor[]
}) {
  // Start på det FØRSTE anker frem for på ingenting. Så findes markeringen fra
  // første billede, også hvis positions-effekten af en eller anden grund ikke
  // når at køre — en skinne uden markering ser død ud, og det var netop
  // klagen.
  const [aktivId, setAktivId] = useState<string | null>(anchors[0]?.id ?? null)

  // Positionen: det SIDSTE anker der er rullet forbi toppen — altså
  // overskriften på det afsnit man står i. En ren «er den synlig»-test
  // markerede ingenting så snart man stod midt i et langt svar, og så virkede
  // skinnen død netop når man havde mest brug for den.
  //
  // Målt på de faktiske elementer, ikke på scroll-tal: beskedernes højde
  // ændrer sig mens indhold folder sig ud, så et regnestykke ville drive.
  useEffect(() => {
    const c = containerRef.current
    if (!c || anchors.length < 2) return
    let ventende = 0
    const beregn = () => {
      ventende = 0
      const top = c.getBoundingClientRect().top
      let valgt: string | null = null
      for (const a of anchors) {
        const el = c.querySelector(`[data-rail-id="${CSS.escape(a.id)}"]`)
        if (!el) continue
        const r = el.getBoundingClientRect()
        // 8px slæk: et anker der lige akkurat rører toppen regnes som passeret.
        if (r.top - top <= 8) valgt = a.id
        else break               // ankrene står i rækkefølge — resten er under
      }
      // Står man over det første anker, er man i det første afsnit.
      setAktivId(valgt ?? anchors[0]?.id ?? null)
    }
    const planlaeg = () => {
      if (ventende) return
      ventende = requestAnimationFrame(beregn)
    }
    beregn()
    c.addEventListener('scroll', planlaeg, { passive: true })
    return () => {
      c.removeEventListener('scroll', planlaeg)
      if (ventende) cancelAnimationFrame(ventende)
    }
  }, [containerRef, anchors])

  if (anchors.length < 2) return null

  const jump = (id: string) => {
    const c = containerRef.current
    const el = c?.querySelector<HTMLElement>(`[data-rail-id="${CSS.escape(id)}"]`)
    el?.scrollIntoView({ behavior: 'smooth', block: 'start' })
  }

  return (
    <nav className="msg-rail" aria-label="Spring til besked">
      <div className="msg-rail-panel">
        {anchors.map((a) => (
          <button
            key={a.id}
            type="button"
            className={`msg-rail-row${a.id === aktivId ? ' is-active' : ''}${a.fejl ? ' har-fejl' : ''}`}
            aria-current={a.id === aktivId ? 'true' : undefined}
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

/**
 * Kort uddrag af en besked til skinnens etiket.
 *
 * FØRSTE LINJE, ikke de første 80 tegn. En besked der starter med to linjers
 * indledning gav før et fragment der stoppede midt i et ord — og en
 * indholdsfortegnelse hvor punkterne ikke kan læses, er ingen
 * indholdsfortegnelse.
 */
export function railLabel(content: unknown): string {
  if (!Array.isArray(content)) return 'Besked'
  const raa = content
    .map((b) => (b && typeof b === 'object' && (b as { type?: string }).type === 'text' ? (b as { text?: string }).text ?? '' : ''))
    .join('')
  const linje = raa
    .split('\n')
    .map((l) => l.replace(/^[\s>#*\-•]+/, '').trim())
    .find((l) => l.length > 0)
  if (!linje) return 'Besked'
  return linje.length > 72 ? `${linje.slice(0, 71)}…` : linje
}

/**
 * Byg skinnens ankre af hele besked-listen.
 *
 * Ét sted, to kaldere (chat + code). Fejl-markeringen kan KUN afgøres her:
 * bruger-beskeden bærer ingen fejl — den ligger i svaret bagefter. Så for hvert
 * anker ses der frem til næste bruger-besked, og fandtes der et værktøjskald
 * der fejlede undervejs, markeres turen.
 */
export function railAnchors(
  messages: Array<{ id: string; role: string; content: unknown }>,
): RailAnchor[] {
  const ud: RailAnchor[] = []
  for (let i = 0; i < messages.length; i++) {
    const m = messages[i]!
    if (m.role !== 'user') continue
    let fejl = false
    for (let j = i + 1; j < messages.length && messages[j]!.role !== 'user'; j++) {
      if (harFejl(messages[j]!.content)) { fejl = true; break }
    }
    ud.push({ id: m.id, label: railLabel(m.content), fejl })
  }
  return ud
}

function harFejl(content: unknown): boolean {
  if (!Array.isArray(content)) return false
  return content.some((b) => {
    if (!b || typeof b !== 'object') return false
    const o = b as { type?: string; status?: string; is_error?: boolean }
    return o.status === 'error' || o.is_error === true
  })
}
