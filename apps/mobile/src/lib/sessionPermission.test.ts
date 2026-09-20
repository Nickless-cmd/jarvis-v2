import { hentSessionPermission, saetSessionPermission } from './sessionPermission'
import * as api from './apiClient'

const config = { apiBaseUrl: 'https://api.srvlab.dk/', authToken: 't' } as never

beforeEach(() => jest.restoreAllMocks())

it('laeser samtalens niveau fra serveren — ikke fra telefonen', async () => {
  // Det er hele pointen (20/9-2026): stod desk paa fuld adgang, skal telefonen
  // vise det samme. Foer havde hver klient sit eget svar.
  jest.spyOn(api, 'apiFetch').mockResolvedValue({ approval_mode: 'trust' } as never)
  expect(await hentSessionPermission(config, 's1')).toBe('trust')
})

it('et ukendt svar falder tilbage til den SIKRE vej', async () => {
  // En tavs eller fordrejet server maa ikke give fuld adgang ved et uheld.
  jest.spyOn(api, 'apiFetch').mockResolvedValue({ noget: 'andet' } as never)
  expect(await hentSessionPermission(config, 's1')).toBe('ask')
  jest.spyOn(api, 'apiFetch').mockResolvedValue({} as never)
  expect(await hentSessionPermission(config, 's1')).toBe('ask')
})

it('skriver til samtalens permission-rute med niveauet i kroppen', async () => {
  const spion = jest.spyOn(api, 'apiFetch').mockResolvedValue({ approval_mode: 'trust' } as never)
  await saetSessionPermission(config, 's1', 'trust')
  const [kaldConfig, sti, valg] = spion.mock.calls[0] ?? []
  expect(kaldConfig).toBe(config)
  expect(String(sti)).toContain('/chat/sessions/s1/permission')
  expect((valg as { method?: string })?.method).toBe('POST')
  expect((valg as { body?: unknown })?.body).toEqual({ approval_mode: 'trust' })
})

it('returnerer SERVERENS svar — ikke det vi bad om', async () => {
  // Serveren er kilden. Afviser den skiftet, skal klienten se det, ikke tro
  // at valget gik igennem.
  jest.spyOn(api, 'apiFetch').mockResolvedValue({ approval_mode: 'ask' } as never)
  expect(await saetSessionPermission(config, 's1', 'trust')).toBe('ask')
})
