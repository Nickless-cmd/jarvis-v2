import { useEffect, useState } from 'react'
import { Code2 } from 'lucide-react'

/**
 * Label-skiftet på tool-linjen — Claude Desktops `GS`, porteret (19/9-2026).
 *
 * Kilden: `claude-desktop-unofficial` v2.110.0, `c3e2391e3-CyTSz9uV.js`
 * (`function GS`) og `c7e6c37f6-DBAD18hv.css`. Tallene her er deres; formen er
 * vores. Spec: ~/cc-tool-linje-prompt-til-claude.md (Jarvis og Bjørn).
 *
 * Tre lag i ÉN grid-celle, så de ligger oven i hinanden:
 *
 *  1. sparken — kun i det øjeblik arbejdet SLUTTER. Code2-glyfen (Bjørns valg:
 *     deres spark er deres maskot, den kopierer vi ikke). Den holder i 210 ms
 *     og toner så ud (`spark-afgang`, .42 s linear, 0-50 % fuld).
 *  2. det GAMLE label, på vej ud (.15 s). Når arbejdet slutter, skubbes det
 *     30 px ind (`ps-7.5`) så der er plads til sparken.
 *  3. det NYE label. Ved afslutning kommer det først efter .21 s — efter
 *     sparken — ellers toner det bare ind (.25 s).
 *
 * | hændelse             | spark | gammel label | nyt label          |
 * |----------------------|-------|--------------|--------------------|
 * | arbejdet slutter     | ja    | ud, + 30 px  | ind efter .21 s    |
 * | arbejdet starter     | nej   | ingen exit   | toner ind          |
 * | kun teksten skifter  | nej   | ud           | toner ind          |
 *
 * Oprydningen sker på animationens EGET event, ikke et gæt — med 600 ms som
 * sikkerhedsnet, præcis som kilden. Første gang linjen tegnes animeres intet
 * (kildens `animateFirstLabel` er som standard falsk): en genindlæst tråd skal
 * ikke sende hver linje gennem et skift.
 */
type Label = { tekst: string; arbejder: boolean; id: number }

const OPRYD_MS = 600

export function LabelSkift({
  tekst,
  arbejder,
  className = '',
  fastIkon = false,
}: {
  tekst: string
  arbejder: boolean
  /** Klasse på det aktuelle label — fx glitteret mens der arbejdes. */
  className?: string
  /**
   * Står `</>` fast foran linjen (Bjørn 19/9-2026: «må gerne komme tilbage»),
   * er der intet at overlevere: afslutningen bliver et almindeligt tekstskift
   * uden spark, ellers stod glyfen der to gange et øjeblik.
   */
  fastIkon?: boolean
}) {
  const [vist, setVist] = useState<Label>({ tekst, arbejder, id: 0 })
  const [gammel, setGammel] = useState<Label | null>(null)
  const [spark, setSpark] = useState(false)
  const [efterSpark, setEfterSpark] = useState(false)

  // Afledt tilstand i render, som kilden: skiftet skal ligge i SAMME tegning
  // som den nye tekst. Via en effekt ville den nye tekst stå alene én frame,
  // og det gamle label ville blinke ind bagefter.
  const slutter = vist.arbejder && !arbejder
  const starter = !vist.arbejder && arbejder
  if (vist.tekst !== tekst || slutter || starter) {
    if (starter) {
      setGammel(null)
      setSpark(false)
      setEfterSpark(false)
    } else {
      setGammel(vist)
      setSpark(slutter && !fastIkon)
      setEfterSpark(slutter && !fastIkon)
    }
    setVist({ tekst, arbejder, id: vist.id + 1 })
  }

  // Sikkerhedsnettet: forsvinder et animationend (fanen i baggrunden, et
  // afbrudt skift), må et gammelt lag ikke blive hængende.
  useEffect(() => {
    if (!gammel && !spark) return
    const t = setTimeout(() => { setGammel(null); setSpark(false) }, OPRYD_MS)
    return () => clearTimeout(t)
  }, [gammel, spark])

  const nyKlasse = vist.id === 0
    ? ''
    : efterSpark ? ' ls-ind-efter-spark' : ' ls-ind'

  return (
    <span className="ls-grid">
      {spark && (
        <span
          className="ls-lag ls-spark-afgang"
          aria-hidden="true"
          data-testid="ls-spark"
          onAnimationEnd={(e) => { if (e.target === e.currentTarget) setSpark(false) }}
        >
          <span className="ls-spark"><Code2 size={15} strokeWidth={1.8} /></span>
        </span>
      )}
      {gammel && (
        <span
          key={`g${gammel.id}`}
          className={`ls-lag ls-ud${spark ? ' ls-plads-til-spark' : ''}`}
          aria-hidden="true"
          data-testid="ls-gammel"
          onAnimationEnd={(e) => {
            if (e.target === e.currentTarget && e.animationName === 'ls-fade-ud') setGammel(null)
          }}
        >
          {gammel.tekst}
        </span>
      )}
      {/* To lag i den nye tekst, og hvorfor:
          `linje-titel` bærer `className` (fx `shimmer`) og genmonteres ALDRIG.
          `shimmer-sweep` har 300 ms delay og 1,5 s bane; skiftede noden ved
          hvert tekstskift, startede sweepet forfra hver gang og blev aldrig
          færdigt — det er «shimmeren staller» (Bjørn 17/10-2026). Det indre
          `ls-tekst` er det der får en ny key, så kun fade-ind-animationen
          genstarter. */}
      <span className={`ls-lag linje-titel${className ? ` ${className}` : ''}`}>
        <span key={`n${vist.id}`} className={`ls-tekst${nyKlasse}`}>{vist.tekst}</span>
      </span>
    </span>
  )
}

