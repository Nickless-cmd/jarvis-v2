import { createContext, useContext, useState } from 'react'
import { AlertTriangle, CheckCircle2, CircleAlert, Info, MapPin } from 'lucide-react'
import { openExternalUrl } from '../../lib/host'
import { WidgetPrompt } from './WidgetBlock'
import { DiffView } from './DiffView'

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
  // `box` (14/11-2026): bærer børn og rendrer dem rekursivt, så en sammensat
  // flade kan bygges uden modelkald. Kun rene bind-navne — ingen evaluator.
  | { type: 'box'; title: string; children: NativeSpec[] }
  // (14/11-2026) Katalogudvidelse, første bølge: fem typer valgt efter gevinst
  // per risiko. Resten af de ~20 er bevidst IKKE bygget — de skal måles først.
  //
  // Rækkefølgen her er ikke kosmetisk: hver type SKAL have en tilsvarende gren
  // i `core/services/jarvis_ui_guard.py::_diagnosticér`, ellers erklærer
  // guarden den «død», erstatter den med en grå linje og fyrer et helt
  // modelkald for at «rette» en flade der var korrekt skrevet.
  | { type: 'keyvalue'; title: string; items: Array<{ key: string; value: string; detail: string }> }
  | { type: 'progress'; title: string; items: Array<{ label: string; value: number; max: number; detail: string }> }
  | { type: 'quote'; title: string; text: string; source: string; href: string }
  | { type: 'code'; title: string; path: string; language: string; code: string; start: number }
  | { type: 'tabs'; title: string; tabs: Array<{ label: string; children: NativeSpec[] }> }
  // (14/11-2026) Anden bølge — de sidste fem. Rækkefølgen følger guarden, og af
  // samme grund som der: en type uden en guard-gren erklæres død og koster et
  // helt modelkald for at «rette» en flade der var korrekt skrevet.
  //
  // `table` er ikke det samme som en GFM-tabel i prosa. Forskellen er ikke
  // udseendet men interaktionen: her kan læseren sortere lokalt.
  | { type: 'table'; title: string; columns: string[]; rows: string[][] }
  // `chart` er ikke `vis_graf`. Værktøjet tegner et billede og koster et run;
  // denne tegner inline fra data der allerede står i svaret.
  | { type: 'chart'; title: string; kind: 'line' | 'bar'; labels: string[]; series: Array<{ name: string; values: number[] }> }
  // `form` bygger videre på `control`s state-lag: samme `bind`, flere felt-typer.
  | { type: 'form'; title: string; fields: Array<
      | { kind: 'slider'; bind: string; label: string; min: number; max: number; step: number; value: number }
      | { kind: 'select'; bind: string; label: string; options: string[]; value: string }
      | { kind: 'toggle'; bind: string; label: string; value: boolean }
      | { kind: 'text'; text: string }
    > }
  // `tree` er en FLAD liste med `depth` — ikke indlejrede børn. En indlejret form
  // ville kræve en evaluator for at udlede indrykningen, og det er netop undgået.
  | { type: 'tree'; title: string; items: Array<{ name: string; kind: 'dir' | 'file'; depth: number; note: string }> }
  // `diff` genbruger `DiffView`, som selv regner diffen med `lib/diff.lineDiff`.
  | { type: 'diff'; title: string; path: string; old: string; new: string }

/** Højeste dybde en `box` må stå i (toppen er dybde 1). En box i dybde 4
 *  afvises; blade (callout osv.) under en dybde-3-box er stadig fine. */
const BOX_MAX_DYBDE = 3
const BOX_MAX_BOERN = 8
// Anden bølge (14/11-2026). Skal matche `_TABLE_MAX_*` m.fl. i
// core/services/jarvis_ui_guard.py — ellers erklærer guarden en flade «ok»
// som parseren derefter kasserer, og så er der ingen der kan se hvorfor.
const TABLE_MAX_KOLONNER = 12
const TABLE_MAX_RAEKKER = 100
const CHART_MAX_SERIER = 4
const CHART_MAX_PUNKTER = 40
const TREE_MAX_DYBDE = 8

const text = (v: unknown, max = 500) => typeof v === 'string' ? v.trim().slice(0, max) : ''
// `Number.isFinite` — ikke `typeof === 'number'`. Forskellen er målt: `NaN` og
// `Infinity` ER tal for typeof, så de slap igennem og gav `<input type=range
// value={NaN}>`, hvilket er en tavs tom slider. Ingen fejl, ingen flade.
const tal = (v: unknown): number | null => typeof v === 'number' && Number.isFinite(v) ? v : null
const list = (v: unknown, max: number): Json[] => Array.isArray(v)
  ? v.filter((x): x is Json => Boolean(x) && typeof x === 'object' && !Array.isArray(x)).slice(0, max)
  : []

