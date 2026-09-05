import { fetchMemoryOverview, memorySectionsFromMarkdown } from './memoryApi'
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
