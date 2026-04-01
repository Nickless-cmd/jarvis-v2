import { SectionTitle } from '../shared/SectionTitle'

export function SkillsTab() {
  return (
    <div className="mc-tab-page">
      <div className="support-card">
        <SectionTitle>Skill Marketplace</SectionTitle>
        <div className="mc-empty-state">
          <strong>Backend endpoint not connected</strong>
          <p className="muted">Skill management will be available when /mc/skills is implemented.</p>
        </div>
      </div>
    </div>
  )
}
