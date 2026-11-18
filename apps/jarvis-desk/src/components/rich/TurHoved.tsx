/**
 * Turens hoved — den ENESTE vandrette streg i samtalen.
 *
 * ## Hvorfor den er delt
 *
 * Code mode og chat mode havde hver sin implementering. Chat-modens var en bar
 * `<div>` uden streg, uden shimmer og uden fold-pil, så de to visninger drev
 * fra hinanden i det øjeblik de blev bygget (målt 17/10-2026: chat viste
 * `.chat-flow-activity`, code viste `.rv-tur`). Bjørn valgte at de skal dele
 * komponenten, ikke bare ligne hinanden — så de ikke KAN divergere igen.
 *
 * ## Kontrakten
 *
 * Højde 33px, tekst i `--rv-tertiary` og fold-pilen i `--fg-3`. Hovedet er
 * bevidst roligt: den levende animation bor i den aktive rundelinje, så to
 * samtidige shimmerfelter ikke konkurrerer.
 *
 * ## Ingen skillestreg (15/11-2026)
 *
 * Hovedet havde en 1px streg under sig, som gled ind når arbejdet begyndte.
 * Bjørn fjernede den i chat mode 14/11 («fjern skill linjen mellem hoved og
 * besked») og i code mode 15/11. Hovedet er en LABEL over indholdet, ikke en
 * selvstændig blok med en streg under — og uden stregen er `skillelinje`,
 * `@keyframes rv-skillelinje-ind` og `::after`-reglen også døde, så de er
 * fjernet frem for at stå som en kapacitet ingen flade kalder.
 */
import { useEffect, useState, type ReactNode, type Ref } from 'react'
import { ChevronDown, ChevronRight } from 'lucide-react'
import { formaterTurTid } from '../../lib/turTid'
import { RullendeTid } from './RullendeTid'
import '../../styles/turhoved.css'

export interface TitelCrossfadeProps {
  /** Serverens aktuelle, sandfærdige arbejdstrin. */
  tekst: string
  /** Kun levende rundelinjer får loftets genstart. */
  aktiv?: boolean
  /** Maksimal tid før den samme titel får en ny transition. */
  intervalMs?: number
  className?: string
}

/**
 * Rundelinjens titeltransition som et loft — ikke et ur der roterer fraser.
 *
 * En ny servertekst skifter straks: det er den primære trigger, og den eneste
 * der kan skifte titlen til noget nyt. Loftet er et VAERN og armes én gang pr.
 * tekst; det fyrer kun hvis der er kommet en anden tekst at skifte til.
 *
 * ## Hvorfor loftet ikke må genarme sig selv (målt 18/11-2026)
 *
 * Stod `vist.transition` i dependency-arrayet, genarmede timeren sig selv, så
 * den fyrede hvert 3,5 s på UÆNDRET tekst. Målt i Chromium: 3 re-fades på 11
 * sekunder hvor teksten aldrig skiftede. Det er en puls, ikke en crossfade —
 * og da vores kilde er serverens `working_step` (målt median 7,22 s mellem
 * ægte skift), ville titlen blinke cirka dobbelt så ofte som sandheden skifter.
 * Hos ChatGPT er `texts` en liste forudskrevne fraser, så et fast ur kan
 * «avancere»; vi har præcis én sand tekst, så der er intet at avancere til.
 *
 * `data-crossfade` er flaget på den ene eksisterende transition; komponenten
 * renderer aldrig to overlappende titler.
 */
export function TitelCrossfade({
  tekst,
  aktiv = false,
  intervalMs = 3500,
  className = '',
}: TitelCrossfadeProps) {
  const [vist, setVist] = useState({ tekst, transition: 0 })

  // Serverens trin er den primære trigger og skal kunne ses i samme render.
  if (vist.tekst !== tekst) {
    setVist({ tekst, transition: vist.transition + 1 })
  }

  // Loftet er et værn, ikke et ur: det armes ÉN gang pr. ny tekst og fyrer
  // kun hvis der er kommet en anden tekst at skifte til. Uændret tekst giver
  // ingen re-fade og ingen ny timer.
  useEffect(() => {
    if (!aktiv || intervalMs <= 0) return
    const timer = window.setTimeout(() => {
      setVist((nu) => (nu.tekst === tekst ? nu : { ...nu, transition: nu.transition + 1 }))
    }, intervalMs)
    return () => window.clearTimeout(timer)
  }, [aktiv, intervalMs, tekst])

  return (
    <span className={`rv-titelCrossfade${className ? ` ${className}` : ''}`}>
      <span
        key={vist.transition}
        className="rv-titelCrossfadeTekst"
        {...(vist.transition > 0 ? { 'data-crossfade': '' } : {})}
      >
        {vist.tekst}
      </span>
    </span>
  )
}

