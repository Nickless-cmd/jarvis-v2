import { createSession, type ApiConfig } from '../lib/api'
import { sendLoesrevet } from '../lib/sendLoesrevet'

/**
 * «Start ny chat» fra figuren (Codex' Quick Chat): opret en samtale og send
 * beskeden løsrevet (lib/sendLoesrevet) — svaret kører videre på serveren
 * og bliver til «Færdig — se svaret».
 */
export async function sendHurtigt(config: ApiConfig, tekst: string): Promise<string> {
  const besked = tekst.trim()
  if (!besked) throw new Error('Tom besked')
  const titel = besked.length > 60 ? `${besked.slice(0, 57)}…` : besked
  const session = await createSession(config, titel, 'chat')
  await sendLoesrevet(config, { sessionId: session.id, message: besked, mode: 'chat' })
  return session.id
}
