import { useEffect, useRef, useState } from 'react'
import { Animated, Easing, LayoutAnimation, Pressable, ScrollView, StyleSheet, Text, View } from 'react-native'
import { ChevronDown, Code2 } from 'lucide-react-native'
import { useStyles, useTheme, type Theme } from '../theme/ThemeContext'
import { useReducedMotion } from '../lib/useReducedMotion'
import { summarizeRound, summerDiff, type ToolItem } from '../lib/toolGroup'
import { LabelSkift } from './LabelSkift'
import { DiffArk } from './DiffArk'
import { Prikker } from './Prikker'

interface Props {
  items: ToolItem[]
  /**
   * Rundens sætning — «Rettede fejl i login». ERSTATTER den mekaniske tekst
   * (Claude Desktop 1:1, 19/9-2026); før stod den som overskrift over linjen.
   *
   * Skrevet af en lille lokal model på serveren og slået op på kaldets id, så
   * den hæfter sig på DE kald den opsummerer. Kommer live fra streamen og
   * gemt fra beskedens tool_use_summary-blok. Udeladt = den mekaniske tekst.
   */
  etiket?: string
  /** Visningen «Alt»: runden står åben fra start (kan stadig foldes). */
  aabenFraStart?: boolean
}

/** Klokken vises først efter 5 s mens runden kører (kildens `zS`). */
export const KLOKKE_EFTER_S = 5

/** Kildens format (`BS`): «12s», «1m 5s», «1h 2m 3s». */
export function formatTid(sek: number): string {
  const s = Math.max(0, Math.floor(sek))
  const t = Math.floor(s / 3600)
  const m = Math.floor((s % 3600) / 60)
  const r = s % 60
  return t > 0 ? `${t}h ${m}m ${r}s` : m > 0 ? `${m}m ${r}s` : `${r}s`
}

/**
 * Én sammenfoldet linje for en HEL runde værktøjsarbejde — med Claude
 * Desktops bevægelse, 1:1 med desk (Bjørn 19/9-2026: «det skal være præcis
 * sådan i mobil appen osse»). Tallene er læst i deres CSS/JS; se desk'
 * `LabelSkift.tsx` og ~/cc-tool-linje-prompt-til-claude.md.
 *
 * - **`</>`** står fast foran linjen, også når runden er færdig (Bjørns
 *   valg 19/9-2026 — Claude Desktop viser den kun mens der arbejdes).
 * - **Labelen** glitrer mens der arbejdes og skifter med kildens overgange.
 * - **Klokken** venter 5 s mens runden kører; en færdig runde viser sit tal.
 * - **Prikker og caret** deler én celle. Telefonen har ingen hover, så
 *   caret'en står altid fremme på en færdig linje — kildens
 *   `[@media(hover:none)]`. Foldet = drejet -90°, åben = lige (150 ms).
 * - **Entréen**: kildens 430 ms, hvor de første 30 % er usynlige. Blur og
 *   skala sker i den usynlige del, så det der ses er en forsinket fade — og
 *   den er med. (RN har ingen blur; den ville ikke ses alligevel.)
 * - **Folden**: 200 ms med opacitet; indholdet i en ramme på højst 200 dp,
 *   der selv scroller.
 */
