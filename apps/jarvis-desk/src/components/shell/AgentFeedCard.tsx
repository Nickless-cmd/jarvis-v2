import { useEffect, useState } from 'react'
import { ShieldAlert, CircleAlert, CircleCheck, Bot, HelpCircle } from 'lucide-react'
import { afgoerAgentApproval, bucketLabel, type FeedCard } from '../../lib/agentContractApi'
import type { ApiConfig } from '../../lib/api'
import { getTotpStatus } from '../../lib/totpApi'
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
  /**
   * Totrinskoden kraeves KUN hvis brugeren har sat totrin op — ruten springer den
   * over ellers (`agent_approvals._kraev_totrin_ved_godkendelse`). Feltet blev tegnet
   * UBETINGET, saa Bjoern 8/10-2026 blev bedt om en sekscifret kode han ikke havde,
   * i et kort hvor den ikke blev brugt til noget. ``null`` = vi ved det ikke endnu
   * (eller status-ruten fejlede): vis feltet, for en godkendelse maa ikke blokeres
   * af en manglende status.
   */
  const [totpAktiv, setTotpAktiv] = useState<boolean | null>(null)
  const a = card.approval
  const approvalId = a?.approval_id ?? ''
  useEffect(() => {
    if (!approvalId) return
    let lever = true
    void getTotpStatus(config)
      .then((s) => { if (lever) setTotpAktiv(Boolean(s.configured)) })
      .catch(() => { if (lever) setTotpAktiv(null) })
    return () => { lever = false }
  }, [config, approvalId])
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
          {totpAktiv !== false && (
            <input aria-label="Totrinskode" inputMode="numeric" autoComplete="one-time-code" placeholder="Totrinskode"
                   value={kode} onChange={(e) => setKode(e.target.value)} />
          )}
          <button type="button" disabled={travl} onClick={() => void afgoer('approve')}>Godkend</button>
          <button type="button" disabled={travl} onClick={() => void afgoer('deny')}>Afvis</button>
        </div>
      )}
    </>
  )
}
