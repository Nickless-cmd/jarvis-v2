import { useState, useEffect } from 'react'
import { RefreshCcw, ShieldCheck, Shield, Lock, Repeat, Clock, FileCode, TrendingUp, Cpu, GitPullRequest } from 'lucide-react'
import { s, T, mono } from '../../shared/theme/tokens'
import { Card, SectionTitle, MetricCard, ScrollPanel, EmptyState, Skeleton, SubTabs } from './shared'
import { backend } from '../../lib/adapters'
import { formatFreshness } from './meta'
import {
  useCognitiveSurfaces,
  SurfaceGrid,
  Section,
  KV,
  Summary,
  JsonBadges,
} from './surfaces'

function IntegrationRow({ label, ok }) {
  const color = ok ? T.green : T.text3
  return (
    <div style={s({ display: 'flex', alignItems: 'center', gap: 8, padding: '5px 0' })}>
      <div style={s({ width: 7, height: 7, borderRadius: '50%', background: color, boxShadow: ok ? `0 0 6px ${color}` : 'none', flexShrink: 0 })} />
      <span style={s({ fontSize: 11, color: ok ? T.text2 : T.text3 })}>{label}</span>
      <span style={s({ ...mono, fontSize: 9, color: T.text3, marginLeft: 'auto' })}>{ok ? 'konfigureret' : 'ikke sat op'}</span>
    </div>
  )
}

function StateChip({ state }) {
  const colorMap = { pending: T.amber, approved: T.green, denied: T.red, expired: T.text3 }
  const color = colorMap[state] || T.text3
  return (
    <span style={s({ ...mono, fontSize: 9, padding: '2px 7px', borderRadius: 10, background: `${color}18`, border: `1px solid ${color}35`, color })}>
      {state}
    </span>
  )
}

