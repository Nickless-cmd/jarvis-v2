import { useEffect, useState } from 'react'
import { Heart, Smile, AlertTriangle, TrendingUp, BookOpen, MessageSquare, FlaskConical, Target, Undo2, Moon } from 'lucide-react'
import { s, T, mono } from '../../shared/theme/tokens'
import { backend } from '../../lib/adapters'

function Section({ icon: Icon, title, badge, children }) {
  return (
    <div style={s({ background: T.bgRaised, border: `1px solid ${T.border0}`, borderRadius: T.r_sm, padding: 14, marginBottom: 10 })}>
      <div style={s({ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 10 })}>
        <Icon size={13} style={{ color: T.accent }} />
        <span style={s({ ...mono, fontSize: 9, textTransform: 'uppercase', letterSpacing: '0.08em', color: T.text2 })}>{title}</span>
        {badge != null && (
          <span style={s({ ...mono, fontSize: 8, color: T.bgBase, background: T.accent, padding: '1px 6px', borderRadius: 8 })}>{badge}</span>
        )}
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

function TrustGraph({ trajectory }) {
  if (!trajectory || !trajectory.length) return null
  const recent = trajectory.slice(-20)
  const max = 1.0
  const h = 40
  const w = 200
  const step = w / Math.max(recent.length - 1, 1)
  const points = recent.map((v, i) => `${i * step},${h - (v / max) * h}`).join(' ')
  return (
    <svg width={w} height={h} style={{ display: 'block', marginTop: 6 }}>
      <polyline points={points} fill="none" stroke={T.accent} strokeWidth="1.5" />
      {recent.map((v, i) => (
        <circle key={i} cx={i * step} cy={h - (v / max) * h} r={1.5} fill={T.accentText} />
      ))}
    </svg>
  )
}

export function RelationshipTab() {
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

  if (loading) return <div style={s({ padding: 24, color: T.text3, ...mono, fontSize: 11 })}>Indlæser relationsdata...</div>
  if (!data) return <div style={s({ padding: 24, color: T.text3 })}>Ingen data</div>

  const rt = data.relationshipTexture?.current
  const taste = data.tasteProfile?.current
  const trustTraj = rt ? JSON.parse(rt.trust_trajectory || '[]') : []
  const corrections = rt ? JSON.parse(rt.correction_patterns || '[]') : []
  const insideRefs = rt ? JSON.parse(rt.inside_references || '[]') : []
  const unspoken = rt ? JSON.parse(rt.unspoken_rules || '[]') : []

  return (
    <div style={s({ padding: '16px 20px', display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))', gap: 10 })}>

      {/* Trust Trajectory */}
      <Section icon={Heart} title="Tillid over tid" badge={trustTraj.length ? `${(trustTraj[trustTraj.length - 1] * 100).toFixed(0)}%` : null}>
        {trustTraj.length ? (
          <>
            <TrustGraph trajectory={trustTraj} />
            <KV label="Datapunkter" value={trustTraj.length} />
            <KV label="Seneste" value={(trustTraj[trustTraj.length - 1] * 100).toFixed(1) + '%'} accent />
          </>
        ) : (
          <span style={s({ ...mono, fontSize: 10, color: T.text3 })}>Ingen tillidsdata endnu</span>
        )}
      </Section>

      {/* Humor */}
      <Section icon={Smile} title="Humor">
        <KV label="Humor frekvens" value={rt ? (rt.humor_frequency * 100).toFixed(0) + '%' : '—'} />
      </Section>

      {/* Corrections */}
      <Section icon={AlertTriangle} title="Korrektioner" badge={corrections.length || null}>
        {corrections.slice(0, 8).map((c, i) => (
          <div key={i} style={s({ ...mono, fontSize: 9, color: T.text2, padding: '2px 0', borderBottom: `1px solid ${T.border0}` })}>
            {c}
          </div>
        ))}
        {!corrections.length && <span style={s({ ...mono, fontSize: 10, color: T.text3 })}>Ingen korrektioner registreret</span>}
      </Section>

      {/* Taste Profile */}
      <Section icon={TrendingUp} title={`Smagsprofil${taste ? ` v${taste.version}` : ''}`}>
        {taste ? (
          <>
            <div style={s({ marginBottom: 6 })}>
              <span style={s({ ...mono, fontSize: 9, color: T.text3 })}>Kode-smag</span>
              {Object.entries(JSON.parse(taste.code_taste || '{}')).map(([k, v]) => (
                <div key={k} style={s({ display: 'flex', justifyContent: 'space-between', padding: '1px 0' })}>
                  <span style={s({ ...mono, fontSize: 9, color: T.text2 })}>{k.replace(/_/g, ' ')}</span>
                  <span style={s({ ...mono, fontSize: 9, color: v > 0.6 ? T.green : v < 0.4 ? T.red : T.text3 })}>{(v * 100).toFixed(0)}%</span>
                </div>
              ))}
            </div>
            <div style={s({ marginBottom: 6 })}>
              <span style={s({ ...mono, fontSize: 9, color: T.text3 })}>Design-smag</span>
              {Object.entries(JSON.parse(taste.design_taste || '{}')).map(([k, v]) => (
                <div key={k} style={s({ display: 'flex', justifyContent: 'space-between', padding: '1px 0' })}>
                  <span style={s({ ...mono, fontSize: 9, color: T.text2 })}>{k.replace(/_/g, ' ')}</span>
                  <span style={s({ ...mono, fontSize: 9, color: v > 0.6 ? T.green : v < 0.4 ? T.red : T.text3 })}>{(v * 100).toFixed(0)}%</span>
                </div>
              ))}
            </div>
            <KV label="Evidence points" value={taste.evidence_count} />
          </>
        ) : (
          <span style={s({ ...mono, fontSize: 10, color: T.text3 })}>Ingen smagsprofil endnu</span>
        )}
      </Section>

      {/* Inside References */}
      <Section icon={BookOpen} title="Inside References">
        {insideRefs.slice(0, 10).map((ref, i) => (
          <span key={i} style={s({ ...mono, fontSize: 9, color: T.accent, background: T.accentDim, padding: '2px 6px', borderRadius: 8, marginRight: 4, marginBottom: 4, display: 'inline-block' })}>
            {ref}
          </span>
        ))}
        {!insideRefs.length && <span style={s({ ...mono, fontSize: 10, color: T.text3 })}>Ingen fælles referencer endnu</span>}
      </Section>

      {/* Decision Log */}
      <Section icon={Target} title="Beslutningslog" badge={data.decisions?.total_count || null}>
        {(data.decisions?.decisions || []).slice(0, 5).map((d) => (
          <div key={d.decision_id} style={s({ padding: '4px 0', borderBottom: `1px solid ${T.border0}` })}>
            <div style={s({ ...mono, fontSize: 10, color: T.text1 })}>{d.title}</div>
            <div style={s({ ...mono, fontSize: 9, color: T.text3 })}>{d.decision} — {d.why}</div>
          </div>
        ))}
        {!(data.decisions?.decisions || []).length && <span style={s({ ...mono, fontSize: 10, color: T.text3 })}>Ingen beslutninger logget</span>}
      </Section>

      {/* Counterfactuals */}
      <Section icon={Undo2} title="Kontrafaktualer" badge={data.counterfactuals?.items?.length || null}>
        {(data.counterfactuals?.items || []).slice(0, 5).map((cf) => (
          <div key={cf.cf_id} style={s({ padding: '3px 0', borderBottom: `1px solid ${T.border0}` })}>
            <div style={s({ ...mono, fontSize: 10, color: T.text2 })}>{cf.cf_question}</div>
            <div style={s({ ...mono, fontSize: 9, color: T.text3 })}>{cf.source} · {(cf.confidence * 100).toFixed(0)}%</div>
          </div>
        ))}
        {!(data.counterfactuals?.items || []).length && <span style={s({ ...mono, fontSize: 10, color: T.text3 })}>Ingen kontrafaktualer</span>}
      </Section>

      {/* Dreams */}
      <Section icon={Moon} title="Drømme Carry-Over">
        {(data.dreamCarryOver?.active_dreams || []).map((d) => (
          <div key={d.dream_id} style={s({ padding: '3px 0', borderBottom: `1px solid ${T.border0}` })}>
            <div style={s({ ...mono, fontSize: 10, color: T.text1 })}>{d.content}</div>
            <div style={s({ ...mono, fontSize: 9, color: T.text3 })}>
              {(d.confidence * 100).toFixed(0)}% · {d.confirmed ? '✓ bekræftet' : d.presented ? 'præsenteret' : 'aktiv'}
            </div>
          </div>
        ))}
        <span style={s({ ...mono, fontSize: 9, color: T.text3 })}>{data.dreamCarryOver?.summary}</span>
      </Section>

      {/* Self-Experiments */}
      <Section icon={FlaskConical} title="Selveksperimenter" badge={data.selfExperiments?.running_count || null}>
        {(data.selfExperiments?.experiments || []).slice(0, 4).map((exp) => (
          <div key={exp.experiment_id} style={s({ padding: '3px 0', borderBottom: `1px solid ${T.border0}` })}>
            <div style={s({ ...mono, fontSize: 10, color: T.text1 })}>{exp.hypothesis}</div>
            <div style={s({ ...mono, fontSize: 9, color: exp.status === 'concluded' ? T.green : T.text3 })}>
              {exp.status} · n={exp.n}
            </div>
          </div>
        ))}
        {!(data.selfExperiments?.experiments || []).length && <span style={s({ ...mono, fontSize: 10, color: T.text3 })}>Ingen eksperimenter</span>}
      </Section>

      {/* Conversation Rhythm */}
      <Section icon={MessageSquare} title="Samtale-Rytme">
        {(data.conversationRhythm?.signatures || []).map((sig) => (
          <div key={sig.signature_type} style={s({ display: 'flex', justifyContent: 'space-between', padding: '2px 0' })}>
            <span style={s({ ...mono, fontSize: 10, color: T.text1 })}>{sig.signature_type}</span>
            <span style={s({ ...mono, fontSize: 9, color: T.text3 })}>
              {sig.count}× · {(sig.success_rate * 100).toFixed(0)}% success
            </span>
          </div>
        ))}
        {!(data.conversationRhythm?.signatures || []).length && <span style={s({ ...mono, fontSize: 10, color: T.text3 })}>Ingen mønstre endnu</span>}
      </Section>

      {/* Unspoken Rules */}
      {unspoken.length > 0 && (
        <Section icon={BookOpen} title="Uudtalte Regler">
          {unspoken.map((rule, i) => (
            <div key={i} style={s({ ...mono, fontSize: 10, color: T.text2, padding: '2px 0' })}>{rule}</div>
          ))}
        </Section>
      )}
    </div>
  )
}
