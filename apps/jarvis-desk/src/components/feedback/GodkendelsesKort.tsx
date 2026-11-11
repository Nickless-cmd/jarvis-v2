import { ApprovalCard } from '../rich/ApprovalCard'
import { useStream } from '../../hooks/useStream'
import { useSettings } from '../../hooks/useSettings'

/** Godkendelses-kortet, vist over composeren paa den flade han staar paa.
 *
 * 25/9-2026. Bjoerns symptom, gentaget over maaneder: «jeg kan sidde i en
 * samtale i desk og tro han er staaet af, fordi mobilen har overtaget og
 * approval-kortet er landet der.»
 *
 * Det var ikke en overtagelse. `ApprovalCard` blev kun renderet i `CodeView`
 * (StreamContext'ens egen kommentar sagde det: «Fang approval_request
 * (code/cowork, permission=ask)»). Stod han paa CHAT-fladen, fandtes kortet
 * slet ikke — kun en OS-notits. Paa telefonen var der et kort. Kortet flyttede
 * sig aldrig; skrivebordet tegnede det bare ikke.
 *
 * Tilstanden bor i den delte StreamContext og fyldes ogsaa af
 * `hentVentendeGodkendelseOveralt`. Kortet maa kun tegnes i sin egen session,
 * selv om opsamlingen finder det fra en anden aktiv samtale.
 *
 * Rollen laeses fra `auth`, ikke fra en prop: hvem der maa svare er en
 * egenskab ved brugeren, ikke ved fladen.
 */
export function GodkendelsesKort({ sessionId }: { sessionId: string | null }) {
  const stream = useStream()
  const { auth } = useSettings()
  const p = stream.pendingApproval
  if (!p) return null

  // 11/11-2026: SESSION-GATEN GÆLDER KUN TOOL-GODKENDELSER.
  //
  // Bjoerns klage: «der godkendelse kort lander i baggrundsjobs panelet og ikk
  // over composer som alle andre approval card … jeg skal have panelet aaben
  // naar du kalder en agent jeg skal godkende ellers ser jeg dem ikke.»
  //
  // Aarsagen er ikke at agent-vejen mangler — den findes i StreamContext og
  // blev bygget 14/10. Det er DENNE linje. En `tool`-godkendelse blokerer den
  // stream den kom fra, saa kun dens egen samtale maa tegne kortet. En
  // `agent`-godkendelse blokerer INGENTING: den parkerer et assignment og
  // venter i lageret indtil nogen svarer. Gatede vi den paa samtalens id,
  // forsvandt den praecis naar agenten var startet fra en anden samtale (eller
  // fra en autonom koersel) — og tilbage var kun panel-raekken.
  //
  // At vise den bredere er ikke en lempelse: afgoerelsen baerer approvalens
  // EGEN session med (`StreamContext.afgoer` -> `post.sessionId`), og
  // `db_agent_approvals.decide` afviser med POLICY_DENIED hvis den ikke
  // matcher `origin_session_id`. Serveren er altsaa stadig den der afgoer
  // hvem der maa svare — kortet afgoer kun hvor spoergsmaalet kan SES.
  const hoererTilHer = p.kind === 'agent' || (!!sessionId && p.sessionId === sessionId)
  if (!hoererTilHer) return null
  return (
    <ApprovalCard
      approvalId={p.approvalId}
      tool={p.tool}
      action={p.action}
      risk="medium"
      canApprove={auth?.role === 'owner'}
      expiresAt={p.expiresAt}
      onApprove={(id) => stream.approve(id)}
      onDeny={(id) => stream.deny(id)}
    />
  )
}
