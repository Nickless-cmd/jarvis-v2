import { useEffect, useRef, useState } from 'react'
import { varighed } from '../../lib/jobsApi'

/** Rullende tal til liveness-linjen (Bjørn 4/10-2026).
 *
 *  «sådan som tallende ruller nede fra og op … osse token tællerne i linjen»
 *
 *  Hvert CIFER er sit eget hjul, og hjulet ruller som et mekanisk
 *  kilometertæller-hjul: når cifferet går 9 → 0 mens tallet STIGER, ruller
 *  sporet frem gennem en dublet-0 og sættes tilbage til den ægte 0 — den
 *  springer ikke baglæns gennem 8-7-6. Sek-tiere har cyklus 6 (0-5), så
 *  59 → 00 ruller rigtigt i stedet for at vise et 6-tal undervejs.
 *
 *  Token-tallet kan også FALDE (kontekst-komprimering). Derfor kan hjulet
 *  rulle begge veje: ved fald glider sporet ned og cifferet kommer ovenfra.
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
  const sporRef = useRef<HTMLSpanElement | null>(null)
  const indeksRef = useRef(0)
  const foersteRef = useRef(true)

  // Viklingen lander på dubletten og skal sættes tilbage. Lytteren sidder på
  // hjulet — ikke i en effekt der genstarter pr. værdi — for ellers kunne et
  // hurtigt skift rive lytteren væk og efterlade hjulet på dubletten.
  useEffect(() => {
    const spor = sporRef.current
    if (!spor) return
    const landede = () => {
      if (indeksRef.current !== cyklus) return
      spor.style.transition = 'none'
      indeksRef.current = 0
      spor.style.transform = 'translateY(0em)'
      void spor.offsetHeight
      spor.style.transition = ''
    }
    spor.addEventListener('transitionend', landede)
    return () => spor.removeEventListener('transitionend', landede)
  }, [cyklus])

  useEffect(() => {
    const spor = sporRef.current
    if (!spor) return
    const v = ((vaerdi % cyklus) + cyklus) % cyklus

    const saet = (i: number) => {
      indeksRef.current = i
      spor.style.transform = `translateY(-${i}em)`
    }

    // Ved montering sættes hjulet DIREKTE på tallet. Ellers ville et genbrugt
    // hjul rulle fra 0 til sin værdi, hver gang formen skifter (fx «999» →
    // «1.0k») og React monterer et nyt hjul på samme plads.
    if (foersteRef.current) {
      foersteRef.current = false
      spor.style.transition = 'none'
      saet(v)
      void spor.offsetHeight
      spor.style.transition = ''
      return
    }

    // Står hjulet midt i en vikling, afsluttes den først — ellers ville det
    // nye tal blive kastet væk.
    if (indeksRef.current === cyklus) {
      spor.style.transition = 'none'
      saet(0)
      void spor.offsetHeight
      spor.style.transition = ''
    }

    const nu = indeksRef.current
    if (v === nu) return
    if (retning === 'ned' || v > nu) {
      saet(v)
      return
    }

    // Stigning hvor cifferet går 9 → 0: rul frem gennem dubletten.
    saet(cyklus)
    const noed = window.setTimeout(() => {
      if (indeksRef.current !== cyklus) return
      spor.style.transition = 'none'
      saet(0)
      void spor.offsetHeight
      spor.style.transition = ''
    }, 900)
    return () => window.clearTimeout(noed)
  }, [vaerdi, cyklus, retning])

  const brikker: string[] = []
  for (let i = 0; i <= cyklus; i++) brikker.push(String(i % cyklus))

  return (
    <span className={hurtig ? 'hjul hjul-hurtig' : 'hjul'} aria-hidden="true">
      <span className="hjul-spor" ref={sporRef}>
        {brikker.map((b, i) => (
          <span key={i}>{b}</span>
        ))}
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
  return (
    <>
      {tegn.map((c, i) =>
        /\d/.test(c) ? (
          <CifferHjul
            key={i}
            cyklus={cyklusser?.[i] ?? 10}
            vaerdi={Number(c)}
            retning={retning}
            hurtig={hurtig}
          />
        ) : (
          <span className="tegn" key={i} aria-hidden="true">
            {c}
          </span>
        ),
      )}
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
