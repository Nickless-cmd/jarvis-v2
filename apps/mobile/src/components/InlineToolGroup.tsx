import { Fragment, memo, useEffect, useRef, useState } from 'react'
import { Animated, Easing, LayoutAnimation, Platform, Pressable, ScrollView, StyleSheet, Text, View } from 'react-native'
import { ChevronDown, Code2 } from 'lucide-react-native'
import { useStyles, useTheme, type Theme } from '../theme/ThemeContext'
import { useReducedMotion } from '../lib/useReducedMotion'
import { summarizeRound, summerDiff, type ToolItem } from '../lib/toolGroup'
import { LabelSkift } from './LabelSkift'
import { DiffArk } from './DiffArk'
import { Prikker } from './Prikker'
import { ThinkingSummary } from './ThinkingSummary'

/** Tænke-linje der hører til runden — tegnes inde i folden, på sin plads. */
export interface TankeRaekke {
  key: string
  seconds?: number
  text?: string
  live?: boolean
  messageId?: string
  /**
   * Antallet af kald der kom FØR tanken i samme runde.
   *
   * Desk tegner rundens elementer i den rækkefølge de skete — tanken står
   * MELLEM de kald den hørte til, ikke samlet øverst. Udeladt = 0, altså før
   * det første kald.
   */
  foerKald?: number
}

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
  /**
   * Tankerne der hørte til denne runde. Ligger INDE i folden — ikke som en
   * søskenderække efter linjen — på den plads de havde (`foerKald`).
   *
   * Desk gør præcis det: tænke-blokken er et ELEMENT i `rv-arbejdsdetaljer`,
   * under rundens knap (`RaekkeTranskript.tsx:324`), tegnet som en selvstændig
   * foldbar række med `data-tanke`. Bjørn 29/9-2026: «tænke-linjen ind i
   * runde-linjen efter foldet.. det er det tætteste på chatview I desk».
   *
   * Udeladt/tom = runden har ingen tanke, og chevronen følger som før kun
   * antallet af kald.
   */
  tanker?: TankeRaekke[]
}

/** Klokken vises først efter 5 s mens runden kører (kildens `zS`). */
export const KLOKKE_EFTER_S = 5

/**
 * Hvor meget af et svar der tegnes før det klippes.
 *
 * Et bash-svar kan være hundreder af kB. Uden et loft ville ét kald skubbe
 * resten af runden ud af syne — og det man leder efter er som regel de første
 * linjer. Klippet siges højt i stedet for at fortie resten.
 */
