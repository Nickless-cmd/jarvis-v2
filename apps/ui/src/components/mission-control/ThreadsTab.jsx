import { Wind, GitBranch, Network, Globe, Users } from 'lucide-react'
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
    </SurfaceGrid>
  )
}
