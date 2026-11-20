import { createContext, useContext, useEffect, useId, useRef, useState, type ReactNode } from 'react'
import { Linking, Pressable, ScrollView, StyleSheet, Text, View } from 'react-native'
import { AlertTriangle, CheckCircle2, CircleAlert, Info, MapPin } from 'lucide-react-native'
import Svg, { Line, Polyline, Rect as SvgRect } from 'react-native-svg'
import { useStyles, useTheme, type Theme } from '../theme/ThemeContext'
import { WidgetPrompt } from './WidgetFlade'
import { beskrivUdfald, normalisérUdfald, type FladeUdfald } from '../lib/fladeHandling'
import { FladeDeferredTurnContext } from '../lib/fladeDeferredTurn'
import type { DeferredToolUdfald } from '../lib/fladeHandling'
import { lineDiff } from '../lib/diff'
import { interpolérUdtryk } from '../lib/udtryk'
import { kompilérFlade, type FladeProgram } from '../lib/fladeProgram'
import { fladeStatus, settleKontrol, vaelgVisning } from '../lib/fladeVisning'

type Json = Record<string, unknown>
export type NativeSpec =
  | { type: 'callout'; tone: 'info' | 'success' | 'warning' | 'danger'; title: string; body: string }
  | { type: 'stats'; title: string; items: Array<{ label: string; value: string; detail: string }> }
  | { type: 'timeline'; title: string; items: Array<{ time: string; title: string; detail: string; status: 'done' | 'current' | 'next' }> }
  | { type: 'comparison'; title: string; columns: string[]; rows: Array<{ label: string; values: string[] }> }
  | { type: 'choices'; title: string; options: Array<{ label: string; prompt: string }> }
  | { type: 'tool'; title: string; tool: string; arguments: Record<string, unknown>; label: string }
  | { type: 'location'; title: string; address: string; latitude?: number; longitude?: number }
  // `control` (14/11-2026): den FØRSTE flade med lokal state. Slideren rykker
  // uden at noget modelkald går ud — state bor i komponenten, ikke i samtalen.
  | { type: 'control'; title: string; fields: Array<
      | { kind: 'slider'; bind: string; label: string; min: number; max: number; step: number; value: number }
      | { kind: 'text'; text: string }
    > }
  // `box` + katalogudvidelsen (14/11-2026). Samme fem typer som desk — og
  // samme krav: hver type SKAL have en gren i `jarvis_ui_guard.py`, ellers
  // erklaerer guarden den doed og fyrer et modelkald for at «rette» den.
  | { type: 'box'; title: string; children: NativeSpec[]; retning: 'kolonne' | 'raekke' | 'grid' }
  | { type: 'keyvalue'; title: string; items: Array<{ key: string; value: string; detail: string }> }
  | { type: 'progress'; title: string; items: Array<{ label: string; value: number; max: number; detail: string }> }
  | { type: 'quote'; title: string; text: string; source: string; href: string }
  | { type: 'code'; title: string; path: string; language: string; code: string; start: number }
  | { type: 'tabs'; title: string; tabs: Array<{ label: string; children: NativeSpec[] }> }
  // (14/11-2026) Anden boelge — de sidste fem, samme som desk. En type uden
  // guard-gren erklaeres doed og koster et modelkald; en type uden mobil-gren
  // forsvinder paa telefonen mens den virker i desk. Begge dele er fejl.
  | { type: 'table'; title: string; columns: string[]; rows: string[][] }
  | { type: 'chart'; title: string; kind: 'line' | 'bar'; labels: string[]; series: Array<{ name: string; values: number[] }> }
  | { type: 'form'; title: string; fields: Array<
      | { kind: 'slider'; bind: string; label: string; min: number; max: number; step: number; value: number }
      | { kind: 'select'; bind: string; label: string; options: string[]; value: string }
      | { kind: 'toggle'; bind: string; label: string; value: boolean }
      | { kind: 'text'; text: string }
    > }
  | { type: 'tree'; title: string; items: Array<{ name: string; kind: 'dir' | 'file'; depth: number; note: string }> }
  | { type: 'diff'; title: string; path: string; old: string; new: string }
  // Katalogets første skabelon (14/11-2026). Samme kontrakt som desk — de to
  // kopier må ikke drive fra hinanden, ellers ser den samme flade forskellig ud
  // alt efter hvilken app den åbnes i.
  | { type: 'leverance-status'; title: string; items: Array<{ label: string; status: 'leveret' | 'igang' | 'blokeret' | 'naeste'; bevis: string }> }

const text = (v: unknown, max = 500) => typeof v === 'string' ? v.trim().slice(0, max) : ''
const tal = (v: unknown): number | null => typeof v === 'number' && Number.isFinite(v) ? v : null
const list = (v: unknown, max: number): Json[] => Array.isArray(v)
  ? v.filter((x): x is Json => Boolean(x) && typeof x === 'object' && !Array.isArray(x)).slice(0, max)
  : []

/** Lofterne for de typer der baerer boern. Skal matche desk og guarden. */
const BOX_MAX_DYBDE = 3
const BOX_MAX_BOERN = 8
// Anden boelge (14/11-2026). Skal matche `_TABLE_MAX_*` m.fl. i guarden.
const TABLE_MAX_KOLONNER = 12
const TABLE_MAX_RAEKKER = 100
const CHART_MAX_SERIER = 4
const CHART_MAX_PUNKTER = 40
const TREE_MAX_DYBDE = 8

/** Er beskeden fladen sidder i stadig ved at blive streamet? Sat af `MessageBubble`. */
export const FladeStreamingContext = createContext(false)

/** Compile-laget (DIL lag 3). Mobil manglede delvis-JSON helt: en halv blok faldt til rå kode.
 *  `delvis` er KUN sat mens blokken streames — se `lib/delvisJson.ts`. */
export function parseNativeRichSpec(code: string, delvis = false): NativeSpec | null {
  return parseNativeRichProgram(code, delvis).spec
}

export function parseNativeRichProgram(code: string, delvis = false): { spec: NativeSpec | null; program: FladeProgram | null } {
  const program = kompilérFlade(code, delvis)
  if (!program) return { spec: null, program: null }
  return { spec: parseNode(program.rod, 1), program }
}

// Rekursion (14/11-2026): mobil-parseren var FLAD, saa `box` kunne ikke
// parses her — den faldt til `return null` og forsvandt paa telefonen mens
// den saa rigtig ud i desk. Samme flade, to svar. `depth` baeres nu med, saa
// dybde-graensen kan haandhaeves praecis som i desk.
function parseNode(raw: unknown, depth: number): NativeSpec | null {
  if (!raw || typeof raw !== 'object' || Array.isArray(raw)) return null
  return parseNodeObj(raw as Json, depth)
}

