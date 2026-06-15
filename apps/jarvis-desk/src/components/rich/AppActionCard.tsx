type AppAction = 'switch_to_code_mode' | 'request_full_access'

const PROMPT: Record<AppAction, string> = {
  switch_to_code_mode: 'Jarvis vil skifte til code mode for at fortsætte. Skift nu?',
  request_full_access: 'Jarvis beder om fuld adgang (trust) til denne opgave. Slå til?',
}

/** Inline godkendelseskort: Jarvis foreslår et mode-/permission-skift.
 *  Kun brugerens klik skifter noget — kortet udfører intet selv. */
export function AppActionCard({
  action,
  reason,
  onApprove,
  onReject,
}: {
  action: AppAction
  reason: string
  onApprove: () => void
  onReject: () => void
}) {
  return (
    <div className="appactioncard">
      <div className="appactioncard-head">{PROMPT[action]}</div>
      {reason ? <div className="appactioncard-reason">{reason}</div> : null}
      <div className="appactioncard-actions">
        <button type="button" onClick={onApprove}>Ja</button>
        <button type="button" onClick={onReject}>Nej</button>
      </div>
    </div>
  )
}
