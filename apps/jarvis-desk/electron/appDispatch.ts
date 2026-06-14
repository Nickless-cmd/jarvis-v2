/**
 * Ren planlægger for runtime→app instruktioner (§18.5 Fase 2).
 *
 * Oversætter en server-instruktion (fra GET /cowork/app-dispatch/pending) til en
 * konkret handling appen kan udføre. Holdt ren (ingen Electron/discord.js) så
 * routing-logikken kan unit-testes. appDispatchWatcher udfører planen.
 *
 * Fase 2 understøtter: native notifikation + Discord-besked (via lokal gateway).
 * Ukendte/ikke-understøttede instruktioner ack'es som 'unsupported' så køen ikke
 * clogger — men logges, så manglende routing er synlig.
 */
export interface AppInstruction {
  id: string
  action: string
  target_user: string
  channel: string | null
  payload: Record<string, unknown>
  requester: string
}

export type DispatchPlan =
  | { kind: 'notify'; title: string; body: string }
  | { kind: 'discord'; channelName: string; text: string }
  | { kind: 'unsupported'; reason: string }

function str(v: unknown): string {
  return typeof v === 'string' ? v : ''
}

export function planDispatch(instr: AppInstruction): DispatchPlan {
  const payload = instr.payload || {}
  const text = str(payload.text)

  if (instr.action === 'notify') {
    return { kind: 'notify', title: str(payload.title) || 'Jarvis', body: text }
  }

  if (instr.action === 'send_message' || instr.action === 'send_report') {
    if ((instr.channel || '') === 'discord') {
      const channelName = str(payload.channel_name) || str(payload.channel)
      if (!channelName) return { kind: 'unsupported', reason: 'mangler channel_name til Discord-besked' }
      if (!text) return { kind: 'unsupported', reason: 'tom besked' }
      return { kind: 'discord', channelName, text }
    }
    return { kind: 'unsupported', reason: `kanal '${instr.channel}' ikke understøttet i Fase 2` }
  }

  return { kind: 'unsupported', reason: `ukendt action '${instr.action}'` }
}
