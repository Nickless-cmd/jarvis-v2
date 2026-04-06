import { useEffect, useState } from 'react'
import { Compass, Waves, Scale, Palette, VolumeX, Languages, Brain, Sparkles, Eye, Fingerprint } from 'lucide-react'
import { s, T, mono } from '../../shared/theme/tokens'
import { backend } from '../../lib/adapters'

function Section({ icon: Icon, title, children }) {
  return (
    <div style={s({ background: T.bgRaised, border: `1px solid ${T.border0}`, borderRadius: T.r_sm, padding: 14, marginBottom: 10 })}>
      <div style={s({ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 10 })}>
        <Icon size={13} style={{ color: T.accent }} />
        <span style={s({ ...mono, fontSize: 9, textTransform: 'uppercase', letterSpacing: '0.08em', color: T.text2 })}>{title}</span>
      </div>
      {children}
    </div>
  )
}

function KV({ label, value, accent }) {
  return (
    <div style={s({ display: 'flex', justifyContent: 'space-between', padding: '3px 0', borderBottom: `1px solid ${T.border0}` })}>
      <span style={s({ ...mono, fontSize: 10, color: T.text3 })}>{label}</span>
      <span style={s({ ...mono, fontSize: 10, color: accent ? T.accentText : T.text1 })}>{String(value ?? '—')}</span>
    </div>
  )
}

function JsonPreview({ data, maxKeys = 6 }) {
  if (!data || typeof data !== 'object') return <span style={s({ ...mono, fontSize: 10, color: T.text3 })}>—</span>
  const entries = Object.entries(data).slice(0, maxKeys)
  return (
    <div style={s({ display: 'flex', flexWrap: 'wrap', gap: 6 })}>
      {entries.map(([k, v]) => (
        <span key={k} style={s({ ...mono, fontSize: 9, color: T.text2, background: T.bgOverlay, padding: '2px 6px', borderRadius: 4 })}>
          {k}={typeof v === 'number' ? v.toFixed(2) : String(v ?? '')}
        </span>
      ))}
    </div>
  )
}

