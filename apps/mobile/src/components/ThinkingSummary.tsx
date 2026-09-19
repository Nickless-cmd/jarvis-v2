import { useEffect, useRef, useState } from 'react'
import { Animated, Easing, LayoutAnimation, Pressable, ScrollView, StyleSheet, Text, View } from 'react-native'
import { Brain, ChevronDown } from 'lucide-react-native'
import { useStyles, useTheme, type Theme } from '../theme/ThemeContext'
import { useReducedMotion } from '../lib/useReducedMotion'
import { useAuthOptional } from '../state/AuthContext'
import { getMessageReasoning } from '../lib/apiClient'
import { loadFullThinking } from '../lib/fullThinking'
import { GlidendeTekst } from './GlidendeTekst'
import { Prikker } from './Prikker'
import { formatTid } from './InlineToolGroup'

/**
 * «🧠 Tænker…» mens den tænker. «🧠 Tænkte i 14 s ›» når den er færdig.
 *
 * Tænkningen forsvinder ikke, den folder sig sammen — og mens den står på,
 * er den én rolig linje med et brain-ikon, præcis som værktøjslinjen
 * (`InlineToolGroup`). Før blev rå CoT smeltet ind i svarets tekstboble;
 * nu står den som sin egen række over værktøjerne.
 *
 * Designmæssigt er den et søskendebarn til `InlineToolGroup`:
 * - Samme ikon + tekst + chevron-layout
 * - Samme padding og fontSize (15)
 * - Samme åndedrag-animation mens den kører
 * - Samme fold-ud når man vil se detaljen
 *
 * Tre tilstande:
 * - `live`: tænkningen streames → «Tænker…» med åndedrag
 * - færdig med målt varighed → «Tænkte i X s»
 * - færdig uden målt varighed men med tekst → «Tænkte» (vi ved den tænkte,
 *   bare ikke hvor længe — så vi påstår ikke et tal vi ikke har)
 *
 * HVOR MEGET MAN SER (12/9-2026). Serveren sender kun HALEN af ræsonneringen
 * (de sidste 4.000 tegn) i blokken — fuld CoT ville sprænge session-pollingen.
 * Det er standarden, og den er ChatGPT-agtig: nok til at følge tanken, ikke
 * hele den interne monolog. En avanceret bruger kan slå HELE strømmen til i
 * indstillingerne; først da hentes resten for den ene besked, dovent.
 */
/**
 * Under så mange sekunder vises varigheden ikke.
 *
 * Målt 14/9-2026 på 1.511 tænke-blokke: 67 % ligger under tre sekunder, mens
 * 90.-percentilen er 8,3 s og den længste 171,7 s. Tærsklen skiller den
 * gentagne talrække fra de pauser der faktisk betyder noget.
 */
export const KORT_TAERSKEL_S = 3

