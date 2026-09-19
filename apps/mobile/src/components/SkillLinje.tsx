import { useEffect, useRef, useState, type ReactNode } from 'react'
import { Animated, LayoutAnimation, Pressable, ScrollView, StyleSheet, Text, View } from 'react-native'
import { ChevronDown, Sparkles } from 'lucide-react-native'
import { useStyles, useTheme, type Theme } from '../theme/ThemeContext'
import { useReducedMotion } from '../lib/useReducedMotion'
import { scoreTekst, skillOversigt, type SkillKald } from '../lib/skillLinje'
import { GlidendeTekst } from './GlidendeTekst'
import { Prikker } from './Prikker'
import { formatTid } from './InlineToolGroup'

/**
 * Skill-gaten og skill-indlæsningen som deres EGEN linje — portet fra desk
 * (`SkillLine.tsx`), Bjørn 19/9-2026: «ja port skill linje». Før stod de på
 * telefonen som almindelige runde-linjer («Brugte skill_gate»), og det man vil
 * vide — hvilken skill, hvor sikkert, blev den indlæst — var væk.
 *
 *     ✦ Tjekker skills for «lav et regneark» · 2s
 *     ✦ Skill-gate: xlsx · 0,82 · indlæst · 4,2k tegn  ›
 *     ✦ Indlæste skill git-advanced · 6,1k tegn  ›
 *
 * Bygget som runde- og tanke-linjen: ikonet i en fast 20 dp celle, glitter
 * mens den arbejder, prikker og ÉN caret der drejes i samme celle, og
 * indholdet i samme ramme.
 */
export function SkillLinje({ kald }: { kald: SkillKald }) {
  const o = skillOversigt(kald)
  // Løbende tid fra det øjeblik linjen stod der og arbejdede — som runde-linjen.
  const startet = useRef<number | null>(o.koerer ? Date.now() : null)
  const [nu, setNu] = useState(Date.now())
  useEffect(() => {
    if (!o.koerer) return
    if (startet.current == null) startet.current = Date.now()
    const iv = setInterval(() => setNu(Date.now()), 250)
    return () => clearInterval(iv)
  }, [o.koerer])
  const sek = o.koerer && startet.current != null ? (nu - startet.current) / 1000 : null
  const meta = sek != null && sek >= 1 ? [...o.meta, formatTid(sek)] : o.meta
  const titel = o.koerer ? o.titel.replace(/…$/, '') : o.titel

  const har = !!o.beskrivelse || o.matches.length > 1
  return (
    <Linje titel={titel} meta={meta} arbejder={o.koerer} fejl={o.fejl} testID="skill-linje">
      {har ? (
        <>
          {o.beskrivelse ? <Beskrivelse tekst={o.beskrivelse} /> : null}
          {o.matches.length > 1 ? <Matches matches={o.matches.map((m) => ({ ...m, primary: false }))} /> : null}
        </>
      ) : null}
    </Linje>
  )
}

export interface SkillFladeMatch { name: string; score: number; primary: boolean }

/**
 * Skills runtimen selv lagde i prompten — den automatiske gate, uden et kald.
 * Et stærkt match er en INSTRUKS, et svagt et tilbud; linjen skelner dem.
 */
export function SkillFladeLinje({ matches }: { matches: SkillFladeMatch[] }) {
  const sorteret = [...matches].sort((a, b) => b.score - a.score)
  const bedst = sorteret[0]
  if (!bedst) return null
  const staerke = sorteret.filter((m) => m.primary)
  const titel = staerke.length
    ? `Skill-match: ${staerke.map((m) => m.name).join(', ')}`
    : `Skills foreslået: ${sorteret.map((m) => m.name).join(', ')}`
  const meta = staerke.length
    ? [scoreTekst(staerke[0]!.score), 'stærkt match', ...(sorteret.length > staerke.length ? [`+${sorteret.length - staerke.length} svagere`] : [])]
    : [`bedst ${scoreTekst(bedst.score)}`]
  return (
    <Linje titel={titel} meta={meta} arbejder={false} fejl={false} testID="skill-flade">
      <Beskrivelse tekst={staerke.length
        ? 'Runtimen lagde skillet i prompten som instruks: læs det før svaret.'
        : 'Runtimen lagde skills i prompten som tilbud — ikke et krav.'} />
      <Matches matches={sorteret} />
    </Linje>
  )
}

