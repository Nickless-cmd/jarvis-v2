import { useEffect, useId, useRef, useState } from 'react'
import { X } from 'lucide-react'

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
 * 1/11-2026: og nu også UDFALDET. `approved` betyder at Bjørn sagde ja —
 * ikke at kommandoen kørte. `failed`/`outcome_unknown`/
 * `aborted_before_dispatch` er de tilstande hvor de to ting ikke er det
 * samme, og de skrives som en tredje række af `db_approval_bridge`.
 *
 * HVORFOR INGEN KNAPPER — og hvorfor det er den rigtige grænse:
 * en persisteret række er historik. Et kort fra en tidligere session kan ikke
 * besvares: serveren har fejet posten, og både «Godkend» og «Afvis» ville
 * fejle. At vise dem alligevel var netop den fejl `ApprovalCard` allerede
 * rettede for udløbne kort («de så brugbare ud og var det ikke»).
 * De LEVENDE kort håndteres fortsat af `GodkendelsesKort` i composer-laget —
 * det er to flader med hver sin sandhed, og de skal ikke blandes sammen.
 */
import type { GodkendelsesHaendelse } from '../../lib/godkendelseIFolden'

/* Typen har ÉT hjem: `lib/godkendelseIFolden.ts`, som ogsaa bruger den til at
 * flette raekkerne ind i turen. Stod den to steder, ville en ny status kun
 * blive tilfoejet det ene — og de to flader ville divergere tavst. */
export type { GodkendelsesHaendelse }

const STATUS: Record<string, { tekst: string; klasse: string }> = {
  pending: { tekst: 'Afventer', klasse: 'venter' },
  approved: { tekst: 'Godkendt', klasse: 'godkendt' },
  denied: { tekst: 'Afvist', klasse: 'afvist' },
  expired: { tekst: 'Udløb uden svar', klasse: 'udloeb' },
  /* UDFALDET, ikke afgørelsen (1/11-2026). Bjørn: «og hvis godkendelsen ikk
   * gik igennem? det ved kun du = så skal det osse fikses».
   *
   * `approved` betyder at HAN sagde ja — ikke at kommandoen kørte. De tre
   * nedenfor er præcis de tilstande hvor de to ting ikke er det samme, og de
   * skal stå med deres egen tekst. Uden dem faldt de i `ukendt` og viste den
   * rå engelske streng — en tilstand der så ud som en teknisk detalje midt i
   * et svar han skal kunne læse. */
  failed: { tekst: 'Kørte ikke igennem', klasse: 'fejlet' },
  outcome_unknown: { tekst: 'Udfald ukendt', klasse: 'ukendt' },
  aborted_before_dispatch: { tekst: 'Kørte aldrig', klasse: 'udloeb' },
}

export function HistoriskGodkendelse({
  data,
  live,
}: {
  data: GodkendelsesHaendelse
  /** Sat naar denne række ER den godkendelse der venter lige nu.
   *
   *  31/10-2026 — DEL 3. Kortet laa i `.composer-area` og skubbede transcriptet
   *  op. Nu ligger det hvor det hører: som en række i samtalen. Men en
   *  persisteret række er historik og kan ikke besvares — så når rækken
   *  matcher den ventende godkendelse, får den knapperne tilbage.
   *
   *  Det er ÉN flade, ikke to: uden dette ville den samme godkendelse stå to
   *  steder (historik-rækken uden knapper + det flydende kort med), og man
   *  ville kunne se sit eget svar stå to gange.
   */
  live?: {
    canApprove: boolean
    expiresAt?: string
    onApprove: (id: string) => void
    onDeny: (id: string) => void
  }
}) {
  const [visDetaljer, setVisDetaljer] = useState(false)
  const status = STATUS[data.status] ?? { tekst: data.status, klasse: 'ukendt' }
  // Baandet holdes HER, ikke kun hos kalderen: status er sandheden om hvorvidt
  // der kan svares. En afgjort raekke maa aldrig faa knapper, heller ikke hvis
  // en kalder sender `live` ved en fejl — saa ville et gammelt svar se ud som
  // et aabent spoergsmaal.
  const erLevende = Boolean(live) && data.status === 'pending'
  const kanSvare = erLevende && Boolean(live?.canApprove)

  return (
    <div className={`approvalcard risk-${data.risk || ''}${erLevende ? ' approvalcard-live' : ' approvalcard-historik'}`}>
      <div className="approvallinje">
        <button
          type="button"
          className="approvallinje-aabn"
          aria-haspopup="dialog"
          onClick={() => setVisDetaljer(true)}
          title="Vis detaljer"
          aria-label={`Vis detaljer for ${data.tool}`}
        >
          <span className="approvallinje-tool">{data.tool}</span>
          <span className="approvallinje-resume">{resume(data.action)}</span>
          <span className="approvallinje-detaljer" aria-hidden="true">Detaljer</span>
        </button>

        {!erLevende ? (
          <span className={`approvallinje-status status-${status.klasse}`}>
            {status.tekst}
          </span>
        ) : null}
      </div>

      {erLevende && live ? (
        <div className="approvalcard-actionbar">
          {kanSvare ? (
            <span className="approvalcard-actions">
              <button type="button" onClick={() => live.onDeny(data.approval_id)}>Afvis</button>
              <button type="button" className="approvalcard-primary" onClick={() => live.onApprove(data.approval_id)}>Godkend</button>
            </span>
          ) : (
            <span className="approvalcard-readonly">Kun owner kan godkende</span>
          )}
        </div>
      ) : null}

      {visDetaljer ? (
        <GodkendelsesDetaljer tool={data.tool} action={data.action} onClose={() => setVisDetaljer(false)} />
      ) : null}
    </div>
  )
}

function GodkendelsesDetaljer({ tool, action, onClose }: {
  tool: string
  action: string
  onClose: () => void
}) {
  const dialogRef = useRef<HTMLDialogElement>(null)
  const titleId = useId()

  useEffect(() => {
    const dialog = dialogRef.current
    if (dialog?.showModal) dialog.showModal()
    else dialog?.setAttribute('open', '')
    return () => dialog?.close?.()
  }, [])

  return (
    <dialog
      ref={dialogRef}
      className="approval-details-dialog"
      aria-labelledby={titleId}
      onCancel={(event) => { event.preventDefault(); onClose() }}
      onClick={(event) => { if (event.target === event.currentTarget) onClose() }}
    >
      <div className="approval-details-content">
        <header className="approval-details-head">
          <div>
            <span className="approval-details-kicker">Godkendelse</span>
            <h2 id={titleId}>{tool}</h2>
          </div>
          <button type="button" className="approval-details-close" aria-label="Luk detaljer" onClick={onClose}>
            <X size={17} />
          </button>
        </header>
        <pre className="approvalcard-action">{action}</pre>
        <footer className="approval-details-foot">
          <button type="button" onClick={onClose}>Luk</button>
        </footer>
      </div>
    </dialog>
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
