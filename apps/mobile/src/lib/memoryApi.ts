import type { ApiConfig } from './types'

export interface MemorySection {
  title: string
  preview: string
}

export interface MemoryOverview {
  sections: MemorySection[]
  identityPreview: string
  brainCount: number
  recentSenses: { description: string; captured_at: string }[]
}

const EMPTY: MemoryOverview = {
  sections: [],
  identityPreview: '',
  brainCount: 0,
  recentSenses: []
}

function cleanLine(line: string): string {
  return line.replace(/^[-*]\s+/, '').trim()
}

export function memorySectionsFromMarkdown(markdown: string): MemorySection[] {
  const out: MemorySection[] = []
  let current = ''
  let body: string[] = []
  const flush = () => {
    if (!current) return
    const preview = body.map(cleanLine).filter(Boolean).join(' ').slice(0, 180)
    out.push({ title: current, preview })
  }
  for (const line of String(markdown || '').split('\n')) {
    const heading = /^(#{1,3})\s+(.+)$/.exec(line.trim())
    if (heading) {
      flush()
      current = heading[2]?.trim() || ''
      body = []
    } else if (current) {
      body.push(line)
    }
  }
  flush()
  return out
}

export async function fetchMemoryOverview(config: ApiConfig): Promise<MemoryOverview> {
  try {
    const url = new URL('/account/memory', config.apiBaseUrl).toString()
    const res = await fetch(url, {
      headers: config.authToken ? { Authorization: `Bearer ${config.authToken}` } : {}
    })
    if (!res.ok) return EMPTY
    const raw = await res.json()
    return {
      sections: memorySectionsFromMarkdown(String(raw.memory_md ?? '')),
      identityPreview: String(raw.user_md ?? '').trim().slice(0, 500),
      brainCount: Number(raw.brain_count ?? 0) || 0,
      recentSenses: Array.isArray(raw.recent_sensory)
        ? raw.recent_sensory
            .filter((x: unknown): x is Record<string, unknown> => typeof x === 'object' && x !== null)
            .map((x: Record<string, unknown>) => ({
              description: String(x.description ?? ''),
              captured_at: String(x.captured_at ?? '')
            }))
        : []
    }
  } catch {
    return EMPTY
  }
}

/** Gem et af Jarvis' svar som en hukommelse.
 *
 *  Serveren (`POST /mobile/memory`) fastlægger selv kind/visibility/domain —
 *  telefonen skal ikke kunne vælge forkert på hans vegne. Den sender kun
 *  teksten og hvilken samtale den kom fra.
 *
 *  Returnerer en besked der kan vises som den er. En fejl er IKKE en
 *  undtagelse her: den skal frem for øjnene af brugeren, ikke ned i loggen.
 */
export async function gemSomHukommelse(
  config: ApiConfig,
  text: string,
  sessionId?: string
): Promise<{ ok: boolean; besked: string }> {
  const indhold = String(text || '').trim()
  if (!indhold) return { ok: false, besked: 'Der er ikke noget at gemme.' }
  try {
    const url = new URL('/mobile/memory', config.apiBaseUrl).toString()
    const res = await fetch(url, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...(config.authToken ? { Authorization: `Bearer ${config.authToken}` } : {})
      },
      body: JSON.stringify({ text: indhold, session_id: sessionId ?? null })
    })
    if (!res.ok) {
      return { ok: false, besked: `Kunne ikke gemme (${res.status}).` }
    }
    return { ok: true, besked: 'Gemt i hans hukommelse.' }
  } catch {
    return { ok: false, besked: 'Ingen forbindelse — hukommelsen blev ikke gemt.' }
  }
}
