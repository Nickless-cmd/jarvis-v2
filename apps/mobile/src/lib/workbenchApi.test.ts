import { fetchOperatorChannel, lukOperatorChannel } from './workbenchApi'
import { apiFetch } from './apiClient'

jest.mock('./apiClient', () => ({
  apiFetch: jest.fn(async () => ({ open: false })),
}))

const cfg = { apiBaseUrl: 'http://x', authToken: 't' } as never

describe('operator-kanalen: session-id skal med', () => {
  beforeEach(() => jest.clearAllMocks())

  // Målt 7/10-2026: telefonen sendte INTET id, så den ramte nøglen `_default`
  // — mens bash bruger `chat-<session>`. «Luk» på telefonen rørte derfor en
  // kanal bash aldrig så. Serveren afviser nu et kald uden id med 400.
  it('læsningen bærer session-id i forespørgslen', async () => {
    await fetchOperatorChannel(cfg, 'chat-abc')
    expect(apiFetch).toHaveBeenCalledWith(cfg, '/workbench/operator-channel?session_id=chat-abc')
  })

  it('lukningen bærer session-id i kroppen', async () => {
    await lukOperatorChannel(cfg, 'chat-abc')
    expect(apiFetch).toHaveBeenCalledWith(cfg, '/workbench/operator-channel/close', {
      method: 'POST',
      body: { session_id: 'chat-abc' },
    })
  })

  it('et id med specialtegn kodes, så det ikke splitter forespørgslen', async () => {
    await fetchOperatorChannel(cfg, 'chat-a&b=c')
    expect(apiFetch).toHaveBeenCalledWith(
      cfg,
      '/workbench/operator-channel?session_id=chat-a%26b%3Dc',
    )
  })

  // Uden id sendes kaldet stadig — men uden nøgle. Serveren svarer 400, og
  // det er meningen: et kald uden id må ikke skrive en nøgle ingen bruger.
  it('uden id sendes ingen session_id — serveren afviser den', async () => {
    await fetchOperatorChannel(cfg)
    expect(apiFetch).toHaveBeenCalledWith(cfg, '/workbench/operator-channel')
    await lukOperatorChannel(cfg)
    expect(apiFetch).toHaveBeenCalledWith(cfg, '/workbench/operator-channel/close', {
      method: 'POST',
      body: {},
    })
  })
})
