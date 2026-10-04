import { useEffect, useRef } from 'react'
import { Animated, Easing, StyleSheet, Text, View } from 'react-native'
import { formatTid, kortTokens } from '../lib/arbejdslinje'

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

/** Én ciffer-højde i px. `lineHeight` på hvert ciffer skal matche.
 *
 *  Eksporteret med vilje: nabo-teksten i `Arbejdslinje` SKAL have samme kasse
 *  (se `talTekst`), ellers centrerer rækken en lavere tekstkasse mod denne og
 *  cifferet løftes. Det er samme fejlklasse som desks 3 px-løft. */
export const CIF_HOEJDE = 16

/** Hjulets bredde i px — desk måler 8,05 px ved fontSize 13.
 *
 * 4/10-2026: 8 → 9 da ciffer-fonten gik fra 12 til 13,5 px. Ved 13,5 px er et
 * tabular ciffer ~8,1 px bredt, så 8 klippede det yderste af stregen. */
const CIF_BREDDE = 9

/** Tekststørrelsen for HELE linjen (Bjørn 4/10-2026).
 *
 * «min/sek og token count og den sidste linje skal være samme tekststørrelse
 * — den efter token count er den rette størrelse for hele linjen.»
 *
 * Sætningen i `Arbejdslinje` er 13,5, så hjulene og «tokens» er det også.
 * Eksporteret så nabo-teksten kan bruge PRÆCIS samme tal: to steder der kan
 * drive fra hinanden er den fejlklasse hele denne fil kæmper imod. */
export const TAL_FONT = 13.5

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
  const tegn = tekst.split('')
  const antal = tegn.length
  return (
    <View style={stil.raekke}>
      {tegn.map((c, i) => {
        // Nøglen er afstanden FRA HØJRE, ikke indekset fra venstre.
        //
        // MÅLT 4/10-2026: med `key={i}` genbrugte React det forreste hjul da
        // strengen voksede, så «9s» → «10s» lod hjul 0 gå 9 → 1. Da 1 < 9
        // ramte det viklings-grenen og viste «0» — uret stod på «90s» i
        // stedet for «10s» (og «59s» → «0m 0s»). Med ankeret fra højre
        // beholder 's' sin nøgle, sekundernes ener-hjul ruller 9 → 0 (den
        // RIGTIGE vikling), og det nye tier-hjul monteres forfra på sit eget
        // ciffer. Samme mønster som et kilometertæller-hjul.
        const anker = antal - i
        return /\d/.test(c) ? (
          <CifferHjul
            key={anker}
            cyklus={cyklusser?.[i] ?? 10}
            vaerdi={Number(c)}
            retning={retning}
            hurtig={hurtig}
            farve={farve}
          />
        ) : (
          // Desk giver ikke-cifre en dæmpet farve (`.tegn { color: var(--fg-3) }`),
          // så tallet læses som tallet og skiller sig ud fra ':' og 'k'.
          <Text key={anker} style={[stil.tegn, { color: tegnFarve }]}>{c}</Text>
        )
      })}
    </View>
  )
}

/** Forløbet tid som rullende tal — «5s», «45s», «1m 12s».
 *
 *  Bjørn 4/10-2026: «Den skal tælle Xs så XXs og så Xm og Xs». Formatet
 *  kommer fra `formatTid()` — samme regel som desks `varighed()` og som
 *  mobilens øvrige tider, så begge klienter skriver tiden ens. Det
 *  foranstillede «00:» står ikke og fylder i det første minut, hvor det
 *  endnu ikke tæller.
 */
export function RullendeUr({ sek, farve, tegnFarve }: { sek: number; farve: string; tegnFarve: string }) {
  const label = formatTid(sek)
  return (
    <View
      style={stil.raekke}
      accessibilityRole="timer"
      accessibilityLabel={label}
      testID="rullende-ur"
    >
      <Ruller tekst={label} retning="op" farve={farve} tegnFarve={tegnFarve} />
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
    fontSize: TAL_FONT,
    textAlign: 'center',
    fontVariant: ['tabular-nums'],
  },
  tegn: {
    height: CIF_HOEJDE,
    lineHeight: CIF_HOEJDE,
    fontSize: TAL_FONT,
    fontVariant: ['tabular-nums'],
  },
})
