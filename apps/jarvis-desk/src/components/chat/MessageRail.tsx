import { useEffect, useRef, useState, type RefObject } from 'react'
import { useSkinneSynlig } from '../../lib/railSynlighed'
import { Pin } from 'lucide-react'

export interface RailAnchor {
  id: string
  label: string
  /** Turen endte i en fejl. Markeres i skinnen, så «hvor gik det galt» kan
   *  besvares uden at scrolle hele samtalen igennem. */
  fejl?: boolean
  /** Kapitel (standard), komprimering eller fastgjort — se `lib/railAnkre.ts`.
   *  «fastgjort» er den ENESTE af de tre brugeren selv har sat. */
  slags?: 'kapitel' | 'komprimering' | 'fastgjort'
  /** Op til tre linjer af SVARET paa turen (spec punkt 3.2).
   *  Etiketten siger hvad man spurgte om; den her siger hvad man fik. */
  svar?: string
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
 *
 * **Svar-kortet (3/10-2026).** Før stod svaret som en blok UNDER hver titel, og
 * hele listen viste titel + svar på én gang. Bjørn: «panelet folder stadig ud,
 * men kun med titler — svaret vises i et rent kort ved den linje musen er på».
 * Han havde ret i at væggen ikke kunne skannes: man ledte efter en titel, men
 * fik to linjers svar oveni for hver eneste række. Nu bærer panelet KUN
 * titlerne, og svaret kommer frem ét sted — ved den række man peger på.
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
  // Hooks staar FOER enhver betinget return; en hook efter et `return null`
  // braekker visningen, og hverken tsc eller testene ser det (17/9-2026).
  const synlig = useSkinneSynlig(containerRef)
  // Hvilken række musen staar paa, og hvor kortet skal staa. `top` maales —
  // ikke gaettes: panelet ruller (max-height + overflow-y), og `offsetTop`
  // ville staa stille mens raekken flyttede sig.
  const [kort, setKort] = useState<{ svar: string; top: number } | null>(null)
  const railRef = useRef<HTMLElement>(null)

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

  // Skinnen trækkes tilbage naar transcriptet er for smalt — den ville ellers
  // folde sig ud hen over samtalen. Kriteriet er transcriptets EGEN bredde,
  // ikke vinduets: aabner man kode-panelet krymper transcriptet uden at
  // vinduet roerer sig. (spec punkt 3.5)
  if (!synlig) return null
  if (anchors.length < 2) return null

  const jump = (id: string) => {
    const c = containerRef.current
    const el = c?.querySelector<HTMLElement>(`[data-rail-id="${CSS.escape(id)}"]`)
    el?.scrollIntoView({ behavior: 'smooth', block: 'start' })
  }

  /** Kortet staar VED den raekke musen er paa. Maalt mod railens egen kant, saa
   *  det foelger raekken ogsaa naar panelet er rullet. En raekke uden svar
   *  rydder kortet — ellers blev det forrige svar staaende ved den nye linje. */
  const visKort = (row: HTMLElement, svar?: string) => {
    const rail = railRef.current
    if (!svar || !rail) { setKort(null); return }
    const r = row.getBoundingClientRect()
    const b = rail.getBoundingClientRect()
    setKort({ svar, top: r.top - b.top })
  }

  return (
    <nav
      className="msg-rail"
      aria-label="Spring til besked"
      ref={railRef}
      onMouseLeave={() => setKort(null)}
    >
      <div className="msg-rail-panel">
        {anchors.map((a, i) => (
          <button
            key={`${a.slags ?? 'kapitel'}:${a.id}`}
            type="button"
            // `er-sidste`: den nederste streg er teal og længere end de andre
            // (Bjørn 16/9-2026) — så man i hvile kan se hvor samtalen slutter.
            className={`msg-rail-row${a.id === aktivId ? ' is-active' : ''}${a.fejl ? ' har-fejl' : ''}${a.slags === 'komprimering' ? ' er-komprimering' : ''}${a.slags === 'fastgjort' ? ' er-fastgjort' : ''}${i === anchors.length - 1 ? ' er-sidste' : ''}`}
            aria-current={a.id === aktivId ? 'true' : undefined}
            onClick={() => jump(a.id)}
            onMouseEnter={(e) => visKort(e.currentTarget, a.svar)}
          >
            <span className="msg-rail-dash" aria-hidden />
            <span className="msg-rail-text" title={a.slags === 'fastgjort' ? `Fastgjort: ${a.label}` : a.label}>
              <span className="msg-rail-spm">
                {a.slags === 'fastgjort' ? <Pin size={9} className="msg-rail-pin" aria-hidden /> : null}
                {a.label}
              </span>
            </span>
          </button>
        ))}
      </div>
      {/* Kortet ligger UDEN FOR panelet med vilje: panelet har
          `overflow-y: auto`, og et kort der stak ud til højre ville blive
          klippet af dets scroll-boks. `pointer-events: none` staar i CSS'en, så
          det ikke fanger musen og får hover'en til at flimre. */}
      {kort ? (
        <div className="msg-rail-kort" style={{ top: kort.top }}>{kort.svar}</div>
      ) : null}
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
