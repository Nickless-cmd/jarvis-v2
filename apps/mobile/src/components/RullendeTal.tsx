import { useEffect, useRef } from 'react'
import { Animated, Easing, StyleSheet, Text, View } from 'react-native'
import { kortTokens } from '../lib/arbejdslinje'

/**
 * Rullende tal til arbejdslinjen i mobilen (Bjørn 4/10-2026).
 *
 * «de rullende tal for tid og token count i arbejds linjen i mobilen … ska
 *  osse laves»
 *
 * Samme mekanik som desks `RullendeTal.tsx`: hvert CIFER er sit eget hjul,
 * klippet til én ciffer-højde, og hjulet ruller som et mekanisk
 * kilometertæller-hjul — når cifferet går 9 → 0 mens tallet STIGER, ruller
 * sporet frem gennem en dublet-0 og sættes tilbage til den ægte 0. Det
 * springer ikke baglæns gennem 8-7-6. Sek-tiere har cyklus 6 (0-5), så
 * 59 → 00 ruller rigtigt i stedet for at vise et 6-tal undervejs.
 *
 * ## Hvorfor den er skrevet om og ikke genbrugt
 *
 * Desks udgave er ren web-DOM: `<span>`, CSS-transitions og
 * `translateY(-Nem)`. Ingen af delene findes i React Native. FORMEN er den
 * samme, men bæreren er en anden: et `Animated.Value` i PIXELS og en
 * `transform: [{ translateY }]` — samme mønster som `AnimeretPuls.tsx`, som
 * er mobilens eget eksempel på netop det.
 *
 * ## Rytmen er desk's, målt
 *
 * Desk ruller 450 ms med `cubic-bezier(.22, 1, .36, 1)` og har en kortere
 * overgang (220 ms) til token-hjulene, fordi token-tallet skifter langt
 * hyppigere. Begge tal er hentet fra `liveness.css` og står her, så de to
 * klienter bevæger sig ens — ikke som en gættet efterligning.
 *
 * ## Tallet kan også FALDE
 *
 * Kontekst-komprimering får token-tallet til at falde. Derfor kan hjulet
 * rulle begge veje: ved fald glider sporet ned og cifferet kommer ovenfra.
 */

type Retning = 'op' | 'ned'

/** Én ciffer-højde i px. `lineHeight` på hvert ciffer skal matche. */
const CIF_HOEJDE = 16

/** Hjulets bredde i px — desk måler 8,05 px ved fontSize 13. */
const CIF_BREDDE = 8

/** Rulningens varighed: desk's `.45s`. */
const RUL_MS = 450

/** Token-hjulenes kortere overgang: desk's `.22s`. */
const HURTIG_MS = 220

/** Desk's kurve, `cubic-bezier(.22, 1, .36, 1)`. */
const KURVE = Easing.bezier(0.22, 1, 0.36, 1)

/**
 * Ét ciffer-hjul. `cyklus` er antallet af tal på hjulet (6 eller 10), og
 * sporet bærer `cyklus + 1` brikker: 0..cyklus-1 plus en dublet-0 at rulle
 * ind i ved viklingen.
 */
function CifferHjul({
  cyklus,
  vaerdi,
  retning,
  hurtig,
  farve,
}: {
  cyklus: number
  vaerdi: number
  retning: Retning
  hurtig?: boolean
  farve: string
}) {
  // Start-positionen sættes ved OPRETTELSEN, ikke først i effekten. Ellers
  // ville sporet stå på ciffer 0 i ét frame og hoppe til sit eget ciffer
  // bagefter — et lille synligt hop, netop når linjen dukker op.
  const start = ((vaerdi % cyklus) + cyklus) % cyklus
  const pos = useRef(new Animated.Value(-start * CIF_HOEJDE)).current
  const indeks = useRef(0)
  const foerste = useRef(true)
  const loeb = useRef<Animated.CompositeAnimation | null>(null)

  useEffect(() => {
    const v = ((vaerdi % cyklus) + cyklus) % cyklus

    // Ved montering sættes hjulet DIREKTE på tallet. Ellers ville et genbrugt
    // hjul rulle fra 0 til sin værdi, hver gang formen skifter (fx «999» →
    // «1.0k»), hvor React monterer et nyt hjul på samme plads.
    if (foerste.current) {
      foerste.current = false
      indeks.current = v
      pos.setValue(-v * CIF_HOEJDE)
      return
    }

    if (v === indeks.current) return

    // Står hjulet midt i en vikling, afsluttes den først — ellers ville det
    // nye tal blive kastet væk.
    loeb.current?.stop()

    const rulTil = (i: number, efter?: () => void) => {
      indeks.current = i
      const a = Animated.timing(pos, {
        toValue: -i * CIF_HOEJDE,
        duration: hurtig ? HURTIG_MS : RUL_MS,
        easing: KURVE,
        useNativeDriver: true,
      })
      loeb.current = a
      a.start(({ finished }) => {
        if (finished) efter?.()
      })
    }

    if (retning === 'ned' || v > indeks.current) {
      rulTil(v)
      return
    }

    // Stigning hvor cifferet går 9 → 0: rul frem gennem dubletten og sæt
    // tilbage til den ægte 0 bagefter.
    rulTil(cyklus, () => {
      indeks.current = 0
      pos.setValue(0)
    })
  }, [vaerdi, cyklus, retning, hurtig, pos])

  useEffect(() => () => { loeb.current?.stop() }, [])

  const brikker: number[] = []
  for (let i = 0; i <= cyklus; i++) brikker.push(i % cyklus)

  return (
    <View style={stil.hjul}>
      <Animated.View style={{ transform: [{ translateY: pos }] }}>
        {brikker.map((b, i) => (
          <Text key={i} style={[stil.ciffer, { color: farve }]}>{b}</Text>
        ))}
      </Animated.View>
    </View>
  )
}

