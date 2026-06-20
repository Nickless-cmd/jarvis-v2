/** Afgør om en indkommende FCM-data-besked skal blive en floatbar samtale-boble.
 *  Kun de proaktive Jarvis-beskeder (svar/påmindelse) med en session floates. */
const FLOAT_KINDS = new Set(['answer_ready', 'reminder'])

export function shouldFloatOnPush(data: Record<string, string> | undefined): boolean {
  if (!data) return false
  const kind = data.kind ?? ''
  const sessionId = data.session_id ?? ''
  return FLOAT_KINDS.has(kind) && sessionId.length > 0
}