export function CognitiveStateTab() {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    let cancelled = false
    async function load() {
      try {
        const result = await backend.getCognitiveArchitecture()
        if (!cancelled) setData(result)
      } catch { /* ignore */ }
      if (!cancelled) setLoading(false)
    }
    load()
    const interval = setInterval(load, 60000)
    return () => { cancelled = true; clearInterval(interval) }
  }, [])

  if (loading) return <div style={s({ padding: 24, color: T.text3, ...mono, fontSize: 11 })}>Indlæser kognitiv tilstand...</div>
  if (!data) return <div style={s({ padding: 24, color: T.text3 })}>Ingen data</div>

  const pv = data.personalityVector?.current
  const compass = data.compass?.current
  const rhythm = data.rhythm?.current
  const injection = data.cognitiveStateInjection

  return (
    <div style={s({ padding: '16px 20px', display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))', gap: 10 })}>

      {/* Prompt Injection Transparens */}
      <Section icon={Eye} title="Prompt Injection">
        <KV label="Sidst injiceret" value={injection?.last_injection_at || 'Aldrig'} />
        <KV label="Chars" value={injection?.last_injection?.chars} />
        <KV label="Kilder" value={(injection?.last_injection?.sources || []).join(', ') || '—'} />
        {injection?.last_injection?.text && (
          <div style={s({ marginTop: 8, padding: 8, background: T.bgBase, borderRadius: 6, ...mono, fontSize: 9, color: T.text2, whiteSpace: 'pre-wrap', maxHeight: 120, overflow: 'auto' })}>
            {injection.last_injection.text}
          </div>
        )}
      </Section>

      {/* Personality Vector */}
      <Section icon={Fingerprint} title={`Personality Vector${pv ? ` v${pv.version}` : ''}`}>
        {pv ? (
          <>
            <KV label="Bearing" value={pv.current_bearing || '—'} accent />
            <div style={s({ marginTop: 6, marginBottom: 4 })}>
              <span style={s({ ...mono, fontSize: 9, color: T.text3 })}>Confidence by domain</span>
            </div>
            <JsonPreview data={JSON.parse(pv.confidence_by_domain || '{}')} />
            <div style={s({ marginTop: 6, marginBottom: 4 })}>
              <span style={s({ ...mono, fontSize: 9, color: T.text3 })}>Emotional baseline</span>
            </div>
            <JsonPreview data={JSON.parse(pv.emotional_baseline || '{}')} />
          </>
        ) : (
          <span style={s({ ...mono, fontSize: 10, color: T.text3 })}>Ingen personality vector endnu</span>
        )}
      </Section>

      {/* Compass */}
      <Section icon={Compass} title="Compass Bearing">
        {compass ? (
          <>
            <KV label="Bearing" value={compass.bearing} accent />
            <KV label="Rationale" value={compass.rationale} />
            <KV label="Open loops" value={compass.open_loop_count} />
            <KV label="Opdateret" value={compass.updated_at} />
          </>
        ) : (
          <span style={s({ ...mono, fontSize: 10, color: T.text3 })}>Ingen compass state</span>
        )}
      </Section>

      {/* Rhythm */}
      <Section icon={Waves} title="Rhythm / Tidevand">
        {rhythm ? (
          <>
            <KV label="Fase" value={rhythm.phase} accent />
            <KV label="Energi" value={rhythm.energy} />
            <KV label="Social" value={rhythm.social} />
            <KV label="Initiative ×" value={rhythm.initiative_multiplier} />
            <KV label="Focus protection" value={rhythm.focus_protection ? 'JA' : 'nej'} />
          </>
        ) : (
          <span style={s({ ...mono, fontSize: 10, color: T.text3 })}>Ingen rhythm state</span>
        )}
      </Section>

      {/* Paradoxes */}
      <Section icon={Scale} title="Paradokser">
        {(data.paradoxes?.axes || []).map((axis) => (
          <div key={axis} style={s({ ...mono, fontSize: 10, color: T.text2, padding: '2px 0' })}>{axis}</div>
        ))}
        <span style={s({ ...mono, fontSize: 9, color: T.text3 })}>{data.paradoxes?.summary}</span>
      </Section>

      {/* Aesthetics */}
      <Section icon={Palette} title="Æstetiske Motiver">
        <div style={s({ display: 'flex', flexWrap: 'wrap', gap: 6 })}>
          {(data.aesthetics?.motifs || []).map((m) => (
            <span key={m} style={s({ ...mono, fontSize: 9, color: T.accent, background: T.accentDim, padding: '3px 8px', borderRadius: 10 })}>{m}</span>
          ))}
        </div>
      </Section>

      {/* Silence Signals */}
      <Section icon={VolumeX} title="Stilhed / Silence">
        <span style={s({ ...mono, fontSize: 10, color: T.text2 })}>{data.silenceSignals?.summary || 'Overvåger...'}</span>
      </Section>

      {/* Shared Language */}
      <Section icon={Languages} title="Fælles Sprog">
        {(data.sharedLanguage?.terms || []).slice(0, 8).map((term) => (
          <div key={term.term_id} style={s({ display: 'flex', justifyContent: 'space-between', padding: '2px 0' })}>
            <span style={s({ ...mono, fontSize: 10, color: T.text1 })}>{term.phrase}</span>
            <span style={s({ ...mono, fontSize: 9, color: T.text3 })}>{(term.confidence * 100).toFixed(0)}%</span>
          </div>
        ))}
        {!(data.sharedLanguage?.terms || []).length && (
          <span style={s({ ...mono, fontSize: 10, color: T.text3 })}>Ingen termer endnu</span>
        )}
      </Section>

      {/* Apophenia Guard */}
      <Section icon={Brain} title="Apophenia Guard">
        <KV label="Min observations" value={data.apopheniaGuard?.thresholds?.min_observations} />
        <KV label="Reject below" value={data.apopheniaGuard?.thresholds?.reject_below} />
        <KV label="Upgrade above" value={data.apopheniaGuard?.thresholds?.upgrade_above} />
      </Section>

      {/* Anticipatory Context */}
      <Section icon={Sparkles} title="Anticipatory Context">
        <span style={s({ ...mono, fontSize: 10, color: T.text2 })}>{data.anticipatoryContext?.summary || 'Forudsiger...'}</span>
      </Section>
    </div>
  )
}
