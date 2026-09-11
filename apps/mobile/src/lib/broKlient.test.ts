import { opretBro, broUrl, GENFORBIND_MS, type WebSocketLignende } from './broKlient'

/** Fake socket: fanger hvad der blev sendt, og lader testen fyre hændelser. */
function fakeSocket() {
  const sendt: string[] = []
  const s: WebSocketLignende & { sendt: string[]; lukket: boolean } = {
    sendt,
    lukket: false,
    send: (d: string) => { sendt.push(d) },
    close: () => { s.lukket = true },
    onopen: null, onclose: null, onerror: null, onmessage: null
  }
  return s
}

function beskeder(s: { sendt: string[] }) {
  return s.sendt.map((r) => JSON.parse(r))
}

const GRUND = {
  apiBaseUrl: 'https://api.srvlab.dk/',
  authToken: 'test-token', // noqa: literal-credential
  capabilities: ['phone_photo', 'phone_location'],
  clientId: 'mobil-1',
  udfoer: async () => ({}),
  // Vagten er en GENTAGENDE timer. Uden en no-op her ville hver test der ikke
  // stopper broen efterlade en levende `setInterval` — Jest meldte præcis det
  // ("did not exit") da vagten blev tilføjet.
  planlaegVagt: () => 0,
  rydVagt: () => {}
}

describe('broUrl', () => {
  it('laver http om til ws og rammer endpointet', () => {
    expect(broUrl('https://api.srvlab.dk/')).toBe('wss://api.srvlab.dk/api/jarvisx-bridge/ws')
    expect(broUrl('http://10.0.0.39:8080')).toBe('ws://10.0.0.39:8080/api/jarvisx-bridge/ws')
  })
})

describe('registrering', () => {
  it('melder sine capabilities — det er dem serveren router på', () => {
    const s = fakeSocket()
    opretBro({ ...GRUND, lavSocket: () => s }).start()
    s.onopen!()

    const reg = beskeder(s)[0]
    expect(reg.type).toBe('register')
    expect(reg.capabilities).toEqual(['phone_photo', 'phone_location'])
    expect(reg.client_id).toBe('mobil-1')
  })

  it('sender token i HEADEREN — ikke i beskeden', () => {
    // Den fejl kostede en hel build: token'et lå i register-beskeden, som
    // serveren aldrig læser. Uden Authorization ved handshaket er der ingen
    // claims, og forbindelsen lukkes med «user_id_missing» før beskeden
    // overhovedet betyder noget. Telefonen kunne ALDRIG registrere sig, og
    // intet i appen sagde det — kun serverloggen, ved at tie.
    const s = fakeSocket()
    let setMuligheder: { headers: Record<string, string> } | undefined
    opretBro({
      ...GRUND,
      lavSocket: (_url, m) => { setMuligheder = m; return s }
    }).start()
    s.onopen!()

    expect(setMuligheder?.headers?.Authorization).toBe('Bearer test-token')
    expect(beskeder(s)[0].auth_token).toBeUndefined()
  })

  it('sender IKKE user_id — serveren tager den fra token', () => {
    // To kilder til hvem enheden tilhører ville kunne komme til at være uenige.
    const s = fakeSocket()
    opretBro({ ...GRUND, lavSocket: () => s }).start()
    s.onopen!()
    expect(beskeder(s)[0].user_id).toBeUndefined()
  })
})

describe('værktøjskald', () => {
  it('udfører og svarer med samme correlation_id', async () => {
    const s = fakeSocket()
    const bro = opretBro({
      ...GRUND,
      lavSocket: () => s,
      udfoer: async (t, a) => ({ vaerktoej: t, fik: a })
    })
    bro.start()
    s.onopen!()
    s.onmessage!({ data: JSON.stringify({
      type: 'tool_invoke', correlation_id: 'c1', tool: 'phone_location', args: { noejagtighed: 'high' }
    }) })
    await new Promise((r) => setTimeout(r, 0))

    const svar = beskeder(s).find((b) => b.type === 'tool_result')
    expect(svar.correlation_id).toBe('c1')
    expect(svar.status).toBe('ok')
    expect(svar.result).toEqual({ vaerktoej: 'phone_location', fik: { noejagtighed: 'high' } })
  })

  it('svarer også når handleren kaster — tavshed ville koste serveren en timeout', async () => {
    const s = fakeSocket()
    opretBro({
      ...GRUND,
      lavSocket: () => s,
      udfoer: async () => { throw new Error('kameraet er optaget') }
    }).start()
    s.onopen!()
    s.onmessage!({ data: JSON.stringify({ type: 'tool_invoke', correlation_id: 'c2', tool: 'phone_photo', args: {} }) })
    await new Promise((r) => setTimeout(r, 0))

    const svar = beskeder(s).find((b) => b.type === 'tool_result')
    expect(svar.status).toBe('error')
    expect(svar.error).toContain('kameraet er optaget')
    expect(svar.correlation_id).toBe('c2')
  })

  it('svarer på ping, så serveren ikke river forbindelsen ned som zombie', () => {
    const s = fakeSocket()
    opretBro({ ...GRUND, lavSocket: () => s }).start()
    s.onopen!()
    s.onmessage!({ data: JSON.stringify({ type: 'ping' }) })
    expect(beskeder(s).some((b) => b.type === 'pong')).toBe(true)
  })

  it('ignorerer vrøvl uden at vælte', () => {
    const s = fakeSocket()
    opretBro({ ...GRUND, lavSocket: () => s }).start()
    s.onopen!()
    expect(() => s.onmessage!({ data: 'ikke json' })).not.toThrow()
  })
})