export function ThinkingSummary({
  seconds,
  text,
  live,
  messageId,
  aabenFraStart
}: {
  seconds?: number
  text?: string
  live?: boolean
  /** Beskedens id — nøglen til at hente den FULDE strøm, hvis tilvalget er til. */
  messageId?: string
  /** Visningen «Alt»: tanken står åben fra start. */
  aabenFraStart?: boolean
}) {
  const tokens = useTheme()
  const styles = useStyles(makestyles)
  const [open, setOpen] = useState(!!aabenFraStart)
  const [fullText, setFullText] = useState<string | null>(null)
  const { config } = useAuthOptional()
  const hasText = !!(text ?? '').trim()
  const reduced = useReducedMotion()
  const pulse = useRef(new Animated.Value(1)).current

  const isLive = !!live
  // Under 0,05 s runder ned til «0 s», og «Tænkte i 0 s» er en paastand vi
  // ikke har daekning for — praecis samme skel som `undefined` vs `0` andre
  // steder. Maalt paa Bjoerns skaerm 13/9-2026: to raekker sagde «Tænkte i
  // 0 s» fordi tanken var lynhurtig. Uden tal siger etiketten bare «Tænkte».
  const hasSeconds = seconds != null && Math.round(seconds * 10) / 10 >= 0.1


  useEffect(() => {
    if (!isLive || reduced) {
      pulse.stopAnimation()
      pulse.setValue(1)
      return
    }
    const loop = Animated.loop(
      Animated.sequence([
        Animated.timing(pulse, {
          toValue: 0.4,
          duration: 800,
          easing: Easing.inOut(Easing.ease),
          useNativeDriver: true
        }),
        Animated.timing(pulse, {
          toValue: 1,
          duration: 800,
          easing: Easing.inOut(Easing.ease),
          useNativeDriver: true
        })
      ])
    )
    loop.start()
    return () => loop.stop()
  }, [isLive, reduced, pulse])

  // Caret'en drejes -90° foldet, lige åben (150 ms) — som runde-linjen.
  const drej = useRef(new Animated.Value(0)).current
  useEffect(() => {
    Animated.timing(drej, { toValue: open ? 1 : 0, duration: reduced ? 0 : 150, useNativeDriver: true }).start()
  }, [open, reduced, drej])

  // Intet at vise: ikke live, ingen tekst, ingen målt varighed. EFTER alle
  // hooks — et betinget return før dem ændrer hook-rækkefølgen i det øjeblik
  // linjen går fra tom til noget, og så vælter hele tråden.
  if (!isLive && !hasText && !hasSeconds) return null

  // ROLIG FORM I TRÅDEN. Selve tankestrømmen står i linjen over komponisten;
  // her er det ikon + «Tænker» + prikker der løber. Tråden skal kunne læses
  // mens han tænker, og rå monolog der flimrer i den gør den ulæselig.
  //
  // Prikkerne og lyset siger to forskellige ting: lyset «her arbejdes»,
  // prikkerne «og det tager tid». Ordet alene siger ingen af delene.
  // KORTE TANKER STÅR STILLE (14/9-2026).
  //
  // Jarvis målte Bjørns skærm: tre «Tænkte i X s» på ét billede (1,5 / 2,6 /
  // 1,1 s) — tre af 31 bånd der siger næsten det samme og stjæler
  // opmærksomhed fra de linjer der bærer indhold.
  //
  // Men båndet er også DØREN til selve tanken. Målt på 1.511 tænke-blokke:
  // 67 % er under tre sekunder, og de korte er IKKE tomme — median 457 tegn,
  // nul tomme. At skjule dem ville ikke fjerne støj; det ville skjule 1.018
  // tanker.
  //
  // Derfor mister de korte deres TAL, ikke deres plads. Den gentagne talrække
  // var støjen; døren er ikke.
  const kort = !isLive && hasSeconds && seconds! < KORT_TAERSKEL_S

  // Prikkerne står i cellen ude til højre, som på runde-linjen — ikke i teksten.
  const label = isLive
    ? 'Tænker'
    : hasSeconds && !kort
      // «12s», «1m 5s» — samme format som runde-linjens klokke og Claude
      // Desktop («Thought for {seconds}s»). Bjørn 19/9-2026: «tiden skal være
      // 12s og ikk 12 s».
      ? `Tænkte i ${formatTid(seconds!)}`
      : 'Tænkte'

  // Fold-ud er kun relevant når der er tekst at vise.
  const expandable = hasText

  const toggle = () => {
    if (!expandable) return
    const naeste = !open
    if (!reduced) LayoutAnimation.configureNext(LayoutAnimation.create(200, 'easeOut', 'opacity'))
    setOpen(naeste)
    // Kun når man ÅBNER, tilvalget er slået til, og vi har noget at hente fra.
    // Er halen allerede det hele (en kort ræsonnering), sker der ingenting —
    // den fulde tekst er den samme, og et kald ville være spild.
    if (naeste) void hentFuld()
  }

  /** Hent den fulde strøm — men kun hvis brugeren selv har slået det til.
   *
   *  Self-safe: fejler kaldet (netværk, 404, gammel besked uden gemt
   *  ræsonnering), bliver halen stående. En fejl her må aldrig fjerne noget
   *  brugeren allerede kunne se.
   */
  const hentFuld = async () => {
    if (fullText !== null || !messageId || !config) return
    if (!(await loadFullThinking())) return
    try {
      const fuld = await getMessageReasoning(config, messageId)
      if (fuld.trim()) setFullText(fuld)
    } catch {
      /* behold halen */
    }
  }

  const vist = fullText ?? text

  return (
    <View style={styles.wrap}>
      <Pressable
        testID="thinking-summary"
        accessibilityRole={expandable ? 'button' : 'text'}
        accessibilityLabel={isLive ? label : open ? `${label}, skjul` : `${label}, vis`}
        accessibilityState={expandable ? { expanded: open } : undefined}
        disabled={!expandable}
        onPress={toggle}
        hitSlop={8}
      >
        {/* LYSET GLIDER GENNEM TEKSTEN — hele linjen toner ikke op og ned.
            Et aandedrag siger «noget er i gang»; et lys der vandrer siger det
            samme uden at goere teksten svaer at laese i halvdelen af tiden.
            Man kan laese med mens den koerer. */}
        {/* SAMME opbygning som runde-linjen (Bjørn 19/9-2026: «tænker linje og
            skill linje bør have det samme tema/design/udseende»): ikonet i en
            fast 20 dp celle, glitter mens den tænker, prikker og ÉN caret der
            drejes i samme celle, og tanken i samme ramme som runde-detaljerne. */}
        <View style={styles.row}>
          <View style={styles.ikon}>
            <Brain size={16} color={tokens.color.fg2} strokeWidth={1.8} />
          </View>
          <GlidendeTekst text={label} aktiv={!!isLive} style={styles.label} numberOfLines={1} />
          {isLive || expandable ? (
            <View style={styles.celle} testID="thinking-caret">
              {isLive ? <Prikker farve={tokens.color.fg2} /> : null}
              {!isLive && expandable ? (
                <Animated.View style={{ transform: [{ rotate: drej.interpolate({ inputRange: [0, 1], outputRange: ['-90deg', '0deg'] }) }] }}>
                  <ChevronDown size={16} color={tokens.color.fg2} strokeWidth={1.8} />
                </Animated.View>
              ) : null}
            </View>
          ) : null}
        </View>
      </Pressable>
      {open && vist ? (
        <View style={styles.ramme}>
          <ScrollView nestedScrollEnabled style={styles.rammeScroll} contentContainerStyle={styles.rammeIndhold}>
            <Text selectable style={styles.body}>{vist}</Text>
          </ScrollView>
        </View>
      ) : null}
    </View>
  )
}


const makestyles = (tokens: Theme) => StyleSheet.create({
  wrap: { paddingHorizontal: tokens.spacing.lg },
  row: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: tokens.spacing.sm,
    paddingVertical: tokens.spacing.sm
  },
  label: { color: tokens.color.fg2, fontSize: 15, flexShrink: 1 },
  // Samme mål som runde-linjens celler (InlineToolGroup).
  ikon: { width: 20, height: 20, marginRight: 2, alignItems: 'center', justifyContent: 'center' },
  celle: { minWidth: 16, alignItems: 'center', justifyContent: 'center' },
  ramme: {
    borderWidth: StyleSheet.hairlineWidth, borderColor: tokens.color.line, borderRadius: 8,
    marginTop: 4, marginHorizontal: 10, marginBottom: 8, maxHeight: 200, overflow: 'hidden',
    backgroundColor: 'rgba(0,0,0,0.25)'
  },
  rammeScroll: { maxHeight: 200 },
  rammeIndhold: { padding: 10 },
  body: { color: tokens.color.fg3, fontSize: 14, lineHeight: 21 }
})