export const SVAR_KLIP = 4000

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
export const InlineToolGroup = memo(function InlineToolGroup({ items, etiket, aabenFraStart, tanker }: Props) {
  const tokens = useTheme()
  const styles = useStyles(makestyles)
  const reduced = useReducedMotion()
  const harTanker = !!tanker?.length
  const [open, setOpen] = useState(!!aabenFraStart && (items.length > 1 || harTanker))
  const [vistAendring, setVistAendring] = useState<ToolItem['aendring']>(null)
  // Hvilke kald i runden der har deres SVAR foldet ud. Ét sæt pr. runde, så
  // flere kald kan stå åbne samtidig — man læser typisk to svar mod hinanden.
  const [aabneSvar, setAabneSvar] = useState<Record<number, boolean>>({})
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
  // «0s» er ikke et tal — det er en runde der blev færdig så hurtigt at der
  // ikke ER noget at vise. SkillLinjen vægter allerede ved ét sekund
  // (`sek >= 1` i SkillLinje.tsx:37); her manglede vægnet, så en runde under
  // et sekund skrev «0s» ud for sit ikon. (Bjørn 29/9-2026: «0s skal væk fra
  // tool result linjen».)
  const visSek = sek == null || sek < 1 || (running && sek < KLOKKE_EFTER_S) ? null : Math.floor(sek)

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
  // MEN bærer runden en tanke, er der noget at folde ud alligevel: tanken.
  const expandable = items.length > 1 || harTanker

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
            {/* Rundens elementer i den rækkefølge de skete: tanken står MELLEM
                de kald den hørte til — ikke samlet øverst. Desk tegner dem
                sådan (`RaekkeTranskript`), og `foerKald` bærer positionen.
                Tanken har sin egen chevron: den er stadig døren til selve
                teksten, ét tryk længere inde. */}
            {items.map((item, i) => (
              <Fragment key={`${item.label}-${i}`}>
                {(tanker ?? []).filter((t) => (t.foerKald ?? 0) === i).map((t) => (
                  <ThinkingSummary
                    key={t.key}
                    seconds={t.seconds}
                    text={t.text}
                    live={t.live}
                    messageId={t.messageId}
                    indlejret
                    // Visningen «Alt» åbner HELE vejen: runden, og tanken i den.
                    aabenFraStart={aabenFraStart}
                  />
                ))}
              {/* En række der redigerede eller skrev en fil kan trykkes: ændringen
                  åbner i diff-arket (Claude Desktop §9: «Click a filename on an
                  Edited or Wrote row»). */}
              {/* Kaldet kan åbnes. Redigerede kald går til diff-arket (rigere
                  end rå tekst); alle andre folder deres SVAR ud — det er dét
                  der gør runden gennemsigtig i stedet for en liste af
                  etiketter (Bjørn 30/9-2026). */}
              {(() => {
                const svar = (item.result ?? '').trim()
                const harSvar = !item.aendring && svar.length > 0
                const aaben = !!aabneSvar[i]
                const kanAabnes = !!item.aendring || harSvar
                return (
                  <>
                    <Pressable
                      style={styles.detailRaekke}
                      disabled={!kanAabnes}
                      onPress={() => item.aendring
                        ? setVistAendring(item.aendring)
                        : setAabneSvar((v) => ({ ...v, [i]: !v[i] }))}
                      accessibilityRole={kanAabnes ? 'button' : 'text'}
                      accessibilityState={kanAabnes ? { expanded: aaben } : undefined}
                      accessibilityLabel={item.aendring
                        ? `${item.label} — vis ændringen`
                        : harSvar ? `${item.label} — vis svaret` : item.label}
                      testID={item.aendring ? `aendring-${i}` : undefined}
                    >
                      {harSvar ? (
                        <ChevronDown
                          size={13}
                          color={tokens.color.fg3}
                          strokeWidth={2}
                          style={{ transform: [{ rotate: aaben ? '0deg' : '-90deg' }] }}
                        />
                      ) : null}
                      <Text style={[styles.detail, item.aendring ? styles.detailLink : null]} numberOfLines={1}>{item.label}</Text>
                      {item.diff ? (
                        // Grøn/rød pr. kald: `ok` og `error`, ikke accent.
                        <View style={styles.tal}>
                          {item.diff.tilfoejet ? <Text style={[styles.talTekst, styles.plus]}>+{item.diff.tilfoejet}</Text> : null}
                          {item.diff.fjernet ? <Text style={[styles.talTekst, styles.minus]}>−{item.diff.fjernet}</Text> : null}
                        </View>
                      ) : null}
                    </Pressable>
                    {harSvar && aaben ? (
                      <View style={styles.svarRamme} testID={`svar-${i}`}>
                        <Text style={styles.svarTekst} selectable>
                          {svar.length > SVAR_KLIP ? `${svar.slice(0, SVAR_KLIP)}\n… afkortet (${svar.length} tegn)` : svar}
                        </Text>
                      </View>
                    ) : null}
                  </>
                )
              })()}
              </Fragment>
            ))}
            {/* Tanker der kom efter det SIDSTE kald i runden. */}
            {(tanker ?? []).filter((t) => (t.foerKald ?? 0) >= items.length).map((t) => (
              <ThinkingSummary
                key={t.key}
                seconds={t.seconds}
                text={t.text}
                live={t.live}
                messageId={t.messageId}
                indlejret
                aabenFraStart={aabenFraStart}
              />
            ))}
          </ScrollView>
        </View>
      ) : null}
      <DiffArk aendring={vistAendring ?? null} onClose={() => setVistAendring(null)} />
    </Animated.View>
  )
})

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
    marginTop: 4, marginHorizontal: 10, marginBottom: 8, maxHeight: 320, overflow: 'hidden',
    backgroundColor: 'rgba(0,0,0,0.25)'
  },
  rammeScroll: { maxHeight: 320 },
  details: { padding: 10, gap: 6 },
  detail: { color: tokens.color.fg3, fontSize: 14, flexShrink: 1 },
  // Trykbar: filen åbner i diff-arket. Understreget svagt — ikke en knap-form.
  detailLink: { color: tokens.color.fg2, textDecorationLine: 'underline', textDecorationColor: tokens.color.line },
  // Tallene står LIGE efter teksten, ikke ude ved kanten.
  detailRaekke: { flexDirection: 'row', alignItems: 'center', gap: 6 },
  // Kaldets svar: rå tekst i fast bredde. Rammen er svagere end foldens egen,
  // så man kan se hvor svaret begynder og etiketten slutter.
  svarRamme: {
    borderLeftWidth: 2, borderLeftColor: tokens.color.line,
    paddingLeft: 8, marginLeft: 6, marginTop: 2, marginBottom: 2
  },
  svarTekst: {
    color: tokens.color.fg3, fontSize: 12, lineHeight: 17,
    fontFamily: Platform.select({ ios: 'Menlo', android: 'monospace', default: 'monospace' })
  },
  tal: { flexDirection: 'row', gap: 6 },
  talTekst: { fontSize: 12.5, fontWeight: '600', fontVariant: ['tabular-nums'] },
  plus: { color: tokens.color.ok },
  minus: { color: tokens.color.error }
})
