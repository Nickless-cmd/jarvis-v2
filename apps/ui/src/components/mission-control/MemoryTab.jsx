import { Search } from 'lucide-react'
import { s, T, mono } from '../../shared/theme/tokens'
import { Card, SectionTitle, EmptyState } from './shared'

export function MemoryTab() {
  return (
    <div style={s({ display: 'flex', flexDirection: 'column', gap: 16 })}>
      <div style={s({ display: 'flex', alignItems: 'center', gap: 8 })}>
        <div style={s({ display: 'flex', alignItems: 'center', gap: 6, flex: 1, padding: '6px 10px', background: T.bgOverlay, border: `1px solid ${T.border1}`, borderRadius: 6 })}>
          <Search size={11} color={T.text3} />
          <input
            placeholder="Search memory..."
            style={s({ flex: 1, background: 'transparent', border: 'none', color: T.text1, fontSize: 11, ...mono, outline: 'none' })}
          />
        </div>
      </div>
      <Card>
        <SectionTitle>Memory Items</SectionTitle>
        <EmptyState title="Backend endpoint not connected">Memory search will be available when /mc/memory is implemented.</EmptyState>
      </Card>
    </div>
  )
}
