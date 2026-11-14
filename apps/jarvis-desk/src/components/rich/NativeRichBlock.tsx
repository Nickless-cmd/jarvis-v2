import { createContext, useContext, useState } from 'react'
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
  // `control` (14/11-2026): den FØRSTE flade med lokal state. Slideren rykker
  // uden at noget modelkald går ud — state bor i komponenten, ikke i samtalen.
  //
  // Forskellen til `choices` er hele pointen: `choices` er et SVAR der sendes
  // tilbage og koster et helt run. `control` regner lokalt. `{bind}` i et
  // tekstfelt interpoleres fra slidernes aktuelle værdi, så fladen kan svare
  // «du har valgt 12» mens brugeren trækker — uden en tur til modellen.
  | { type: 'control'; title: string; fields: Array<
      | { kind: 'slider'; bind: string; label: string; min: number; max: number; step: number; value: number }
      | { kind: 'text'; text: string }
    > }

const text = (v: unknown, max = 500) => typeof v === 'string' ? v.trim().slice(0, max) : ''
// `Number.isFinite` — ikke `typeof === 'number'`. Forskellen er målt: `NaN` og
// `Infinity` ER tal for typeof, så de slap igennem og gav `<input type=range
// value={NaN}>`, hvilket er en tavs tom slider. Ingen fejl, ingen flade.
const tal = (v: unknown): number | null => typeof v === 'number' && Number.isFinite(v) ? v : null
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
    // 30/10-2026: PAD i stedet for at kassere.
    //
    // Før krævede hver række PRÆCIS `columns.length` values. Manglede én, blev
    // rækken filtreret væk; manglede de alle, blev HELE fladen kasseret og
    // erstattet af en placeholder der aldrig forsvandt. Målt i
    // `state/flade_log.jsonl`: 34 flader med fuldt gyldig JSON blev smidt væk
    // alene på denne regel — de så rigtige ud for mig, var døde for ham.
    //
    // En tom celle er ærlig. En forsvundet flade er ikke.
    const rows = list(raw.rows, 12).map((x) => {
      const givne = Array.isArray(x.values) ? x.values.map((v) => text(v, 240)) : []
      return {
        label: text(x.label, 100),
        values: Array.from({ length: columns.length }, (_, i) => givne[i] ?? ''),
      }
    }).filter((x) => x.label && x.values.some(Boolean))
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
  if (type === 'control') {
    // Felt uden `bind` filtreres væk: uden en nøgle at binde til er der intet
    // at holde state i, og feltet ville se interaktivt ud uden at være det.
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
      // Et ulovligt interval er en død slider — kassér feltet, ikke fladen.
      if (min === null || max === null || max <= min) return null
      const step = tal(x.step)
      const raaVaerdi = tal(x.value) ?? min
      return {
        kind: 'slider' as const, bind, label, min, max,
        step: step !== null && step > 0 ? step : 1,
        // Klemt ind i intervallet: en `value` uden for [min,max] giver et
        // håndtag der står forkert i forhold til det tal der vises.
        value: Math.min(max, Math.max(min, raaVaerdi)),
      }
    }).filter((x): x is NonNullable<typeof x> => Boolean(x))
    // Mindst ÉN slider: uden et `bind` er der ingen lokal state, og fladen ville
    // være ren tekst forklædt som en kontrol. Det er hele pointen med typen.
    return fields.some((f) => f.kind === 'slider') ? { type, title, fields } : null
  }
  return null
}

function Heading({ title }: { title: string }) { return title ? <h4 className="native-rich-title">{title}</h4> : null }

/** Må `control`-fladen vises her? (14/11-2026)
 *
 *  Default er NEJ. Fladen er delt: `BlocksRenderer` bruges både af
 *  `ChatFlowPresentation` (chat mode) og af `RaekkeTranskript` (code mode), så
 *  uden en gate ville slideren også dukke op i maskinrummet. En default der
 *  lukker ude er den eneste sikre retning — glemmer nogen at sætte flaget,
 *  forsvinder fladen i stedet for at dukke op det forkerte sted. */
export const FladeKontrolContext = createContext(false)

