import { ChevronRight } from 'lucide-react'
import { sectionTitleWithMeta } from './meta'

function detailRow(item, label, onOpen) {
  if (!item || !Object.keys(item).length) {
    return (
      <div className="mc-empty-state">
        <strong>No current signal</strong>
        <p className="muted">This Jarvis surface has not produced a current record yet.</p>
      </div>
    )
  }

  return (
    <button
      className="mc-list-row"
      onClick={() => onOpen(label, item)}
      title={sectionTitleWithMeta({
        source: item.source,
        fetchedAt: item.createdAt,
        mode: 'detail drawer',
      })}
    >
      <div>
        <strong>{label}</strong>
        <span>{item.summary || 'Inspect detail'}</span>
      </div>
      <div className="mc-row-meta">
        <small>{item.createdAt || 'current'}</small>
        <ChevronRight size={14} />
      </div>
    </button>
  )
}

export function JarvisTab({ data, onOpenItem }) {
  const summary = data?.summary || {}

  return (
    <div className="mc-tab-page">
      <section className="mc-summary-grid">
        <article className="mc-stat tone-accent" title={sectionTitleWithMeta({
          source: '/mc/jarvis',
          fetchedAt: data?.fetchedAt,
          mode: 'snapshot summary',
        })}>
          <span>State Signal</span>
          <strong>{summary?.state_signal?.mood_tone || 'unknown'}</strong>
          <small className="muted">{summary?.state_signal?.current_concern || 'No current concern'}</small>
        </article>
        <article className="mc-stat tone-blue" title={sectionTitleWithMeta({
          source: '/mc/jarvis',
          fetchedAt: data?.fetchedAt,
          mode: 'snapshot summary',
        })}>
          <span>Retained Memory</span>
          <strong>{summary?.retained_memory?.kind || 'unknown'}</strong>
          <small className="muted">{summary?.retained_memory?.focus || 'No retained focus'}</small>
        </article>
        <article className="mc-stat tone-amber" title={sectionTitleWithMeta({
          source: '/mc/jarvis',
          fetchedAt: data?.fetchedAt,
          mode: 'snapshot summary',
        })}>
          <span>Development</span>
          <strong>{summary?.development?.direction || 'unknown'}</strong>
          <small className="muted">{summary?.development?.identity_focus || 'No identity focus'}</small>
        </article>
        <article className="mc-stat tone-green" title={sectionTitleWithMeta({
          source: '/mc/jarvis',
          fetchedAt: data?.fetchedAt,
          mode: 'snapshot summary',
        })}>
          <span>Continuity</span>
          <strong>{summary?.continuity?.continuity_mode || 'unknown'}</strong>
          <small className="muted">{summary?.continuity?.relation_pull || 'No continuity pull'}</small>
        </article>
      </section>

      <section className="mc-section-grid">
        <article className="support-card" id="jarvis-state" title={sectionTitleWithMeta({
          source: '/mc/jarvis::state',
          fetchedAt: data?.fetchedAt,
          mode: 'snapshot + drilldown',
        })}>
          <div className="panel-header">
            <div>
              <h3>State</h3>
              <p className="muted">Visible and internal state signals for Jarvis right now.</p>
            </div>
            <span className="mc-section-hint">Read-only</span>
          </div>
          <div className="compact-grid">
            <div className="compact-metric">
              <span>Mood tone</span>
              <strong>{summary?.state_signal?.mood_tone || 'unknown'}</strong>
            </div>
            <div className="compact-metric">
              <span>Confidence</span>
              <strong>{summary?.state_signal?.confidence || 'unknown'}</strong>
            </div>
          </div>
          <div className="mc-list">
            {detailRow(data?.state?.visibleIdentity, 'Visible Identity', onOpenItem)}
            {detailRow(data?.state?.protectedInnerVoice, 'Protected Inner Voice', onOpenItem)}
            {detailRow(data?.state?.privateState, 'Private State', onOpenItem)}
            {detailRow(data?.state?.initiativeTension, 'Initiative Tension', onOpenItem)}
          </div>
        </article>

        <article className="support-card" id="jarvis-memory" title={sectionTitleWithMeta({
          source: '/mc/jarvis::memory',
          fetchedAt: data?.fetchedAt,
          mode: 'snapshot + drilldown',
        })}>
          <div className="panel-header">
            <div>
              <h3>Memory</h3>
              <p className="muted">Retained signals and current retained projection.</p>
            </div>
            <span className="mc-section-hint">Projection-first</span>
          </div>
          <div className="compact-grid">
            <div className="compact-metric">
              <span>Retention scope</span>
              <strong>{summary?.retained_memory?.scope || 'unknown'}</strong>
            </div>
            <div className="compact-metric">
              <span>Confidence</span>
              <strong>{summary?.retained_memory?.confidence || 'unknown'}</strong>
            </div>
          </div>
          <div className="mc-list">
            {detailRow(data?.memory?.retainedProjection, 'Retained Projection', onOpenItem)}
            {detailRow(data?.memory?.retainedRecord, 'Current Retained Record', onOpenItem)}
            {(data?.memory?.recentRecords || []).slice(0, 3).map((record) => (
              <button className="mc-list-row" key={record.record_id || record.recordId || record.createdAt} onClick={() => onOpenItem('Recent Retained Record', record)}>
                <div>
                  <strong>{record.retained_kind || 'retained-record'}</strong>
                  <span>{record.summary || 'Inspect retained record'}</span>
                </div>
                <div className="mc-row-meta">
                  <small>{record.createdAt || 'recent'}</small>
                  <ChevronRight size={14} />
                </div>
              </button>
            ))}
          </div>
        </article>
      </section>

      <section className="mc-section-grid">
        <article className="support-card" id="jarvis-development" title={sectionTitleWithMeta({
          source: '/mc/jarvis::development',
          fetchedAt: data?.fetchedAt,
          mode: 'snapshot + drilldown',
        })}>
          <div className="panel-header">
            <div>
              <h3>Development</h3>
              <p className="muted">Self-model, development direction, and operational preference signals.</p>
            </div>
            <span className="mc-section-hint">Read-only</span>
          </div>
          <div className="compact-grid">
            <div className="compact-metric">
              <span>Work mode</span>
              <strong>{summary?.development?.work_mode || 'unknown'}</strong>
            </div>
            <div className="compact-metric">
              <span>Recurring tension</span>
              <strong>{summary?.development?.tension || 'unknown'}</strong>
            </div>
          </div>
          <div className="mc-list">
            {detailRow(data?.development?.selfModel, 'Self Model', onOpenItem)}
            {detailRow(data?.development?.developmentState, 'Development State', onOpenItem)}
            {detailRow(data?.development?.growthNote, 'Latest Growth Note', onOpenItem)}
            {detailRow(data?.development?.reflectiveSelection, 'Latest Reflective Selection', onOpenItem)}
            {detailRow(data?.development?.operationalPreference, 'Operational Preference', onOpenItem)}
            {detailRow(data?.development?.operationalAlignment, 'Preference Alignment', onOpenItem)}
          </div>
        </article>

        <article className="support-card" id="jarvis-continuity" title={sectionTitleWithMeta({
          source: '/mc/jarvis::continuity',
          fetchedAt: data?.fetchedAt,
          mode: 'snapshot + drilldown',
        })}>
          <div className="panel-header">
            <div>
              <h3>Continuity</h3>
              <p className="muted">Session continuity, relation pull, and promotion-style signals.</p>
            </div>
            <span className="mc-section-hint">Read-only</span>
          </div>
          <div className="compact-grid">
            <div className="compact-metric">
              <span>Session status</span>
              <strong>{summary?.continuity?.session_status || 'unknown'}</strong>
            </div>
            <div className="compact-metric">
              <span>Interaction mode</span>
              <strong>{summary?.continuity?.interaction_mode || 'unknown'}</strong>
            </div>
          </div>
          <div className="mc-list">
            {detailRow(data?.continuity?.visibleSession, 'Visible Session Continuity', onOpenItem)}
            {detailRow(data?.continuity?.visibleContinuity, 'Visible Continuity', onOpenItem)}
            {detailRow(data?.continuity?.relationState, 'Relation State', onOpenItem)}
            {detailRow(data?.continuity?.promotionSignal, 'Promotion Signal', onOpenItem)}
            {detailRow(data?.continuity?.promotionDecision, 'Promotion Decision', onOpenItem)}
          </div>
        </article>
      </section>
    </div>
  )
}
