import { ChevronRight } from 'lucide-react'
import { s, T, mono } from '../../shared/theme/tokens'
import { Card, SectionTitle, MetricCard, ListRow, EmptyState, KeyValGrid, KeyValCell, CodeCard, ScrollPanel } from './shared'
import { formatFreshness, sectionTitleWithMeta } from './meta'

function summarizeFailures(data) {
  const failed = data?.failures?.failedRuns || []
  return { count: failed.length, latest: failed[0] || null }
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
    <div style={s({ display: 'flex', flexDirection: 'column', gap: 16 })}>

      {/* Summary metrics */}
      <div style={s({ display: 'flex', gap: 10 })}>
        <MetricCard label="Total cost" value={`$${Number(costSummary.total_cost_usd || 0).toFixed(2)}`} />
        <MetricCard label="Failures" value={failure.count} color={failure.count > 0 ? T.amber : undefined} alert={failure.count > 0} />
        <MetricCard label="Visible Provider" value={data?.providerHealth?.visible?.provider_status || 'unknown'} />
        <MetricCard label="Recent events" value={(data?.events || []).length} />
      </div>

      {/* Two-column detail sections */}
      <div style={s({ display: 'grid', gridTemplateColumns: 'repeat(2, minmax(0, 1fr))', gap: 12 })}>

        {/* Failure & Error Summary */}
        <Card>
          <SectionTitle>Failure & Error Summary</SectionTitle>
          <div style={s({ fontSize: 10, color: T.text3, marginTop: -8, marginBottom: 8 })}>Recent failed or cancelled runs.</div>
          <div style={s({ display: 'flex', flexDirection: 'column', gap: 6 })}>
            {(data?.failures?.failedRuns || []).length === 0 ? (
              <EmptyState title="No recent failures">Failed or cancelled runs will collect here.</EmptyState>
            ) : null}
            {(data?.failures?.failedRuns || []).slice(0, 8).map((run) => (
              <ListRow key={run.runId} onClick={() => onOpenRun(run)}>
                <div style={s({ minWidth: 0 })}>
                  <div style={s({ fontSize: 12, fontWeight: 500, marginBottom: 2 })}>{run.provider} / {run.model}</div>
                  <div style={s({ fontSize: 10, color: T.text2, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' })}>{run.status} · {run.error || run.textPreview || 'No error detail'}</div>
                </div>
                <div style={s({ display: 'flex', alignItems: 'center', gap: 6, flexShrink: 0 })}>
                  <small style={s({ ...mono, fontSize: 9, color: T.text3 })}>{run.finishedAt || run.startedAt || 'unknown'}</small>
                  <ChevronRight size={12} color={T.text3} />
                </div>
              </ListRow>
            ))}
          </div>
        </Card>

        {/* Provider-Lane Health */}
        <Card>
          <SectionTitle>Provider-Lane Health</SectionTitle>
          <div style={s({ fontSize: 10, color: T.text3, marginTop: -8, marginBottom: 8 })}>Provider and lane status evidence.</div>
          <KeyValGrid>
            {healthItems.map(([label, item]) => (
              <KeyValCell
                key={label}
                label={label}
                value={item?.status || item?.provider_status || 'unknown'}
                color={item?.status === 'ok' || item?.provider_status === 'ok' ? T.green : undefined}
              />
            ))}
          </KeyValGrid>
        </Card>

        {/* Visible Execution Trace */}
        <Card style={{ gridColumn: '1 / -1' }}>
          <SectionTitle>Visible Execution Trace</SectionTitle>
          <div style={s({ fontSize: 10, color: T.text3, marginTop: -8, marginBottom: 8 })}>Latest capability-run trace.</div>
          {!tracePresent ? (
            <EmptyState title="No visible trace yet">A visible capability run will surface here.</EmptyState>
          ) : (
            <div style={s({ display: 'flex', flexDirection: 'column', gap: 10 })}>
              <div style={s({ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 8 })}>
                <KeyValCell label="Capability" value={visibleTrace?.selectedCapabilityId || 'none'} />
                <KeyValCell label="Invoke" value={visibleTrace?.invokeStatus || 'not-invoked'} />
                <KeyValCell label="First pass" value={visibleTrace?.providerFirstPassStatus || 'unknown'} />
                <KeyValCell label="Second pass" value={visibleTrace?.providerSecondPassStatus || 'not-started'} />
              </div>

              <KeyValGrid>
                <KeyValCell label="Command" value={visibleTrace?.parsedCommandText || 'none'} />
                <KeyValCell label="Target Path" value={visibleTrace?.parsedTargetPath || 'none'} />
                <KeyValCell label="Arg Binding" value={visibleTrace?.argumentBindingMode || 'id-only'} />
                <KeyValCell label="Final Status" value={visibleTrace?.finalStatus || 'unknown'} />
              </KeyValGrid>

              {visibleTrace?.blockedReason ? (
                <CodeCard tone="danger"><strong>Blocked reason</strong><br />{visibleTrace.blockedReason}</CodeCard>
              ) : null}

              {visibleTrace?.providerErrorSummary ? (
                <CodeCard tone="danger"><strong>Provider error</strong><br />{visibleTrace.providerErrorSummary}</CodeCard>
              ) : null}

              <ListRow onClick={() => onOpenEvent(buildTraceDetailEvent(visibleTrace))}>
                <div style={s({ minWidth: 0 })}>
                  <div style={s({ fontSize: 12, fontWeight: 500, marginBottom: 2 })}>Inspect full trace</div>
                  <div style={s({ fontSize: 10, color: T.text2 })}>{visibleTrace?.summary || 'Open payload detail'}</div>
                </div>
                <div style={s({ display: 'flex', alignItems: 'center', gap: 6, flexShrink: 0 })}>
                  <small style={s({ ...mono, fontSize: 9, color: T.text3 })}>{visibleTrace?.runId || 'trace'}</small>
                  <ChevronRight size={12} color={T.text3} />
                </div>
              </ListRow>
            </div>
          )}
        </Card>
      </div>

      {/* Event Timeline + Run Evidence */}
      <div style={s({ display: 'grid', gridTemplateColumns: 'repeat(2, minmax(0, 1fr))', gap: 12 })}>
        <Card>
          <SectionTitle>Event Timeline</SectionTitle>
          <div style={s({ fontSize: 10, color: T.text3, marginTop: -8, marginBottom: 8 })}>Canonical event feed for Mission Control.</div>
          <ScrollPanel maxHeight={460}>
            <div style={s({ display: 'flex', flexDirection: 'column', gap: 6 })}>
              {(data?.events || []).length === 0 ? (
                <EmptyState title="No recent events">Realtime events will appear here.</EmptyState>
              ) : null}
              {(data?.events || []).map((event) => (
                <ListRow key={`${event.id}-${event.kind}`} onClick={() => onOpenEvent(event)}>
                  <div style={s({ minWidth: 0 })}>
                    <div style={s({ fontSize: 12, fontWeight: 500, marginBottom: 2 })}>{event.kind}</div>
                    <div style={s({ fontSize: 10, color: T.text2, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' })}>{event.family} · {event.relativeTime}</div>
                  </div>
                  <div style={s({ display: 'flex', alignItems: 'center', gap: 6, flexShrink: 0 })}>
                    <small style={s({ ...mono, fontSize: 9, color: T.text3 })}>Inspect</small>
                    <ChevronRight size={12} color={T.text3} />
                  </div>
                </ListRow>
              ))}
            </div>
          </ScrollPanel>
        </Card>

        <Card>
          <SectionTitle>Run Evidence</SectionTitle>
          <div style={s({ fontSize: 10, color: T.text3, marginTop: -8, marginBottom: 8 })}>Recent run and work evidence.</div>
          <div style={s({ display: 'flex', flexDirection: 'column', gap: 6 })}>
            {(data?.runEvidence?.recentWorkUnits || []).length === 0 ? (
              <EmptyState title="No recent work evidence">Work units will appear here.</EmptyState>
            ) : null}
            {(data?.runEvidence?.recentWorkUnits || []).map((item) => (
              <ListRow key={item.work_id} staticRow>
                <div style={s({ minWidth: 0 })}>
                  <div style={s({ fontSize: 12, fontWeight: 500, marginBottom: 2 })}>{item.provider} / {item.model}</div>
                  <div style={s({ fontSize: 10, color: T.text2, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' })}>{item.status} · {item.user_message_preview || 'No preview'}</div>
                </div>
                <small style={s({ ...mono, fontSize: 9, color: T.text3 })}>{item.finished_at || item.started_at || 'unknown'}</small>
              </ListRow>
            ))}
          </div>
        </Card>
      </div>
    </div>
  )
}