export function parseNativeRichSpec(code: string): NativeSpec | null {
  // Halv JSON under streaming: `JSON.parse` kaster her, og det er den ENESTE
  // der må kaste. Børnene er allerede parsede objekter når `parseNode` kører.
  let raw: Json
  try { raw = JSON.parse(code) as Json } catch { return null }
  return parseNode(raw, 1)
}

function parseNode(raw: unknown, depth: number): NativeSpec | null {
  if (!raw || typeof raw !== 'object' || Array.isArray(raw)) return null
  const node = raw as Json
  return parseNodeObj(node, depth)
}

function parseNodeObj(raw: Json, depth: number): NativeSpec | null {
  const type = text(raw.type, 30)
  const title = text(raw.title, 120)
  if (type === 'box') {
    if (depth > BOX_MAX_DYBDE) return null
    const children = list(raw.children, BOX_MAX_BOERN)
      .map((x) => parseNode(x, depth + 1))
      .filter((x): x is NativeSpec => x !== null)
    return children.length ? { type, title, children } : null
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
      // Samme værn som slideren: et `value` der ikke er et endeligt tal giver
      // en bjælke med `width: NaN%` — usynlig, uden nogen fejl nogen steder.
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
  if (type === 'tabs') {
    if (depth > BOX_MAX_DYBDE) return null
    const tabs = list(raw.tabs, 5).map((x) => ({
      label: text(x.label, 60),
      children: list(x.children, BOX_MAX_BOERN)
        .map((c) => parseNode(c, depth + 1))
        .filter((c): c is NativeSpec => c !== null),
    })).filter((x) => x.label && x.children.length)
    // Én fane er ikke faner — det er en box med en knap. Samme regel som guarden.
    return tabs.length >= 2 ? { type, title, tabs } : null
  }
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
  if (type === 'table') {
    // Kolonnerne klippes FØRST, og rækkerne klippes til samme længde. Ellers
    // ville en række med flere celler end kolonner forskubbe alt til højre, så
    // tal stod under den forkerte overskrift — værre end at vise færre kolonner.
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
      // `tal()` kasserer NaN/Infinity. Uden det ville SVG'en tegne en streg der
      // knækkede usynligt: den springer ugyldige punkter over uden at fejle.
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
        const raa = tal(x.value) ?? min
        return {
          kind: 'slider' as const, bind, label, min, max,
          step: step !== null && step > 0 ? step : 1,
          value: Math.min(max, Math.max(min, raa)),
        }
      }
      if (art === 'select') {
        const options = (Array.isArray(x.options) ? x.options : [])
          .map((o) => text(o, 80)).filter(Boolean).slice(0, 12)
        if (options.length < 2) return null
        const val = text(x.value, 80)
        // Falder tilbage til første mulighed: en `value` der ikke findes i
        // listen ville give et `<select>` uden valgt punkt, altså en tom rude.
        return { kind: 'select' as const, bind, label, options, value: options.includes(val) ? val : options[0] ?? '' }
      }
      if (art === 'toggle') return { kind: 'toggle' as const, bind, label, value: x.value === true }
      return null
    }).filter((x): x is NonNullable<typeof x> => Boolean(x))
    // Mindst ét felt med `bind`: ellers er der ingen lokal state, og fladen
    // ville være ren tekst forklædt som en formular — samme regel som control.
    return fields.some((f) => f.kind !== 'text') ? { type, title, fields } : null
  }
  if (type === 'tree') {
    const items = list(raw.items, 60).map((x) => {
      const name = text(x.name, 200)
      if (!name) return null
      const d = tal(x.depth)
      // Ulovlig dybde klippes til 0 i stedet for at kassere rækken: navnet er
      // stadig sandt, og en rod der mangler ville gøre træet sværere at læse.
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
  return spec ? <FladeNode spec={spec} /> : null
}

// Én node i fladetræet. Hver node er sin EGEN komponent med sine egne hooks,
// så `control` i et barn har sin egen state, og hook-rækkefølgen i hver
// instans er konstant uanset fladetype.
function FladeNode({ spec }: { spec: NativeSpec }) {
  const send = useContext(WidgetPrompt)
  const kontrolTilladt = useContext(FladeKontrolContext)
  // Lokal state for `control` (14/11-2026). Hooken SKAL stå før alle
  // betingede returns nedenfor: ellers ville hook-rækkefølgen skifte med
  // fladetypen, og React kaster ved næste render. Det er den fælde der gør
  // at en flade kan se rigtig ud én gang og dræbe visningen bagefter.
  const [kontrolVaerdier, setKontrolVaerdi] = useState<Record<string, number | string | boolean>>({})
  // Sortering for `table` (14/11-2026). Også en hook, og af samme grund som
  // ovenfor: den står før alle betingede returns, så rækkefølgen er konstant.
  // Sorteringen er LOKAL — den rører ikke data og sender intet afsted.
  const [sortering, setSortering] = useState<{ kolonne: number; retning: 1 | -1 } | null>(null)
  // Fanevalg for `tabs` (14/11-2026). Samme krav som ovenfor: hooken står før
  // alle betingede returns, så rækkefølgen er konstant uanset fladetype.
  const [valgtFane, setValgtFane] = useState(0)
  if (spec.type === 'box') return <section className="native-rich native-box" aria-label={spec.title || 'Samling'}>
    <Heading title={spec.title} />
    <div className="native-box-boern">{spec.children.map((c, i) => <FladeNode key={`${c.type}-${i}`} spec={c} />)}</div>
  </section>
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
    const aktuel = (bind: string, fallback: number): number => {
      // `kontrolVaerdier` bærer nu også tekst og bool (for `form`). Uden
      // typetjekket ville en `select`-værdi kunne lande i en slider.
      const v = kontrolVaerdier[bind]
      return typeof v === 'number' ? v : fallback
    }
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
  if (spec.type === 'keyvalue') return <section className="native-rich" aria-label={spec.title || 'Fakta'}>
    <Heading title={spec.title} /><dl className="native-keyvalue">{spec.items.map((x, i) => <div key={`${x.key}-${i}`}><dt>{x.key}</dt><dd>{x.value}{x.detail && <small>{x.detail}</small>}</dd></div>)}</dl>
  </section>
  if (spec.type === 'progress') return <section className="native-rich" aria-label={spec.title || 'Status'}>
    <Heading title={spec.title} /><div className="native-progress">{spec.items.map((x, i) => {
      // Klemt til 0–100: en værdi over `max` ville give en bjælke der løb ud
      // over rammen, og en negativ en bjælke der pegede baglæns.
      const pct = Math.max(0, Math.min(100, (x.value / x.max) * 100))
      return <div className="native-progress-post" key={`${x.label}-${i}`}>
        <div className="native-progress-hoved"><span>{x.label}</span><output>{x.value} / {x.max}</output></div>
        <div className="native-progress-bjaelke" role="progressbar" aria-label={x.label}
          aria-valuenow={x.value} aria-valuemin={0} aria-valuemax={x.max}>
          <span style={{ width: `${pct}%` }} />
        </div>
        {x.detail && <small>{x.detail}</small>}
      </div>
    })}</div>
  </section>
  if (spec.type === 'quote') return <blockquote className="native-rich native-quote" aria-label={spec.title || 'Citat'}>
    <Heading title={spec.title} /><p>{spec.text}</p>
    {spec.source && (spec.href
      ? <cite><button type="button" onClick={() => openExternalUrl(spec.href)}>{spec.source}</button></cite>
      : <cite>{spec.source}</cite>)}
  </blockquote>
  if (spec.type === 'code') return <section className="native-rich native-code" aria-label={spec.title || 'Kode'}>
    {(spec.title || spec.path) && <div className="native-code-hoved">
      <Heading title={spec.title} />{spec.path && <code className="native-code-sti">{spec.path}</code>}
    </div>}
    <pre className="native-code-blok">{spec.code.split('\n').map((l, i) => <span className="native-code-linje" key={i}>
      <span className="native-code-nr" aria-hidden="true">{spec.start + i}</span>
      <span className="native-code-tekst">{l || ' '}</span>
    </span>)}</pre>
  </section>
  if (spec.type === 'tabs') {
    // `Math.min` fordi antallet af faner kan ændre sig mellem to flader i samme
    // samtale: uden klemningen ville et gemt indeks pege ud i tomrummet og
    // fladen ville rendere ingenting — uden fejl.
    const idx = Math.min(valgtFane, spec.tabs.length - 1)
    const aktiv = spec.tabs[idx]
    // Parser og guard kræver mindst to faner, så grenen er i praksis uopnåelig.
    // Den står her fordi `noUncheckedIndexedAccess` ellers gør opslaget
    // «muligvis undefined» — og et typetjek er billigere end en tom flade.
    if (!aktiv) return null
    return <section className="native-rich native-tabs" aria-label={spec.title || 'Faner'}>
      <Heading title={spec.title} />
      <div className="native-tabs-liste" role="tablist">
        {spec.tabs.map((t, i) => <button type="button" role="tab" key={`${t.label}-${i}`}
          aria-selected={i === idx} className={i === idx ? 'native-tab aktiv' : 'native-tab'}
          onClick={() => setValgtFane(i)}>{t.label}</button>)}
      </div>
      <div className="native-tabs-indhold" role="tabpanel">
        {aktiv.children.map((c, i) => <FladeNode key={`${c.type}-${i}`} spec={c} />)}
      </div>
    </section>
  }
  if (spec.type === 'table') {
    // Sorteringen er LOKAL (14/11-2026): et klik på en kolonne ændrer kun
    // rækkefølgen i denne visning. Det er hele forskellen til en GFM-tabel, og
    // det koster nul modelkald.
    const raekker = sortering
      ? [...spec.rows].sort((a, b) => {
        const x = a[sortering.kolonne] ?? ''
        const y = b[sortering.kolonne] ?? ''
        // Tal sorteres som tal, ikke som tekst: ellers ville «10» komme før «9».
        const nx = Number(x.replace(',', '.'))
        const ny = Number(y.replace(',', '.'))
        const beggeTal = x.trim() !== '' && y.trim() !== ''
          && Number.isFinite(nx) && Number.isFinite(ny)
        const cmp = beggeTal ? nx - ny : x.localeCompare(y, 'da')
        return cmp * sortering.retning
      })
      : spec.rows
    return <section className="native-rich native-table" aria-label={spec.title || 'Tabel'}>
      <Heading title={spec.title} />
      <div className="native-table-ramme">
        <table>
          <thead><tr>{spec.columns.map((k, i) => <th key={`${k}-${i}`} scope="col">
            <button type="button" className="native-table-sorter"
              onClick={() => setSortering((forrige) => forrige?.kolonne === i
                ? { kolonne: i, retning: forrige.retning === 1 ? -1 : 1 }
                : { kolonne: i, retning: 1 })}>
              {k}{sortering?.kolonne === i && <span aria-hidden="true">{sortering.retning === 1 ? ' ▲' : ' ▼'}</span>}
            </button>
          </th>)}</tr></thead>
          <tbody>{raekker.map((r, i) => <tr key={i}>
            {r.map((c, j) => <td key={j}>{c}</td>)}
          </tr>)}</tbody>
        </table>
      </div>
    </section>
  }
  if (spec.type === 'chart') {
    // Inline SVG, ingen værktøjskald. Skalaen regnes fra data, så en serie der
    // kun ændrer sig lidt stadig fylder hele højden — ellers ville to næsten
    // identiske tal se ud som en flad streg.
    const alle = spec.series.flatMap((s) => s.values)
    const min = Math.min(...alle)
    const maks = Math.max(...alle)
    const spaend = maks - min || 1
    const B = 320, H = 120, P = 8
    const antal = Math.max(...spec.series.map((s) => s.values.length))
    const px = (i: number) => antal <= 1 ? B / 2 : P + (i / (antal - 1)) * (B - 2 * P)
    const py = (v: number) => H - P - ((v - min) / spaend) * (H - 2 * P)
    const bjBredde = (B - 2 * P) / Math.max(1, antal)
    const perSerie = bjBredde / spec.series.length
    return <section className="native-rich native-chart" aria-label={spec.title || 'Graf'}>
      <Heading title={spec.title} />
      <svg viewBox={`0 0 ${B} ${H}`} className="native-chart-svg" role="img"
        aria-label={`${spec.kind === 'bar' ? 'Søjler' : 'Linje'}: ${spec.series.map((s) => s.name).join(', ')}`}>
        <line x1={P} y1={H - P} x2={B - P} y2={H - P} className="native-chart-akse" />
        {spec.series.map((s, si) => s.values.length < 2 ? null : spec.kind === 'bar'
          ? s.values.map((v, i) => <rect key={`${si}-${i}`} className={`native-chart-soejle native-chart-serie-${si}`}
              x={P + i * bjBredde + si * perSerie + perSerie * 0.1}
              y={py(v)} width={Math.max(1, perSerie * 0.8)} height={Math.max(0, H - P - py(v))} />
          )
          : <polyline key={si} className={`native-chart-linje native-chart-serie-${si}`} fill="none"
              points={s.values.map((v, i) => `${px(i)},${py(v)}`).join(' ')} />
        )}
      </svg>
      <div className="native-chart-forklaring">
        {spec.series.map((s, i) => <span key={`${s.name}-${i}`} className={`native-chart-noegle native-chart-serie-${i}`}>
          {s.name || `Serie ${i + 1}`}
        </span>)}
      </div>
      {spec.labels.length > 0 && <div className="native-chart-labels">
        {spec.labels.slice(0, 6).map((l, i) => <span key={`${l}-${i}`}>{l}</span>)}
      </div>}
    </section>
  }
  if (spec.type === 'form') {
    // Samme gate som `control`: code mode må ikke se den.
    if (!kontrolTilladt) return null
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
    const interpolér = (s: string) => s.replace(/\{(\w+)\}/g, (m, k) => {
      const v = kontrolVaerdier[k]
      return v === undefined ? m : String(v)
    })
    return <section className="native-rich native-form" aria-label={spec.title || 'Formular'}>
      <Heading title={spec.title} />
      <div className="native-control-felter">
        {spec.fields.map((f, i) => {
          if (f.kind === 'text') return <p key={`t-${i}`}>{interpolér(f.text)}</p>
          if (f.kind === 'slider') return <label className="native-control-slider" key={`${f.bind}-${i}`}>
            <span className="native-control-label">{f.label}</span>
            <input type="range" min={f.min} max={f.max} step={f.step}
              value={talV(f.bind, f.value)}
              onChange={(e) => {
                const n = Number(e.currentTarget.value)
                if (Number.isFinite(n)) setKontrolVaerdi((forrige) => ({ ...forrige, [f.bind]: n }))
              }} />
            <output className="native-control-vaerdi">{talV(f.bind, f.value)}</output>
          </label>
          if (f.kind === 'select') return <label className="native-form-select" key={`${f.bind}-${i}`}>
            <span className="native-control-label">{f.label}</span>
            <select value={tekstV(f.bind, f.value)}
              onChange={(e) => {
                // `currentTarget` nulstilles når handleren returnerer. Læses den
                // inde i opdateringsfunktionen — som kører under render, bagefter —
                // er den `null`, og React kaster «Cannot read properties of null».
                const v = e.currentTarget.value
                setKontrolVaerdi((forrige) => ({ ...forrige, [f.bind]: v }))
              }}>
              {f.options.map((o) => <option key={o} value={o}>{o}</option>)}
            </select>
          </label>
          return <label className="native-form-toggle" key={`${f.bind}-${i}`}>
            <input type="checkbox" checked={boolV(f.bind, f.value)}
              onChange={(e) => {
                // Samme fælde som select: værdien skal ud af eventet FØR state-kaldet.
                const v = e.currentTarget.checked
                setKontrolVaerdi((forrige) => ({ ...forrige, [f.bind]: v }))
              }} />
            <span>{f.label}</span>
          </label>
        })}
      </div>
    </section>
  }
  if (spec.type === 'tree') {
    return <section className="native-rich native-tree" aria-label={spec.title || 'Struktur'}>
      <Heading title={spec.title} />
      <ul className="native-tree-liste">
        {spec.items.map((x, i) => <li key={`${x.name}-${i}`} className={`native-tree-item native-tree-${x.kind}`}
          style={{ paddingLeft: `${x.depth * 16}px` }}>
          <span className="native-tree-navn">{x.name}</span>
          {x.note && <small className="native-tree-note">{x.note}</small>}
        </li>)}
      </ul>
    </section>
  }
  if (spec.type === 'diff') {
    return <section className="native-rich" aria-label={spec.title || 'Ændring'}>
      <Heading title={spec.title} />
      <DiffView oldText={spec.old} newText={spec.new} filename={spec.path} />
    </section>
  }
  const q = spec.latitude !== undefined && spec.longitude !== undefined ? `${spec.latitude},${spec.longitude}` : spec.address
  const href = `https://www.openstreetmap.org/search?query=${encodeURIComponent(q)}`
  return <section className="native-rich native-card native-location" aria-label={spec.title || 'Lokation'}>
    <MapPin size={22} aria-hidden="true" /><div><Heading title={spec.title} />{spec.address && <p>{spec.address}</p>}<button type="button" onClick={() => openExternalUrl(href)}>Åbn kort</button></div>
  </section>
}
