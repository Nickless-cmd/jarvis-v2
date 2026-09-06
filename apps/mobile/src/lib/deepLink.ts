export type MobileIntent =
  | { kind: 'session'; sessionId: string }
  | { kind: 'run'; runId: string; sessionId?: string }
  | { kind: 'approval'; approvalId: string; sessionId?: string }
  | { kind: 'artifact'; artifactId?: string }
  | { kind: 'memory'; memoryId?: string }
  | { kind: 'settings'; section?: 'sensors' | 'devices' | 'notifications' | string }

function clean(value: unknown): string | undefined {
  const s = typeof value === 'string' ? value.trim() : ''
  return s || undefined
}

export function intentFromUrl(raw: string): MobileIntent | null {
  try {
    const url = new URL(raw)
    const path = url.protocol === 'jarvis:'
      ? [url.hostname, ...url.pathname.split('/').filter(Boolean)].filter(Boolean)
      : url.pathname.split('/').filter(Boolean).filter((p) => p !== 'mobile')
    const [head, id, tail] = path
    if (head === 'session' && id) return { kind: 'session', sessionId: id }
    if (head === 'run' && id) return { kind: 'run', runId: id, sessionId: clean(url.searchParams.get('session')) }
    if (head === 'approval' && id) return { kind: 'approval', approvalId: id, sessionId: clean(url.searchParams.get('session')) }
    if (head === 'artifact') return { kind: 'artifact', artifactId: id }
    if (head === 'memory') return { kind: 'memory', memoryId: id }
    if (head === 'settings') return { kind: 'settings', section: id ?? tail }
  } catch {
    return null
  }
  return null
}

export function intentFromPushData(data: Record<string, unknown> | null | undefined): MobileIntent | null {
  const kind = String(data?.kind ?? '')
  const sessionId = clean(data?.session_id)
  if (kind === 'approval_requested') {
    const approvalId = clean(data?.request_id)
    return approvalId ? { kind: 'approval', approvalId, sessionId } : { kind: 'settings', section: 'notifications' }
  }
  if (kind === 'run_in_progress' || kind === 'answer_ready') {
    const runId = clean(data?.run_id)
    return runId ? { kind: 'run', runId, sessionId } : sessionId ? { kind: 'session', sessionId } : null
  }
  if (kind === 'artifact_ready') return { kind: 'artifact', artifactId: clean(data?.artifact_id) }
  if (kind === 'memory_review') return { kind: 'memory', memoryId: clean(data?.memory_id) }
  return sessionId ? { kind: 'session', sessionId } : null
}

export function routePathForIntent(intent: MobileIntent | null): string {
  if (!intent) return ''
  if (intent.kind === 'session') return `session/${intent.sessionId}`
  if (intent.kind === 'run') return `run/${intent.runId}`
  if (intent.kind === 'approval') return `approval/${intent.approvalId}`
  if (intent.kind === 'artifact') return `artifact/${intent.artifactId ?? ''}`.replace(/\/$/, '')
  if (intent.kind === 'memory') return `memory/${intent.memoryId ?? ''}`.replace(/\/$/, '')
  return `settings/${intent.section ?? ''}`.replace(/\/$/, '')
}
