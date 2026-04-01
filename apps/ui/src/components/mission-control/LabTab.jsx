import { SectionTitle } from '../shared/SectionTitle'

export function LabTab() {
  return (
    <div className="mc-tab-page">
      <div className="support-card">
        <SectionTitle>Debug &amp; Lab</SectionTitle>
        <div className="mc-empty-state">
          <strong>Backend endpoint not connected</strong>
          <p className="muted">Debug inspect, kernel queue, and model benchmarks will be available when /mc/lab is implemented.</p>
        </div>
      </div>
    </div>
  )
}