export function NativeRichBlock({ code }: { code: string }) {
  // Ankomst-laget (29/10-2026). Bjørn så fladen poppe ind i ét hug når
  // paceren sprang over JSON'en: «så blink».
  //
  // `key` er bundet til fladens INDHOLD, ikke til renderet. Skiftede nøglen
  // ved hver re-render, ville fladen danse hver gang paceren rykker ét tegn i
  // prosaen ovenover — værre end den kodeboks den afløser. Nu remountes noden
  // kun når en NY flade lander, og CSS-animationen fyrer præcis én gang.
  return (
    <div className="flade-ankomst" key={code}>
      <NativeRichIndhold code={code} />
    </div>
  )
}

function NativeRichIndhold({ code }: { code: string }) {
  const spec = parseNativeRichSpec(code)
  const send = useContext(WidgetPrompt)
  const kontrolTilladt = useContext(FladeKontrolContext)
  // Lokal state for `control` (14/11-2026). Hooken SKAL stå før alle
  // betingede returns nedenfor: ellers ville hook-rækkefølgen skifte med
  // fladetypen, og React kaster ved næste render. Det er den fælde der gør
  // at en flade kan se rigtig ud én gang og dræbe visningen bagefter.
  const [kontrolVaerdier, setKontrolVaerdi] = useState<Record<string, number>>({})
  if (!spec) return null
  if (spec.type === 'callout') {
    const Icon = spec.tone === 'success' ? CheckCircle2 : spec.tone === 'warning' ? AlertTriangle : spec.tone === 'danger' ? CircleAlert : Info
    return <aside className={`native-rich native-card native-callout tone-${spec.tone}`} aria-label={spec.title || 'Bemærkning'}>
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
  if (spec.type === 'choices') return <section className="native-rich native-card" aria-label={spec.title || 'Valgmuligheder'}>
    <Heading title={spec.title} /><div className="native-choices">{spec.options.map((x, i) => <button type="button" key={`${x.label}-${i}`} disabled={!send} onClick={() => send?.(`[fra valgkort] ${x.prompt}`)}>{x.label}</button>)}</div>
  </section>
  if (spec.type === 'control') {
    // Gaten: code mode må ikke se den. Default er falsk (se
    // `FladeKontrolContext`), så kun chat-visningen sætter flaget.
    if (!kontrolTilladt) return null
    // Sliderens værdi: lokal state først, ellers den værdi fladen kom med.
    // Der er ingen `useEffect` der synkroniserer — state ER sandheden så snart
    // brugeren har rørt håndtaget, og ellers er den medfødte værdi.
    const aktuel = (bind: string, fallback: number) => kontrolVaerdier[bind] ?? fallback
    // `{bind}` i et tekstfelt interpoleres fra sliderne. Det er her fladen
    // svarer brugeren uden et modelkald: teksten regnes om ved hvert træk.
    const interpolér = (s: string) => {
      const opslag: Record<string, number> = {}
      for (const f of spec.fields) if (f.kind === 'slider') opslag[f.bind] = aktuel(f.bind, f.value)
      return s.replace(/\{(\w+)\}/g, (m, k) => (k in opslag ? String(opslag[k]) : m))
    }
    return <section className="native-rich native-control" aria-label={spec.title || 'Kontrol'}>
      <Heading title={spec.title} />
      <div className="native-control-felter">
        {spec.fields.map((f, i) => f.kind === 'slider' ? (
          <label className="native-control-slider" key={`${f.bind}-${i}`}>
            <span className="native-control-label">{f.label}</span>
            <input type="range" min={f.min} max={f.max} step={f.step}
              value={aktuel(f.bind, f.value)}
              onChange={(e) => {
                const n = Number(e.currentTarget.value)
                // Samme værn som i parseren: `Number('')` er 0, og en NaN ville
                // gøre håndtaget usynligt uden en fejl nogen steder.
                if (Number.isFinite(n)) setKontrolVaerdi((forrige) => ({ ...forrige, [f.bind]: n }))
              }} />
            <output className="native-control-vaerdi">{aktuel(f.bind, f.value)}</output>
          </label>
        ) : <p key={`t-${i}`}>{interpolér(f.text)}</p>)}
      </div>
    </section>
  }
  const q = spec.latitude !== undefined && spec.longitude !== undefined ? `${spec.latitude},${spec.longitude}` : spec.address
  const href = `https://www.openstreetmap.org/search?query=${encodeURIComponent(q)}`
  return <section className="native-rich native-card native-location" aria-label={spec.title || 'Lokation'}>
    <MapPin size={22} aria-hidden="true" /><div><Heading title={spec.title} />{spec.address && <p>{spec.address}</p>}<button type="button" onClick={() => openExternalUrl(href)}>Åbn kort</button></div>
  </section>
}
