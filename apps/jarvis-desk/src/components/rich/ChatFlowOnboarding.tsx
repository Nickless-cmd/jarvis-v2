import { useEffect, useRef, useState } from 'react'
import { useChatFlow } from '../../hooks/useChatFlow'
import type { ChatFlowModel } from '../../lib/chatFlowModel'

const EXAMPLE_LINES = [
  'Undersøger det vigtigste først',
  'Samler fundene',
  'Gør svaret klar',
]

export function ChatFlowOnboarding({
  runId,
  streaming,
  model,
}: {
  runId: string
  streaming: boolean
  model: ChatFlowModel
}) {
  const flow = useChatFlow()
  const [claimId, setClaimId] = useState<string | null>(null)
  const attemptedRun = useRef<string | null>(null)
  const acknowledgedClaims = useRef(new Set<string>())

  useEffect(() => {
    if (!streaming || !runId || flow.state.onboarding_seen || attemptedRun.current === runId) return
    attemptedRun.current = runId
    let alive = true
    void flow.claimOnboarding(runId).then((claim) => {
      if (alive && claim.claimed && claim.claim_id) setClaimId(claim.claim_id)
    }).catch(() => { /* Onboarding persistence never blocks the answer. */ })
    return () => { alive = false }
  }, [flow, runId, streaming])

  useEffect(() => {
    if (!claimId || acknowledgedClaims.current.has(claimId)) return
    acknowledgedClaims.current.add(claimId)
    const frame = requestAnimationFrame(() => {
      void flow.acknowledgeOnboarding(claimId).catch(() => {
        /* An unacknowledged claim expires, so a later real run can retry. */
      })
    })
    return () => cancelAnimationFrame(frame)
  }, [claimId, flow])

  if (!claimId) return null

  const hasDemonstration = model.visibleSynthesis.length >= 2
  const living = hasDemonstration ? model.visibleSynthesis : EXAMPLE_LINES
  const calm = hasDemonstration ? model.calmStatus : EXAMPLE_LINES[EXAMPLE_LINES.length - 1]

  return (
    <section className="chat-flow-onboarding" role="group" aria-label="Vælg Chat Mode-visning">
      <p className="chat-flow-onboarding-title">Hvordan skal Jarvis' arbejde leve i chatten?</p>
      <div className="chat-flow-onboarding-choices">
        <article className="chat-flow-onboarding-choice" data-testid="onboarding-living">
          <h3>B · Levende</h3>
          {!hasDemonstration ? <span className="chat-flow-example-label">Eksempel</span> : null}
          <div className="chat-flow-preview chat-flow-preview--living">
            {living.map((line) => <span key={line}>{line}</span>)}
          </div>
          <button type="button" onClick={() => void flow.setPreference('living')}>Vælg levende</button>
        </article>
        <article className="chat-flow-onboarding-choice" data-testid="onboarding-calm">
          <h3>C · Rolig</h3>
          {!hasDemonstration ? <span className="chat-flow-example-label">Eksempel</span> : null}
          <div className="chat-flow-preview chat-flow-preview--calm"><span>{calm}</span></div>
          <button type="button" onClick={() => void flow.setPreference('calm')}>Vælg rolig</button>
        </article>
      </div>
      <button type="button" className="chat-flow-adaptive-choice"
        onClick={() => void flow.setPreference('adaptive')}>Tilpas automatisk</button>
    </section>
  )
}