/**
 * Den levende syntese-linje i chat mode.
 *
 * Samme lag-mekanik som `LabelSkift`, men med én afgørende forskel: en
 * STREAMENDE tekst må ikke krydsfade. Mens modellen skriver samme syntese,
 * kommer der et nyt tegn ad gangen, og en crossfade pr. tegn ville flimre.
 * Derfor:
 *
 *  - samme `noegle` → teksten opdateres PÅ STEDET (ingen animation, og
 *    shimmer-noden genmonteres ikke)
 *  - ny `noegle` (syntesen er erstattet) → den gamle fader ud oveni den nye
 *    i samme grid-celle, så linjen ikke hopper i højden
 *
 * Det er `noegle` der afgør det — ikke en tekst-sammenligning, som ville
 * tage fejl når to synteser tilfældigvis begynder med samme ord.
 */
export function SynteseLinje({ tekst, noegle }: { tekst: string; noegle: number | string }) {
  const [vist, setVist] = useState<{ tekst: string; noegle: number | string; id: number }>({
    tekst,
    noegle,
    id: 0,
  })
  const [gammel, setGammel] = useState<{ tekst: string; id: number } | null>(null)

  // Afledt i render, som LabelSkift: skiftet skal ligge i samme tegning som
  // den nye tekst, ellers står den alene én frame.
  if (vist.noegle !== noegle) {
    setGammel({ tekst: vist.tekst, id: vist.id })
    setVist({ tekst, noegle, id: vist.id + 1 })
  } else if (vist.tekst !== tekst) {
    setVist({ tekst, noegle, id: vist.id })
  }

  // Sikkerhedsnet hvis `animationend` aldrig kommer (fane i baggrunden).
  useEffect(() => {
    if (!gammel) return
    const t = setTimeout(() => setGammel(null), OPRYD_MS)
    return () => clearTimeout(t)
  }, [gammel])

  const nyKlasse = vist.id === 0 ? '' : ' ls-ind'

  return (
    <span className="ls-grid">
      {gammel && (
        <span
          key={`g${gammel.id}`}
          className="ls-lag ls-ud"
          aria-hidden="true"
          data-testid="syntese-gammel"
          onAnimationEnd={(e) => {
            if (e.target === e.currentTarget && e.animationName === 'ls-fade-ud') setGammel(null)
          }}
        >
          {gammel.tekst}
        </span>
      )}
      <span className="ls-lag linje-titel shimmer">
        <span key={`n${vist.id}`} className={`ls-tekst${nyKlasse}`}>{vist.tekst}</span>
      </span>
    </span>
  )
}

/** Klokken i kildens format (`BS`): «12s», «1m 5s», «1h 2m 3s». */
export function formatTid(sek: number): string {
  const s = Math.max(0, Math.floor(sek))
  const t = Math.floor(s / 3600)
  const m = Math.floor((s % 3600) / 60)
  const r = s % 60
  return t > 0 ? `${t}h ${m}m ${r}s` : m > 0 ? `${m}m ${r}s` : `${r}s`
}
