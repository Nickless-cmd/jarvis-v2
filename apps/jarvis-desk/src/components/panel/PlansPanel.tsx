import { useEffect, useState } from 'react'
import { X, ListChecks } from 'lucide-react'
import type { ApiConfig } from '../../lib/api'
import { getCoworkPlans, type CoworkPlan } from '../../lib/coworkApi'
import { PlansPane } from '../cowork/PlansPane'

/**
 * Planer ved samtalen — Jarvis' `desk_show_pane('plan')`.
 *
 * 3/10-2026: desk afviste `plan` med «Desk har intet plan-panel», og panelet
 * stod i `IKKE_I_DESK`. Men planerne FINDES — cowork-fladen viser dem gennem
 * `PlansPane` og `getCoworkPlans`. Der manglede kun en visning ved samtalen,
 * ikke data. Vi genbruger begge, så der ikke opstår to sandheder om hvad en
 * plan er.
 */
export function PlansPanel({ config, onClose }: { config: ApiConfig; onClose: () => void }) {
  const [plans, setPlans] = useState<CoworkPlan[] | null>(null)
  const [fejl, setFejl] = useState('')
  useEffect(() => {
    let levende = true
    setFejl('')
    getCoworkPlans(config)
      .then((p) => { if (levende) setPlans(p) })
      .catch(() => { if (levende) { setFejl('Kunne ikke hente planer'); setPlans([]) } })
    return () => { levende = false }
  }, [config])
  return (
    <div className="artifact-panel">
      <div className="artifact-head">
        <ListChecks size={14} /> <span className="artifact-title">Planer</span>
        <button type="button" className="artifact-close" aria-label="Luk panel" onClick={onClose}>
          <X size={15} />
        </button>
      </div>
      <div className="artifact-body">
        {fejl && <div className="artifact-error">{fejl}</div>}
        {!fejl && !plans && <div className="artifact-loading">Henter…</div>}
        {plans && <PlansPane plans={plans} />}
      </div>
    </div>
  )
}
