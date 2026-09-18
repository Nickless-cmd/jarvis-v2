/**
 * Oversigten — nøgletal, forløb, og hvad der IKKE kunne hentes.
 *
 * Snapshotet er sammensat af seks kilder, og en af dem kan svigte uden at de
 * andre gør. Derfor har hver sektion sin egen konvolut med kilde og friskhed,
 * og derfor står en fejlet sektion som en linje på skærmen frem for at tage
 * resten med sig. Et panel der går i sort fordi balanceren ikke svarede,
 * fortæller mindre end det ved.
 */
import { AlertTriangle } from 'lucide-react'
import type { Sektion, Snapshot } from '../../../lib/cheapLaneApi'
import { CheapLaneChart, type Punkt } from './CheapLaneChart'

function tal(v: number | null | undefined): string {
  if (v === null || v === undefined) return '–'
  return v.toLocaleString('da-DK')
}

function tid(s?: string | null): string {
  if (!s) return '–'
  const d = new Date(s)
  return Number.isNaN(d.getTime()) ? String(s).slice(0, 16)
    : d.toLocaleString('da-DK', { day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit' })
}

/** En fejlet sektion siger hvad der mangler — og hvor det kom fra. */
function SektionsFejl({ navn, sektion }: { navn: string; sektion?: Sektion<unknown> }) {
  const fejl = sektion?.error
  if (!fejl) return null
  return (
    <p className="cl-sektionsfejl">
      <AlertTriangle size={13} aria-hidden="true" />
      <strong>{navn}</strong>
      <span>{fejl.message || fejl.detail || fejl.code || 'kunne ikke hentes'}</span>
      <span className="cl-dæmpet">kilde: {sektion?.source || 'ukendt'}</span>
    </p>
  )
}

function Noegletal({ label, vaerdi, note }: { label: string; vaerdi: string; note?: string }) {
  return (
    <div className="cl-kpi">
      <span className="cl-kpi-label">{label}</span>
      <span className="cl-kpi-tal">{vaerdi}</span>
      {note ? <span className="cl-kpi-note">{note}</span> : null}
    </div>
  )
}

export function CheapLaneOverview({
  snapshot, serie, serieHenter = false, serieFejl = '',
}: {
  snapshot: Snapshot
  /** Tidsserien hentes for sig: snapshotet bærer summer, ikke forløb. */
  serie: { start: string; kald: number; fejl: number; tokens: number }[]
  serieHenter?: boolean
  serieFejl?: string
}) {
  const k = snapshot.kpis || {}
  const fejlpct = k.requests ? Math.round(((k.errors ?? 0) / k.requests) * 100) : null
  const punkter: Punkt[] = serie.map((s) => ({
    start: s.start, Kald: s.kald, Fejl: s.fejl, Tokens: s.tokens,
  }))

  return (
    <div className="cl-oversigt">
      <div className="cl-kpi-gitter">
        <Noegletal label="Kald" vaerdi={tal(k.requests)}
                   note={fejlpct === null ? undefined : `${fejlpct} % fejlede`} />
        <Noegletal label="Tokens" vaerdi={tal(k.tokens)} />
        <Noegletal label="Fejl" vaerdi={tal(k.errors)} />
        <Noegletal label="Slots klar" vaerdi={tal(k.eligible_slots)} />
        <Noegletal label="Fund" vaerdi={tal(k.active_findings)}
                   note={k.active_findings ? 'se diagnose' : undefined} />
        <Noegletal label="Pris" vaerdi={`$${(k.cost_usd ?? 0).toLocaleString('da-DK', { maximumFractionDigits: 4 })}`} />
      </div>

      <p className="cl-maalt">
        Målt {tid(snapshot.generated_at)} · vindue {snapshot.window_hours} timer · {snapshot.status}
      </p>

      <SektionsFejl navn="Balancer" sektion={snapshot.sections?.balancer} />
      <SektionsFejl navn="Kapacitet" sektion={snapshot.sections?.capacity} />
      <SektionsFejl navn="Udbydere" sektion={snapshot.sections?.providers} />
      <SektionsFejl navn="Forløb" sektion={snapshot.sections?.trends} />
      <SektionsFejl navn="Diagnose" sektion={snapshot.sections?.diagnostics} />

      {/* Centrals egne haendelser: speccen vil have dem PAA oversigten, fordi
          «er lanen rask» ofte besvares af noget Central saa foer os. */}
      {(snapshot.sections?.central?.data ?? []).length ? (
        <>
          <p className="cl-forklaring-overskrift">Fra Central</p>
          <ul className="cl-central">
            {(snapshot.sections?.central?.data ?? []).slice(0, 5).map((h, i) => (
              <li key={`${h.id ?? i}`}>
                <span className="cl-kilde">{h.severity ?? 'info'}</span>
                <span className="cl-dæmpet cl-lille">{tid(h.ts)}</span>
                <span className="cl-besked">{h.message ?? h.kind ?? '—'}</span>
              </li>
            ))}
          </ul>
        </>
      ) : null}

      <CheapLaneChart
        titel="Kald og fejl"
        henter={serieHenter}
        fejl={serieFejl}
        punkter={punkter}
        serier={[
          { key: 'Kald', navn: 'Kald', farve: 'var(--accent)' },
          { key: 'Fejl', navn: 'Fejl', farve: 'var(--error-fg, #d9534f)' },
        ]}
      />
    </div>
  )
}
