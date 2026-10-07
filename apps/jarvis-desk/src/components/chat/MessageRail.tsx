import { useEffect, useRef, useState, type RefObject } from 'react'
import { useSkinneSynlig } from '../../lib/railSynlighed'
import { Bookmark, Pin } from 'lucide-react'

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
 * beskeder). Klik scroller.
 *
 * **1:1 med Codex (4/10-2026).** Bjørn sendte fem skærmbilleder og bad om
 * railen «1:1». Det der ændrede sig, er HVAD der vises hvornår:
 *
 *  - I hvile er der KUN streger. Ingen titel-liste folder ud — hverken ved
 *    hover på railen eller på rækken. Rækkehøjden er 8px, altså 6px luft
 *    mellem to 2px streger.
 *  - Den række musen er på bliver længere (26px) og fuld hvid.
 *  - Et kort kommer frem VED den række: spørgsmålet i fed som første linje
 *    (klippet med «…»), svaret i op til tre dæmpede linjer under, og et
 *    bogmærke-ikon øverst til højre. Det er derfor han kalder den *saved*rail.
 *  - Den NEDERSTE streg er grøn og 18px — længere end en almindelig (13px),
 *    kortere end hover (26px) — og den vokser ALDRIG. Den viser hvor samtalen
 *    slutter; den er ikke en markør der flytter sig.
 *  - Ingen rød nogen steder i railen. En fejlet tur meldes i kortet.
 *
 * Før bar panelet titlerne og kortet KUN svaret. Nu bærer kortet begge, og
 * panelet bærer ingen tekst — det var den væg der gjorde listen uskannelig.
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
  const [kort, setKort] = useState<{
    label: string; svar?: string; fejl?: boolean; fastgjort?: boolean; top: number
  } | null>(null)
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
   *  det foelger raekken ogsaa naar panelet er rullet.
   *
   *  4/10-2026: kortet vises nu ogsaa naar turen ikke HAR et svar. Foer ryddede
   *  et tomt svar kortet helt, og saa stod raekken uden noget at laese — men
   *  spoergsmaalet findes altid, og det er den ene linje der siger hvad raekken
   *  ER. Kun naar musen forlader railen helt, ryddes kortet. */
  const visKort = (row: HTMLElement, a: RailAnchor) => {
    const rail = railRef.current
    if (!rail) { setKort(null); return }
    const r = row.getBoundingClientRect()
    const b = rail.getBoundingClientRect()
    setKort({
      label: a.label,
      svar: a.svar,
      fejl: a.fejl,
      fastgjort: a.slags === 'fastgjort',
      top: r.top - b.top,
    })
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
            // `er-sidste`: den nederste streg er grøn og længere end de andre
            // (Bjørn 16/9-2026) — så man i hvile kan se hvor samtalen slutter.
            // Den vokser ikke ved hover (se CSS'en).
            className={`msg-rail-row${a.id === aktivId ? ' is-active' : ''}${a.fejl ? ' har-fejl' : ''}${a.slags === 'komprimering' ? ' er-komprimering' : ''}${a.slags === 'fastgjort' ? ' er-fastgjort' : ''}${i === anchors.length - 1 ? ' er-sidste' : ''}`}
            aria-current={a.id === aktivId ? 'true' : undefined}
            // Rækken har ingen synlig tekst mere — kortet bærer spørgsmålet.
            // Uden det her stod knappen uden tilgængeligt navn.
            aria-label={a.label}
            onClick={() => jump(a.id)}
            onMouseEnter={(e) => visKort(e.currentTarget, a)}
          >
            <span className="msg-rail-dash" aria-hidden />
          </button>
        ))}
      </div>
      {/* Kortet ligger UDEN FOR panelet med vilje: panelet har
          `overflow-y: auto`, og et kort der stak ud til højre ville blive
          klippet af dets scroll-boks. `pointer-events: none` staar i CSS'en, så
          det ikke fanger musen og får hover'en til at flimre. */}
      {kort ? (
        <div className="msg-rail-kort" style={{ top: kort.top }}>
          <div className="msg-rail-kort-top">
            <span className="msg-rail-kort-spm">{kort.label}</span>
            {kort.fastgjort
              ? <Pin size={13} className="msg-rail-kort-ikon" aria-hidden />
              : <Bookmark size={13} className="msg-rail-kort-ikon" aria-hidden />}
          </div>
          {kort.svar ? <div className="msg-rail-kort-svar">{kort.svar}</div> : null}
          {/* Den røde streg er væk fra railen (Bjørn 4/10-2026: «den røde
              farve i dit rail irriterer mig»). «Hvor gik det galt» besvares i
              stedet her, hvor der er plads til at sige det med ord. */}
          {kort.fejl ? <div className="msg-rail-kort-fejl">Turen endte i en fejl</div> : null}
        </div>
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
