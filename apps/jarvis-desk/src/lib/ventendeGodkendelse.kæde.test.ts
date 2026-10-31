import { describe, it, expect, vi, afterEach } from 'vitest'
import { getSession } from './api'
import { findesGodkendelseIRækken } from './ventendeGodkendelse'
import { mergeServer } from '../contexts/SessionContext'

/**
 * Kæden fra server-række til «findes kortet?» — målt, ikke antaget.
 *
 * 31/10-2026. DEL 3 blev bygget og 0.6.294 udgivet, og Bjørn så INTET
 * godkendelses-kort i PWA'en. Årsagen var ikke komponenten: `getSession`
 * normaliserede hver besked til `content` og DROPPEDE `content_json` undervejs.
 * Historik-grenen læste derfor `undefined`, tegnede et tomt kort, og
 * fallbacken blev aldrig undertrykt fordi den heller ikke kunne se rækken.
 *
 * Testene her renderer INGENTING. De måler den ene ting der gik galt: kommer
 * `approval_id` hele vejen fra HTTP-svaret til den funktion der afgør om
 * kortet findes? En test der bygger besked-objektet i hånden kan ikke se den
 * fejl — den ville være grøn, præcis som de 3100 var det.
 */

const config = { apiBaseUrl: 'http://test.local', authToken: 'token' }

function svarMed(rows: unknown[]): void {
  vi.stubGlobal(
    'fetch',
    vi.fn(async () =>
      new Response(JSON.stringify({ session: { id: 's1', title: 't', messages: rows } }), {
        status: 200,
        headers: { 'content-type': 'application/json', etag: '"x"' },
      }),
    ),
  )
}

const raekke = {
  id: 'message-a1',
  role: 'approval_request',
  content: 'Godkendelse afventer: exec_command — rm -rf /tmp/x',
  content_json: [{ approval_id: 'a1', tool: 'exec_command', action: 'rm -rf /tmp/x', status: 'pending' }],
  created_at: '2026-10-31T12:00:00+00:00',
  parent_id: null,
}

afterEach(() => {
  vi.unstubAllGlobals()
})

describe('godkendelsen naar klienten som data', () => {
  it('getSession bærer content_json videre uændret', async () => {
    svarMed([raekke])
    const snap = await getSession(config, 's1')
    expect(snap).not.toBeNull()
    const m = snap!.messages[0]!
    expect(m.role).toBe('approval_request')
    expect(Array.isArray(m.content_json)).toBe(true)
    expect((m.content_json as Array<{ approval_id: string }>)[0]!.approval_id).toBe('a1')
  })

  it('overlever mergeServer — den er vejen ind i sessions.messages', async () => {
    svarMed([raekke])
    const snap = await getSession(config, 's1')
    const flettet = mergeServer([], snap!.messages)
    expect(Array.isArray(flettet[0]!.content_json)).toBe(true)
  })

  it('findesGodkendelseIRækken ser rækken efter den ægte kæde', async () => {
    svarMed([raekke])
    const snap = await getSession(config, 's1')
    const flettet = mergeServer([], snap!.messages)
    expect(findesGodkendelseIRækken(flettet, 'a1')).toBe(true)
  })

  it('matcher ikke en anden godkendelse — to kan have samme kommando', async () => {
    svarMed([raekke])
    const snap = await getSession(config, 's1')
    const flettet = mergeServer([], snap!.messages)
    expect(findesGodkendelseIRækken(flettet, 'a2')).toBe(false)
  })

  it('uden rækken er svaret nej — saa bærer fallbacken kortet', async () => {
    svarMed([{ ...raekke, id: 'm2', role: 'user', content: 'hej', content_json: null }])
    const snap = await getSession(config, 's1')
    expect(findesGodkendelseIRækken(mergeServer([], snap!.messages), 'a1')).toBe(false)
  })
})
