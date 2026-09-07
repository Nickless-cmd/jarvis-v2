import { fetchMemoryOverview, gemSomHukommelse, memorySectionsFromMarkdown } from './memoryApi'
import type { ApiConfig } from './types'

const config: ApiConfig = { apiBaseUrl: 'https://api.srvlab.dk/', authToken: 'token' }

beforeEach(() => {
  global.fetch = jest.fn()
})

it('henter self-scoped memory overview fra account-endpointet', async () => {
  ;(global.fetch as jest.Mock).mockResolvedValue({
    ok: true,
    status: 200,
    json: async () => ({
      memory_md: '## Preferencer\n- Kaffe sort',
      user_md: '# Bjørn\nBor i Svendborg',
      recent_sensory: [{ description: 'Lyset var tændt', captured_at: '2026-09-05T10:00:00Z' }],
      brain_count: 42
    })
  })

  const res = await fetchMemoryOverview(config)

  expect((global.fetch as jest.Mock).mock.calls[0][0]).toContain('/account/memory')
  expect(res.sections[0]).toMatchObject({ title: 'Preferencer', preview: 'Kaffe sort' })
  expect(res.identityPreview).toContain('Bjørn')
  expect(res.brainCount).toBe(42)
  expect(res.recentSenses).toHaveLength(1)
})

it('deler markdown op i overskrifter og renser punkttegn', () => {
  expect(memorySectionsFromMarkdown('## Mad\n- Kan lide ramen\n## Arbejde\nHolder branches adskilt')).toEqual([
    { title: 'Mad', preview: 'Kan lide ramen' },
    { title: 'Arbejde', preview: 'Holder branches adskilt' }
  ])
})

it('returnerer tomt overview når endpointet fejler', async () => {
  ;(global.fetch as jest.Mock).mockResolvedValue({ ok: false, status: 500, json: async () => ({}) })
  await expect(fetchMemoryOverview(config)).resolves.toMatchObject({
    sections: [],
    identityPreview: '',
    brainCount: 0,
    recentSenses: []
  })
})

describe('gemSomHukommelse', () => {
  const cfg = { apiBaseUrl: 'https://api.test', authToken: 't' } as any
  afterEach(() => { (global.fetch as any) = undefined })

  it('nægter at sende tom tekst — et tomt kald er ikke en hukommelse', async () => {
    const spy = jest.fn()
    global.fetch = spy as any
    const r = await gemSomHukommelse(cfg, '   ')
    expect(r.ok).toBe(false)
    expect(spy).not.toHaveBeenCalled()
  })

  it('sender tekst og session til /mobile/memory', async () => {
    const spy = jest.fn().mockResolvedValue({ ok: true, json: async () => ({}) })
    global.fetch = spy as any
    const r = await gemSomHukommelse(cfg, 'noget værd at huske', 's1')
    expect(r.ok).toBe(true)
    const [url, init] = spy.mock.calls[0]
    expect(url).toBe('https://api.test/mobile/memory')
    expect(JSON.parse(init.body)).toEqual({ text: 'noget værd at huske', session_id: 's1' })
  })

  it('viser serverens status frem for at tie', async () => {
    global.fetch = jest.fn().mockResolvedValue({ ok: false, status: 502 }) as any
    const r = await gemSomHukommelse(cfg, 'x')
    expect(r).toEqual({ ok: false, besked: 'Kunne ikke gemme (502).' })
  })

  it('siger det ligeud når nettet er væk', async () => {
    global.fetch = jest.fn().mockRejectedValue(new Error('offline')) as any
    const r = await gemSomHukommelse(cfg, 'x')
    expect(r.ok).toBe(false)
    expect(r.besked).toMatch(/forbindelse/)
  })
})
