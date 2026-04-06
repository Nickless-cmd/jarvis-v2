import { s } from '../../shared/theme/tokens'
import { Card, SectionTitle, EmptyState } from './shared'

export function LabTab() {
  return (
    <div style={s({ display: 'flex', flexDirection: 'column', gap: 16 })}>
      <Card>
        <SectionTitle>Debug & Lab</SectionTitle>
        <EmptyState title="Backend endpoint not connected">Debug inspect, kernel queue, and model benchmarks will be available when /mc/lab is implemented.</EmptyState>
      </Card>
    </div>
  )
}
