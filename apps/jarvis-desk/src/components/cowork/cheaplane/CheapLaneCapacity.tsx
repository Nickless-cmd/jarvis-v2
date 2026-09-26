/**
 * Kapacitet pr. kvotevindue — og forskellen på «0 tilbage» og «ukendt».
 *
 * Det er fanens eneste virkelige opgave. Bjørn bruger den til at afgøre om han
 * kan køre videre, og et panel der viser 0 % fordi ingen har fortalt det hvad
 * grænsen er, siger noget FORKERT — ikke noget ufuldstændigt. Ukendt kapacitet
 * er derfor aldrig et tal, aldrig en fyldt bjælke og aldrig nul procent.
 *
 * Enheder blandes heller ikke: tokens, kald og dollars står hver for sig,
 * fordi en sum af dem ikke betyder noget.
 */
import type { Kapacitet, KvoteVindue } from '../../../lib/cheapLaneApi'

const PERIODE: Record<string, string> = {
  minute: 'pr. minut', day: 'i dag', week: 'denne uge', month: 'denne måned',
}

const ENHED: Record<string, string> = {
  tokens: 'tokens', requests: 'kald', credits_usd: 'dollars',
}

function tal(v: number | null | undefined): string {
  if (v === null || v === undefined) return '–'
  return v.toLocaleString('da-DK')
}