export function InlineToolGroup({ items, etiket, aabenFraStart }: Props) {
  const tokens = useTheme()
  const styles = useStyles(makestyles)
  const reduced = useReducedMotion()
  const [open, setOpen] = useState(!!aabenFraStart && items.length > 1)
  const [vistAendring, setVistAendring] = useState<ToolItem['aendring']>(null)
  const running = items.some((i) => i.running)
  const summary = summarizeRound(items)
  const sum = summerDiff(items)

  // Klokken: fra det øjeblik linjen stod der og arbejdede. Strømmen bærer
  // ikke kaldets starttid på mobilen; linjen dukker op når kaldet starter.
  const startet = useRef<number | null>(running ? Date.now() : null)
  const [slut, setSlut] = useState<number | null>(null)
  const [nu, setNu] = useState(Date.now())
  useEffect(() => {
    if (running) {
      if (startet.current == null) startet.current = Date.now()
      setSlut(null)
      const iv = setInterval(() => setNu(Date.now()), 250)
      return () => clearInterval(iv)
    }
    if (startet.current != null && slut == null) setSlut(Date.now())
  }, [running]) // eslint-disable-line react-hooks/exhaustive-deps
  const sek = startet.current == null ? null : ((slut ?? nu) - startet.current) / 1000
  const visSek = sek == null || (running && sek < KLOKKE_EFTER_S) ? null : Math.floor(sek)

  // Entréen — kun når linjen BEGYNDER at arbejde; en genindlæst tråd skal
  // ikke sende hver linje gennem den.
  const entre = useRef(new Animated.Value(running && !reduced ? 0 : 1)).current
  useEffect(() => {
    if (!running || reduced) return
    Animated.sequence([
      Animated.delay(129),                     // 30 % af 430 ms: usynlig
      Animated.timing(entre, { toValue: 1, duration: 301, easing: Easing.out(Easing.ease), useNativeDriver: true }),
    ]).start()
  }, []) // eslint-disable-line react-hooks/exhaustive-deps

  // Caret: drejes -90° når foldet, lige når åben (150 ms).
  const drej = useRef(new Animated.Value(0)).current
  useEffect(() => {
    Animated.timing(drej, { toValue: open ? 1 : 0, duration: reduced ? 0 : 150, useNativeDriver: true }).start()
  }, [open, reduced, drej])

  if (!summary) return null
  // Claude Desktop 1:1 (læst i deres `Tf`: `summary || … || mekanisk`).
  const tekst = etiket ? etiket : summary.replace(/…$/, '')
  // Ét kald har ingen detalje at folde ud — så er caret'en et tomt løfte.
  const expandable = items.length > 1

  const toggle = () => {
    if (!expandable) return
    if (!reduced) LayoutAnimation.configureNext(LayoutAnimation.create(200, 'easeOut', 'opacity'))
    setOpen((v) => !v)
  }

  return (
    <Animated.View style={[styles.wrap, { opacity: entre }]}>
      <Pressable
        accessibilityRole={expandable ? 'button' : 'text'}
        accessibilityLabel={tekst}
        accessibilityState={expandable ? { expanded: open } : undefined}
        onPress={toggle}
        testID="tool-group"
      >
        <View style={styles.row}>
          {/* `</>` står fast — også når runden er færdig (Bjørn 19/9-2026:
              «må gerne komme tilbage»). Claude Desktop viser den kun mens der
              arbejdes; her er det et bevidst valg, i desk og mobil. */}
          <View style={styles.spark} testID="tool-spark">
            <Code2 size={16} color={tokens.color.fg2} strokeWidth={1.8} />
          </View>
          <LabelSkift tekst={tekst} arbejder={running} style={styles.summary} farve={tokens.color.fg2} fastIkon />
          {visSek != null ? (
            <Text style={styles.tid} testID="runde-tid">{formatTid(visSek)}</Text>
          ) : null}
          {/* Summen i selve linjen — foldet som standard ville tallene ellers
              kun ses af den der folder ud. Et nul vises ikke. */}
          {sum ? (
            <View style={styles.tal}>
              {sum.tilfoejet ? <Text style={[styles.talTekst, styles.plus]}>+{sum.tilfoejet}</Text> : null}
              {sum.fjernet ? <Text style={[styles.talTekst, styles.minus]}>−{sum.fjernet}</Text> : null}
            </View>
          ) : null}
          {running || expandable ? (
            <View style={styles.celle} testID="tool-status-caret">
              {running ? <Prikker farve={tokens.color.fg2} /> : null}
              {!running && expandable ? (
                <Animated.View style={{ transform: [{ rotate: drej.interpolate({ inputRange: [0, 1], outputRange: ['-90deg', '0deg'] }) }] }}>
                  <ChevronDown size={16} color={tokens.color.fg2} strokeWidth={1.8} />
                </Animated.View>
              ) : null}
            </View>
          ) : null}
        </View>
      </Pressable>

      {open ? (
        <View style={styles.ramme} testID="tool-group-details">
          <ScrollView nestedScrollEnabled style={styles.rammeScroll} contentContainerStyle={styles.details}>
            {items.map((item, i) => (
              // En række der redigerede eller skrev en fil kan trykkes: ændringen
              // åbner i diff-arket (Claude Desktop §9: «Click a filename on an
              // Edited or Wrote row»).
              <Pressable
                key={`${item.label}-${i}`}
                style={styles.detailRaekke}
                disabled={!item.aendring}
                onPress={() => item.aendring && setVistAendring(item.aendring)}
                accessibilityRole={item.aendring ? 'button' : 'text'}
                accessibilityLabel={item.aendring ? `${item.label} — vis ændringen` : item.label}
                testID={item.aendring ? `aendring-${i}` : undefined}
              >
                <Text style={[styles.detail, item.aendring ? styles.detailLink : null]} numberOfLines={1}>{item.label}</Text>
                {item.diff ? (
                  // Grøn/rød pr. kald: `ok` og `error`, ikke accent.
                  <View style={styles.tal}>
                    {item.diff.tilfoejet ? <Text style={[styles.talTekst, styles.plus]}>+{item.diff.tilfoejet}</Text> : null}
                    {item.diff.fjernet ? <Text style={[styles.talTekst, styles.minus]}>−{item.diff.fjernet}</Text> : null}
                  </View>
                ) : null}
              </Pressable>
            ))}
          </ScrollView>
        </View>
      ) : null}
      <DiffArk aendring={vistAendring ?? null} onClose={() => setVistAendring(null)} />
    </Animated.View>
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
  spark: { width: 20, height: 20, marginRight: 2, alignItems: 'center', justifyContent: 'center' },
  summary: { color: tokens.color.fg2, fontSize: 15 },
  tid: { color: tokens.color.fg2, fontSize: 13, opacity: 0.65, fontVariant: ['tabular-nums'] },
  celle: { minWidth: 16, alignItems: 'center', justifyContent: 'center' },
  // Kildens ramme: ½ dp kant, 8 dp hjørner, 4/10/8 dp margen, højst 200 dp.
  ramme: {
    borderWidth: StyleSheet.hairlineWidth, borderColor: tokens.color.line, borderRadius: 8,
    marginTop: 4, marginHorizontal: 10, marginBottom: 8, maxHeight: 200, overflow: 'hidden',
    backgroundColor: 'rgba(0,0,0,0.25)'
  },
  rammeScroll: { maxHeight: 200 },
  details: { padding: 10, gap: 6 },
  detail: { color: tokens.color.fg3, fontSize: 14, flexShrink: 1 },
  // Trykbar: filen åbner i diff-arket. Understreget svagt — ikke en knap-form.
  detailLink: { color: tokens.color.fg2, textDecorationLine: 'underline', textDecorationColor: tokens.color.line },
  // Tallene står LIGE efter teksten, ikke ude ved kanten.
  detailRaekke: { flexDirection: 'row', alignItems: 'center', gap: 6 },
  tal: { flexDirection: 'row', gap: 6 },
  talTekst: { fontSize: 12.5, fontWeight: '600', fontVariant: ['tabular-nums'] },
  plus: { color: tokens.color.ok },
  minus: { color: tokens.color.error }
})
