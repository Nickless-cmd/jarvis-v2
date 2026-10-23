import { useContext } from 'react'
import { Linking, Pressable, ScrollView, StyleSheet, Text, View } from 'react-native'
import { AlertTriangle, CheckCircle2, CircleAlert, Info, MapPin } from 'lucide-react-native'
import { useStyles, useTheme, type Theme } from '../theme/ThemeContext'
import { WidgetPrompt } from './WidgetFlade'

type Json = Record<string, unknown>
export type NativeSpec =
  | { type: 'callout'; tone: 'info' | 'success' | 'warning' | 'danger'; title: string; body: string }
  | { type: 'stats'; title: string; items: Array<{ label: string; value: string; detail: string }> }
  | { type: 'timeline'; title: string; items: Array<{ time: string; title: string; detail: string; status: 'done' | 'current' | 'next' }> }
  | { type: 'comparison'; title: string; columns: string[]; rows: Array<{ label: string; values: string[] }> }
  | { type: 'choices'; title: string; options: Array<{ label: string; prompt: string }> }
  | { type: 'location'; title: string; address: string; latitude?: number; longitude?: number }

const text = (v: unknown, max = 500) => typeof v === 'string' ? v.trim().slice(0, max) : ''
const list = (v: unknown, max: number): Json[] => Array.isArray(v)
  ? v.filter((x): x is Json => Boolean(x) && typeof x === 'object' && !Array.isArray(x)).slice(0, max)
  : []

export function parseNativeRichSpec(code: string): NativeSpec | null {
  let raw: Json
  try { raw = JSON.parse(code) as Json } catch { return null }
  if (!raw || typeof raw !== 'object' || Array.isArray(raw)) return null
  const type = text(raw.type, 30); const title = text(raw.title, 120)
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
    const rows = list(raw.rows, 12).map((x) => ({ label: text(x.label, 100), values: Array.isArray(x.values) ? x.values.map((v) => text(v, 240)).slice(0, columns.length) : [] })).filter((x) => x.label && x.values.length === columns.length)
    return columns.length >= 2 && rows.length ? { type, title, columns, rows } : null
  }
  if (type === 'choices') {
    const options = list(raw.options, 6).map((x) => ({ label: text(x.label, 100), prompt: text(x.prompt, 1000) })).filter((x) => x.label && x.prompt)
    return options.length ? { type, title, options } : null
  }
  if (type === 'location') {
    const address = text(raw.address, 300)
    const latitude = typeof raw.latitude === 'number' && raw.latitude >= -90 && raw.latitude <= 90 ? raw.latitude : undefined
    const longitude = typeof raw.longitude === 'number' && raw.longitude >= -180 && raw.longitude <= 180 ? raw.longitude : undefined
    return address || (latitude !== undefined && longitude !== undefined) ? { type, title, address, latitude, longitude } : null
  }
  return null
}

export function NativeRichBlock({ code }: { code: string }) {
  const spec = parseNativeRichSpec(code)
  const styles = useStyles(makeStyles); const theme = useTheme(); const send = useContext(WidgetPrompt)
  if (!spec) return null
  const heading = spec.title ? <Text style={styles.title}>{spec.title}</Text> : null
  if (spec.type === 'callout') {
    const Icon = spec.tone === 'success' ? CheckCircle2 : spec.tone === 'warning' ? AlertTriangle : spec.tone === 'danger' ? CircleAlert : Info
    const color = spec.tone === 'success' ? theme.color.ok : spec.tone === 'warning' ? theme.color.warn : spec.tone === 'danger' ? theme.color.error : theme.color.accent
    return <View accessibilityLabel={spec.title || 'Bemærkning'} style={[styles.card, styles.callout, { borderLeftColor: color }]}><Icon size={20} color={color} /><View style={styles.flex}>{heading}{spec.body ? <Text style={styles.body}>{spec.body}</Text> : null}</View></View>
  }
  if (spec.type === 'stats') return <View accessibilityLabel={spec.title || 'Nøgletal'} style={styles.card}>{heading}<View style={styles.wrap}>{spec.items.map((x, i) => <View key={`${x.label}-${i}`} style={styles.stat}><Text style={styles.muted}>{x.label}</Text><Text style={styles.value}>{x.value}</Text>{x.detail ? <Text style={styles.body}>{x.detail}</Text> : null}</View>)}</View></View>
  if (spec.type === 'timeline') return <View accessibilityLabel={spec.title || 'Tidslinje'} style={styles.card}>{heading}{spec.items.map((x, i) => <View key={`${x.title}-${i}`} style={styles.timelineRow}><View style={[styles.dot, x.status === 'done' && styles.dotDone, x.status === 'current' && styles.dotCurrent]} /><View style={styles.flex}>{x.time ? <Text style={styles.muted}>{x.time}</Text> : null}<Text style={styles.strong}>{x.title}</Text>{x.detail ? <Text style={styles.body}>{x.detail}</Text> : null}</View></View>)}</View>
  if (spec.type === 'comparison') return <View accessibilityLabel={spec.title || 'Sammenligning'} style={styles.card}>{heading}<ScrollView horizontal showsHorizontalScrollIndicator><View><View style={styles.tableRow}><Text style={[styles.cell, styles.rowHead]}>Punkt</Text>{spec.columns.map((x) => <Text key={x} style={[styles.cell, styles.strong]}>{x}</Text>)}</View>{spec.rows.map((r, i) => <View key={`${r.label}-${i}`} style={styles.tableRow}><Text style={[styles.cell, styles.rowHead]}>{r.label}</Text>{r.values.map((v, j) => <Text key={j} style={styles.cell}>{v}</Text>)}</View>)}</View></ScrollView></View>
  if (spec.type === 'choices') return <View accessibilityLabel={spec.title || 'Valgmuligheder'} style={styles.card}>{heading}<View style={styles.wrap}>{spec.options.map((x, i) => <Pressable key={`${x.label}-${i}`} accessibilityRole="button" accessibilityLabel={x.label} accessibilityState={{ disabled: !send }} disabled={!send} onPress={() => send?.(`[fra valgkort] ${x.prompt}`)} style={({ pressed }) => [styles.button, pressed && styles.pressed]}><Text style={styles.buttonText}>{x.label}</Text></Pressable>)}</View></View>
  const q = spec.latitude !== undefined && spec.longitude !== undefined ? `${spec.latitude},${spec.longitude}` : spec.address
  const href = `https://www.openstreetmap.org/search?query=${encodeURIComponent(q)}`
  return <View accessibilityLabel={spec.title || 'Lokation'} style={[styles.card, styles.callout]}><MapPin size={22} color={theme.color.accent} /><View style={styles.flex}>{heading}{spec.address ? <Text style={styles.body}>{spec.address}</Text> : null}<Pressable accessibilityRole="link" accessibilityLabel="Åbn kort" onPress={() => void Linking.openURL(href)} style={({ pressed }) => [styles.button, styles.mapButton, pressed && styles.pressed]}><Text style={styles.buttonText}>Åbn kort</Text></Pressable></View></View>
}

const makeStyles = (t: Theme) => StyleSheet.create({
  card: { backgroundColor: t.color.bg1, borderWidth: 1, borderColor: t.color.line, borderRadius: t.radius.lg, padding: t.spacing.md, marginVertical: t.spacing.xs, gap: t.spacing.sm },
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
})
