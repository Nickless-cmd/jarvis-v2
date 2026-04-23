import { useState } from 'react'
import { Bot } from 'lucide-react'
import { s, T } from '../../shared/theme/tokens'
import { SubTabs } from './shared'
import { OperationsTab } from './OperationsTab'
import { AgentsTab } from './AgentsTab'

const OPS_SUBTABS = [
  { id: 'operations', label: 'Operationer' },
  { id: 'agents', label: 'Agenter' },
]

export function OpsTab({
  data,
  selection,
  onSelectionChange,
  onOpenRun,
  onOpenSession,
  onOpenApproval,
  onOpenItem,
  onToolIntentAction,
  toolIntentActionBusy,
  toolIntentActionError,
  thoughtProposals,
  onResolveThoughtProposal,
}) {
  const [sub, setSub] = useState('operations')

  return (
    <div style={s({ display: 'flex', flexDirection: 'column', gap: 0 })}>
      <div style={s({ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 16 })}>
        <Bot size={15} color={T.accent} />
        <span style={s({ fontSize: 14, fontWeight: 500, color: T.text1 })}>Ops</span>
        <div style={s({ marginLeft: 'auto' })}>
          <SubTabs tabs={OPS_SUBTABS} active={sub} onChange={setSub} />
        </div>
      </div>
      {sub === 'operations' ? (
        <OperationsTab
          data={data}
          selection={selection}
          onSelectionChange={onSelectionChange}
          onOpenRun={onOpenRun}
          onOpenSession={onOpenSession}
          onOpenApproval={onOpenApproval}
          onOpenItem={onOpenItem}
          onToolIntentAction={onToolIntentAction}
          toolIntentActionBusy={toolIntentActionBusy}
          toolIntentActionError={toolIntentActionError}
          thoughtProposals={thoughtProposals}
          onResolveThoughtProposal={onResolveThoughtProposal}
        />
      ) : null}
      {sub === 'agents' ? <AgentsTab /> : null}
    </div>
  )
}
