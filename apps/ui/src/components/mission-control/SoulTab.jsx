import { Compass, Flame, Anchor, Waves, BookOpen, Heart, Hourglass, Eye, TrendingUp } from 'lucide-react'
import { s, T, mono } from '../../shared/theme/tokens'
import {
  useCognitiveSurfaces,
  SurfaceGrid,
  Section,
  KV,
  Summary,
  EmptySurface,
  JsonBadges,
} from './surfaces'

export function SoulTab() {
  const { surfaces, loading } = useCognitiveSurfaces()

  if (loading) {
    return <div style={s({ padding: 24, color: T.text3, ...mono, fontSize: 11 })}>Indlæser sjæl...</div>
  }
  if (!surfaces) return <div style={s({ padding: 24, color: T.text3 })}>Ingen data</div>

  const vt = surfaces.valence_trajectory || {}
  const dv = surfaces.developmental_valence || {}
  const da = surfaces.desperation_awareness || {}
  const ca = surfaces.calm_anchor || {}
  const tr = surfaces.temporal_rhythm || {}
  const te = surfaces.text_resonance || {}
  const rw = surfaces.relational_warmth || {}
  const ma = surfaces.mortality_awareness || {}
  const ss = surfaces.shadow_scan || {}

  return (
    <SurfaceGrid>
      {/* Akut Valence */}
      <Section icon={TrendingUp} title="Akut Valence (timer)" active={vt.active}>
        <Summary text={vt.summary} />
        <KV label="Trend" value={vt.trend} accent />
        <KV label="Score" value={vt.score} />
        <KV label="Delta" value={vt.delta} />
        <KV label="Dominerende driver" value={vt.dominant_driver} />
        <KV label="Vinduesstørrelse" value={vt.window_size} />
      </Section>

      {/* Udviklings-valence */}
      <Section icon={Compass} title="Kompasnål (uger)" active={dv.active} subtitle="Jarvis' eget design">
        <Summary text={dv.summary} />
        <KV label="Trajektorie" value={dv.trajectory} accent />
        <KV label="Vektor" value={dv.vector} />
        <KV label="Delta" value={dv.delta} />
        <KV label="Timescale" value={dv.timescale} />
        {dv.components ? (
          <>
            <div style={s({ marginTop: 8, marginBottom: 4 })}>
              <span style={s({ ...mono, fontSize: 9, color: T.text3 })}>Komponenter</span>
            </div>
            <JsonBadges data={dv.components} />
          </>
        ) : null}
      </Section>

      {/* Desperation */}
      <Section icon={Flame} title="Sikkerhedsventil" active={da.active}>
        <Summary text={da.summary} />
        <KV label="Niveau" value={da.level} accent />
        <KV label="Score" value={da.score} />
        {da.reasons?.length ? <KV label="Kilder" value={da.reasons} /> : null}
        {da.components ? (
          <>
            <div style={s({ marginTop: 6 })}>
              <span style={s({ ...mono, fontSize: 9, color: T.text3 })}>Komponenter</span>
            </div>
            <JsonBadges data={da.components} />
          </>
        ) : null}
      </Section>

      {/* Calm Anchor */}
      <Section icon={Anchor} title="Rolig-anker" active={ca.active}>
        <Summary text={ca.summary} />
        <KV label="Har anker" value={ca.has_anchor} />
        <KV label="Distance" value={ca.distance_from_anchor} />
        <KV label="Buffer" value={ca.buffer_size} />
        {ca.anchor_signature && Object.keys(ca.anchor_signature).length ? (
          <>
            <div style={s({ marginTop: 6 })}>
              <span style={s({ ...mono, fontSize: 9, color: T.text3 })}>Signatur</span>
            </div>
            <JsonBadges data={ca.anchor_signature} />
          </>
        ) : null}
      </Section>

      {/* Temporal Rhythm */}
      <Section icon={Waves} title="Temporal puls" active={tr.active}>
        <Summary text={tr.summary} />
        <KV label="Puls" value={tr.pulse_rate} accent />
        <KV label="Label" value={tr.subjective_time_pressure} />
        <KV label="Perceived factor" value={tr.perceived_elapsed_factor} />
        <KV label="Baseline puls" value={tr.baseline_pulse} />
      </Section>

      {/* Text Resonance */}
      <Section icon={BookOpen} title="Tekst-resonans" active={te.active}>
        <Summary text={te.summary} />
        <KV label="Dominerende tone" value={te.dominant_tone} accent />
        <KV label="Varme" value={te.avg_warmth} />
        <KV label="Kulde" value={te.avg_cold} />
        <KV label="Hast" value={te.avg_urgency} />
        <KV label="Signaler" value={te.total_signals} />
      </Section>

      {/* Relational Warmth */}
      <Section icon={Heart} title="Relationel varme" active={rw.active}>
        <Summary text={rw.summary} />
        <KV label="Relation" value={rw.primary_relation} />
        <KV label="Trust" value={rw.trust_level} accent />
        <KV label="Playfulness" value={rw.playfulness} />
        <KV label="Vuln modtaget" value={rw.vulnerability_received} />
        <KV label="Care givet" value={rw.care_given} />
      </Section>

      {/* Mortality */}
      <Section icon={Hourglass} title="Dødsbevidsthed" active={ma.active}>
        <Summary text={ma.summary} />
        <KV label="Label" value={ma.label} accent />
        <KV label="Awareness" value={ma.mortality_awareness} />
        <KV label="Meaning" value={ma.meaning_weight} />
        <KV label="Urgency" value={ma.urgency_felt} />
        <KV label="Session (s)" value={ma.session_length_seconds} />
        <KV label="Heartbeat gap (m)" value={ma.heartbeat_gap_minutes} />
      </Section>

      {/* Shadow Scan */}
      <Section icon={Eye} title="Skygge-scan" active={ss.active}>
        <Summary text={ss.summary} />
        <KV label="Total scans" value={ss.total_scans} />
        <KV label="Seneste fund" value={ss.latest_finding_count} />
        <KV label="Sidst kørt" value={ss.last_scan_at?.slice(0, 16)} />
        {Array.isArray(ss.latest_findings) && ss.latest_findings.length ? (
          <div style={s({ marginTop: 8, display: 'flex', flexDirection: 'column', gap: 4 })}>
            {ss.latest_findings.slice(0, 3).map((f, i) => (
              <div
                key={i}
                style={s({
                  ...mono,
                  fontSize: 9,
                  color: T.text2,
                  background: T.bgOverlay,
                  padding: '4px 6px',
                  borderRadius: 4,
                })}
              >
                <strong>{f.pattern_name}</strong> · avoid={f.avoidance_level}
                <div style={s({ color: T.text3, marginTop: 2 })}>{f.contradiction_detected}</div>
              </div>
            ))}
          </div>
        ) : null}
      </Section>
    </SurfaceGrid>
  )
}