/** Ruller hvert CIFER i `tekst`. Ikke-cifre (':', '.', 'k') står stille. */
function Ruller({
  tekst,
  retning,
  cyklusser,
  hurtig,
  farve,
  tegnFarve,
}: {
  tekst: string
  retning: Retning
  cyklusser?: (number | null)[]
  hurtig?: boolean
  farve: string
  tegnFarve: string
}) {
  return (
    <View style={stil.raekke}>
      {tekst.split('').map((c, i) =>
        /\d/.test(c) ? (
          <CifferHjul
            key={i}
            cyklus={cyklusser?.[i] ?? 10}
            vaerdi={Number(c)}
            retning={retning}
            hurtig={hurtig}
            farve={farve}
          />
        ) : (
          // Desk giver ikke-cifre en dæmpet farve (`.tegn { color: var(--fg-3) }`),
          // så tallet læses som tallet og skiller sig ud fra ':' og 'k'.
          <Text key={i} style={[stil.tegn, { color: tegnFarve }]}>{c}</Text>
        ),
      )}
    </View>
  )
}

/** Forløbet tid som rullende min:sek. */
export function RullendeUr({ sek, farve, tegnFarve }: { sek: number; farve: string; tegnFarve: string }) {
  const m = Math.floor(sek / 60)
  const s = sek % 60
  const label = `${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`
  return (
    <View
      style={stil.raekke}
      accessibilityRole="timer"
      accessibilityLabel={label}
      testID="rullende-ur"
    >
      <Ruller
        tekst={label}
        retning="op"
        cyklusser={[10, 10, null, 6, 10]}
        farve={farve}
        tegnFarve={tegnFarve}
      />
    </View>
  )
}

/** Kontekst-størrelsen som rullende tal — «12.8k», eller «456» under 1000. */
export function RullendeTokens({ tokens, farve, tegnFarve }: { tokens: number; farve: string; tegnFarve: string }) {
  const forrige = useRef(tokens)
  const retning: Retning = tokens >= forrige.current ? 'op' : 'ned'
  useEffect(() => {
    forrige.current = tokens
  }, [tokens])

  const tekst = kortTokens(tokens)
  return (
    <View style={stil.raekke} accessibilityLabel={tekst} testID="rullende-tokens">
      <Ruller tekst={tekst} retning={retning} hurtig farve={farve} tegnFarve={tegnFarve} />
    </View>
  )
}

const stil = StyleSheet.create({
  raekke: { flexDirection: 'row', alignItems: 'center' },
  // Klippet til ÉN ciffer-højde, så rullingen sker indefra og der ikke er
  // nogen synlig bane — se `overflow: hidden`.
  hjul: { height: CIF_HOEJDE, width: CIF_BREDDE, overflow: 'hidden' },
  ciffer: {
    height: CIF_HOEJDE,
    lineHeight: CIF_HOEJDE,
    fontSize: 12,
    textAlign: 'center',
    fontVariant: ['tabular-nums'],
  },
  tegn: {
    height: CIF_HOEJDE,
    lineHeight: CIF_HOEJDE,
    fontSize: 12,
    fontVariant: ['tabular-nums'],
  },
})