function SecurityPanel() {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [fetchedAt, setFetchedAt] = useState('')

  useEffect(() => {
    let cancelled = false
    async function load() {
      setLoading(true)
      try {
        const result = await backend.getMissionControlHardening()
        if (!cancelled) { setData(result); setFetchedAt(new Date().toISOString()) }
      } finally { if (!cancelled) setLoading(false) }
    }
    load()
    return () => { cancelled = true }
  }, [])

  async function refresh() {
    setLoading(true)
    try {
      const result = await backend.getMissionControlHardening()
      setData(result); setFetchedAt(new Date().toISOString())
    } finally { setLoading(false) }
  }

  const pending = data?.pending ?? 0
  const integrations = data?.integrations || {}

  return (
    <div style={s({ display: 'flex', flexDirection: 'column', gap: 16 })}>
      <div style={s({ display: 'flex', alignItems: 'center', gap: 8 })}>
        <span style={s({ ...mono, fontSize: 9, color: T.text3 })}>{fetchedAt ? formatFreshness(fetchedAt) : ''}</span>
        <button onClick={refresh} disabled={loading}
          style={s({ marginLeft: 'auto', padding: '4px 8px', borderRadius: 7, border: `1px solid ${T.border1}`, background: T.bgOverlay, color: T.text2, cursor: loading ? 'not-allowed' : 'pointer', opacity: loading ? 0.5 : 1 })}>
          <RefreshCcw size={11} />
        </button>
      </div>

      <div style={s({ display: 'flex', gap: 10 })}>
        <MetricCard label="Afventer" value={loading ? '…' : pending} color={pending > 0 ? T.amber : undefined} alert={pending > 0} />
        <MetricCard label="Godkendt i dag" value={loading ? '…' : data?.approved_today ?? 0} color={T.green} />
        <MetricCard label="Afvist i dag" value={loading ? '…' : data?.denied_today ?? 0} color={data?.denied_today > 0 ? T.red : undefined} />
        <MetricCard label="Autonomi-niveau" value={loading ? '…' : (data?.autonomy_level || 'ukendt')} />
      </div>

      <div style={s({ display: 'grid', gridTemplateColumns: 'repeat(2, minmax(0, 1fr))', gap: 12 })}>
        <Card>
          <SectionTitle>Integrationer</SectionTitle>
          {loading ? (
            <div style={s({ display: 'flex', flexDirection: 'column', gap: 6 })}>
              {Array.from({ length: 4 }).map((_, i) => <Skeleton key={i} height={24} />)}
            </div>
          ) : (
            <>
              <IntegrationRow label="Telegram" ok={integrations.telegram} />
              <IntegrationRow label="Discord" ok={integrations.discord} />
              <IntegrationRow label="Home Assistant" ok={integrations.home_assistant} />
              <IntegrationRow label="Anthropic API" ok={integrations.anthropic} />
            </>
          )}
        </Card>

        <Card>
          <SectionTitle>Seneste tool-intent anmodninger</SectionTitle>
          {loading ? (
            <div style={s({ display: 'flex', flexDirection: 'column', gap: 6 })}>
              {Array.from({ length: 4 }).map((_, i) => <Skeleton key={i} height={28} />)}
            </div>
          ) : (data?.recent_approvals || []).length === 0 ? (
            <EmptyState title="Ingen anmodninger endnu">Tool-intent godkendelser vises her.</EmptyState>
          ) : (
            <ScrollPanel maxHeight={200}>
              <div style={s({ display: 'flex', flexDirection: 'column', gap: 4 })}>
                {(data.recent_approvals || []).map((row, i) => (
                  <div key={i} style={s({ display: 'flex', alignItems: 'center', gap: 8, padding: '5px 8px', borderRadius: 7, border: `1px solid ${T.border0}`, background: T.bgOverlay })}>
                    <span style={s({ ...mono, fontSize: 10, color: T.accentText, minWidth: 120, flexShrink: 0 })}>{row.intent_type}</span>
                    <span style={s({ fontSize: 10, color: T.text3, flex: 1, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' })}>{row.intent_target}</span>
                    <StateChip state={row.approval_state} />
                  </div>
                ))}
              </div>
            </ScrollPanel>
          )}
        </Card>
      </div>
    </div>
  )
}

function GovernancePanel() {
  const { surfaces, loading } = useCognitiveSurfaces()

  if (loading) return <div style={s({ padding: 24, color: T.text3, ...mono, fontSize: 11 })}>Indlæser governance...</div>
  if (!surfaces) return <div style={s({ padding: 24, color: T.text3 })}>Ingen data</div>

  const scr = surfaces.skill_contract_registry || {}
  const mwp = surfaces.memory_write_policy || {}
  const sr = surfaces.spaced_repetition || {}
  const sjw = surfaces.scheduled_job_windows || {}
  const ad = surfaces.automation_dsl || {}
  const ol = surfaces.outcome_learning || {}
  const je = surfaces.jobs_engine || {}
  const pml = surfaces.prompt_mutation_loop || {}

  return (
    <SurfaceGrid>
      <Section icon={Shield} title="Skill-kontrakter" active={scr.active}>
        <Summary text={scr.summary} />
        <KV label="Total skills" value={scr.total_skills} accent />
        <KV label="Approval-gated" value={scr.approval_gated} />
        {scr.by_tag && Object.keys(scr.by_tag).length ? (
          <><div style={s({ marginTop: 6 })}><span style={s({ ...mono, fontSize: 9, color: T.text3 })}>Tags</span></div><JsonBadges data={scr.by_tag} /></>
        ) : null}
        {Array.isArray(scr.skills) && scr.skills.length ? (
          <div style={s({ marginTop: 8, display: 'flex', flexDirection: 'column', gap: 3, maxHeight: 200, overflow: 'auto' })}>
            {scr.skills.slice(0, 10).map((sk, i) => (
              <div key={i} style={s({ ...mono, fontSize: 9, color: T.text2 })}>
                <strong>{sk.name}</strong> v{sk.version}{sk.requires_approval ? <span style={{ color: T.text3 }}> · approval</span> : null}
              </div>
            ))}
          </div>
        ) : null}
      </Section>

      <Section icon={Lock} title="Memory-skrivepolicy" active={mwp.active}>
        <Summary text={mwp.summary} />
        <KV label="Rate (per min)" value={mwp.rate_limit_per_minute} />
        <KV label="Cooldown (s)" value={mwp.cooldown_seconds} />
        <KV label="Conf. tærskel" value={mwp.confidence_threshold} />
        <KV label="Review-kø aktiv" value={mwp.review_queue_enabled} />
        <KV label="Afventer review" value={mwp.pending_reviews} accent />
        <KV label="Godkendt total" value={mwp.approved_total} />
        <KV label="Afvist total" value={mwp.rejected_total} />
        <KV label="Writes sidste min" value={mwp.writes_in_last_minute} />
      </Section>

      <Section icon={Repeat} title="Spaced repetition" active={sr.active}>
        <Summary text={sr.summary} />
        <KV label="Forfaldne nu" value={sr.due_now} accent />
        <KV label="Kommende" value={sr.upcoming_total} />
        <KV label="Profiler" value={sr.profile_count} />
        <KV label="Gns. confidence" value={sr.avg_confidence} />
        {Array.isArray(sr.due_topics) && sr.due_topics.length ? (
          <div style={s({ marginTop: 6, display: 'flex', flexWrap: 'wrap', gap: 4 })}>
            {sr.due_topics.slice(0, 6).map((t, i) => (
              <span key={i} style={s({ ...mono, fontSize: 9, color: T.text2, background: T.bgOverlay, padding: '2px 6px', borderRadius: 4 })}>{t}</span>
            ))}
          </div>
        ) : null}
      </Section>

      <Section icon={Clock} title="Tids-vinduer" active={sjw.active}>
        <Summary text={sjw.summary} />
        <KV label="Total vinduer" value={sjw.total_windows} accent />
        <KV label="Fires i dag" value={sjw.fires_today} />
        {Array.isArray(sjw.inside_window_now) && sjw.inside_window_now.length ? (
          <KV label="Inde i nu" value={sjw.inside_window_now.join(', ')} />
        ) : null}
        {Array.isArray(sjw.active_windows) && sjw.active_windows.length ? (
          <div style={s({ marginTop: 8, display: 'flex', flexDirection: 'column', gap: 3 })}>
            {sjw.active_windows.slice(0, 5).map((w, i) => (
              <div key={i} style={s({ ...mono, fontSize: 9, color: T.text2 })}>
                <strong>{w.name}</strong> · {String(w.start_hour).padStart(2, '0')}→{String(w.end_hour).padStart(2, '0')}
                {w.prefer_free_first ? <span style={{ color: T.text3 }}> · free-first</span> : null}
              </div>
            ))}
          </div>
        ) : null}
      </Section>

      <Section icon={FileCode} title="Automation DSL" active={ad.active}>
        <Summary text={ad.summary} />
        <KV label="Aktive" value={ad.active_count} accent />
        <KV label="Inaktive" value={ad.inactive_count} />
        <KV label="Udløbet" value={ad.expired_count} />
        <KV label="Total" value={ad.total} />
        {Array.isArray(ad.recent_active) && ad.recent_active.length ? (
          <div style={s({ marginTop: 8, display: 'flex', flexDirection: 'column', gap: 3 })}>
            {ad.recent_active.slice(0, 3).map((a, i) => (
              <div key={i} style={s({ ...mono, fontSize: 9, color: T.text2 })}>
                <strong>{a.name}</strong> · {a.trigger_type}/{a.action_type} · {a.channel}
              </div>
            ))}
          </div>
        ) : null}
      </Section>

      <Section icon={TrendingUp} title="Outcome learning" active={ol.active}>
        <Summary text={ol.summary} />
        <KV label="Total records" value={ol.total_records} accent />
        <KV label="Decayed signal" value={ol.total_decayed_strength} />
        <KV label="Half-life (dage)" value={ol.half_life_days} />
        {ol.outcome_distribution && Object.keys(ol.outcome_distribution).length ? (
          <><div style={s({ marginTop: 6 })}><span style={s({ ...mono, fontSize: 9, color: T.text3 })}>Outcome-fordeling</span></div><JsonBadges data={ol.outcome_distribution} /></>
        ) : null}
        {Array.isArray(ol.top_patterns) && ol.top_patterns.length ? (
          <div style={s({ marginTop: 8, display: 'flex', flexDirection: 'column', gap: 3 })}>
            {ol.top_patterns.slice(0, 4).map((p, i) => (
              <div key={i} style={s({ ...mono, fontSize: 9, color: T.text2 })}>
                <strong>{p.strength}</strong> · {p.context}
              </div>
            ))}
          </div>
        ) : null}
      </Section>

      <Section icon={Cpu} title="Jobs engine" active={je.active}>
        <Summary text={je.summary} />
        <KV label="Total jobs" value={je.total_jobs} accent />
        {je.by_status && Object.keys(je.by_status).length ? (
          <><div style={s({ marginTop: 6 })}><span style={s({ ...mono, fontSize: 9, color: T.text3 })}>Status</span></div><JsonBadges data={je.by_status} /></>
        ) : null}
        {je.cost_totals ? (
          <><KV label="Tokens" value={je.cost_totals.tokens} /><KV label="USD" value={je.cost_totals.usd} /></>
        ) : null}
        {Array.isArray(je.registered_handlers) && je.registered_handlers.length ? (
          <KV label="Handlers" value={je.registered_handlers.join(', ')} />
        ) : null}
      </Section>

      <Section icon={GitPullRequest} title="Prompt-mutation loop" active={pml.active}>
        <Summary text={pml.summary} />
        <KV label="Under observation" value={pml.monitoring} accent />
        <KV label="Adopteret" value={pml.adopted} />
        <KV label="Rullet tilbage" value={pml.rolled_back} />
        <KV label="Auto-rullet" value={pml.auto_rolled_back} />
        <KV label="Gns. score" value={pml.avg_monitoring_score} />
        <KV label="Rollback-tærskel" value={pml.rollback_score_threshold} />
        <KV label="Per-fil cooldown (t)" value={pml.per_file_cooldown_hours} />
        {Array.isArray(pml.evolvable_files) && pml.evolvable_files.length ? (
          <div style={s({ marginTop: 6 })}>
            <span style={s({ ...mono, fontSize: 9, color: T.text3 })}>Evolverbare filer</span>
            <div style={s({ display: 'flex', flexWrap: 'wrap', gap: 4, marginTop: 4 })}>
              {pml.evolvable_files.map((f, i) => (
                <span key={i} style={s({ ...mono, fontSize: 9, color: T.text2, background: T.bgOverlay, padding: '2px 6px', borderRadius: 4 })}>{f}</span>
              ))}
            </div>
          </div>
        ) : null}
      </Section>
    </SurfaceGrid>
  )
}

const HARDENING_SUBTABS = [
  { id: 'security', label: 'Sikkerhed' },
  { id: 'governance', label: 'Governance' },
]

export function HardeningTab() {
  const [sub, setSub] = useState('security')

  return (
    <div style={s({ display: 'flex', flexDirection: 'column', gap: 0 })}>
      <div style={s({ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 16 })}>
        <ShieldCheck size={15} color={T.accent} />
        <span style={s({ fontSize: 14, fontWeight: 500, color: T.text1 })}>Hardening</span>
        <div style={s({ marginLeft: 'auto' })}>
          <SubTabs tabs={HARDENING_SUBTABS} active={sub} onChange={setSub} />
        </div>
      </div>
      {sub === 'security' ? <SecurityPanel /> : <GovernancePanel />}
    </div>
  )
}
