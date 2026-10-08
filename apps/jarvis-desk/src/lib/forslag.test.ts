import { afterEach, describe, expect, it, vi } from 'vitest'
import { hentNaesteForslag, INTET_FORSLAG, meldValg } from './forslag'
import type { ApiConfig } from './api'

const cfg: ApiConfig = { apiBaseUrl: 'http://x', authToken: 't' }

afterEach(() => { vi.restoreAllMocks() })

function svar(krop: unknown, ok = true) {
  return vi.fn().mockResolvedValue({ ok, json: async () => krop } as unknown as Response)
}

// Svaret bærer siden 20/9-2026 også `forslag_id` og `kilde_besked_id` (fase
// 2): komponisten skal kunne melde tilbage hvad der skete med NETOP dette
// forslag. Uden id er der intet at melde — derfor er den tomme form et helt
// objekt og ikke en tom streng.

describe('hentNaesteForslag', () => {
  it('sender KUN sessionen — intet udkast — og bærer forslaget igennem', async () => {
    const f = svar({ forslag: 'deploy det til ct105' })
    vi.stubGlobal('fetch', f)
    expect(await hentNaesteForslag(cfg, 'sess-1')).toEqual({
      tekst: 'deploy det til ct105', id: '', kildeBeskedId: '' })
    const krop = JSON.parse((f.mock.calls[0]?.[1] as RequestInit).body as string)
    expect(krop).toEqual({ session_id: 'sess-1' })
  })

  it('spørger slet ikke uden en session — der er intet at bygge forslaget på', async () => {
    const f = svar({ forslag: 'noget' })
    vi.stubGlobal('fetch', f)
    expect(await hentNaesteForslag(cfg, '')).toEqual(INTET_FORSLAG)
    expect(f).not.toHaveBeenCalled()
  })

  it('trimmer — forslaget skal kunne stå hvor pladsholderen står', async () => {
    vi.stubGlobal('fetch', svar({ forslag: '  kør testene igen  ', forslag_id: 'cs-1', kilde_besked_id: 'm3' }))
    expect(await hentNaesteForslag(cfg, 's1')).toEqual({
      tekst: 'kør testene igen', id: 'cs-1', kildeBeskedId: 'm3' })
  })

  it('giver tom streng ved en fejlkode — komponisten skal kunne skrives i', async () => {
    vi.stubGlobal('fetch', svar({ forslag: 'x' }, false))
    expect(await hentNaesteForslag(cfg, 's1')).toEqual(INTET_FORSLAG)
  })

  it('giver tom streng når kaldet fejler', async () => {
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new Error('nede')))
    expect(await hentNaesteForslag(cfg, 's1')).toEqual(INTET_FORSLAG)
  })

  it('giver tom streng hvis serveren svarer med noget andet end en streng', async () => {
    vi.stubGlobal('fetch', svar({ forslag: { nej: 1 } }))
    expect(await hentNaesteForslag(cfg, 's1')).toEqual(INTET_FORSLAG)
  })

  it('udelader Authorization når der ikke er noget token', async () => {
    const f = svar({ forslag: '' })
    vi.stubGlobal('fetch', f)
    await hentNaesteForslag({ apiBaseUrl: 'http://x', authToken: '' }, 's1')
    const h = (f.mock.calls[0]?.[1] as RequestInit).headers as Record<string, string>
    expect(h.Authorization).toBeUndefined()
  })

  it('et forslag UDEN id kan stadig vises — det kan bare ikke meldes', async () => {
    // En ældre server svarer uden id'erne. Forslaget skal stadig frem; det er
    // valget der falder væk, ikke tilbuddet.
    vi.stubGlobal('fetch', svar({ forslag: 'kør testene igen' }))
    const f = await hentNaesteForslag(cfg, 's1')
    expect(f.tekst).toBe('kør testene igen')
    expect(f.id).toBe('')
  })

  it('bygger stien rigtigt når apiBaseUrl slutter på en skråstreg', async () => {
    // Målt 8/10-2026: desk gemmer `https://api.srvlab.dk/` (SetupScreen), og
    // strengsammensætning gav `//composer/suggest`. Den sti matcher ingen
    // API-rute, falder igennem til StaticFiles-mountet og svarer 405 — tavst,
    // fordi `!r.ok` giver INTET_FORSLAG uden at logge. Derfor nåede forslaget
    // kun mobilen, hvis base ikke har skråstregen.
    const f = svar({ forslag: 'x' })
    vi.stubGlobal('fetch', f)
    await hentNaesteForslag({ apiBaseUrl: 'https://api.srvlab.dk/', authToken: 't' }, 's1')
    expect(f.mock.calls[0]?.[0]).toBe('https://api.srvlab.dk/composer/suggest')
  })

  it('og når basen IKKE har skråstregen — begge konventioner skal virke', async () => {
    const f = svar({ forslag: 'x' })
    vi.stubGlobal('fetch', f)
    await hentNaesteForslag({ apiBaseUrl: 'https://api.srvlab.dk', authToken: 't' }, 's1')
    expect(f.mock.calls[0]?.[0]).toBe('https://api.srvlab.dk/composer/suggest')
  })
})

describe('meldValg', () => {
  const forslag = { tekst: 'kør testene igen', id: 'cs-9', kildeBeskedId: 'message-3' }

  it('sender forslagets EGNE ord og id\'erne — aldrig brugerens tekst', () => {
    const f = svar({ ok: true })
    vi.stubGlobal('fetch', f)
    meldValg(cfg, forslag, 'eget', 's1')
    const krop = JSON.parse((f.mock.calls[0]?.[1] as RequestInit).body as string)
    expect(krop).toEqual({
      forslag_id: 'cs-9', session_id: 's1', forslag: 'kør testene igen',
      kilde_besked_id: 'message-3', valg: 'eget',
    })
  })

  it('melder ikke uden id eller session — der er intet at pege på', () => {
    const f = svar({ ok: true })
    vi.stubGlobal('fetch', f)
    meldValg(cfg, INTET_FORSLAG, 'vist', 's1')
    meldValg(cfg, forslag, 'vist', '')
    expect(f).not.toHaveBeenCalled()
  })

  it('en fejl i meldingen kaster ikke — komponisten skriver videre', () => {
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new Error('nede')))
    expect(() => meldValg(cfg, forslag, 'accepteret', 's1')).not.toThrow()
  })

  it('melder til den rigtige sti — også med skråstreg i basen', () => {
    // Samme fejl som i `hentNaesteForslag`, samme dag: `valg`-telemetrien var
    // også død, fordi stien blev bygget med strengsammensætning.
    const f = svar({ ok: true })
    vi.stubGlobal('fetch', f)
    meldValg({ apiBaseUrl: 'https://api.srvlab.dk/', authToken: 't' }, forslag, 'accepteret', 's1')
    expect(f.mock.calls[0]?.[0]).toBe('https://api.srvlab.dk/composer/choice')
  })
})
