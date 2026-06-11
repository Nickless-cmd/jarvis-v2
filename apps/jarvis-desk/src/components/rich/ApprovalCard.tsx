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
}: {
  approvalId: string
  tool: string
  action: string
  risk: string
  canApprove: boolean
  onApprove: (id: string) => void
  onDeny: (id: string) => void
}) {
  return (
    <div className={`approvalcard risk-${risk}`}>
      <div className="approvalcard-head">{tool} · {risk}</div>
      <pre className="approvalcard-action">{action}</pre>
      {canApprove ? (
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