function parseNodeObj(raw: Json, depth: number): NativeSpec | null {
  const type = text(raw.type, 30); const title = text(raw.title, 120)
  if (type === 'box') {
    if (depth > BOX_MAX_DYBDE) return null
    const children = list(raw.children, BOX_MAX_BOERN)
      .map((x) => parseNode(x, depth + 1))
      .filter((x): x is NativeSpec => x !== null)
    // `retning` er valgfri: kun `raekke`/`grid` kendes; alt andet = kolonne (gammel adfærd).
    const r = text(raw.retning, 10)
    const retning = r === 'raekke' || r === 'grid' ? r : 'kolonne'
    return children.length ? { type, title, children, retning } : null
  }
  if (type === 'tabs') {
    if (depth > BOX_MAX_DYBDE) return null
    const tabs = list(raw.tabs, 5).map((x) => ({
      label: text(x.label, 60),
      children: list(x.children, BOX_MAX_BOERN)
        .map((c) => parseNode(c, depth + 1))
        .filter((c): c is NativeSpec => c !== null),
    })).filter((x) => x.label && x.children.length)
    return tabs.length >= 2 ? { type, title, tabs } : null
  }
  if (type === 'keyvalue') {
    const items = list(raw.items, 12).map((x) => ({
      key: text(x.key, 80) || text(x.label, 80), value: text(x.value, 240), detail: text(x.detail, 240),
    })).filter((x) => x.key && x.value)
    return items.length ? { type, title, items } : null
  }
  if (type === 'progress') {
    const items = list(raw.items, 8).map((x) => {
      const label = text(x.label, 120)
      const value = tal(x.value)
      const max = tal(x.max) ?? 100
      if (!label || value === null || max <= 0) return null
      return { label, value, max, detail: text(x.detail, 240) }
    }).filter((x): x is NonNullable<typeof x> => Boolean(x))
    return items.length ? { type, title, items } : null
  }
  if (type === 'quote') {
    const body = text(raw.text, 2000)
    return body ? { type, title, text: body, source: text(raw.source, 200), href: text(raw.href, 500) } : null
  }
  if (type === 'code') {
    const kode = text(raw.code, 8000)
    if (!kode) return null
    const start = tal(raw.start)
    return {
      type, title, code: kode, path: text(raw.path, 300), language: text(raw.language, 30),
      start: start !== null && start > 0 ? Math.floor(start) : 1,
    }
  }
  if (type === 'callout') {
    const body = text(raw.body, 1200)
    const tone = ['info', 'success', 'warning', 'danger'].includes(String(raw.tone)) ? String(raw.tone) as 'info' | 'success' | 'warning' | 'danger' : 'info'
    return title || body ? { type, tone, title, body } : null
  }
  if (type === 'stats') {
    const items = list(raw.items, 8).map((x) => ({ label: text(x.label, 80), value: text(x.value, 120), detail: text(x.detail, 240) })).filter((x) => x.label && x.value)
    return items.length ? { type, title, items } : null
  }
  if (type === 'timeline') {
    const items = list(raw.items, 12).map((x) => ({ time: text(x.time, 60), title: text(x.title, 120), detail: text(x.detail, 500), status: ['done', 'current', 'next'].includes(String(x.status)) ? x.status as 'done' | 'current' | 'next' : 'next' })).filter((x) => x.title)
    return items.length ? { type, title, items } : null
  }
  if (type === 'comparison') {
    const columns = Array.isArray(raw.columns) ? raw.columns.map((x) => text(x, 80)).filter(Boolean).slice(0, 4) : []
    // 14/11-2026: PAD i stedet for at kassere — samme regel som desk fik
    // 30/10-2026. Mobil kasserede stadig rækker hvis values var kortere end
    // columns, så den samme flade så rigtig ud i desk og død ud på telefonen.
    const rows = list(raw.rows, 12).map((x) => {
      const givne = Array.isArray(x.values) ? x.values.map((v) => text(v, 240)) : []
      return { label: text(x.label, 100), values: Array.from({ length: columns.length }, (_, i) => givne[i] ?? '') }
    }).filter((x) => x.label && x.values.some(Boolean))
    return columns.length >= 2 && rows.length ? { type, title, columns, rows } : null
  }
  if (type === 'choices') {
    const options = list(raw.options, 6).map((x) => ({ label: text(x.label, 100), prompt: text(x.prompt, 1000) })).filter((x) => x.label && x.prompt)
    return options.length ? { type, title, options } : null
  }
  if (type === 'tool') {
    const tool = text(raw.tool, 120)
    const label = text(raw.label, 120)
    const args = raw.arguments
    return tool && label && args && typeof args === 'object' && !Array.isArray(args)
      ? { type, title, tool, arguments: args as Record<string, unknown>, label }
      : null
  }
  if (type === 'location') {
    const address = text(raw.address, 300)
    const latitude = typeof raw.latitude === 'number' && raw.latitude >= -90 && raw.latitude <= 90 ? raw.latitude : undefined
    const longitude = typeof raw.longitude === 'number' && raw.longitude >= -180 && raw.longitude <= 180 ? raw.longitude : undefined
    return address || (latitude !== undefined && longitude !== undefined) ? { type, title, address, latitude, longitude } : null
  }
  if (type === 'control') {
    const fields = list(raw.fields, 8).map((x) => {
      if (text(x.kind, 20) === 'text') {
        const t = text(x.text, 600)
        return t ? { kind: 'text' as const, text: t } : null
      }
      const bind = text(x.bind, 40)
      const label = text(x.label, 120)
      if (!bind || !label) return null
      const min = tal(x.min)
      const max = tal(x.max)
      if (min === null || max === null || max <= min) return null
      const step = tal(x.step)
      const raaVaerdi = tal(x.value) ?? min
      return {
        kind: 'slider' as const, bind, label, min, max,
        step: step !== null && step > 0 ? step : 1,
        value: Math.min(max, Math.max(min, raaVaerdi)),
      }
    }).filter((x): x is NonNullable<typeof x> => Boolean(x))
    // Mindst ÉN slider: uden et `bind` er der ingen lokal state.
    return fields.some((f) => f.kind === 'slider') ? { type, title, fields } : null
  }
  if (type === 'table') {
    const columns = (Array.isArray(raw.columns) ? raw.columns : [])
      .map((k) => text(k, 80)).filter(Boolean).slice(0, TABLE_MAX_KOLONNER)
    if (!columns.length) return null
    const rows = (Array.isArray(raw.rows) ? raw.rows : [])
      .filter((r): r is unknown[] => Array.isArray(r))
      .map((r) => r.slice(0, columns.length).map((c) => text(c, 300)))
      .filter((r) => r.length === columns.length)
      .slice(0, TABLE_MAX_RAEKKER)
    return rows.length ? { type, title, columns, rows } : null
  }
  if (type === 'chart') {
    const labels = (Array.isArray(raw.labels) ? raw.labels : [])
      .map((l) => text(l, 40)).slice(0, CHART_MAX_PUNKTER)
    const series = list(raw.series, CHART_MAX_SERIER).map((s) => ({
      name: text(s.name, 60),
      values: (Array.isArray(s.values) ? s.values : [])
        .map((v) => tal(v)).filter((v): v is number => v !== null).slice(0, CHART_MAX_PUNKTER),
    })).filter((s) => s.values.length >= 2)
    if (!series.length) return null
    const kind = text(raw.kind, 10) === 'bar' ? 'bar' as const : 'line' as const
    return { type, title, kind, labels, series }
  }
  if (type === 'form') {
    const fields = list(raw.fields, 10).map((x) => {
      const art = text(x.kind, 20)
      if (art === 'text') {
        const t = text(x.text, 600)
        return t ? { kind: 'text' as const, text: t } : null
      }
      const bind = text(x.bind, 40)
      const label = text(x.label, 120)
      if (!bind || !label) return null
      if (art === 'slider') {
        const min = tal(x.min)
        const max = tal(x.max)
        if (min === null || max === null || max <= min) return null
        const step = tal(x.step)
        const raaVaerdi = tal(x.value) ?? min
        return {
          kind: 'slider' as const, bind, label, min, max,
          step: step !== null && step > 0 ? step : 1,
          value: Math.min(max, Math.max(min, raaVaerdi)),
        }
      }
      if (art === 'select') {
        const options = (Array.isArray(x.options) ? x.options : [])
          .map((o) => text(o, 80)).filter(Boolean).slice(0, 12)
        if (options.length < 2) return null
        const val = text(x.value, 80)
        return { kind: 'select' as const, bind, label, options, value: options.includes(val) ? val : options[0] ?? '' }
      }
      if (art === 'toggle') return { kind: 'toggle' as const, bind, label, value: x.value === true }
      return null
    }).filter((x): x is NonNullable<typeof x> => Boolean(x))
    return fields.some((f) => f.kind !== 'text') ? { type, title, fields } : null
  }
  if (type === 'tree') {
    const items = list(raw.items, 60).map((x) => {
      const name = text(x.name, 200)
      if (!name) return null
      const d = tal(x.depth)
      const depth = d !== null && d >= 0 && d <= TREE_MAX_DYBDE ? Math.floor(d) : 0
      return {
        name, depth, note: text(x.note, 160),
        kind: text(x.kind, 10) === 'dir' ? 'dir' as const : 'file' as const,
      }
    }).filter((x): x is NonNullable<typeof x> => Boolean(x))
    return items.length ? { type, title, items } : null
  }
  if (type === 'diff') {
    const foer = text(raw.old, 20000)
    const efter = text(raw.new, 20000)
    if (!foer && !efter) return null
    return { type, title, path: text(raw.path, 300), old: foer, new: efter }
  }
  if (type === 'fil-diff') {
    // Skabelon-alias (14/11-2026): navnet er genvejen, formen er `diff`s.
    const foer = text(raw.old, 20000)
    const efter = text(raw.new, 20000)
    if (!foer && !efter) return null
    return { type: 'diff', title: text(raw.title, 200), path: text(raw.path, 300), old: foer, new: efter }
  }
  if (type === 'maaling-over-tid') {
    // Alias for `chart`. `points` er aliasets navn for `values`.
    const series = list(raw.series, 4).map((x) => {
      const name = text(x.name, 80)
      const kilde = Array.isArray(x.values) ? x.values : (Array.isArray(x.points) ? x.points : [])
      const values = kilde.filter((v): v is number => typeof v === 'number' && Number.isFinite(v)).slice(0, 60)
      return values.length ? { name, values } : null
    }).filter((x): x is NonNullable<typeof x> => Boolean(x))
    if (!series.length) return null
    const labels = Array.isArray(raw.xLabels) ? raw.xLabels.map((v) => text(v, 40)).slice(0, 60) : []
    return { type: 'chart', title: text(raw.title, 200), kind: 'line', labels, series }
  }
  if (type === 'beslutningsvalg') {
    // Alias for `choices`.
    const options = list(raw.options, 6).map((x) => {
      const label = text(x.label, 120)
      if (!label) return null
      return { label, prompt: text(x.prompt, 500) }
    }).filter((x): x is NonNullable<typeof x> => Boolean(x))
    if (!options.length) return null
    return { type: 'choices', title: text(raw.title, 200), options }
  }
  if (type === 'leverance-status') {
    const items = list(raw.items, 12).map((x) => {
      const label = text(x.label, 120)
      if (!label) return null
      const status = ['leveret', 'igang', 'blokeret', 'naeste'].includes(String(x.status))
        ? String(x.status) as 'leveret' | 'igang' | 'blokeret' | 'naeste'
        : 'naeste'
      return { label, status, bevis: text(x.bevis, 300) }
    }).filter((x): x is NonNullable<typeof x> => Boolean(x))
    return items.length ? { type, title, items } : null
  }
  return null
}

