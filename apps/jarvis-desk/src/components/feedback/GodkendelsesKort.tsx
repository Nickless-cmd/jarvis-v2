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
 * Tilstanden var der hele tiden: `stream.pendingApproval` bor i den delte
 * StreamContext og fyldes af `hentVentendeGodkendelseOveralt`. Kun tegningen
 * manglede — samme figur som [[GenoptagelsesVarsel]] samme dag, ét lag under.
 *
 * Rollen laeses fra `auth`, ikke fra en prop: hvem der maa svare er en
 * egenskab ved brugeren, ikke ved fladen.
 */
export function GodkendelsesKort() {
  const stream = useStream()
  const { auth } = useSettings()
  const p = stream.pendingApproval
  if (!p) return null
  return (
    <ApprovalCard
      approvalId={p.approvalId}
      tool={p.tool}
      action={p.action}
      risk="medium"
      canApprove={auth?.role === 'owner'}
      onApprove={(id) => stream.approve(id)}
      onDeny={(id) => stream.deny(id)}
    />
  )
}
