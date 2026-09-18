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
import type { KvoteVindue } from '../../../lib/cheapLaneApi'

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

export function CheapLaneCapacity({ vinduer }: { vinduer: KvoteVindue[] }) {
  if (!vinduer.length) {
    return (
      <p className="cl-tom">
        Ingen kvoter er registreret for cheap lane endnu. Sæt en kvotepolitik på
        en udbyder for at se forbrug mod en grænse her.
      </p>
    )
  }
  return <ul className="cl-kvoter">{vinduer.map((v, i) => <Vindue key={`${v.provider}-${v.period}-${v.unit}-${i}`} v={v} />)}</ul>
}