// Slideren er diskrete trykfelter, ikke en kontinuerlig skyder: pakken
// `@react-native-community/slider` er ikke installeret, og en ny native-
// afhaengighed til ét felt er ikke prisen vaerd. Trinene regnes fra min/max/step.
const trinVaerdier = (f: { min: number; max: number; step: number }): number[] => {
  const antal = Math.floor((f.max - f.min) / f.step) + 1
  const maks = Math.min(antal, 12)
  return Array.from({ length: maks }, (_, i) => Number((f.min + i * f.step).toFixed(4)))
}

export function NativeRichBlock({
  code,
  hostMessageIsStreaming = false,
  fallbackNode = null,
}: {
  code: string
  hostMessageIsStreaming?: boolean
  /** Vises kun når der hverken er en ny eller en sidst virkende flade. */
  fallbackNode?: ReactNode
}) {
  // DIL lag 4: et nyt program der fejler lader det SIDST VIRKENDE stå.
  const { spec: ny, program } = parseNativeRichProgram(code, hostMessageIsStreaming)
  const sidst = useRef<NativeSpec | null>(null)
  if (ny) sidst.current = ny
  const visning = vaelgVisning(ny, sidst.current)
  const isSourceStreaming = hostMessageIsStreaming && (program === null || program.trunkeret)
  const afsluttet = !isSourceStreaming && !hostMessageIsStreaming
  const [afvigelser, setAfvigelser] = useState<string[]>([])
  // S3: efterkontrol af det tolkede resultat når streamen er stoppet (mobil har ingen DOM-tekst).
  useEffect(() => {
    if (!afsluttet || !ny || !program) { setAfvigelser([]); return }
    setAfvigelser(settleKontrol(program, ny).afvigelser)
  }, [afsluttet, code]) // eslint-disable-line react-hooks/exhaustive-deps
  const styles = useStyles(makeStyles)
  if (!visning.spec) return <>{fallbackNode}</>
  const status = fladeStatus({ isSourceStreaming, hostMessageIsStreaming, fallback: visning.fallback, afvigelser })
  return (
    <View>
      <FladeNode spec={visning.spec} />
      {status ? <Text style={styles.muted} accessibilityLiveRegion="polite">{status}</Text> : null}
    </View>
  )
}

