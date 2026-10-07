import { useState } from 'react'
import { ShieldAlert, CircleAlert, CircleCheck, Bot, HelpCircle } from 'lucide-react'
import { afgoerAgentApproval, bucketLabel, type FeedCard } from '../../lib/agentContractApi'
import type { ApiConfig } from '../../lib/api'
import '../../styles/agent-contract.css'

const MODEL_CLAIM: Record<string, string> = {
  accepted: 'ikke set af modellen endnu', delivered: 'leveret til Jarvis', claimed_by_model_step: 'set af modellen',
  acknowledged: 'bekræftet af Jarvis',
}

export function agentKortIkon(card: FeedCard) {
  if (card.ref_kind === 'approval' || card.bucket === 'waiting_for_approval') return ShieldAlert
  if (card.bucket === 'outcome_unknown' || card.bucket === 'unknown') return HelpCircle
  if (card.section === 'svar') return CircleCheck
  if (card.section === 'venter') return CircleAlert
  return Bot
}

/** Brødteksten i et agentkort i notifikationsfeedet. Kortet viser KUN det serveren har gjort sikkert og
 *  begrænset (titel, årsag, fejlkode, kort resumé) — fuldt output ligger bag inspectoren med ejer-/sessionskontrol,
 *  og intet herfra sendes ind i den åbne samtale. Læst, kvitteret, godkendt og modelclaim er fire adskilte
 *  tilstande og vises som sådan. */
export function AgentFeedCardBody({
  config, card, onChanged, onError,
}: {
  config: ApiConfig
  card: FeedCard
  onChanged: () => void
  onError: (message: string) => void
}) {
  const [kode, setKode] = useState('')
  const [travl, setTravl] = useState(false)
  const a = card.approval
  const sidste = (card.error?.code || card.error?.reason)
    ? [card.error?.phase && `fase ${card.error.phase}`, card.error?.code, card.error?.reason].filter(Boolean).join(' · ')
    : ''

  const afgoer = async (decision: 'approve' | 'deny') => {
    if (!a) return
    setTravl(true); onError('')
    try {
      await afgoerAgentApproval(config, a.approval_id, decision, a.digest, kode)
      setKode('')
      onChanged()
    } catch (reason) {
      onError(reason instanceof Error ? reason.message : 'Afgørelsen kunne ikke sendes.')
    } finally { setTravl(false) }
  }

  return (
    <>
      {card.reason && <p className="ac-kort-aarsag" data-testid={`ac-aarsag-${card.ref_id}`}>{card.reason}</p>}
      {sidste && <p className="ac-kort-fejl">Fejlårsag: {sidste}</p>}
      {card.summary && <p className="ac-kort-resume" data-testid={`ac-resume-${card.ref_id}`}>{card.summary}</p>}
      {card.ref_kind === 'agent' && (
        <p className="ac-tilstande" data-testid={`ac-tilstande-${card.ref_id}`}>
          {bucketLabel(card.bucket)} · {card.state.read ? 'læst' : 'ulæst'}
          {card.state.assignment_status && ['completed', 'failed', 'cancelled', 'timed_out'].includes(card.state.assignment_status)
            ? ` · ${card.state.acknowledged ? 'kvitteret' : 'ikke kvitteret'}` : ''}
          {card.state.model_claim ? ` · modellen: ${MODEL_CLAIM[card.state.model_claim] ?? card.state.model_claim}` : ''}
        </p>
      )}
      {a && (
        <div className="ac-kort-handlinger">
          <input aria-label="Totrinskode" inputMode="numeric" autoComplete="one-time-code" placeholder="Totrinskode"
                 value={kode} onChange={(e) => setKode(e.target.value)} />
          <button type="button" disabled={travl} onClick={() => void afgoer('approve')}>Godkend</button>
          <button type="button" disabled={travl} onClick={() => void afgoer('deny')}>Afvis</button>
        </div>
      )}
    </>
  )
}
