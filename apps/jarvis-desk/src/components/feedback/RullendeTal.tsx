import { useEffect, useRef, useState } from 'react'

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

/** Dæmpning: vis højst én ny værdi hver `ms`.
 *
 *  MÅLT 4/10-2026 med headless chromium: ulaempet token-rulning stod stille
 *  20 % af tiden ved ~60 opdateringer/sek — det er en blur, ikke en rulning.
 *  Ved 1 opdatering/sek stod den stille 76 %. Dæmpningen er derfor ikke
 *  kosmetik: uden den ruller tallet ikke, det vibrerer.
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

/** Forløbet tid som rullende min:sek. */
export function RullendeUr({ sek }: { sek: number }) {
  const m = Math.floor(sek / 60)
  const s = sek % 60
  const label = `${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`
  return (
    <span className="rullende" role="timer" aria-label={label}>
      <Ruller tekst={label} retning="op" cyklusser={[10, 10, null, 6, 10]} />
    </span>
  )
}

/** Kontekst-størrelsen som rullende tal — «12.8k», eller «456» under 1000. */
export function RullendeTokens({ tokens }: { tokens: number }) {
  const dampet = useDampet(tokens, 260)
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