// Hver node er sin EGEN komponent (14/11-2026), saa `control` og `tabs` i et
// barn har deres egen state, og hook-raekkefoelgen er konstant uanset
// fladetype. Foer laa alt i een funktion, hvilket gjorde rekursion umulig.
function FladeNode({ spec }: { spec: NativeSpec }) {
  const styles = useStyles(makeStyles); const theme = useTheme(); const send = useContext(WidgetPrompt)
  const deferred = useContext(FladeDeferredTurnContext)
  const widgetInstanceId = useId()
  const [kontrolVaerdier, setKontrolVaerdi] = useState<Record<string, number | string | boolean>>({})
  const [valgtFane, setValgtFane] = useState(0)
  // Udfaldet af den seneste handling fladen selv satte i gang (14/11-2026).
  // Hooken staar FOER alle betingede returns, saa raekkefoelgen er konstant.
  const [handlingUdfald, setHandlingUdfald] = useState<FladeUdfald | null>(null)
  const [toolUdfald, setToolUdfald] = useState<DeferredToolUdfald | null>(null)
  const [toolResultat, setToolResultat] = useState<unknown>(null)
  const [toolRevision, setToolRevision] = useState(0)
  const [toolKoerer, setToolKoerer] = useState(false)
  // Sortering for `table` (14/11-2026). LOKAL — rører ikke data, sender intet.
  const [sortering, setSortering] = useState<{ kolonne: number; retning: 1 | -1 } | null>(null)
  // `control` har ingen titel — den er et lille haandtag, ikke et kort.
  const heading = 'title' in spec && spec.title ? <Text style={styles.title}>{spec.title}</Text> : null
  if (spec.type === 'box') return <View accessibilityLabel={spec.title || 'Samling'} style={[styles.card, spec.retning === 'raekke' && styles.boxRaekke, spec.retning === 'grid' && styles.boxGrid]}>{heading}
    {spec.children.map((c, i) => <FladeNode key={`${c.type}-${i}`} spec={c} />)}
  </View>
  if (spec.type === 'tabs') {
    // `Math.min` klemmer et gemt indeks der peger ud i tomrummet efter en
    // kortere flade — uden den ville fane-indholdet rendere ingenting.
    const idx = Math.min(valgtFane, spec.tabs.length - 1)
    const aktiv = spec.tabs[idx]
    if (!aktiv) return null
    return <View accessibilityLabel={spec.title || 'Faner'} style={styles.card}>{heading}
      <View style={styles.tabsListe}>{spec.tabs.map((t, i) => (
        <Pressable key={`${t.label}-${i}`} accessibilityRole="tab" accessibilityLabel={t.label}
          accessibilityState={{ selected: i === idx }} onPress={() => setValgtFane(i)}
          style={({ pressed }) => [styles.tab, i === idx && styles.tabAktiv, pressed && styles.pressed]}>
          <Text style={[styles.tabTekst, i === idx && styles.tabTekstAktiv]}>{t.label}</Text>
        </Pressable>
      ))}</View>
      <View style={styles.tabsIndhold}>{aktiv.children.map((c, i) => <FladeNode key={`${c.type}-${i}`} spec={c} />)}</View>
    </View>
  }
  if (spec.type === 'keyvalue') return <View accessibilityLabel={spec.title || 'Fakta'} style={styles.card}>{heading}
    {spec.items.map((x, i) => <View key={`${x.key}-${i}`} style={styles.kvRaekke}>
      <Text style={styles.kvNoegle}>{x.key}</Text>
      <View style={styles.flex}><Text style={styles.kvVaerdi}>{x.value}</Text>{x.detail ? <Text style={styles.body}>{x.detail}</Text> : null}</View>
    </View>)}
  </View>
  if (spec.type === 'progress') return <View accessibilityLabel={spec.title || 'Status'} style={styles.card}>{heading}
    {spec.items.map((x, i) => {
      // Klemt til 0-100: en vaerdi over `max` ville loebe ud over rammen.
      const pct = Math.max(0, Math.min(100, (x.value / x.max) * 100))
      return <View key={`${x.label}-${i}`} style={styles.progressPost}>
        <View style={styles.progressHoved}><Text style={styles.muted}>{x.label}</Text><Text style={styles.strong}>{x.value} / {x.max}</Text></View>
        <View style={styles.progressBjaelke}><View style={[styles.progressFyld, { width: `${pct}%` }]} /></View>
        {x.detail ? <Text style={styles.muted}>{x.detail}</Text> : null}
      </View>
    })}
  </View>
  if (spec.type === 'quote') return <View accessibilityLabel={spec.title || 'Citat'} style={styles.quote}>{heading}
    <Text style={styles.quoteTekst}>{spec.text}</Text>
    {spec.source ? (spec.href
      ? <Pressable accessibilityRole="link" accessibilityLabel={spec.source} onPress={() => void Linking.openURL(spec.href)}>
          <Text style={styles.quoteKilde}>{spec.source}</Text>
        </Pressable>
      : <Text style={styles.quoteKilde}>{spec.source}</Text>) : null}
  </View>
  if (spec.type === 'code') return <View accessibilityLabel={spec.title || 'Kode'} style={styles.codeKasse}>
    {(spec.title || spec.path) ? <View style={styles.codeHoved}>{heading}{spec.path ? <Text style={styles.codeSti}>{spec.path}</Text> : null}</View> : null}
    <ScrollView horizontal showsHorizontalScrollIndicator>
      <View>{spec.code.split('\n').map((l, i) => <View key={i} style={styles.codeLinje}>
        <Text style={styles.codeNr}>{spec.start + i}</Text>
        <Text style={styles.codeTekst}>{l || ' '}</Text>
      </View>)}</View>
    </ScrollView>
  </View>
  if (spec.type === 'callout') {
    const Icon = spec.tone === 'success' ? CheckCircle2 : spec.tone === 'warning' ? AlertTriangle : spec.tone === 'danger' ? CircleAlert : Info
    const color = spec.tone === 'success' ? theme.color.ok : spec.tone === 'warning' ? theme.color.warn : spec.tone === 'danger' ? theme.color.error : theme.color.accent
    return <View accessibilityLabel={spec.title || 'Bemærkning'} style={[styles.card, styles.cardBox, styles.callout, { borderLeftColor: color }]}><Icon size={20} color={color} /><View style={styles.flex}>{heading}{spec.body ? <Text style={styles.body}>{spec.body}</Text> : null}</View></View>
  }
  if (spec.type === 'stats') return <View accessibilityLabel={spec.title || 'Nøgletal'} style={styles.card}>{heading}<View style={styles.wrap}>{spec.items.map((x, i) => <View key={`${x.label}-${i}`} style={styles.stat}><Text style={styles.muted}>{x.label}</Text><Text style={styles.value}>{x.value}</Text>{x.detail ? <Text style={styles.body}>{x.detail}</Text> : null}</View>)}</View></View>
  if (spec.type === 'timeline') return <View accessibilityLabel={spec.title || 'Tidslinje'} style={styles.card}>{heading}{spec.items.map((x, i) => <View key={`${x.title}-${i}`} style={styles.timelineRow}><View style={[styles.dot, x.status === 'done' && styles.dotDone, x.status === 'current' && styles.dotCurrent]} /><View style={styles.flex}>{x.time ? <Text style={styles.muted}>{x.time}</Text> : null}<Text style={styles.strong}>{x.title}</Text>{x.detail ? <Text style={styles.body}>{x.detail}</Text> : null}</View></View>)}</View>
  if (spec.type === 'comparison') return <View accessibilityLabel={spec.title || 'Sammenligning'} style={styles.card}>{heading}<ScrollView horizontal showsHorizontalScrollIndicator><View><View style={styles.tableRow}><Text style={[styles.cell, styles.rowHead]}>Punkt</Text>{spec.columns.map((x) => <Text key={x} style={[styles.cell, styles.strong]}>{x}</Text>)}</View>{spec.rows.map((r, i) => <View key={`${r.label}-${i}`} style={styles.tableRow}><Text style={[styles.cell, styles.rowHead]}>{r.label}</Text>{r.values.map((v, j) => <Text key={j} style={styles.cell}>{v}</Text>)}</View>)}</View></ScrollView></View>
  if (spec.type === 'choices') {
    // (14/11-2026) Samme kontrakt som desk: knappen er ikke tavst doed, og en
    // afvist handling siger det. Mobilen har ingen code mode, saa her er der
    // ingen gate at respektere — fladen er altid i samtalen.
    const tryk = (prompt: string) => {
      // Uden modtager er knappen stadig trykbar — så den må ikke tie. Den
      // gamle gren (`if (!send) return`) gjorde præcis det: en aktiv knap der
      // intet gjorde og intet sagde.
      let ud: FladeUdfald
      try {
        ud = normalisérUdfald(send?.(`[fra valgkort] ${prompt}`))
      } catch (e) {
        ud = { status: 'failed', kode: 'tool_failed', besked: String((e as Error)?.message || e), retryable: true }
      }
      setHandlingUdfald(ud.status === 'failed' ? ud : null)
    }
    const fejlTekst = handlingUdfald ? beskrivUdfald(handlingUdfald) : ''
    return <View accessibilityLabel={spec.title || 'Valgmuligheder'} style={[styles.card, styles.cardBox]}>{heading}
      <View style={styles.wrap}>{spec.options.map((x, i) => <Pressable key={`${x.label}-${i}`} accessibilityRole="button" accessibilityLabel={x.label} onPress={() => tryk(x.prompt)} style={({ pressed }) => [styles.button, pressed && styles.pressed]}><Text style={styles.buttonText}>{x.label}</Text></Pressable>)}</View>
      {fejlTekst ? <Text style={styles.muted} accessibilityRole="text">{fejlTekst}</Text> : null}
    </View>
  }
  if (spec.type === 'tool') {
    const kør = async () => {
      if (!deferred || toolKoerer) return
      setToolKoerer(true)
      const udfald = await deferred.run({
        address: {
          accountId: deferred.accountId,
          conversationId: deferred.conversationId,
          sourceMessageId: deferred.sourceMessageId,
          widgetInstanceId,
          contentRevision: toolRevision,
        },
        tool: spec.tool,
        arguments: spec.arguments,
      })
      setToolUdfald(udfald)
      if (udfald.status === 'delivered') {
        setToolResultat(udfald.result)
        setToolRevision(udfald.address.contentRevision)
      }
      setToolKoerer(false)
    }
    const fejl = toolUdfald?.status === 'failed' ? beskrivUdfald(toolUdfald) : ''
    return <View accessibilityLabel={spec.title || spec.label} style={[styles.card, styles.cardBox]}>{heading}
      <Pressable accessibilityRole="button" accessibilityLabel={spec.label}
        disabled={toolKoerer || !deferred} onPress={() => void kør()}
        style={({ pressed }) => [styles.button, pressed && styles.pressed]}>
        <Text style={styles.buttonText}>{toolKoerer ? 'Arbejder…' : spec.label}</Text>
      </Pressable>
      {toolResultat !== null ? <Text style={styles.body}>{JSON.stringify(toolResultat, null, 2)}</Text> : null}
      {fejl ? <Text style={styles.muted}>{fejl}</Text> : null}
      {toolUdfald?.status === 'failed' && toolUdfald.retryable ? (
        <Pressable accessibilityRole="button" accessibilityLabel="Prøv igen" onPress={() => void kør()}
          style={({ pressed }) => [styles.button, pressed && styles.pressed]}>
          <Text style={styles.buttonText}>Prøv igen</Text>
        </Pressable>
      ) : null}
    </View>
  }
  if (spec.type === 'control') {
    // Sliderens værdi: lokal state først, ellers den værdi fladen kom med.
    const aktuel = (bind: string, fallback: number): number => {
      // `kontrolVaerdier` baerer nu ogsaa tekst og bool (for `form`). Uden
      // typetjekket kunne en `select`-vaerdi lande i en slider.
      const v = kontrolVaerdier[bind]
      return typeof v === 'number' ? v : fallback
    }
    const interpolér = (t: string) => {
      const kontekst: Record<string, unknown> = { ...kontrolVaerdier }
      for (const f of spec.fields) if (f.kind === 'slider') kontekst[f.bind] = aktuel(f.bind, f.value)
      return interpolérUdtryk(t, kontekst).tekst
    }
    return <View style={styles.controlFelter}>{heading}
      {spec.fields.map((f, i) => f.kind === 'slider' ? (
        <View key={`${f.bind}-${i}`} style={styles.controlFelt}>
          <Text style={styles.muted}>{f.label}</Text>
          <View style={styles.controlSkinne}>
            {trinVaerdier(f).map((vaerdi) => {
              const valgt = aktuel(f.bind, f.value) === vaerdi
              return (
                <Pressable
                  key={`${f.bind}-${vaerdi}`}
                  accessibilityRole="adjustable"
                  accessibilityLabel={`${f.label}: ${vaerdi}`}
                  accessibilityState={{ selected: valgt }}
                  onPress={() => setKontrolVaerdi((forrige) => ({ ...forrige, [f.bind]: vaerdi }))}
                  style={[styles.controlTrin, valgt && styles.controlTrinValgt]}
                >
                  <Text style={[styles.controlTrinTekst, valgt && styles.controlTrinTekstValgt]}>{vaerdi}</Text>
                </Pressable>
              )
            })}
          </View>
          <Text style={styles.strong}>{aktuel(f.bind, f.value)}</Text>
        </View>
      ) : <Text key={`t-${i}`} style={styles.body}>{interpolér(f.text)}</Text>)}
    </View>
  }
  if (spec.type === 'table') {
    // Sorteringen er LOKAL (14/11-2026): et tryk paa en kolonne aendrer kun
    // raekkefoelgen her. Det er forskellen til en GFM-tabel, og det koster
    // nul modelkald.
    const raekker = sortering
      ? [...spec.rows].sort((a, b) => {
        const x = a[sortering.kolonne] ?? ''
        const y = b[sortering.kolonne] ?? ''
        const nx = Number(x.replace(',', '.'))
        const ny = Number(y.replace(',', '.'))
        const beggeTal = x.trim() !== '' && y.trim() !== ''
          && Number.isFinite(nx) && Number.isFinite(ny)
        const cmp = beggeTal ? nx - ny : x.localeCompare(y, 'da')
        return cmp * sortering.retning
      })
      : spec.rows
    return <View accessibilityLabel={spec.title || 'Tabel'} style={styles.card}>{heading}
      <ScrollView horizontal showsHorizontalScrollIndicator>
        <View>
          <View style={styles.tableRow}>
            {spec.columns.map((k, i) => <Pressable key={`${k}-${i}`} accessibilityRole="button"
              accessibilityLabel={`Sortér efter ${k}`}
              onPress={() => setSortering((forrige) => forrige?.kolonne === i
                ? { kolonne: i, retning: forrige.retning === 1 ? -1 : 1 }
                : { kolonne: i, retning: 1 })}
              style={styles.tabelHovedCelle}>
              <Text style={styles.rowHead}>{k}{sortering?.kolonne === i ? (sortering.retning === 1 ? ' ▲' : ' ▼') : ''}</Text>
            </Pressable>)}
          </View>
          {raekker.map((r, i) => <View key={i} style={styles.tableRow}>
            {r.map((c, j) => <Text key={j} style={styles.cell}>{c}</Text>)}
          </View>)}
        </View>
      </ScrollView>
    </View>
  }
  if (spec.type === 'chart') {
    // Inline SVG, intet vaerktoejskald. Skalaen regnes fra data, saa en serie
    // der kun aendrer sig lidt stadig fylder hele hoejden.
    const alle = spec.series.flatMap((s) => s.values)
    const min = Math.min(...alle); const maks = Math.max(...alle)
    const spaend = maks - min || 1
    const B = 320, H = 120, P = 8
    const antal = Math.max(...spec.series.map((s) => s.values.length))
    const px = (i: number) => antal <= 1 ? B / 2 : P + (i / (antal - 1)) * (B - 2 * P)
    const py = (v: number) => H - P - ((v - min) / spaend) * (H - 2 * P)
    const bjBredde = (B - 2 * P) / Math.max(1, antal)
    const perSerie = bjBredde / spec.series.length
    return <View accessibilityLabel={spec.title || 'Graf'} style={styles.card}>{heading}
      <Svg viewBox={`0 0 ${B} ${H}`} width="100%" height={H}>
        <Line x1={P} y1={H - P} x2={B - P} y2={H - P} stroke={theme.color.line} strokeWidth={1} />
        {spec.series.map((s, si) => s.values.length < 2 ? null : spec.kind === 'bar'
          ? s.values.map((v, i) => <SvgRect key={`${si}-${i}`} fill={theme.color.accent} opacity={1 - si * 0.22}
              x={P + i * bjBredde + si * perSerie + perSerie * 0.1}
              y={py(v)} width={Math.max(1, perSerie * 0.8)} height={Math.max(0, H - P - py(v))} />
          )
          : <Polyline key={si} fill="none" stroke={theme.color.accent} opacity={1 - si * 0.22}
              strokeWidth={2} strokeLinejoin="round" strokeLinecap="round"
              points={s.values.map((v, i) => `${px(i)},${py(v)}`).join(' ')} />
        )}
      </Svg>
      <View style={styles.wrap}>{spec.series.map((s, i) => (
        <Text key={`${s.name}-${i}`} style={styles.muted}>{s.name || `Serie ${i + 1}`}</Text>
      ))}</View>
    </View>
  }
  if (spec.type === 'form') {
    // Ingen gate her: mobilen har kun chat-visning (`MessageBubble`), ingen
    // code mode — praecis som `control`, der heller ikke er gatet her.
    const talV = (bind: string, fallback: number): number => {
      const v = kontrolVaerdier[bind]
      return typeof v === 'number' ? v : fallback
    }
    const tekstV = (bind: string, fallback: string): string => {
      const v = kontrolVaerdier[bind]
      return typeof v === 'string' ? v : fallback
    }
    const boolV = (bind: string, fallback: boolean): boolean => {
      const v = kontrolVaerdier[bind]
      return typeof v === 'boolean' ? v : fallback
    }
    // Alle felt-typer i konteksten — ikke kun sliderne (14/11-2026).
    const interpolér = (s: string) => {
      const kontekst: Record<string, unknown> = { ...kontrolVaerdier }
      for (const f of spec.fields) {
        if (f.kind === 'text') continue
        if (f.kind === 'slider') kontekst[f.bind] = talV(f.bind, f.value)
        else if (f.kind === 'select') kontekst[f.bind] = tekstV(f.bind, f.value)
        else kontekst[f.bind] = boolV(f.bind, f.value)
      }
      return interpolérUdtryk(s, kontekst).tekst
    }
    return <View accessibilityLabel={spec.title || 'Formular'} style={styles.card}>{heading}
      <View style={styles.controlFelter}>
        {spec.fields.map((f, i) => {
          if (f.kind === 'text') return <Text key={`t-${i}`} style={styles.body}>{interpolér(f.text)}</Text>
          if (f.kind === 'slider') {
            // Samme diskrete trykfelter som `control` — husets moenster for
            // justering uden modelkald.
            const nu = talV(f.bind, f.value)
            const trin: number[] = []
            for (let v = f.min; v <= f.max && trin.length < 12; v += f.step) trin.push(v)
            return <View key={`${f.bind}-${i}`} style={styles.controlFelt}>
              <Text style={styles.muted}>{f.label}</Text>
              <View style={styles.controlSkinne}>{trin.map((vaerdi) => (
                <Pressable key={`${f.bind}-${vaerdi}`} accessibilityRole="adjustable"
                  accessibilityLabel={`${f.label}: ${vaerdi}`} accessibilityState={{ selected: vaerdi === nu }}
                  onPress={() => setKontrolVaerdi((forrige) => ({ ...forrige, [f.bind]: vaerdi }))}
                  style={[styles.controlTrin, vaerdi === nu && styles.controlTrinValgt]}>
                  <Text style={[styles.controlTrinTekst, vaerdi === nu && styles.controlTrinTekstValgt]}>{vaerdi}</Text>
                </Pressable>
              ))}</View>
            </View>
          }
          if (f.kind === 'select') {
            const nu = tekstV(f.bind, f.value)
            return <View key={`${f.bind}-${i}`} style={styles.controlFelt}>
              <Text style={styles.muted}>{f.label}</Text>
              <View style={styles.controlSkinne}>{f.options.map((o) => (
                <Pressable key={o} accessibilityRole="radio" accessibilityLabel={o}
                  accessibilityState={{ selected: o === nu }}
                  onPress={() => setKontrolVaerdi((forrige) => ({ ...forrige, [f.bind]: o }))}
                  style={[styles.controlTrin, o === nu && styles.controlTrinValgt]}>
                  <Text style={[styles.controlTrinTekst, o === nu && styles.controlTrinTekstValgt]}>{o}</Text>
                </Pressable>
              ))}</View>
            </View>
          }
          const til = boolV(f.bind, f.value)
          return <Pressable key={`${f.bind}-${i}`} accessibilityRole="switch" accessibilityLabel={f.label}
            accessibilityState={{ checked: til }}
            onPress={() => setKontrolVaerdi((forrige) => ({ ...forrige, [f.bind]: !til }))}
            style={[styles.controlTrin, til && styles.controlTrinValgt]}>
            <Text style={[styles.controlTrinTekst, til && styles.controlTrinTekstValgt]}>{f.label}</Text>
          </Pressable>
        })}
      </View>
    </View>
  }
  if (spec.type === 'tree') {
    return <View accessibilityLabel={spec.title || 'Struktur'} style={styles.card}>{heading}
      {spec.items.map((x, i) => <View key={`${x.name}-${i}`} style={[styles.treeItem, { paddingLeft: x.depth * 16 }]}>
        <Text style={x.kind === 'dir' ? styles.treeDir : styles.treeNavn}>
          {x.name}{x.kind === 'dir' ? '/' : ''}
        </Text>
        {x.note ? <Text style={styles.muted}>{x.note}</Text> : null}
      </View>)}
    </View>
  }
  if (spec.type === 'diff') {
    // Samme `lineDiff` som desk — filen er kopieret, saa diffen ser ens ud.
    const linjer = lineDiff(spec.old, spec.new)
    const adds = linjer.filter((l) => l.type === 'add').length
    const dels = linjer.filter((l) => l.type === 'del').length
    return <View accessibilityLabel={spec.title || 'Ændring'} style={styles.card}>{heading}
      <View style={styles.diffHoved}>
        {spec.path ? <Text style={styles.codeSti}>{spec.path}</Text> : null}
        <Text style={styles.muted}>+{adds} −{dels}</Text>
      </View>
      <View style={styles.codeKasse}>
        {linjer.map((l, i) => <View key={i} style={[styles.diffLinje,
          l.type === 'add' && styles.diffAdd, l.type === 'del' && styles.diffDel]}>
          <Text style={styles.codeNr}>{l.type === 'add' ? '+' : l.type === 'del' ? '−' : ' '}</Text>
          <Text style={styles.codeTekst}>{l.text || ' '}</Text>
        </View>)}
      </View>
    </View>
  }
  if (spec.type === 'leverance-status') {
    // Samme kontrakt som desk. Ikonet bærer tilstanden sammen med etiketten —
    // farve alene er ikke en etiket.
    const farve = (s: string) => s === 'leveret' ? theme.color.ok : s === 'blokeret' ? theme.color.warn : s === 'igang' ? theme.color.fg2 : theme.color.fg3
    const Ikon = (s: string) => s === 'leveret' ? CheckCircle2 : s === 'blokeret' ? AlertTriangle : s === 'igang' ? CircleAlert : Info
    const ETIKET: Record<string, string> = { leveret: 'Leveret', igang: 'I gang', blokeret: 'Blokeret', naeste: 'Næste' }
    return <View accessibilityLabel={spec.title || 'Leverance'} style={styles.card}>{heading}
      {spec.items.map((x, i) => {
        const I = Ikon(x.status)
        return <View key={`${x.label}-${i}`} style={styles.levRow}>
          <View style={styles.levStatus}>
            <I size={13} color={farve(x.status)} />
            <Text style={[styles.muted, { color: farve(x.status) }]}>{ETIKET[x.status]}</Text>
          </View>
          <View style={styles.flex}>
            <Text style={styles.body}>{x.label}</Text>
            {x.bevis ? <Text style={styles.muted}>{x.bevis}</Text> : null}
          </View>
        </View>
      })}
    </View>
  }
  const q = spec.latitude !== undefined && spec.longitude !== undefined ? `${spec.latitude},${spec.longitude}` : spec.address
  const href = `https://www.openstreetmap.org/search?query=${encodeURIComponent(q)}`
  return <View accessibilityLabel={spec.title || 'Lokation'} style={[styles.card, styles.cardBox, styles.callout]}><MapPin size={22} color={theme.color.accent} /><View style={styles.flex}>{heading}{spec.address ? <Text style={styles.body}>{spec.address}</Text> : null}<Pressable accessibilityRole="link" accessibilityLabel="Åbn kort" onPress={() => void Linking.openURL(href)} style={({ pressed }) => [styles.button, styles.mapButton, pressed && styles.pressed]}><Text style={styles.buttonText}>Åbn kort</Text></Pressable></View></View>
}

