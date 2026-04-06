import { s } from '../../shared/theme/tokens'
import { Card, SectionTitle, EmptyState } from './shared'

export function SkillsTab() {
  return (
    <div style={s({ display: 'flex', flexDirection: 'column', gap: 16 })}>
      <Card>
        <SectionTitle>Skill Marketplace</SectionTitle>
        <EmptyState title="Backend endpoint not connected">Skill management will be available when /mc/skills is implemented.</EmptyState>
      </Card>
    </div>
  )
}
