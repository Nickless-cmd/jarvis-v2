import type { ApiConfig } from './types'

/**
 * Sender en besked til en sessions run via /chat/stream/v2 (fire-and-forget:
 * runnet spawnes server-autoritativt ved request-modtagelse, så vi behøver ikke
 * læse SSE-streamen). Bruges af statusbar-svar (Direct Reply) — svaret kommer
 * tilbage som en ny FCM-notifikation når runnet finisher server-side.
 * Returnerer true ved ok; sluger alle fejl → false.
 */
export async function replyToSession(
  config: ApiConfig,
  sessionId: string,
  text: string
): Promise<boolean> {
  const body = (text ?? '').trim()
  if (!sessionId || !body) return false
  try {
    const url = new URL('/chat/stream/v2', config.apiBaseUrl).toString()
    const r = await fetch(url, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Accept: 'text/event-stream',
        ...(config.authToken ? { Authorization: `Bearer ${config.authToken}` } : {})
      },
      body: JSON.stringify({
        message: body,
        session_id: sessionId,
        mode: 'chat',
        approval_mode: 'ask',
        thinking_mode: 'think',
        model: '',
        provider_choice: '',
        attachment_ids: []
      })
    })
    return r.ok
  } catch {
    return false
  }
}