const makeStyles = (t: Theme) => StyleSheet.create({
  // `card` er kun luft og mellemrum — data (comparison/timeline/stats) skal
  // ligge i tekstens materiale. `cardBox` er for objekter der skal skille sig
  // ud (callout/choices/location). Målt 24/10-2026 mod DSH's tabel.
  card: { marginVertical: t.spacing.xs, gap: t.spacing.sm },
  // `leverance-status` (14/11-2026): status-kolonne med fast bredde, så
  // etiketterne står på linje uanset ordlængde.
  levRow: { flexDirection: 'row', gap: t.spacing.sm, alignItems: 'flex-start', paddingVertical: 4 },
  levStatus: { flexDirection: 'row', alignItems: 'center', gap: 4, minWidth: 86 },
  boxRaekke: { flexDirection: 'row', flexWrap: 'wrap', alignItems: 'flex-start' },
  boxGrid: { flexDirection: 'row', flexWrap: 'wrap', alignItems: 'flex-start' },
  cardBox: { backgroundColor: t.color.bg1, borderWidth: 1, borderColor: t.color.line, borderRadius: t.radius.lg, padding: t.spacing.md },
  callout: { flexDirection: 'row', alignItems: 'flex-start', borderLeftWidth: 3 },
  flex: { flex: 1, minWidth: 0 }, title: { color: t.color.fg1, fontWeight: '800', fontSize: 15, marginBottom: 4 },
  body: { color: t.color.fg2, lineHeight: 20 }, muted: { color: t.color.fg3, fontSize: 12 }, strong: { color: t.color.fg1, fontWeight: '700' },
  wrap: { flexDirection: 'row', flexWrap: 'wrap', gap: t.spacing.sm },
  stat: { minWidth: 120, flexGrow: 1, flexBasis: 130, backgroundColor: t.color.bg0, borderWidth: 1, borderColor: t.color.line, borderRadius: t.radius.md, padding: t.spacing.sm },
  value: { color: t.color.fg1, fontWeight: '800', fontSize: 20, marginVertical: 2 },
  timelineRow: { flexDirection: 'row', gap: t.spacing.sm, paddingBottom: t.spacing.sm },
  dot: { width: 11, height: 11, borderRadius: 6, borderWidth: 2, borderColor: t.color.fg3, marginTop: 4 },
  dotDone: { backgroundColor: t.color.ok, borderColor: t.color.ok }, dotCurrent: { borderColor: t.color.accent },
  tableRow: { flexDirection: 'row', borderBottomWidth: 1, borderColor: t.color.line },
  cell: { color: t.color.fg2, width: 150, padding: t.spacing.sm }, rowHead: { color: t.color.fg1, fontWeight: '700', width: 120 },
  button: { minHeight: 44, justifyContent: 'center', paddingHorizontal: 14, paddingVertical: 9, borderWidth: 1, borderColor: t.color.line, borderRadius: t.radius.md, backgroundColor: t.color.bg2 },
  buttonText: { color: t.color.fg1, fontWeight: '700' }, pressed: { opacity: .7 }, mapButton: { alignSelf: 'flex-start', marginTop: t.spacing.sm },
  controlFelter: { gap: t.spacing.sm },
  controlFelt: { gap: 4 },
  controlSkinne: { flexDirection: 'row', flexWrap: 'wrap', gap: 6 },
  controlTrin: { minWidth: 44, minHeight: 44, alignItems: 'center', justifyContent: 'center', borderWidth: 1, borderColor: t.color.line, borderRadius: t.radius.md, backgroundColor: t.color.bg2 },
  controlTrinValgt: { borderColor: t.color.accent, backgroundColor: t.color.bg1 },
  controlTrinTekst: { color: t.color.fg2, fontSize: 13 },
  controlTrinTekstValgt: { color: t.color.fg1, fontWeight: '700' },
  // Katalogudvidelse (14/11-2026): keyvalue · progress · quote · code · tabs
  kvRaekke: { flexDirection: 'row', gap: t.spacing.sm, paddingVertical: 6, borderTopWidth: 1, borderColor: t.color.line },
  kvNoegle: { color: t.color.fg3, fontSize: 13, minWidth: 90 },
  kvVaerdi: { color: t.color.fg1 },
  progressPost: { gap: 4 },
  progressHoved: { flexDirection: 'row', justifyContent: 'space-between', gap: t.spacing.sm },
  progressBjaelke: { height: 7, borderRadius: 4, backgroundColor: t.color.bg2, overflow: 'hidden' },
  progressFyld: { height: 7, borderRadius: 4, backgroundColor: t.color.accent },
  // quote: venstrekant i stedet for citationstegn — et uddrag, ikke pynt.
  quote: { marginVertical: t.spacing.xs, paddingLeft: t.spacing.md, borderLeftWidth: 3, borderColor: t.color.line, gap: 4 },
  quoteTekst: { color: t.color.fg1, fontStyle: 'italic', lineHeight: 21 },
  quoteKilde: { color: t.color.fg3, fontSize: 13, textDecorationLine: 'underline' },
  codeKasse: { marginVertical: t.spacing.xs, borderWidth: 1, borderColor: t.color.line, borderRadius: t.radius.md, backgroundColor: t.color.bg1, overflow: 'hidden' },
  codeHoved: { flexDirection: 'row', flexWrap: 'wrap', alignItems: 'baseline', gap: 8, paddingHorizontal: t.spacing.sm, paddingVertical: 8, borderBottomWidth: 1, borderColor: t.color.line },
  codeSti: { color: t.color.fg3, fontSize: 12 },
  codeLinje: { flexDirection: 'row', gap: 10, paddingHorizontal: t.spacing.sm },
  codeNr: { color: t.color.fg3, fontSize: 12, minWidth: 30, textAlign: 'right' },
  codeTekst: { color: t.color.fg2, fontSize: 12, fontFamily: 'monospace' },
  tabsListe: { flexDirection: 'row', flexWrap: 'wrap', gap: 6, marginBottom: t.spacing.sm },
  tab: { minHeight: 36, justifyContent: 'center', paddingHorizontal: 12, borderWidth: 1, borderColor: t.color.line, borderRadius: t.radius.md, backgroundColor: t.color.bg1 },
  tabAktiv: { borderColor: t.color.accent, backgroundColor: t.color.bg2 },
  tabTekst: { color: t.color.fg2, fontSize: 13 },
  tabTekstAktiv: { color: t.color.fg1, fontWeight: '700' },
  tabsIndhold: { gap: t.spacing.sm },
  // Anden boelge (14/11-2026): table · chart · form · tree · diff
  tabelHovedCelle: { justifyContent: 'center', paddingHorizontal: t.spacing.sm, paddingVertical: 6, backgroundColor: t.color.bg1 },
  treeItem: { flexDirection: 'row', alignItems: 'baseline', gap: 8, paddingVertical: 2 },
  treeNavn: { color: t.color.fg2, fontFamily: 'monospace', fontSize: 13 },
  treeDir: { color: t.color.fg1, fontFamily: 'monospace', fontSize: 13, fontWeight: '700' },
  diffHoved: { flexDirection: 'row', flexWrap: 'wrap', alignItems: 'baseline', gap: 8 },
  diffLinje: { flexDirection: 'row', gap: 10, paddingHorizontal: t.spacing.sm },
  diffAdd: { backgroundColor: t.color.bg2 },
  diffDel: { backgroundColor: t.color.bg0 },
})
