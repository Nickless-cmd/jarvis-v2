import { render } from '@testing-library/react-native'
import { redeemPairingCode, hentKodeAdgang } from './apiClient'
import { errorDetail } from './streamClient'
import { KodeLaastBanner } from '../components/KodeLaastBanner'

/** Enheds-reglen på telefonen (19/9-2026). */
beforeEach(() => { global.fetch = jest.fn() })

it('parringen sender telefonens navn og platform', async () => {
  ;(global.fetch as jest.Mock).mockResolvedValue({ json: async () => ({ status: 'ok', token: 't' }) })
  await redeemPairingCode('https://api.x/', 'kode1', { navn: 'Pixel 9 (Android)', platform: 'android' })
  expect(JSON.parse((global.fetch as jest.Mock).mock.calls[0][1].body)).toEqual({ code: 'kode1', navn: 'Pixel 9 (Android)', platform: 'android' })
})

it('en 403 med forklaring bliver forklaringen — ikke «http=403»', () => {
  expect(errorDetail({ type: 'error', xhrStatus: 403, message: JSON.stringify({ detail: 'Code mode kræver at denne enhed er tilføjet i desk.' }) }))
    .toBe('Code mode kræver at denne enhed er tilføjet i desk.')
  expect(errorDetail({ type: 'error', xhrStatus: 500, message: 'boom' })).toBe('error · http=500 · boom')
})

it('hentKodeAdgang læser reglen og om DENNE telefon må — og er «ved ikke» ved fejl', async () => {
  ;(global.fetch as jest.Mock).mockResolvedValue({ ok: true, status: 200, json: async () => ({ kraev_aktivt: true, denne: { kode_tilladt: false } }) })
  expect(await hentKodeAdgang({ apiBaseUrl: 'https://api.x/', authToken: 't' })).toEqual({ kraevAktivt: true, kodeTilladt: false })
  ;(global.fetch as jest.Mock).mockRejectedValue(new Error('net'))
  expect(await hentKodeAdgang({ apiBaseUrl: 'https://api.x/', authToken: 't' })).toBeNull()
})

it('banneret siger hvor man tilføjer telefonen — og vises kun når den er låst', async () => {
  const a = await render(<KodeLaastBanner vis />)
  expect(a.getByText(/Indstillinger → Konto → Enheder/)).toBeTruthy()
  const b = await render(<KodeLaastBanner vis={false} />)
  expect(b.queryByTestId('kode-laast')).toBeNull()
})
