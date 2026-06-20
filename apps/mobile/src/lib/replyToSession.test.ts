import { replyToSession } from './replyToSession'

const cfg = { apiBaseUrl: 'https://api.srvlab.dk/', authToken: 'tok' }

it('POSTer beskeden til /chat/stream/v2 med auth + body', async () => {
  const fetchMock = jest.fn(async () => ({ ok: true }))
  global.fetch = fetchMock as unknown as typeof fetch
  const ok = await replyToSession(cfg, 's1', 'hej')
  expect(ok).toBe(true)
  const [url, init] = fetchMock.mock.calls[0] as unknown as [string, RequestInit]
  expect(url).toBe('https://api.srvlab.dk/chat/stream/v2')
  expect(init.method).toBe('POST')
  expect((init.headers as Record<string, string>).Authorization).toBe('Bearer tok')
  const parsed = JSON.parse(init.body as string)
  expect(parsed.message).toBe('hej')
  expect(parsed.session_id).toBe('s1')
})

it('returnerer false ved tom tekst eller manglende session', async () => {
  expect(await replyToSession(cfg, '', 'hej')).toBe(false)
  expect(await replyToSession(cfg, 's1', '   ')).toBe(false)
})

it('returnerer false ved fetch-fejl', async () => {
  global.fetch = jest.fn(async () => {
    throw new Error('net')
  }) as unknown as typeof fetch
  expect(await replyToSession(cfg, 's1', 'hej')).toBe(false)
})
