import { useEffect, useState } from 'react'

/** Interaktivt approval-kort. Approve/Deny er ÆGTE UI-knapper (ikke renderet fra
 *  model/tool-tekst). Action-teksten vises inert via <pre> så fjendtligt indhold
 *  ikke kan spoofe en klikbar approve-knap. Rolle-gate: kun owner (canApprove)
 *  ser knapperne — serveren håndhæver den reelle grænse. */
export function ApprovalCard({
  approvalId,
  tool,
  action,
  risk,
  canApprove,
  onApprove,
  onDeny,
  expiresAt,
}: {
  approvalId: string
  tool: string
  action: string
  risk: string
  canApprove: boolean
  onApprove: (id: string) => void
  onDeny: (id: string) => void
  /** Serverens frist (ISO-tid). Se `PendingApproval.expiresAt` for hvorfor
   *  den findes: uden den kunne kortet hænge for evigt. */
  expiresAt?: string
}) {
  const [nu, setNu] = useState(() => Date.now())
  const harFrist = Boolean(expiresAt)

  // Kun en tikker når der FAKTISK er en frist. Et kort uden frist skal ikke
  // starte et ur der aldrig viser noget — det ville være en usynlig byrde pr.
  // kort, og der kan ligge flere.
  useEffect(() => {
    if (!harFrist) return
    const id = window.setInterval(() => setNu(Date.now()), 1000)
    return () => window.clearInterval(id)
  }, [harFrist, expiresAt])

  const slut = expiresAt ? Date.parse(expiresAt) : NaN
  const msTilbage = Number.isFinite(slut) ? slut - nu : NaN
  const udloebet = Number.isFinite(msTilbage) && msTilbage <= 0

  return (
    <div className={`approvalcard risk-${risk}${udloebet ? ' approvalcard-udloebet' : ''}`}>
      <div className="approvalcard-head">
        <span>{tool} · {risk}</span>
        {udloebet ? (
          <span className="approvalcard-frist">Fristen løb ud</span>
        ) : Number.isFinite(msTilbage) ? (
          <span className="approvalcard-frist">{nedtaelling(msTilbage)}</span>
        ) : null}
      </div>
      <pre className="approvalcard-action">{action}</pre>
      {udloebet ? (
        // Kortet svarer ikke længere: serveren har fejet posten, og både
        // «Godkend» og «Afvis» ville fejle. At vise knapperne alligevel var
        // netop fejlen — de så brugbare ud og var det ikke. Runnet har selv
        // afsluttet, og beskeden er sendt ad notifikations-vejen.
        <div className="approvalcard-readonly">
          Ingen godkendelse kom i tide. Runnet er afsluttet og venter på næste træk.
        </div>
      ) : canApprove ? (
        <div className="approvalcard-actions">
          <button type="button" onClick={() => onApprove(approvalId)}>Godkend</button>
          <button type="button" onClick={() => onDeny(approvalId)}>Afvis</button>
        </div>
      ) : (
        <div className="approvalcard-readonly">Kun owner kan godkende</div>
      )}
    </div>
  )
}

/** «4:32 tilbage» — eller «under 1 min» når det haster. */
function nedtaelling(ms: number): string {
  const sek = Math.max(0, Math.floor(ms / 1000))
  if (sek < 60) return `${sek}s tilbage`
  const min = Math.floor(sek / 60)
  const rest = sek % 60
  return `${min}:${String(rest).padStart(2, '0')} tilbage`
}