/** Den fælles linje: samme mål og bevægelse som `InlineToolGroup`. */
function Linje({ titel, meta, arbejder, fejl, testID, children }: {
  titel: string
  meta: string[]
  arbejder: boolean
  fejl: boolean
  testID: string
  children?: ReactNode
}) {
  const tokens = useTheme()
  const styles = useStyles(makestyles)
  const reduced = useReducedMotion()
  const [open, setOpen] = useState(false)
  const udfoldelig = !!children
  const drej = useRef(new Animated.Value(0)).current
  useEffect(() => {
    Animated.timing(drej, { toValue: open ? 1 : 0, duration: reduced ? 0 : 150, useNativeDriver: true }).start()
  }, [open, reduced, drej])

  const toggle = () => {
    if (!udfoldelig) return
    if (!reduced) LayoutAnimation.configureNext(LayoutAnimation.create(200, 'easeOut', 'opacity'))
    setOpen((v) => !v)
  }
  const farve = fejl ? tokens.color.error : tokens.color.fg2

  return (
    <View style={styles.wrap}>
      <Pressable
        testID={testID}
        accessibilityRole={udfoldelig ? 'button' : 'text'}
        accessibilityLabel={titel}
        accessibilityState={udfoldelig ? { expanded: open } : undefined}
        disabled={!udfoldelig}
        onPress={toggle}
      >
        <View style={styles.row}>
          <View style={styles.ikon}>
            <Sparkles size={16} color={farve} strokeWidth={1.8} />
          </View>
          <View style={styles.tekst}>
            <GlidendeTekst text={titel} aktiv={arbejder} style={[styles.titel, { color: farve }]} numberOfLines={1} />
            {meta.length ? <Text style={styles.meta} numberOfLines={1}>{meta.map((m) => ` · ${m}`).join('')}</Text> : null}
          </View>
          {arbejder || udfoldelig ? (
            <View style={styles.celle} testID="skill-caret">
              {arbejder ? <Prikker farve={tokens.color.fg2} /> : null}
              {!arbejder && udfoldelig ? (
                <Animated.View style={{ transform: [{ rotate: drej.interpolate({ inputRange: [0, 1], outputRange: ['-90deg', '0deg'] }) }] }}>
                  <ChevronDown size={16} color={tokens.color.fg2} strokeWidth={1.8} />
                </Animated.View>
              ) : null}
            </View>
          ) : null}
        </View>
      </Pressable>
      {open && children ? (
        <View style={styles.ramme}>
          <ScrollView nestedScrollEnabled style={styles.rammeScroll} contentContainerStyle={styles.rammeIndhold}>
            {children}
          </ScrollView>
        </View>
      ) : null}
    </View>
  )
}

function Beskrivelse({ tekst }: { tekst: string }) {
  const styles = useStyles(makestyles)
  return <Text style={styles.beskrivelse}>{tekst}</Text>
}

function Matches({ matches }: { matches: SkillFladeMatch[] }) {
  const styles = useStyles(makestyles)
  return (
    <View style={styles.matches}>
      {matches.map((m) => (
        <View key={m.name} style={styles.match}>
          <Text style={styles.matchNavn} numberOfLines={1}>{m.name}{m.primary ? ' · stærkt' : ''}</Text>
          <Text style={styles.score}>{scoreTekst(m.score)}</Text>
        </View>
      ))}
    </View>
  )
}

const makestyles = (tokens: Theme) => StyleSheet.create({
  wrap: { paddingHorizontal: tokens.spacing.lg },
  row: { flexDirection: 'row', alignItems: 'center', gap: tokens.spacing.sm, paddingVertical: tokens.spacing.sm },
  // Samme mål som runde-linjens celler (InlineToolGroup).
  ikon: { width: 20, height: 20, marginRight: 2, alignItems: 'center', justifyContent: 'center' },
  tekst: { flexDirection: 'row', flexShrink: 1, minWidth: 0, alignItems: 'center' },
  titel: { color: tokens.color.fg2, fontSize: 15, flexShrink: 1 },
  meta: { color: tokens.color.fg3, fontSize: 15, flexShrink: 0, fontVariant: ['tabular-nums'] },
  celle: { minWidth: 16, alignItems: 'center', justifyContent: 'center' },
  ramme: {
    borderWidth: StyleSheet.hairlineWidth, borderColor: tokens.color.line, borderRadius: 8,
    marginTop: 4, marginHorizontal: 10, marginBottom: 8, maxHeight: 200, overflow: 'hidden',
    backgroundColor: 'rgba(0,0,0,0.25)'
  },
  rammeScroll: { maxHeight: 200 },
  rammeIndhold: { padding: 10, gap: 6 },
  beskrivelse: { color: tokens.color.fg3, fontSize: 13, lineHeight: 19 },
  matches: { gap: 2 },
  match: { flexDirection: 'row', justifyContent: 'space-between', gap: 12 },
  matchNavn: { color: tokens.color.fg2, fontSize: 13, flexShrink: 1 },
  score: { color: tokens.color.fg3, fontSize: 13, fontVariant: ['tabular-nums'] }
})
