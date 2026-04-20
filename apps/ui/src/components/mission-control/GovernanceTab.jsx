import { Shield, Lock, Repeat, Clock, FileCode, TrendingUp, Cpu, GitPullRequest } from 'lucide-react'
import { s, T, mono } from '../../shared/theme/tokens'
import {
  useCognitiveSurfaces,
  SurfaceGrid,
  Section,
  KV,
  Summary,
  JsonBadges,
} from './surfaces'

export function GovernanceTab() {
  const { surfaces, loading } = useCognitiveSurfaces()

  if (loading) {
    return <div style={s({ padding: 24, color: T.text3, ...mono, fontSize: 11 })}>Indlæser governance...</div>
  }
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
      {/* Skill Contract Registry */}
      <Section icon={Shield} title="Skill-kontrakter" active={scr.active}>
        <Summary text={scr.summary} />
        <KV label="Total skills" value={scr.total_skills} accent />
        <KV label="Approval-gated" value={scr.approval_gated} />
        {scr.by_tag && Object.keys(scr.by_tag).length ? (
          <>
            <div style={s({ marginTop: 6 })}>
              <span style={s({ ...mono, fontSize: 9, color: T.text3 })}>Tags</span>
            </div>
            <JsonBadges data={scr.by_tag} />
          </>
        ) : null}
        {Array.isArray(scr.skills) && scr.skills.length ? (
          <div style={s({ marginTop: 8, display: 'flex', flexDirection: 'column', gap: 3, maxHeight: 200, overflow: 'auto' })}>
            {scr.skills.slice(0, 10).map((sk, i) => (
              <div key={i} style={s({ ...mono, fontSize: 9, color: T.text2 })}>
                <strong>{sk.name}</strong> v{sk.version}
                {sk.requires_approval ? <span style={{ color: T.text3 }}> · approval</span> : null}
              </div>
            ))}
          </div>
        ) : null}
      </Section>

      {/* Memory Write Policy */}
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

      {/* Spaced Repetition */}
      <Section icon={Repeat} title="Spaced repetition" active={sr.active}>
        <Summary text={sr.summary} />
        <KV label="Forfaldne nu" value={sr.due_now} accent />
        <KV label="Kommende" value={sr.upcoming_total} />
        <KV label="Profiler" value={sr.profile_count} />
        <KV label="Gns. confidence" value={sr.avg_confidence} />
        {Array.isArray(sr.due_topics) && sr.due_topics.length ? (
          <div style={s({ marginTop: 6, display: 'flex', flexWrap: 'wrap', gap: 4 })}>
            {sr.due_topics.slice(0, 6).map((t, i) => (
              <span
                key={i}
                style={s({
                  ...mono,
                  fontSize: 9,
                  color: T.text2,
                  background: T.bgOverlay,
                  padding: '2px 6px',
                  borderRadius: 4,
                })}
              >
                {t}
              </span>
            ))}
          </div>
        ) : null}
      </Section>

      {/* Scheduled Job Windows */}
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

      {/* Automation DSL */}
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

      {/* Outcome Learning */}
      <Section icon={TrendingUp} title="Outcome learning (decay)" active={ol.active}>
        <Summary text={ol.summary} />
        <KV label="Total records" value={ol.total_records} accent />
        <KV label="Decayed signal" value={ol.total_decayed_strength} />
        <KV label="Half-life (dage)" value={ol.half_life_days} />
        {ol.outcome_distribution && Object.keys(ol.outcome_distribution).length ? (
          <>
            <div style={s({ marginTop: 6 })}>
              <span style={s({ ...mono, fontSize: 9, color: T.text3 })}>Outcome-fordeling</span>
            </div>
            <JsonBadges data={ol.outcome_distribution} />
          </>
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

      {/* Jobs Engine */}
      <Section icon={Cpu} title="Jobs engine" active={je.active}>
        <Summary text={je.summary} />
        <KV label="Total jobs" value={je.total_jobs} accent />
        {je.by_status && Object.keys(je.by_status).length ? (
          <>
            <div style={s({ marginTop: 6 })}>
              <span style={s({ ...mono, fontSize: 9, color: T.text3 })}>Status</span>
            </div>
            <JsonBadges data={je.by_status} />
          </>
        ) : null}
        {je.cost_totals ? (
          <>
            <KV label="Tokens" value={je.cost_totals.tokens} />
            <KV label="USD" value={je.cost_totals.usd} />
          </>
        ) : null}
        {Array.isArray(je.registered_handlers) && je.registered_handlers.length ? (
          <KV label="Handlers" value={je.registered_handlers.join(', ')} />
        ) : null}
      </Section>

      {/* Prompt Mutation Loop */}
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
                <span
                  key={i}
                  style={s({
                    ...mono,
                    fontSize: 9,
                    color: T.text2,
                    background: T.bgOverlay,
                    padding: '2px 6px',
                    borderRadius: 4,
                  })}
                >
                  {f}
                </span>
              ))}
            </div>
          </div>
        ) : null}
      </Section>
    </SurfaceGrid>
  )
}
