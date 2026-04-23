import { useState } from 'react'
import { Eye } from 'lucide-react'
import { s, T } from '../../shared/theme/tokens'
import { SubTabs } from './shared'
import { SelfReviewTab } from './SelfReviewTab'
import { DevelopmentTab } from './DevelopmentTab'
import { ContinuityTab } from './ContinuityTab'

const REFLECTION_SUBTABS = [
  { id: 'self-review', label: 'Selvreview' },
  { id: 'development', label: 'Udvikling' },
  { id: 'continuity', label: 'Kontinuitet' },
]

export function ReflectionTab({ data, onOpenItem, onDevelopmentFocusAction }) {
  const [sub, setSub] = useState('self-review')

  return (
    <div style={s({ display: 'flex', flexDirection: 'column', gap: 0 })}>
      <div style={s({ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 16 })}>
        <Eye size={15} color={T.accent} />
        <span style={s({ fontSize: 14, fontWeight: 500, color: T.text1 })}>Reflection</span>
        <div style={s({ marginLeft: 'auto' })}>
          <SubTabs tabs={REFLECTION_SUBTABS} active={sub} onChange={setSub} />
        </div>
      </div>
      {sub === 'self-review' ? <SelfReviewTab data={data} onOpenItem={onOpenItem} /> : null}
      {sub === 'development' ? <DevelopmentTab data={data} onOpenItem={onOpenItem} onDevelopmentFocusAction={onDevelopmentFocusAction} /> : null}
      {sub === 'continuity' ? <ContinuityTab data={data} onOpenItem={onOpenItem} /> : null}
    </div>
  )
}
