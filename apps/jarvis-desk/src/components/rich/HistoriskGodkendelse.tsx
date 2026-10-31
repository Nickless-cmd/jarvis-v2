import { useState } from 'react'

/** Et AFGJORT (eller forladt) godkendelses-kort, læst fra historikken.
 *
 * 31/10-2026 — DEL 1 af «kortet skal kunne findes igen».
 *
 * FØR: kortet levede KUN i klientens `pendingApproval`. En reload slettede det
 * sporløst, og en godkendelse Bjørn havde svaret på, kunne ikke findes igen.
 * Hans ord: «approval cards må ikk kunne dø et run».
 *
 * NU skriver serveren to hændelser i samtalens historik — `pending` da kortet
 * blev lavet, og `approved`/`denied`/`expired` da det blev afgjort. Formen er
 * append-only, så en afgørelse er en NY række, ikke en opdatering.
 *
 * HVORFOR INGEN KNAPPER — og hvorfor det er den rigtige grænse:
 * en persisteret række er historik. Et kort fra en tidligere session kan ikke
 * besvares: serveren har fejet posten, og både «Godkend» og «Afvis» ville
 * fejle. At vise dem alligevel var netop den fejl `ApprovalCard` allerede
 * rettede for udløbne kort («de så brugbare ud og var det ikke»).
 * De LEVENDE kort håndteres fortsat af `GodkendelsesKort` i composer-laget —
 * det er to flader med hver sin sandhed, og de skal ikke blandes sammen.
 */
export interface GodkendelsesHaendelse {
  approval_id: string
  tool: string
  action: string
  status: string
  risk?: string
  decided_by?: string
  decided_at?: string
}

const STATUS: Record<string, { tekst: string; klasse: string }> = {
  pending: { tekst: 'Afventer', klasse: 'venter' },
  approved: { tekst: 'Godkendt', klasse: 'godkendt' },
  denied: { tekst: 'Afvist', klasse: 'afvist' },
  expired: { tekst: 'Udløb uden svar', klasse: 'udloeb' },
}

export function HistoriskGodkendelse({ data }: { data: GodkendelsesHaendelse }) {
  const [aaben, setAaben] = useState(false)
  const status = STATUS[data.status] ?? { tekst: data.status, klasse: 'ukendt' }

  return (
    <div className={`approvalcard risk-${data.risk || ''} approvalcard-historik`}>
      <div className="approvallinje">
        <button
          type="button"
          className="approvallinje-aabn"
          aria-expanded={aaben}
          onClick={() => setAaben((v) => !v)}
          title={aaben ? 'Skjul kommandoen' : 'Vis kommandoen'}
        >
          <span className="approvallinje-pil" aria-hidden="true">{aaben ? '▾' : '▸'}</span>
          <span className="approvallinje-tool">{data.tool}</span>
          <span className="approvallinje-resume">{resume(data.action)}</span>
        </button>

        <span className={`approvallinje-status status-${status.klasse}`}>
          {status.tekst}
        </span>
      </div>

      <div className="approvallinje-krop" data-aaben={aaben ? 'true' : 'false'}>
        <div className="approvallinje-indre">
          <pre className="approvalcard-action" inert={!aaben}>{data.action}</pre>
        </div>
      </div>
    </div>
  )
}

/** Første meningsfulde linje, kortet ned — samme regel som det levende kort,
 *  så de to flader læses ens når man scroller tilbage. */
function resume(tekst: string): string {
  const første = String(tekst || '')
    .split('\n')
    .map((l) => l.trim())
    .find((l) => l.length > 0) || ''
  if (!første) return ''
  return første.length > 72 ? `${første.slice(0, 71)}…` : første
}
