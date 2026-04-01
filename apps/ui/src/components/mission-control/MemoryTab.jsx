import { Search } from 'lucide-react'
import { SectionTitle } from '../shared/SectionTitle'

export function MemoryTab() {
  return (
    <div className="mc-tab-page">
      <div className="mc-filter-bar">
        <div className="mc-search-input">
          <Search size={11} />
          <input placeholder="Search memory..." />
        </div>
      </div>
      <div className="support-card">
        <SectionTitle>Memory Items</SectionTitle>
        <div className="mc-empty-state">
          <strong>Backend endpoint not connected</strong>
          <p className="muted">Memory search will be available when /mc/memory is implemented.</p>
        </div>
      </div>
    </div>
  )
}
