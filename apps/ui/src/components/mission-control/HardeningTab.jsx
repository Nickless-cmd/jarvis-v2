import { SectionTitle } from '../shared/SectionTitle'

export function HardeningTab() {
  return (
    <div className="mc-tab-page">
      <div className="support-card">
        <SectionTitle>Security Hardening</SectionTitle>
        <div className="mc-empty-state">
          <strong>Backend endpoint not connected</strong>
          <p className="muted">Hardening presets and security doctor will be available when /mc/hardening is implemented.</p>
        </div>
      </div>
    </div>
  )
}
