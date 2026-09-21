/**
 * Fund og revisionsspor.
 *
 * Fundene er deterministiske: samme tilstand giver samme fund. Fladen må
 * derfor ikke omskrive dem til noget blødere — koden, alvorligheden og
 * BEVISET står som serveren gav dem, fordi beviset er dét der gør et fund
 * handlingsbart. «auth-profile-starvation» alene siger ingenting;
 * «auth_profile: mistral, slots: 1» siger hvor man går hen.
 *
 * Revisionssporet står på samme flade, fordi det oftest er svaret på «hvorfor
 * ser det sådan ud» — nogen pausede noget for tyve minutter siden.
 */
import type { Diagnose, Revision } from '../../../lib/cheapLaneApi'

const RANG: Record<string, number> = { high: 0, medium: 1, low: 2 }

function tid(s?: string | null): string {
  if (!s) return '–'
  const d = new Date(s)
  return Number.isNaN(d.getTime()) ? String(s).slice(0, 16)
    : d.toLocaleString('da-DK', { day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit' })
}

export function CheapLaneDiagnostics({
  diagnose, revisioner, revisionFejl = false, central = [], pakkeUrl,
}: {
  diagnose: Diagnose | null
  revisioner: Revision[]
  /** Kunne sporet ikke hentes? Et TOMT spor betyder «ingen har ændret noget» —
   *  en helt anden oplysning end «vi kunne ikke hente det». */
  revisionFejl?: boolean
  /** Centrals egne haendelser for lanen — samme tidslinje som fundene, fordi
   *  et fund og en Central-haendelse ofte er to sider af samme sag. */
  central?: { id?: string; ts?: string; kind?: string; severity?: string; message?: string }[]
  /** Hele diagnose-pakken som fil: tidsrum, snapshot, fund, logs og
   *  konfigurations-fingeraftryk — uden hemmeligheder. */
  pakkeUrl?: string
}) {
  const fund = [...(diagnose?.findings ?? [])].sort(
    (a, b) => (RANG[a.severity] ?? 9) - (RANG[b.severity] ?? 9))

  return (
    <div className="cl-diagnose">
      {fund.length === 0 ? (
        <p className="cl-tom">Ingen fund. Cheap lane opfører sig som forventet.</p>
      ) : (
        <ul className="cl-fund-liste">
          {fund.map((f, i) => (
            <li key={`${f.code}-${i}`} className={`cl-fund cl-fund-${f.severity}`}>
              <div className="cl-fund-hoved">
                <span className="cl-fund-kode">{f.code}</span>
                <span className="cl-kilde">{f.severity}</span>
                <span className="cl-dæmpet cl-lille">{tid(f.last_observed_at)}</span>
              </div>
              {f.evidence ? (
                <dl className="cl-fund-bevis">
                  {Object.entries(f.evidence).map(([k, v]) => (
                    <div key={k}><dt>{k}</dt><dd>{String(v)}</dd></div>
                  ))}
                </dl>
              ) : null}
            </li>
          ))}
        </ul>
      )}

      {central.length ? (
        <>
          <h4 className="cl-forklaring-overskrift">Fra Central</h4>
          <ul className="cl-central">
            {central.slice(0, 8).map((h, i) => (
              <li key={`${h.id ?? i}`}>
                <span className="cl-kilde">{h.severity ?? 'info'}</span>
                <span className="cl-dæmpet cl-lille">{tid(h.ts)}</span>
                <span className="cl-besked">{h.message ?? h.kind ?? '—'}</span>
              </li>
            ))}
          </ul>
        </>
      ) : null}

      {pakkeUrl ? (
        <p className="cl-dæmpet cl-lille">
          <a href={pakkeUrl} download>Hent diagnose-pakken</a> — snapshot, fund,
          logs og konfigurations-fingeraftryk, uden hemmeligheder.
        </p>
      ) : null}

      <h4 className="cl-forklaring-overskrift">Revisionsspor</h4>
      {revisionFejl ? (
        <p className="cl-tom">Revisionssporet kunne ikke hentes.</p>
      ) : revisioner.length === 0 ? (
        <p className="cl-tom">Ingen handlinger endnu.</p>
      ) : (
        <div className="cl-tabel-holder">
          <table className="cl-tabel">
            <thead>
              <tr>
                <th scope="col">Tid</th><th scope="col">Handling</th>
                <th scope="col">Mål</th><th scope="col">Grund</th><th scope="col">Udfald</th>
              </tr>
            </thead>
            <tbody>
              {revisioner.map((r, i) => (
                <tr key={`${r.revision}-${i}`}>
                  <th scope="row">{tid(r.at)}</th>
                  <td>{r.action}</td>
                  <td>{r.target}</td>
                  <td className="cl-besked">{r.reason || '–'}</td>
                  <td>{r.outcome ?? '–'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
