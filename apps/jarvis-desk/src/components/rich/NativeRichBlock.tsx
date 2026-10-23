import { useContext } from 'react'
import { AlertTriangle, CheckCircle2, CircleAlert, Info, MapPin } from 'lucide-react'
import { openExternalUrl } from '../../lib/host'
import { WidgetPrompt } from './WidgetBlock'

type Json = Record<string, unknown>
type NativeSpec =
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
  const type = text(raw.type, 30)
  const title = text(raw.title, 120)
  if (type === 'callout') {
    const body = text(raw.body, 1200)
    const tone = ['info', 'success', 'warning', 'danger'].includes(String(raw.tone))
      ? String(raw.tone) as 'info' | 'success' | 'warning' | 'danger' : 'info'
    if (!title && !body) return null
    return { type, tone, title, body }
  }
  if (type === 'stats') {
    const items = list(raw.items, 8).map((x) => ({ label: text(x.label, 80), value: text(x.value, 120), detail: text(x.detail, 240) }))
      .filter((x) => x.label && x.value)
    return items.length ? { type, title, items } : null
  }
  if (type === 'timeline') {
    const items = list(raw.items, 12).map((x) => ({
      time: text(x.time, 60), title: text(x.title, 120), detail: text(x.detail, 500),
      status: ['done', 'current', 'next'].includes(String(x.status)) ? x.status as 'done' | 'current' | 'next' : 'next',
    })).filter((x) => x.title)
    return items.length ? { type, title, items } : null
  }
  if (type === 'comparison') {
    const columns = Array.isArray(raw.columns) ? raw.columns.map((x) => text(x, 80)).filter(Boolean).slice(0, 4) : []
    const rows = list(raw.rows, 12).map((x) => ({
      label: text(x.label, 100), values: Array.isArray(x.values) ? x.values.map((v) => text(v, 240)).slice(0, columns.length) : [],
    })).filter((x) => x.label && x.values.length === columns.length)
    return columns.length >= 2 && rows.length ? { type, title, columns, rows } : null
  }
  if (type === 'choices') {
    const options = list(raw.options, 6).map((x) => ({ label: text(x.label, 100), prompt: text(x.prompt, 1000) }))
      .filter((x) => x.label && x.prompt)
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

function Heading({ title }: { title: string }) { return title ? <h4 className="native-rich-title">{title}</h4> : null }

export function NativeRichBlock({ code }: { code: string }) {
  const spec = parseNativeRichSpec(code)
  const send = useContext(WidgetPrompt)
  if (!spec) return null
  if (spec.type === 'callout') {
    const Icon = spec.tone === 'success' ? CheckCircle2 : spec.tone === 'warning' ? AlertTriangle : spec.tone === 'danger' ? CircleAlert : Info
    return <aside className={`native-rich native-callout tone-${spec.tone}`} aria-label={spec.title || 'Bemærkning'}>
      <Icon size={20} aria-hidden="true" /><div><Heading title={spec.title} />{spec.body && <p>{spec.body}</p>}</div>
    </aside>
  }
  if (spec.type === 'stats') return <section className="native-rich" aria-label={spec.title || 'Nøgletal'}>
    <Heading title={spec.title} /><dl className="native-stats">{spec.items.map((x, i) => <div key={`${x.label}-${i}`}><dt>{x.label}</dt><dd>{x.value}</dd>{x.detail && <small>{x.detail}</small>}</div>)}</dl>
  </section>
  if (spec.type === 'timeline') return <section className="native-rich" aria-label={spec.title || 'Tidslinje'}>
    <Heading title={spec.title} /><ol className="native-timeline">{spec.items.map((x, i) => <li className={`status-${x.status}`} key={`${x.title}-${i}`}><span className="native-timeline-dot" aria-hidden="true" /><div>{x.time && <time>{x.time}</time>}<strong>{x.title}</strong>{x.detail && <p>{x.detail}</p>}</div></li>)}</ol>
  </section>
  if (spec.type === 'comparison') return <section className="native-rich" aria-label={spec.title || 'Sammenligning'}>
    <Heading title={spec.title} /><div className="native-comparison-scroll"><table className="native-comparison"><thead><tr><th scope="col">Punkt</th>{spec.columns.map((x) => <th scope="col" key={x}>{x}</th>)}</tr></thead><tbody>{spec.rows.map((r, i) => <tr key={`${r.label}-${i}`}><th scope="row">{r.label}</th>{r.values.map((v, j) => <td key={j}>{v}</td>)}</tr>)}</tbody></table></div>
  </section>
  if (spec.type === 'choices') return <section className="native-rich" aria-label={spec.title || 'Valgmuligheder'}>
    <Heading title={spec.title} /><div className="native-choices">{spec.options.map((x, i) => <button type="button" key={`${x.label}-${i}`} disabled={!send} onClick={() => send?.(`[fra valgkort] ${x.prompt}`)}>{x.label}</button>)}</div>
  </section>
  const q = spec.latitude !== undefined && spec.longitude !== undefined ? `${spec.latitude},${spec.longitude}` : spec.address
  const href = `https://www.openstreetmap.org/search?query=${encodeURIComponent(q)}`
  return <section className="native-rich native-location" aria-label={spec.title || 'Lokation'}>
    <MapPin size={22} aria-hidden="true" /><div><Heading title={spec.title} />{spec.address && <p>{spec.address}</p>}<button type="button" onClick={() => openExternalUrl(href)}>Åbn kort</button></div>
  </section>
}
