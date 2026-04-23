import { useState } from 'react'
import { Brain } from 'lucide-react'
import { s, T } from '../../shared/theme/tokens'
import { SubTabs } from './shared'
import { LivingMindTab } from './LivingMindTab'
import { SoulTab } from './SoulTab'
import { CognitiveStateTab } from './CognitiveStateTab'

const MIND_SUBTABS = [
  { id: 'consciousness', label: 'Bevidsthed' },
  { id: 'soul', label: 'Sjæl' },
  { id: 'cognitive', label: 'Kognition' },
]

export function MindTab({ data, onOpenItem, onHeartbeatTick, heartbeatBusy }) {
  const [sub, setSub] = useState('consciousness')

  return (
    <div style={s({ display: 'flex', flexDirection: 'column', gap: 0 })}>
      <div style={s({ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 16 })}>
        <Brain size={15} color={T.accent} />
        <span style={s({ fontSize: 14, fontWeight: 500, color: T.text1 })}>Mind</span>
        <div style={s({ marginLeft: 'auto' })}>
          <SubTabs tabs={MIND_SUBTABS} active={sub} onChange={setSub} />
        </div>
      </div>
      {sub === 'consciousness' ? (
        <LivingMindTab data={data} onOpenItem={onOpenItem} onHeartbeatTick={onHeartbeatTick} heartbeatBusy={heartbeatBusy} />
      ) : null}
      {sub === 'soul' ? <SoulTab /> : null}
      {sub === 'cognitive' ? <CognitiveStateTab /> : null}
    </div>
  )
}
