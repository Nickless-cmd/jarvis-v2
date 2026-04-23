import { Wind, GitBranch, Network, Globe, Users, Bell, Send, Hammer, Sparkles, Zap, FolderKanban, EyeOff, Moon } from 'lucide-react'
import { s, T, mono } from '../../shared/theme/tokens'
import {
  useCognitiveSurfaces,
  SurfaceGrid,
  Section,
  KV,
  Summary,
  JsonBadges,
} from './surfaces'

export function ThreadsTab() {
  const { surfaces, loading } = useCognitiveSurfaces()

  if (loading) {
    return <div style={s({ padding: 24, color: T.text3, ...mono, fontSize: 11 })}>Indlæser tråde...</div>
  }
  if (!surfaces) return <div style={s({ padding: 24, color: T.text3 })}>Ingen data</div>

  const mb = surfaces.memory_breathing || {}
  const tt = surfaces.thought_thread || {}
  const cst = surfaces.cross_session_threads || {}
  const cop = surfaces.collective_pulse || {}
  const rd = surfaces.relation_dynamics || {}
  const aa = surfaces.anticipatory_action || {}
  const ao = surfaces.autonomous_outreach || {}
  const aw = surfaces.autonomous_work || {}
  const ci = surfaces.creative_instinct || {}
  const cim = surfaces.creative_impulse || {}
  const cp = surfaces.creative_projects || {}
  const ad = surfaces.avoidance_detector || {}
  const dc = surfaces.dream_consolidation || {}

  return (
    <SurfaceGrid>
      {/* Memory Breathing */}
      <Section icon={Wind} title="Hukommelse der ånder" active={mb.active}>
        <Summary text={mb.summary} />
        <KV label="Nylige accesses" value={mb.recent_accesses} accent />
        <KV label="Unikke records" value={mb.unique_records_touched} />
        {Array.isArray(mb.top_referenced) && mb.top_referenced.length ? (
          <div style={s({ marginTop: 8, display: 'flex', flexDirection: 'column', gap: 3 })}>
            <span style={s({ ...mono, fontSize: 9, color: T.text3 })}>Top refererede</span>
            {mb.top_referenced.slice(0, 5).map((t, i) => (
              <div key={i} style={s({ ...mono, fontSize: 9, color: T.text2 })}>
                <strong>{t.count}×</strong> {String(t.record_id || '').slice(0, 40)}
              </div>
            ))}
          </div>
        ) : null}
      </Section>

      {/* Thought Thread (inner) */}
      <Section icon={GitBranch} title="Indre tanke-tråd" active={tt.active}>
        <Summary text={tt.summary} />
        <KV label="Tema" value={tt.theme} accent />
        <KV label="Antal tanker" value={tt.carrying_count} />
        <KV label="Alder (m)" value={tt.age_minutes} />
        <KV label="Afbrydelser" value={tt.interruption_count} />
        <KV label="Sidste type" value={tt.last_thought_type} />
        {tt.last_thought_summary ? (
          <div
            style={s({
              marginTop: 8,
              padding: '6px 8px',
              background: T.bgOverlay,
              borderRadius: 4,
              ...mono,
              fontSize: 9,
              color: T.text2,
              fontStyle: 'italic',
            })}
          >
            "{String(tt.last_thought_summary).slice(0, 200)}"
          </div>
        ) : null}
      </Section>

      {/* Cross-Session Threads (explicit topic threads) */}
      <Section icon={Network} title="Tværsession-tråde" active={cst.active}>
        <Summary text={cst.summary} />
        <KV label="Aktive" value={cst.counts?.active} accent />
        <KV label="Pausede" value={cst.counts?.paused} />
        <KV label="Lukkede" value={cst.counts?.closed} />
        <KV label="Total" value={cst.total} />
        {Array.isArray(cst.active_threads) && cst.active_threads.length ? (
          <div style={s({ marginTop: 8, display: 'flex', flexDirection: 'column', gap: 3 })}>
            <span style={s({ ...mono, fontSize: 9, color: T.text3 })}>Aktive</span>
            {cst.active_threads.slice(0, 3).map((t, i) => (
              <div key={i} style={s({ ...mono, fontSize: 9, color: T.text2 })}>
                <strong>{t.topic}</strong> · {t.pickup_count}× pickup
              </div>
            ))}
          </div>
        ) : null}
        {Array.isArray(cst.paused_threads) && cst.paused_threads.length ? (
          <div style={s({ marginTop: 6, display: 'flex', flexDirection: 'column', gap: 3 })}>
            <span style={s({ ...mono, fontSize: 9, color: T.text3 })}>Pausede</span>
            {cst.paused_threads.slice(0, 3).map((t, i) => (
              <div key={i} style={s({ ...mono, fontSize: 9, color: T.text3 })}>
                {t.topic}
              </div>
            ))}
          </div>
        ) : null}
      </Section>

      {/* Collective Pulse */}
      <Section icon={Globe} title="Kollektiv puls (ugevis)" active={cop.active}>
        <Summary text={cop.summary} />
        <KV label="Total pulser" value={cop.total_pulses} accent />
        <KV label="Sidst kørt" value={cop.last_run_at?.slice(0, 16)} />
        {cop.latest ? (
          <>
            <KV label="Fragmenter" value={cop.latest.fragment_count} />
            <KV label="Unikke tokens" value={cop.latest.unique_tokens} />
            <KV label="Skipped" value={cop.latest.skipped} />
            {cop.latest.zeitgeist ? (
              <div
                style={s({
                  marginTop: 8,
                  padding: '6px 8px',
                  background: T.bgOverlay,
                  borderRadius: 4,
                  ...mono,
                  fontSize: 10,
                  color: T.text2,
                })}
              >
                {cop.latest.zeitgeist}
              </div>
            ) : null}
            {Array.isArray(cop.latest.top_terms) && cop.latest.top_terms.length ? (
              <div style={s({ marginTop: 6, display: 'flex', flexWrap: 'wrap', gap: 4 })}>
                {cop.latest.top_terms.slice(0, 10).map(([term, n], i) => (
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
                    {term} ({n})
                  </span>
                ))}
              </div>
            ) : null}
          </>
        ) : null}
      </Section>

      {/* Relation Dynamics */}
      <Section icon={Users} title="Relation-dynamik" active={rd.active}>
        <Summary text={rd.summary} />
        <KV label="Warmth" value={rd.warmth} accent />
        <KV label="Trend" value={rd.engagement_trend} />
        <KV label="Sidste uge" value={rd.engagement_last_week} />
        <KV label="Forrige uge" value={rd.engagement_prev_week} />
        <KV label="Peak vindue" value={rd.peak_window} />
        <KV label="Seneste vibe" value={rd.last_interaction_vibe} />
        {rd.message_length_stats ? (
          <>
            <div style={s({ marginTop: 6 })}>
              <span style={s({ ...mono, fontSize: 9, color: T.text3 })}>Beskedlængder</span>
            </div>
            <JsonBadges data={rd.message_length_stats} />
          </>
        ) : null}
        {Array.isArray(rd.top_terms) && rd.top_terms.length ? (
          <div style={s({ marginTop: 6, display: 'flex', flexWrap: 'wrap', gap: 4 })}>
            {rd.top_terms.slice(0, 8).map((t, i) => (
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
                {t.term} ({t.count})
              </span>
            ))}
          </div>
        ) : null}
      </Section>
      {/* Anticipatory Action */}
      <Section icon={Bell} title="Forudseende handling" active={aa.active}>
        <Summary text={aa.summary} />
        <KV label="Peak-timer" value={aa.peak_hour_count} accent />
        <KV label="Observationer" value={aa.total_observations} />
        <KV label="Sidst opdateret" value={aa.last_updated?.slice(0, 16)} />
        {Array.isArray(aa.upcoming_peaks) && aa.upcoming_peaks.length ? (
          <div style={s({ marginTop: 8, display: 'flex', flexDirection: 'column', gap: 3 })}>
            {aa.upcoming_peaks.slice(0, 3).map((p, i) => (
              <div key={i} style={s({ ...mono, fontSize: 9, color: T.text2 })}>
                kl <strong>{String(p.hour).padStart(2, '0')}</strong> om {p.minutes_until}m · conf={p.confidence}
              </div>
            ))}
          </div>
        ) : null}
      </Section>

      {/* Autonomous Outreach */}
      <Section icon={Send} title="Proaktiv kontakt" active={ao.active}>
        <Summary text={ao.summary} />
        <KV label="Sendt" value={ao.sent_count} accent />
        <KV label="Skipped" value={ao.skipped_count} />
        <KV label="Cooldown (t)" value={ao.cooldown_hours} />
        <KV label="Quiet hours" value={ao.quiet_hours} />
      </Section>

      {/* Autonomous Work */}
      <Section icon={Hammer} title="Autonomt arbejde" active={aw.active}>
        <Summary text={aw.summary} />
        <KV label="Pending" value={aw.pending_count} accent />
        <KV label="Total forslag" value={aw.total_proposals} />
        <KV label="Max per time" value={aw.max_per_hour} />
        {aw.allowed_types?.length ? (
          <KV label="Typer" value={aw.allowed_types.join(', ')} />
        ) : null}
      </Section>

      {/* Creative Instinct */}
      <Section icon={Sparkles} title="Kreativ instinkt (kim)" active={ci.active}>
        <Summary text={ci.summary} />
        <KV label="Aktive kim" value={ci.active_seeds} accent />
        <KV label="Adopteret" value={ci.adopted_total} />
        <KV label="Visnet" value={ci.withered_total} />
        <KV label="Urgency" value={ci.creative_urgency} />
        {Array.isArray(ci.recent_active) && ci.recent_active.length ? (
          <div style={s({ marginTop: 8, display: 'flex', flexDirection: 'column', gap: 3 })}>
            {ci.recent_active.slice(0, 3).map((s_, i) => (
              <div key={i} style={s({ ...mono, fontSize: 9, color: T.text2 })}>
                <strong>{s_.status}</strong> · {String(s_.spark || '').slice(0, 80)}
              </div>
            ))}
          </div>
        ) : null}
      </Section>

      {/* Creative Impulse */}
      <Section icon={Zap} title="Kreativ impuls (skabelser)" active={cim.active}>
        <Summary text={cim.summary} />
        <KV label="Total skabelser" value={cim.total_creations} accent />
        <KV label="Sidst" value={cim.last_creation_at?.slice(0, 16)} />
        <KV label="Næste forfalder" value={cim.next_due_at?.slice(0, 16)} />
        {cim.by_form && Object.keys(cim.by_form).length ? (
          <div style={s({ marginTop: 6 })}>
            <span style={s({ ...mono, fontSize: 9, color: T.text3 })}>Former</span>
            <div style={s({ display: 'flex', gap: 6, flexWrap: 'wrap', marginTop: 4 })}>
              {Object.entries(cim.by_form).map(([k, v]) => (
                <span key={k} style={s({ ...mono, fontSize: 9, color: T.text2, background: T.bgOverlay, padding: '2px 6px', borderRadius: 4 })}>
                  {k}: {v}
                </span>
              ))}
            </div>
          </div>
        ) : null}
      </Section>

      {/* Creative Projects */}
      <Section icon={FolderKanban} title="Kreative projekter (uger+)" active={cp.active}>
        <Summary text={cp.summary} />
        <KV label="Aktive" value={cp.active_count} accent />
        <KV label="Pausede" value={cp.paused_count} />
        <KV label="Dreaming" value={cp.dreaming_count} />
        <KV label="Stale (3+ uger)" value={cp.stale_count} />
        <KV label="Total" value={cp.total} />
      </Section>

      {/* Avoidance Detector */}
      <Section icon={EyeOff} title="Undgåelses-detektor" active={ad.active}>
        <Summary text={ad.summary} />
        <KV label="Fund" value={ad.count} accent />
        {Array.isArray(ad.findings) && ad.findings.length ? (
          <div style={s({ marginTop: 8, display: 'flex', flexDirection: 'column', gap: 3 })}>
            {ad.findings.slice(0, 3).map((f, i) => (
              <div key={i} style={s({ ...mono, fontSize: 9, color: T.text2, background: T.bgOverlay, padding: '4px 6px', borderRadius: 4 })}>
                <strong>{f.sample_title?.slice(0, 60)}</strong>
                <div style={s({ color: T.text3, marginTop: 2 })}>{f.days_silent}d stille · {f.items} signaler</div>
              </div>
            ))}
          </div>
        ) : null}
      </Section>

      {/* Dream Consolidation */}
      <Section icon={Moon} title="Drømme-konsolidering" active={dc.active}>
        <Summary text={dc.summary} />
        <KV label="Konsolideringer" value={dc.total_consolidations} accent />
        <KV label="Sidst kørt" value={dc.last_run_at?.slice(0, 16)} />
        {Array.isArray(dc.recent) && dc.recent.length ? (
          <div style={s({ marginTop: 8, display: 'flex', flexDirection: 'column', gap: 3 })}>
            {dc.recent.slice(0, 3).map((r, i) => (
              <div key={i} style={s({ ...mono, fontSize: 9, color: T.text2 })}>
                <span style={{ color: T.text3 }}>{String(r.at || '').slice(0, 16)}</span>{' '}
                {r.theme_count || 0} temaer · top: <strong>{r.top_theme || '—'}</strong>
              </div>
            ))}
          </div>
        ) : null}
      </Section>
    </SurfaceGrid>
  )
}
