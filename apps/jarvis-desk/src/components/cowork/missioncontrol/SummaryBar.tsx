/** Pinned tælle-bar øverst i Mission Control — "kan jeg se med ét blik at alt er ok?".
 *  Det enkelt-mest kontrolcenter-agtige element. Klik en tælle → skift til den fane. */

export interface SummaryCounts {
  running: number
  failed: number
  pendingApprovals: number
  scheduled: number
  agents: number
  costUsd?: number
}

export function SummaryBar({
  counts,
  onPick,
}: {
  counts: SummaryCounts
  onPick?: (tab: 'runs' | 'godkendelser' | 'planlagt' | 'agenter') => void
}) {
  const cell = (
    label: string, value: string | number, tone: string,
    tab?: 'runs' | 'godkendelser' | 'planlagt' | 'agenter',
  ) => (
    <button
      type="button"
      className={`mc-summary-cell mc-summary-cell--${tone}`}
      onClick={() => tab && onPick?.(tab)}
      disabled={!tab}
    >
      <span className="mc-summary-value">{value}</span>
      <span className="mc-summary-label">{label}</span>
    </button>
  )
  return (
    <div className="mc-summary">
      {cell('kører', counts.running, 'blue', 'runs')}
      {cell('fejlet', counts.failed, counts.failed > 0 ? 'red' : 'gray', 'runs')}
      {cell('afventer', counts.pendingApprovals, counts.pendingApprovals > 0 ? 'amber' : 'gray', 'godkendelser')}
      {cell('planlagt', counts.scheduled, 'gray', 'planlagt')}
      {cell('agenter', counts.agents, 'gray', 'agenter')}
      {counts.costUsd !== undefined && cell('pris', `$${counts.costUsd.toFixed(2)}`, 'gray')}
    </div>
  )
}
