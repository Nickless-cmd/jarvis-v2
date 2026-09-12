import { hentSessionBilleder, billedUrl } from './billederApi'
import * as api from './apiClient'

const config = { apiBaseUrl: 'https://api.srvlab.dk/', authToken: 't' } as never

// UDEN denne husker spionen kaldene fra forrige test: jest.spyOn genbruger
// samme objekt, saa mock.calls[0] var en anden tests kald. Testen bestod paa
// det forkerte grundlag.
beforeEach(() => jest.restoreAllMocks())

it('skelner Jarvis egne billeder fra dem man selv sendte', async () => {
  // «Har han lavet det, eller sendte jeg det?» er det foerste man vil vide
  // naar man ser billedet igen uger senere.
  jest.spyOn(api, 'apiFetch').mockResolvedValue({
    items: [
      { attachment_id: 'a', session_id: 's1', filename: 'x.jpg', channel_type: 'generated' },
      { attachment_id: 'b', session_id: 's1', filename: 'y.jpg', channel_type: 'chat' },
    ],
  } as never)
  const r = await hentSessionBilleder(config, 's1')
  expect(r.map((b) => b.lavetAfJarvis)).toEqual([true, false])
})

it('en raekke UDEN id kastes vaek frem for at blive et tomt felt', async () => {
  jest.spyOn(api, 'apiFetch').mockResolvedValue({
    items: [{ filename: 'uden-id.jpg' }, { attachment_id: 'a' }],
  } as never)
  expect((await hentSessionBilleder(config, 's1')).map((b) => b.attachmentId)).toEqual(['a'])
})

it('sessionen kommer MED i kaldet', async () => {
  // Uden den ville skaermen vise hele historikken og hedde «Billeder i denne
  // samtale».
  const spion = jest.spyOn(api, 'apiFetch').mockResolvedValue({ items: [] } as never)
  await hentSessionBilleder(config, 's1')
  expect(String(spion.mock.calls[0]?.[1])).toContain('session_id=s1')
})

it('en TOM session sender ingen filter-parameter', async () => {
  const spion = jest.spyOn(api, 'apiFetch').mockResolvedValue({ items: [] } as never)
  await hentSessionBilleder(config, '')
  expect(String(spion.mock.calls[0]?.[1])).not.toContain('session_id')
})

it('billeder hentes over den HISTORISKE rute', () => {
  // /attachments/{id} kender kun den aktuelle sessions registry og fejler paa
  // alt aeldre; /attachments/image/{id} slaar op i databasen.
  expect(billedUrl(config, 'abc')).toBe('https://api.srvlab.dk/attachments/image/abc')
})
