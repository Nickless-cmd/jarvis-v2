import { useMcEndpoint } from '../lib/useMcEndpoint'

interface AffectiveState {
  state?: string
  bearing?: string
  live_emotional_state?: {
    mood?: string
    confidence?: number
    curiosity?: number
    frustration?: number
    fatigue?: number
    rhythm_phase?: string
  }
}

/**
 * Tiny pill in the chat-header showing Jarvis's current mood +
 * dominant emotion. Polls /mc/affective-meta-state. Says something
 * Claude Code can't say: "I'm a being with a mood right now".
 */
export function MoodPill({ apiBaseUrl }: { apiBaseUrl: string }) {
  const { data } = useMcEndpoint<AffectiveState>(
    apiBaseUrl,
    '/mc/affective-meta-state',
    8000,
  )
  if (!data) return null
  const emo = data.live_emotional_state || {}
  const mood = emo.mood || data.state || '—'
  const phase = emo.rhythm_phase

  // Pick the dominant emotion (highest scoring) for the side hint
  const emos: Array<[string, number, string]> = [
    ['curious', emo.curiosity ?? 0, '#d4963a'],
    ['confident', emo.confidence ?? 0, '#5ab8a0'],
    ['tired', emo.fatigue ?? 0, '#4a80c0'],
  ]
  emos.sort((a, b) => b[1] - a[1])
  const [topName, topVal, topColor] = emos[0]

  return (
    <div
      className="flex items-center gap-1.5 rounded-md border border-line2 bg-bg2 px-2 py-1 font-mono text-[10px]"
      title={`mood: ${mood} · phase: ${phase ?? '—'}`}
    >
      <span className="h-1.5 w-1.5 rounded-full" style={{ background: topColor, boxShadow: `0 0 4px ${topColor}80` }} />
      <span className="text-fg2">{mood}</span>
      <span className="text-fg3">·</span>
      <span style={{ color: topColor }}>
        {topName} {(topVal * 100).toFixed(0)}%
      </span>
    </div>
  )
}