describe('genforbindelse', () => {
  it('prøver igen når socket lukker — Android kapper den hver gang appen går i baggrunden', () => {
    const pauser: number[] = []
    const sockets: ReturnType<typeof fakeSocket>[] = []
    const bro = opretBro({
      ...GRUND,
      lavSocket: () => { const s = fakeSocket(); sockets.push(s); return s },
      planlaeg: (fn, ms) => { pauser.push(ms); fn(); return 0 }
    })
    bro.start()
    sockets[0]!.onclose!()
    sockets[1]!.onclose!()

    expect(pauser).toEqual([GENFORBIND_MS[0], GENFORBIND_MS[1]])
    expect(sockets.length).toBe(3)
  })

  it('pausen vokser men stopper — en telefon skal være tilbage inden for et halvt minut', () => {
    const pauser: number[] = []
    const sockets: ReturnType<typeof fakeSocket>[] = []
    opretBro({
      ...GRUND,
      lavSocket: () => { const s = fakeSocket(); sockets.push(s); return s },
      planlaeg: (fn, ms) => { pauser.push(ms); if (pauser.length < 10) fn(); return 0 }
    }).start()
    for (let i = 0; i < 9; i++) sockets[i]!.onclose!()

    expect(Math.max(...pauser)).toBe(30000)
  })

  it('stop() forhindrer genforbindelse — ellers ville en logget-ud app blive ved', () => {
    const sockets: ReturnType<typeof fakeSocket>[] = []
    const bro = opretBro({
      ...GRUND,
      lavSocket: () => { const s = fakeSocket(); sockets.push(s); return s },
      planlaeg: (fn) => { fn(); return 0 }
    })
    bro.start()
    bro.stop()
    sockets[0]!.onclose!()

    expect(sockets.length).toBe(1)
    expect(bro.erForbundet()).toBe(false)
  })

  it('nulstiller tælleren når registreringen lykkes', () => {
    const sockets: ReturnType<typeof fakeSocket>[] = []
    const bro = opretBro({
      ...GRUND,
      lavSocket: () => { const s = fakeSocket(); sockets.push(s); return s },
      planlaeg: (fn) => { fn(); return 0 }
    })
    bro.start()
    sockets[0]!.onclose!()
    expect(bro.forsoeg()).toBe(1)

    sockets[1]!.onopen!()
    sockets[1]!.onmessage!({ data: JSON.stringify({ type: 'registered' }) })
    expect(bro.forsoeg()).toBe(0)
    expect(bro.erForbundet()).toBe(true)
  })
})

describe('trafik-vagt', () => {
  /** En vagt man selv kan tikke, og et ur man selv kan flytte. */
  function medVagt() {
    let tik: (() => void) | null = null
    let tid = 0
    return {
      opsaetning: {
        planlaegVagt: (fn: () => void) => { tik = fn; return 1 },
        rydVagt: () => { tik = null },
        nu: () => tid
      },
      frem(ms: number) { tid += ms },
      tik() { tik?.() },
      lever() { return tik !== null }
    }
  }

  it('tvinger genforbindelse når intet er kommet ind i 75 sekunder', () => {
    // En halvåben socket: Android suspenderer den, serveren lukker efter tre
    // ubesvarede ping — men `onclose` kommer aldrig. Uden vagten sad klienten
    // og troede den var forbundet. Målt levetid-median: 99 sekunder.
    const s = fakeSocket()
    const v = medVagt()
    const pauser: number[] = []
    opretBro({
      ...GRUND, ...v.opsaetning, lavSocket: () => s,
      planlaeg: (fn, ms) => { pauser.push(ms); return 0 }
    }).start()
    s.onopen?.()
    v.frem(76_000)
    v.tik()
    expect(s.lukket).toBe(true)
    expect(pauser).toEqual([1000])
  })

  it('rører ikke en socket der stadig får trafik', () => {
    const s = fakeSocket()
    const v = medVagt()
    const pauser: number[] = []
    opretBro({
      ...GRUND, ...v.opsaetning, lavSocket: () => s,
      planlaeg: (fn, ms) => { pauser.push(ms); return 0 }
    }).start()
    s.onopen?.()
    v.frem(60_000)
    s.onmessage?.({ data: JSON.stringify({ type: 'ping' }) })  // livstegn
    v.frem(60_000)
    v.tik()
    expect(s.lukket).toBe(false)
    expect(pauser).toEqual([])
  })

  it('et ping ER trafik — ikke kun tool_invoke', () => {
    const s = fakeSocket()
    const v = medVagt()
    opretBro({ ...GRUND, ...v.opsaetning, lavSocket: () => s, planlaeg: () => 0 }).start()
    s.onopen?.()
    v.frem(70_000)
    s.onmessage?.({ data: JSON.stringify({ type: 'ping' }) })
    v.frem(70_000)
    v.tik()
    expect(s.lukket).toBe(false)
  })

  it('genforbinder KUN én gang selv om onclose kommer bagefter', () => {
    // Den halvåbne socket kan lukke sent. Uden spærren ville vagten og
    // `onclose` give to parallelle genforbindelser — to brorepræsentationer
    // af samme telefon.
    const s = fakeSocket()
    const v = medVagt()
    const pauser: number[] = []
    opretBro({
      ...GRUND, ...v.opsaetning, lavSocket: () => s,
      planlaeg: (fn, ms) => { pauser.push(ms); return 0 }
    }).start()
    s.onopen?.()
    v.frem(76_000)
    v.tik()
    s.onclose?.()
    expect(pauser).toEqual([1000])
  })

  it('stop() rydder vagten', () => {
    const s = fakeSocket()
    const v = medVagt()
    const bro = opretBro({ ...GRUND, ...v.opsaetning, lavSocket: () => s, planlaeg: () => 0 })
    bro.start()
    s.onopen?.()
    expect(v.lever()).toBe(true)
    bro.stop()
    expect(v.lever()).toBe(false)
  })
})
