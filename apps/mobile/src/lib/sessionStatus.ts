import type { ChatSession } from './types'

export function isWorking(sessionId: string, activeRunIds: string[]): boolean {
  return activeRunIds.includes(sessionId)
}

export function computeUnread(
  sessions: ChatSession[],
  lastSeen: Record<string, number>,
  activeId: string | null,
): Record<string, boolean> {
  const out: Record<string, boolean> = {}
  for (const s of sessions) {
    const count = s.message_count ?? 0
    out[s.id] = s.id !== activeId && count > (lastSeen[s.id] ?? 0)
  }
  return out
}