function tid(s?: string | null): string {
  if (!s) return ''
  const d = new Date(s)
  return Number.isNaN(d.getTime()) ? String(s).slice(0, 16)
    : d.toLocaleString('da-DK', { day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit' })
}

function Vindue({ v }: { v: KvoteVindue }) {
  const kendt = typeof v.limit === 'number' && v.limit > 0
  const pct = kendt ? Math.min(100, Math.round((v.used / (v.limit as number)) * 100)) : null
  return (
    <li className="cl-kvote">
      <div className="cl-kvote-hoved">
        <span className="cl-kvote-navn">
          {v.provider || '—'}{v.auth_profile ? ` · ${v.auth_profile}` : ''}
        </span>
        <span className="cl-kvote-periode">
          {ENHED[v.unit] ?? v.unit} {PERIODE[v.period] ?? v.period}
        </span>
        <span className={`cl-kilde cl-kilde-${v.source}`}>{v.source}</span>
      </div>

      {kendt ? (
        <>
          <div className="cl-bar" role="img"
               aria-label={`${tal(v.used)} af ${tal(v.limit)} brugt, ${tal(v.remaining)} tilbage`}>
            <div className="cl-bar-fyld" style={{ width: `${pct}%` }} />
          </div>
          <div className="cl-kvote-tal">
            <span>{tal(v.used)} / {tal(v.limit)}</span>
            <span>{pct} %</span>
            <span>{tal(v.remaining)} tilbage</span>
          </div>
        </>
      ) : (
        <>
          {/* Ingen bjælke. En tom bjælke ville læses som «næsten intet brugt». */}
          <div className="cl-ukendt">Ukendt kapacitet</div>
          <div className="cl-kvote-tal">
            <span>{tal(v.used)} brugt</span>
            <span className="cl-dæmpet">grænsen er ikke oplyst</span>
          </div>
        </>
      )}

      {v.reset_at ? <div className="cl-kvote-reset">nulstilles {tid(v.reset_at)}</div> : null}
    </li>
  )
}

const PERIODER = [
  { id: 'day', label: 'I dag' },
  { id: 'week', label: 'Denne uge' },
  { id: 'month', label: 'Denne måned' },
] as const

export function CheapLaneCapacity({ kapacitet }: { kapacitet: Kapacitet | null }) {
  if (!kapacitet) return <p className="cl-tom">Henter kapacitet…</p>
  const vinduer = kapacitet.windows ?? []
  return (
    <div className="cl-kapacitet">
      <p className="cl-note">
        Målt forbrug er registrerede cheap lane-kald i UTC. Kapacitet er kun et kendt
        tal, når kvoten er oplyst. Kaldsbaserede tal er et estimat ud fra aktive
        konti, konfigurerede kaldsgrænser og de seneste syv dages tokenforbrug pr. kald.
      </p>
      <div className="cl-tabel-holder">
        <table className="cl-kapacitet-tabel">
          <thead><tr>
            <th>Periode</th><th>Ind</th><th>Ud</th><th>Samlet</th>
            <th>Kendt restkvote</th><th>Estimeret rest</th>
          </tr></thead>
          <tbody>{PERIODER.map(({ id, label }) => {
            const brug = kapacitet.usage?.[id]
            const kvote = kapacitet.totals?.[`${id}:tokens`]
            const skøn = kapacitet.estimated_capacity?.[id]
            return <tr key={id}>
              <th scope="row">{label}</th>
              <td>{brug ? tal(brug.input_tokens) : '–'}</td>
              <td>{brug ? tal(brug.output_tokens) : '–'}</td>
              <td>{brug ? tal(brug.total_tokens) : '–'}</td>
              <td title={kvote?.complete ? 'Alle aktive konti har kendt kvote' : 'Kun kendte konti er med'}>
                {kvote ? <>{tal(kvote.remaining)}{!kvote.complete && <small> delvist</small>}</> : 'Ukendt'}
              </td>
              <td title="Skøn fra kaldsgrænser og målt tokens pr. kald; ingen garanteret tokenkvote">
                {skøn?.profiles.length
                  ? <>{tal(skøn.known_estimate_tokens)}<small> estimat{!skøn.complete ? ' · delvist' : ''}</small></>
                  : 'Ukendt'}
              </td>
            </tr>
          })}</tbody>
        </table>
      </div>
      {PERIODER.map(({ id, label }) => {
        const brug = kapacitet.usage?.[id]
        if (!brug?.profiles.length) return null
        return <details className="cl-kapacitet-detaljer" key={id}>
          <summary>{label}: forbrug pr. udbyder og konto · {brug.profiles.length} konti</summary>
          <div className="cl-tabel-holder"><table className="cl-kapacitet-tabel">
            <thead><tr><th>Udbyder · konto</th><th>Ind</th><th>Ud</th><th>Samlet</th><th>Kald</th></tr></thead>
            <tbody>{brug.profiles.map((p) => <tr key={`${p.provider}:${p.auth_profile}`}>
              <th scope="row">{p.provider} · {p.auth_profile}</th>
              <td>{tal(p.input_tokens)}</td><td>{tal(p.output_tokens)}</td>
              <td>{tal(p.total_tokens)}</td><td>{tal(p.calls)}</td>
            </tr>)}</tbody>
          </table></div>
          {brug.unmetered_calls > 0 && <p className="cl-note">
            {tal(brug.unmetered_calls)} vellykkede kald mangler tokenmåling. Forbruget er et minimum.
          </p>}
        </details>
      })}
      {kapacitet.estimated_capacity?.month && <details className="cl-kapacitet-detaljer">
        <summary>Estimeret restkapacitet pr. konto</summary>
        <div className="cl-tabel-holder"><table className="cl-kapacitet-tabel">
          <thead><tr><th>Udbyder · konto</th><th>Kald/dag</th><th>Målt tokens/kald</th><th>Estimeret rest denne måned</th></tr></thead>
          <tbody>{kapacitet.estimated_capacity.month.profiles.map((p) =>
            <tr key={`${p.provider}:${p.auth_profile}`}>
              <th scope="row">{p.provider} · {p.auth_profile}</th>
              <td>{tal(p.daily_call_limit)}</td>
              <td>{tal(p.mean_tokens_per_call)} <small>({tal(p.sample_calls)} kald)</small></td>
              <td>{tal(p.estimated_tokens)}</td>
            </tr>)}</tbody>
        </table></div>
        {kapacitet.estimated_capacity.month.unknown_members.length > 0 && <p className="cl-note">
          {tal(kapacitet.estimated_capacity.month.unknown_members.length)} aktive konti har
          ukendt kaldsgrænse eller for lidt målt forbrug og er ikke med i estimatet.
        </p>}
        <p className="cl-note">
          Konti med forskellige profiler regnes som separate kvoter. Hvis de deler
          udbyderens kvotepulje, er estimatet for højt.
        </p>
      </details>}
      <h3>Kvoter pr. konto</h3>
      {vinduer.length
        ? <ul className="cl-kvoter">{vinduer.map((v, i) =>
          <Vindue key={`${v.provider}-${v.auth_profile}-${v.period}-${v.unit}-${i}`} v={v} />)}</ul>
        : <p className="cl-tom">Ingen tokenkvoter er registreret endnu. Det målte forbrug ovenfor er stadig tilgængeligt.</p>}
    </div>
  )
}
