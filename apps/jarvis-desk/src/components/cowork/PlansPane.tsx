import type { CoworkPlan } from '../../lib/coworkApi'

export function PlansPane({ plans }: { plans: CoworkPlan[] }) {
  if (plans.length === 0) return <div className="cowork-empty">Ingen planer</div>
  return (
    <div className="cowork-plans">
      {plans.map((p) => {
        const pct = p.steps_total > 0 ? Math.round((p.steps_done / p.steps_total) * 100) : 0
        return (
          <div key={p.id} className="cowork-plan">
            <div className="cowork-plan-title">{p.title}</div>
            <div className="cowork-plan-sub">{p.steps_done} af {p.steps_total} trin · {p.status || 'forslag'}</div>
            <div className="cowork-progress"><div className="cowork-progress-fill" style={{ width: `${pct}%` }} /></div>
          </div>
        )
      })}
    </div>
  )
}
