import { afterEach, describe, expect, it, vi } from 'vitest'
import { hentNaesteForslag } from './forslag'
import type { ApiConfig } from './api'

const cfg: ApiConfig = { apiBaseUrl: 'http://x', authToken: 't' }

afterEach(() => { vi.restoreAllMocks() })

function svar(krop: unknown, ok = true) {
  return vi.fn().mockResolvedValue({ ok, json: async () => krop } as unknown as Response)
}

describe('hentNaesteForslag', () => {
  it('sender samtalen — ikke et udkast — og bærer forslaget igennem', async () => {
    const f = svar({ forslag: 'deploy det til ct105' })
    vi.stubGlobal('fetch', f)
    expect(await hentNaesteForslag(cfg, 'sess-1')).toBe('deploy det til ct105')
    const krop = JSON.parse((f.mock.calls[0]?.[1] as RequestInit).body as string)
    expect(krop).toEqual({ udkast: '', session_id: 'sess-1' })
  })

  it('spørger slet ikke uden en session — der er intet at bygge forslaget på', async () => {
    const f = svar({ forslag: 'noget' })
    vi.stubGlobal('fetch', f)
    expect(await hentNaesteForslag(cfg, '')).toBe('')
    expect(f).not.toHaveBeenCalled()
  })

  it('trimmer — forslaget skal kunne stå hvor pladsholderen står', async () => {
    vi.stubGlobal('fetch', svar({ forslag: '  kør testene igen  ' }))
    expect(await hentNaesteForslag(cfg, 's1')).toBe('kør testene igen')
  })

  it('giver tom streng ved en fejlkode — komponisten skal kunne skrives i', async () => {
    vi.stubGlobal('fetch', svar({ forslag: 'x' }, false))
    expect(await hentNaesteForslag(cfg, 's1')).toBe('')
  })

  it('giver tom streng når kaldet fejler', async () => {
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new Error('nede')))
    expect(await hentNaesteForslag(cfg, 's1')).toBe('')
  })

  it('giver tom streng hvis serveren svarer med noget andet end en streng', async () => {
    vi.stubGlobal('fetch', svar({ forslag: { nej: 1 } }))
    expect(await hentNaesteForslag(cfg, 's1')).toBe('')
  })

  it('udelader Authorization når der ikke er noget token', async () => {
    const f = svar({ forslag: '' })
    vi.stubGlobal('fetch', f)
    await hentNaesteForslag({ apiBaseUrl: 'http://x', authToken: '' }, 's1')
    const h = (f.mock.calls[0]?.[1] as RequestInit).headers as Record<string, string>
    expect(h.Authorization).toBeUndefined()
  })
})
