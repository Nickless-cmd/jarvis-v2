import { useEffect, useRef, useState } from 'react'
import { varighed } from '../../lib/jobsApi'

/** Rullende tal til liveness-linjen (Bjørn 4/10-2026).
 *
 *  «sådan som tallende ruller nede fra og op … osse token tællerne i linjen»
 *
 *  Hvert CIFER er sit eget hjul. Det gamle ciffer ruller ud, mens det nye
 *  ruller ind fra den modsatte kant — også ved 9 → 0. Cifrene ligger i samme
 *  gridcelle, så de forbliver almindelig tekst i linjens fælles shimmermaske.
 *
 *  Token-tallet kan også FALDE (kontekst-komprimering). Derfor kan hjulet
 *  rulle begge veje: ved fald glider det gamle ciffer ned, og det nye kommer
 *  ovenfra.
 */

type Retning = 'op' | 'ned'

/** Ét ciffer-hjul. `cyklus` er antallet af tal på hjulet (6 eller 10). */
function CifferHjul({
  cyklus,
  vaerdi,
  retning,
  hurtig,
}: {
  cyklus: number
  vaerdi: number
  retning: Retning
  hurtig?: boolean
}) {
  const v = ((vaerdi % cyklus) + cyklus) % cyklus
  const forrigeRef = useRef<number | null>(null)
  const forrige = forrigeRef.current
  const animer = forrige !== null && forrige !== v
  useEffect(() => {
    forrigeRef.current = v
  }, [v])

  return (
    <span className={hurtig ? 'hjul hjul-hurtig' : 'hjul'} aria-hidden="true">
      {animer ? (
        <span key={`forrige-${forrige}`} className={`hjul-ciffer hjul-ciffer--forrige hjul-ciffer--ud-${retning}`}>
          {forrige}
        </span>
      ) : null}
      <span key={`aktuel-${v}`} className={`hjul-ciffer${animer ? ` hjul-ciffer--ind-${retning}` : ''}`}>
        {v}
      </span>
    </span>
  )
}

/** Ruller hvert CIFER i `tekst`. Ikke-cifre (':', '.', 'k') står stille. */
function Ruller({
  tekst,
  retning,
  cyklusser,
  hurtig,
}: {
  tekst: string
  retning: Retning
  cyklusser?: (number | null)[]
  hurtig?: boolean
}) {
  const tegn = tekst.split('')
  const antal = tegn.length
  return (
    <>
      {tegn.map((c, i) => {
        // Nøglen er afstanden FRA HØJRE, ikke indekset fra venstre.
        //
        // MÅLT 4/10-2026 i mobilen (samme kode): med `key={i}` genbrugte
        // React det forreste hjul da strengen voksede, så «9s» → «10s» lod
        // hjul 0 gå 9 → 1. Da 1 < 9 ramte det viklings-grenen og viste «0» —
        // uret stod på «90s» i stedet for «10s». Med ankeret fra højre
        // beholder 's' sin nøgle, ener-hjulet ruller 9 → 0 (den RIGTIGE
        // rulning), og det nye tier-hjul monteres forfra på sit eget ciffer.
        const anker = antal - i
        return /\d/.test(c) ? (
          <CifferHjul
            key={anker}
            cyklus={cyklusser?.[i] ?? 10}
            vaerdi={Number(c)}
            retning={retning}
            hurtig={hurtig}
          />
        ) : (
          <span className="tegn" key={anker} aria-hidden="true">
            {c}
          </span>
        )
      })}
    </>
  )
}

/** Hvor meget token-tallet dæmpes, i millisekunder.
 *
 *  MÅLT 4/10-2026 med headless chromium: ulaempet token-rulning stod stille
 *  20 % af tiden ved ~60 opdateringer/sek — det er en blur, ikke en rulning.
 *  Ved 1 opdatering/sek stod den stille 76 %.
 *
 *  Bjørn valgte 4/10-2026 den ULAEMPEDE variant — «ur OG tokens ruller».
 *  Den står derfor på 0 med vilje. Det er ÉT tal at skrue på, hvis bluren
 *  generer i drift: 260 giver den rolige rulning målingen pegede på.
 */
const DAEMPNING_MS = 0

/** Dæmpning: vis højst én ny værdi hver `ms`.
 *
 *  `ms = 0` er en gennemløbs-vej: den viste værdi sættes med det samme, så
 *  hjulet følger hvert eneste token-tal.
 */
function useDampet(vaerdi: number, ms: number): number {
  const [vist, setVist] = useState(vaerdi)
  const seneste = useRef(vaerdi)
  const sidste = useRef(0)
  const timer = useRef<number | null>(null)
  seneste.current = vaerdi

  useEffect(() => {
    const nu = Date.now()
    const siden = nu - sidste.current
    if (siden >= ms) {
      sidste.current = nu
      setVist(seneste.current)
      return
    }
    if (timer.current !== null) return
    timer.current = window.setTimeout(() => {
      timer.current = null
      sidste.current = Date.now()
      setVist(seneste.current)
    }, ms - siden)
  }, [vaerdi, ms])

  useEffect(
    () => () => {
      if (timer.current !== null) window.clearTimeout(timer.current)
    },
    [],
  )

  return vist
}

/** Forløbet tid som rullende tal — «5s», «45s», «1m 12s».
 *
 *  Bjørn 4/10-2026: «Den skal tælle Xs så XXs og så Xm og Xs». Formatet
 *  kommer fra `varighed()` — samme funktion som panelet og tænke-tiden
 *  bruger, så hele linjen skriver tiden ens. Det foranstillede «00:» står
 *  ikke og fylder i det første minut, hvor det endnu ikke tæller.
 */
export function RullendeUr({ sek }: { sek: number }) {
  const label = varighed(sek)
  return (
    <span className="rullende" role="timer" aria-label={label}>
      <Ruller tekst={label} retning="op" />
    </span>
  )
}

/** Kontekst-størrelsen som rullende tal — «12.8k», eller «456» under 1000. */
export function RullendeTokens({ tokens }: { tokens: number }) {
  const dampet = useDampet(tokens, DAEMPNING_MS)
  const forrige = useRef(dampet)
  const retning: Retning = dampet >= forrige.current ? 'op' : 'ned'
  useEffect(() => {
    forrige.current = dampet
  }, [dampet])

  const tekst = dampet >= 1000 ? `${(dampet / 1000).toFixed(1)}k` : String(dampet)
  return (
    <span className="rullende" aria-label={tekst}>
      <Ruller tekst={tekst} retning={retning} hurtig />
    </span>
  )
}
