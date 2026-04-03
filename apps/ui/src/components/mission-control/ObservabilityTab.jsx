import { ChevronRight } from 'lucide-react'
import { formatFreshness, sectionTitleWithMeta } from './meta'

function summarizeFailures(data) {
  const failed = data?.failures?.failedRuns || []
  return {
    count: failed.length,
    latest: failed[0] || null,
  }
}

function buildTraceDetailEvent(trace) {
  return {
    id: trace?.runId || 'visible-trace',
    kind: 'runtime.visible_run_execution_trace',
    family: 'runtime',
    relativeTime: formatFreshness(trace?.updatedAt),
    payload: trace?.raw || trace || {},
  }
}

function hasVisibleTrace(trace) {
  return Boolean(
    trace?.selectedCapabilityId ||
    trace?.parsedCommandText ||
    trace?.parsedTargetPath ||
    trace?.providerErrorSummary ||
    trace?.invokeStatus !== 'not-invoked' ||
    trace?.providerFirstPassStatus !== 'unknown' ||
    trace?.providerSecondPassStatus !== 'not-started'
  )
}

export function ObservabilityTab({ data, onOpenEvent, onOpenRun }) {
  const failure = summarizeFailures(data)
  const costSummary = data?.costs?.summary || {}
  const visibleTrace = data?.visibleTrace || null
  const tracePresent = hasVisibleTrace(visibleTrace)
  const healthItems = [
    ['Visible', data?.providerHealth?.visible],
    ['Cheap', data?.providerHealth?.cheap],
    ['Coding', data?.providerHealth?.coding],
    ['Local', data?.providerHealth?.local],
  ]

  return (
    <div className="mc-tab-page">
      <section className="mc-summary-grid">
        <article className="mc-stat tone-blue" id="cost-usage" title={sectionTitleWithMeta({
          source: '/mc/costs',
          fetchedAt: data?.fetchedAt,
          mode: '60s summary refresh',
        })}>
          <span>Total cost</span>
          <strong>${Number(costSummary.total_cost_usd || 0).toFixed(2)}</strong>
        </article>
        <article className={`mc-stat ${failure.count > 0 ? 'tone-amber' : 'tone-green'}`} id="failure-summary" title={sectionTitleWithMeta({
          source: '/mc/runs + /mc/events',
          fetchedAt: data?.fetchedAt,
          mode: 'event-assisted summary',
        })}>
          <span>Failures</span>
          <strong>{failure.count}</strong>
        </article>
        <article className="mc-stat tone-accent" id="provider-health" title={sectionTitleWithMeta({
          source: '/mc/runtime',
          fetchedAt: data?.fetchedAt,
          mode: '60s summary refresh',
        })}>
          <span>Visible Provider</span>
          <strong>{data?.providerHealth?.visible?.provider_status || 'unknown'}</strong>
        </article>
        <article className="mc-stat tone-blue" title={sectionTitleWithMeta({
          source: '/mc/events + /ws',
          fetchedAt: data?.fetchedAt,
          mode: 'websocket timeline',
        })}>
          <span>Recent events</span>
          <strong>{(data?.events || []).length}</strong>
        </article>
      </section>

      <section className="mc-section-grid">
        <article className="support-card" id="failure-summary-panel" title={sectionTitleWithMeta({
          source: '/mc/runs',
          fetchedAt: data?.fetchedAt,
          mode: 'evidence list',
        })}>
          <div className="panel-header">
            <div>
              <h3>Failure & Error Summary</h3>
              <p className="muted">Recent failed or cancelled runs.</p>
            </div>
            <span className="mc-section-hint">Run evidence</span>
          </div>
          <div className="mc-list">
            {(data?.failures?.failedRuns || []).length === 0 ? (
              <div className="mc-empty-state">
                <strong>No recent failures</strong>
                <p className="muted">Failed or cancelled runs will collect here for drilldown.</p>
              </div>
            ) : null}
            {(data?.failures?.failedRuns || []).slice(0, 8).map((run) => (
              <button className="mc-list-row" key={run.runId} onClick={() => onOpenRun(run)}>
                <div>
                  <strong>{run.provider} / {run.model}</strong>
                  <span>{run.status} · {run.error || run.textPreview || 'No error detail'}</span>
                </div>
                <div className="mc-row-meta">
                  <small>{run.finishedAt || run.startedAt || 'unknown'}</small>
                  <ChevronRight size={14} />
                </div>
              </button>
            ))}
          </div>
        </article>

        <article className="support-card" id="provider-health-panel" title={sectionTitleWithMeta({
          source: '/mc/runtime',
          fetchedAt: data?.fetchedAt,
          mode: 'read-only health detail',
        })}>
          <div className="panel-header">
            <div>
              <h3>Provider-Lane Health</h3>
              <p className="muted">Canonical home for provider and lane status evidence.</p>
            </div>
            <span className="mc-section-hint">Canonical detail</span>
          </div>
          <div className="compact-grid">
            {healthItems.map(([label, item]) => (
              <div className="compact-metric" key={label} title={`Readiness: ${item?.status || item?.provider_status || 'unknown'} · Auth: ${item?.auth_status || 'n/a'}`}>
                <span>{label}</span>
                <strong>{item?.status || item?.provider_status || 'unknown'}</strong>
                <p className="muted">{item?.auth_status || item?.provider_status || 'unknown'}</p>
              </div>
            ))}
          </div>
        </article>

        <article className="support-card" id="visible-execution-trace" title={sectionTitleWithMeta({
          source: '/mc/operations.visible_run.last_execution_trace',
          fetchedAt: data?.fetchedAt,
          mode: 'latest visible capability trace',
        })}>
          <div className="panel-header">
            <div>
              <h3>Visible Execution Trace</h3>
              <p className="muted">Latest capability-run trace without chain-of-thought.</p>
            </div>
            <span className="mc-section-hint">Trace detail</span>
          </div>
          {!tracePresent ? (
            <div className="mc-empty-state">
              <strong>No visible trace yet</strong>
              <p className="muted">A visible capability run will surface selected capability, args, invoke status and provider pass state here.</p>
            </div>
          ) : (
            <>
              <div className="compact-grid compact-grid-4">
                <div className="compact-metric">
                  <span>Capability</span>
                  <strong>{visibleTrace?.selectedCapabilityId || 'none'}</strong>
                  <p className="muted">{visibleTrace?.argumentSource || 'no arg source'}</p>
                </div>
                <div className="compact-metric">
                  <span>Invoke</span>
                  <strong>{visibleTrace?.invokeStatus || 'not-invoked'}</strong>
                  <p className="muted">{visibleTrace?.finalStatus || 'unknown'}</p>
                </div>
                <div className="compact-metric">
                  <span>First pass</span>
                  <strong>{visibleTrace?.providerFirstPassStatus || 'unknown'}</strong>
                  <p className="muted">{visibleTrace?.providerCallCount || 0} provider calls</p>
                </div>
                <div className="compact-metric">
                  <span>Second pass</span>
                  <strong>{visibleTrace?.providerSecondPassStatus || 'not-started'}</strong>
                  <p className="muted">{visibleTrace?.updatedAt ? formatFreshness(visibleTrace.updatedAt) : 'unknown'}</p>
                </div>
              </div>

              <div className="mc-keyval-grid">
                <div>
                  <span>Command</span>
                  <strong>{visibleTrace?.parsedCommandText || 'none'}</strong>
                </div>
                <div>
                  <span>Target Path</span>
                  <strong>{visibleTrace?.parsedTargetPath || 'none'}</strong>
                </div>
                <div>
                  <span>Arg Binding</span>
                  <strong>{visibleTrace?.argumentBindingMode || 'id-only'}</strong>
                </div>
                <div>
                  <span>Final Status</span>
                  <strong>{visibleTrace?.finalStatus || 'unknown'}</strong>
                </div>
              </div>

              {visibleTrace?.blockedReason ? (
                <article className="mc-code-card tone-danger">
                  <strong>Blocked reason</strong>
                  <p>{visibleTrace.blockedReason}</p>
                </article>
              ) : null}

              {visibleTrace?.providerErrorSummary ? (
                <article className="mc-code-card tone-danger">
                  <strong>Provider error</strong>
                  <p>{visibleTrace.providerErrorSummary}</p>
                </article>
              ) : null}

              <button className="mc-list-row" onClick={() => onOpenEvent(buildTraceDetailEvent(visibleTrace))}>
                <div>
                  <strong>Inspect full trace</strong>
                  <span>{visibleTrace?.summary || 'Open payload detail'}</span>
                </div>
                <div className="mc-row-meta">
                  <small>{visibleTrace?.runId || 'trace'}</small>
                  <ChevronRight size={14} />
                </div>
              </button>
            </>
          )}
        </article>
      </section>

      <section className="mc-section-grid">
        <article className="support-card" id="event-timeline" title={sectionTitleWithMeta({
          source: '/mc/events + /ws',
          fetchedAt: data?.fetchedAt,
          mode: 'websocket + route-entry baseline',
        })}>
          <div className="panel-header">
            <div>
              <h3>Event Timeline</h3>
              <p className="muted">Canonical event feed for Mission Control.</p>
            </div>
            <span className="mc-section-hint">Canonical detail</span>
          </div>
          <div className="mc-list dense">
            {(data?.events || []).length === 0 ? (
              <div className="mc-empty-state">
                <strong>No recent events</strong>
                <p className="muted">Realtime and recent baseline events will appear here.</p>
              </div>
            ) : null}
            {(data?.events || []).map((event) => (
              <button className="mc-list-row" key={`${event.id}-${event.kind}`} onClick={() => onOpenEvent(event)}>
                <div>
                  <strong>{event.kind}</strong>
                  <span>{event.family} · {event.relativeTime}</span>
                </div>
                <div className="mc-row-meta">
                  <small>Inspect</small>
                  <ChevronRight size={14} />
                </div>
              </button>
            ))}
          </div>
        </article>

        <article className="support-card" id="run-evidence" title={sectionTitleWithMeta({
          source: '/mc/runs',
          fetchedAt: data?.fetchedAt,
          mode: 'manual drilldown support',
        })}>
          <div className="panel-header">
            <div>
              <h3>Run Evidence</h3>
              <p className="muted">Recent run and work evidence surfaces.</p>
            </div>
            <span className="mc-section-hint">Evidence only</span>
          </div>
          <div className="mc-list">
            {(data?.runEvidence?.recentWorkUnits || []).length === 0 ? (
              <div className="mc-empty-state">
                <strong>No recent work evidence</strong>
                <p className="muted">Work units and notes will appear here as visible runs persist evidence.</p>
              </div>
            ) : null}
            {(data?.runEvidence?.recentWorkUnits || []).map((item) => (
              <div className="mc-list-row static" key={item.work_id}>
                <div>
                  <strong>{item.provider} / {item.model}</strong>
                  <span>{item.status} · {item.user_message_preview || 'No preview'}</span>
                </div>
                <small>{item.finished_at || item.started_at || 'unknown'}</small>
              </div>
            ))}
          </div>
        </article>
      </section>
    </div>
  )
}
