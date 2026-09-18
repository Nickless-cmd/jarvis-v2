/**
 * En graf man også kan læse uden mus.
 *
 * Recharts' tooltip findes kun under en markør. En tastaturbruger — og enhver
 * der bare vil se det præcise tal — får ellers ingenting ud af kurven. Derfor
 * bærer hver graf sin egen tabel: skjult for øjet, til stede for skærmlæseren
 * og udfoldelig med en knap.
 *
 * Det er også grunden til at komponenten tager rå punkter og ikke en færdig
 * Recharts-konfiguration: tabellen og kurven skal komme fra SAMME tal, ellers
 * kan de nå at sige hver sit.
 */
import { useId, useState } from 'react'
import {
  Area, AreaChart, CartesianGrid, Legend, ResponsiveContainer, Tooltip, XAxis, YAxis,
} from 'recharts'

export interface Punkt {
  /** ISO-tid for spandens start. */
  start: string
  [serie: string]: string | number
}

export interface Serie {
  key: string
  navn: string
  farve: string
}

function klokke(s: string): string {
  const d = new Date(s)
  return Number.isNaN(d.getTime()) ? s.slice(11, 16)
    : d.toLocaleTimeString('da-DK', { hour: '2-digit', minute: '2-digit' })
}

export function CheapLaneChart({
  punkter, serier, titel, hoejde = 180, henter = false, fejl = '',
}: {
  punkter: Punkt[]
  serier: Serie[]
  titel: string
  hoejde?: number
  /** Hentes der stadig? En tom graf og en graf der ikke er hentet endnu er
   *  to forskellige beskeder. */
  henter?: boolean
  /** Kunne kilden ikke læses? Så er «ingen målinger» en løgn. */
  fejl?: string
}) {
  const [åben, setÅben] = useState(false)
  const id = useId()

  if (fejl) {
    // «Ingen målinger» ville være forkert: vi VED ikke om der var nogen.
    return <p className="cl-handling-fejl" role="alert">{titel}: {fejl}</p>
  }
  if (henter) return <p className="cl-tom">Henter {titel.toLowerCase()}…</p>
  if (!punkter.length) {
    // Ingen tom ramme: en graf uden punkter ligner et nedbrud.
    return <p className="cl-tom">Ingen målinger i vinduet.</p>
  }

  return (
    <figure className="cl-graf" aria-labelledby={`${id}-titel`}>
      <figcaption id={`${id}-titel`} className="cl-graf-titel">{titel}</figcaption>
      <div className="cl-graf-flade">
        <ResponsiveContainer width="100%" height={hoejde}>
          <AreaChart data={punkter} margin={{ top: 4, right: 8, bottom: 0, left: 0 }}>
            <CartesianGrid strokeDasharray="2 4" stroke="var(--line)" vertical={false} />
            <XAxis dataKey="start" tickFormatter={klokke} tick={{ fontSize: 11 }}
                   stroke="var(--fg-3)" minTickGap={24} />
            <YAxis tick={{ fontSize: 11 }} stroke="var(--fg-3)" width={44}
                   tickFormatter={(v) => Number(v ?? 0).toLocaleString('da-DK')} />
            <Legend verticalAlign="top" height={20}
                    wrapperStyle={{ fontSize: 11, color: 'var(--fg-3)' }} />
            <Tooltip
              contentStyle={{ background: 'var(--bg-2)', border: '1px solid var(--line)',
                borderRadius: 8, fontSize: 12 }}
              labelFormatter={(v) => klokke(String(v ?? ''))}
              formatter={(v, navn) => [Number(v ?? 0).toLocaleString('da-DK'), String(navn)]}
            />
            {serier.map((s) => (
              <Area key={s.key} type="monotone" dataKey={s.key} name={s.navn}
                    stroke={s.farve} fill={s.farve} fillOpacity={0.14} strokeWidth={1.5}
                    isAnimationActive={false} />
            ))}
          </AreaChart>
        </ResponsiveContainer>
      </div>

      <button type="button" className="cl-graf-tabelknap" onClick={() => setÅben((o) => !o)}
              aria-expanded={åben}>
        {åben ? 'Skjul tallene' : 'Vis tallene'}
      </button>

      <div className={åben ? 'cl-tabel-holder' : 'cl-kun-skaermlaeser'}>
        <table aria-label={`${titel} som tabel`}>
          <thead>
            <tr>
              <th scope="col">Tidspunkt</th>
              {serier.map((s) => <th key={s.key} scope="col">{s.navn}</th>)}
            </tr>
          </thead>
          <tbody>
            {punkter.map((p) => (
              <tr key={p.start}>
                <th scope="row">{klokke(p.start)}</th>
                {serier.map((s) => (
                  <td key={s.key}>{Number(p[s.key] ?? 0).toLocaleString('da-DK')}</td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </figure>
  )
}
