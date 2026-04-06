import { s } from '../../shared/theme/tokens'
import { Card, SectionTitle, EmptyState } from './shared'

export function HardeningTab() {
  return (
    <div style={s({ display: 'flex', flexDirection: 'column', gap: 16 })}>
      <Card>
        <SectionTitle>Security Hardening</SectionTitle>
        <EmptyState title="Backend endpoint not connected">Hardening presets and security doctor will be available when /mc/hardening is implemented.</EmptyState>
      </Card>
    </div>
  )
}