/** Fold-pilen. Et RIGTIGT ikon — ikke teksttegnet ▸/▾ (Bjørn 23/9-2026:
 *  «slippe for ▸ som ikon og så bare bruge den rigtige >»).
 *
 *  Retningen skiftes ved at BYTTE ikonet frem for at rotere det, så stregen
 *  står skarp i begge tilstande — samme greb som forlægget
 *  (DisclosureRow.tsx:68: `leading = open ? <Chevron/> : icon`). */
export function FoldPil({ aaben, className }: { aaben: boolean; className?: string }) {
  return aaben
    ? <ChevronDown className={className} size={14} strokeWidth={1.75} />
    : <ChevronRight className={className} size={14} strokeWidth={1.75} />
}

export interface TurHovedProps {
  /** Linjen der står i hovedet. Klippes med ellipse — ombrydes aldrig. */
  tekst: string
  aaben: boolean
  onToggle: () => void
  /** Markerer at turen kører. Giver ingen shimmer; den bor i rundelinjen. */
  koerer?: boolean
  /** Turens forløbne sekunder. Vises som `42s` / `1m 5s`; `null` = intet ur. */
  sekunder?: number | null
  /** Levende metadata i ENDEN af hovedet, efter uret — fx code-turens
   *  rullende token-tal. Det er turens resultat, ikke en del af varigheden,
   *  så det må ikke stå mellem «Tænkte» og sekunderne (14/11-2026). */
  meta?: ReactNode
  /** Om turen stadig er i gang i DENNE session. Sætter `data-levende`, som er
   *  det eneste der må starte indglidnings-animationen.
   *
   *  Uden den skelnen animerer stregen ved hver mount — også når persisteret
   *  historik genindlæses. Målt 30/10-2026 i Chromium: 20 persisterede ture
   *  gav 20 `animationstart`-events ved reload, og én React-remount gen-fyrer
   *  animationen midt i en samtale. `koerer` duede ikke som markør, fordi den
   *  slukker når svaret begynder at streame. */
  levende?: boolean
  /** Om der er noget at folde. `false` = hovedet er kun en skillestreg med
   *  uret, og fold-pilen skjules, så den ikke lover et indhold der ikke er der
   *  (Bjørn 17/10-2026: hovedet skal stå der også på ture uden værktøjskald). */
  foldbar?: boolean
  knapRef?: Ref<HTMLButtonElement>
}

export function TurHoved({
  tekst, aaben, onToggle, koerer = false, sekunder = null, meta,
  levende = false, foldbar = true, knapRef,
}: TurHovedProps) {
  const tilstand = {
    ...(koerer ? { 'data-koerer': '' } : {}),
    ...(levende ? { 'data-levende': '' } : {}),
  }
  const indhold = (
    <>
      <span className="rv-turIndhold">
        <span className="rv-turTekst">{tekst}</span>
        {/* Uret hører til teksten («Tænkte 12s»), meta hører til RESULTATET og
            står derfor i enden. Bjørn 14/11-2026: token-tallet «hørte til i
            enden af turhoved». Stod det før uret, læste linjen som om tallet
            var en del af varigheden. */}
        {typeof sekunder === 'number' ? (
          <RullendeTid tekst={formaterTurTid(sekunder)} />
        ) : null}
        {meta}
      </span>
      {foldbar ? (
        <span className="rv-turC" aria-hidden="true">
          <FoldPil aaben={aaben} />
        </span>
      ) : null}
    </>
  )

  // Uden indhold at folde er hovedet ikke en knap. En knap der ikke gør noget
  // er en løgn i tabulatorrækkefølgen — samme streg, ingen affordance.
  if (!foldbar) {
    return (
      <div className="rv-tur rv-tur--statisk" {...tilstand}>
        {indhold}
      </div>
    )
  }

  return (
    <button
      type="button"
      ref={knapRef}
      className="rv-tur"
      aria-expanded={aaben}
      {...tilstand}
      onClick={onToggle}
    >
      {indhold}
    </button>
  )
}
