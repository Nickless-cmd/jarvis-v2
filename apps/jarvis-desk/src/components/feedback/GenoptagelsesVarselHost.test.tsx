import { describe, it, expect, vi } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import { GenoptagelsesVarselHost } from './GenoptagelsesVarselHost'
import { GenoptagelsesVarsel } from './GenoptagelsesVarsel'
import { SettingsProvider } from '../../contexts/SettingsContext'
import { StreamProvider } from '../../contexts/StreamContext'
import * as api from '../../lib/api'

/**
 * Varslet skal naa ham uanset hvilken flade han staar paa.
 *
 * 25/9-2026, den fjerde og rigtige aarsag. Spoergsmaalet laa i `ChatView`, og
 * `App` monterer kun én flade ad gangen:
 *
 *     {surface === 'chat' && <ChatView … />}
 *     {surface === 'code' && <CodeView … />}
 *
 * Maalt i den koerende renderer via fejlfindingsporten: `codeview-main` stod i
 * DOM'en, altsaa var `ChatView` — og dermed baade spoergsmaalet og banneret —
 * slet ikke paa skaermen. Endpointet blev ikke kaldt i 11½ time.
 *
 * Tre rettelser foer den gik til betingelsen inde i effekten, og de saa
 * rigtige ud hver gang, fordi nabo-effekten `warm` fyrede som ventet. `warm`
 * findes bare i BEGGE views. Den fyrede fra `CodeView`.
 *
 * Og testene kunne ikke fange det: de monterede `ChatView` direkte og sprang
 * dermed netop den flade-kontakt over der var i stykker. Derfor monterer
 * denne test INGEN flade — kun vaerten. Bestaar den, virker varslet ogsaa paa
 * en flade der ikke findes endnu.
 */
// Kun hentningen erstattes. Mocker man hele modulet, mangler de exports
// `StreamProvider` bruger — og fejlen ligner en fejl i det man tester.
vi.mock('../../lib/api', async (original) => ({
  ...(await original<typeof api>()),
  hentGenoptagelsesVarsel: vi.fn(),
}))

const cfg = { apiBaseUrl: 'http://x/', authToken: 'tok' }

const varsel = {
  task_id: 't1', run_id: 'r1', state: 'failed_terminal' as const,
  reason: 'opgivet efter aftale', recovery_attempt: 3, recovery_limit: 3,
  checkpoint_summary: '',
  notice: {
    state: 'failed_terminal', reason: 'opgivet efter aftale',
    message: 'Opgaven blev opgivet efter aftale. Skriv den igen hvis den stadig skal laves.',
    continuing: false,
  },
}

const vis = (sessionId: string | null) => render(
  <SettingsProvider initialConfig={cfg}>
    <StreamProvider config={cfg}>
      <GenoptagelsesVarselHost sessionId={sessionId} />
      <GenoptagelsesVarsel />
    </StreamProvider>
  </SettingsProvider>,
)

describe('GenoptagelsesVarselHost', () => {
  it('spoerger UDEN at nogen flade er monteret', async () => {
    // Kernen. Hverken ChatView eller CodeView er med her.
    vi.mocked(api.hentGenoptagelsesVarsel).mockResolvedValue(varsel)
    vis('s1')
    await waitFor(() => {
      expect(vi.mocked(api.hentGenoptagelsesVarsel)).toHaveBeenCalledWith(
        expect.objectContaining({ apiBaseUrl: 'http://x/' }), 's1')
    })
  })

  it('og viser varslet paa skaermen', async () => {
    vi.mocked(api.hentGenoptagelsesVarsel).mockResolvedValue(varsel)
    vis('s1')
    expect(await screen.findByText(/opgivet efter aftale/)).toBeInTheDocument()
  })

  it('uden session spoerges der ikke', async () => {
    vi.mocked(api.hentGenoptagelsesVarsel).mockClear()
    vi.mocked(api.hentGenoptagelsesVarsel).mockResolvedValue(null)
    vis(null)
    await new Promise((r) => setTimeout(r, 50))
    expect(vi.mocked(api.hentGenoptagelsesVarsel)).not.toHaveBeenCalled()
  })

  it('et tomt svar tegner intet banner', async () => {
    vi.mocked(api.hentGenoptagelsesVarsel).mockResolvedValue(null)
    const { container } = vis('s2')
    await new Promise((r) => setTimeout(r, 50))
    expect(container.querySelector('.recovery-notice')).toBeNull()
  })

  it('en fejl i hentningen vaelter ikke fladen', async () => {
    // Varslet er en hjaelp, ikke en forudsaetning. Kaster den, skal resten staa.
    vi.mocked(api.hentGenoptagelsesVarsel).mockRejectedValue(new Error('nede'))
    const { container } = vis('s3')
    await new Promise((r) => setTimeout(r, 50))
    expect(container.querySelector('.recovery-notice')).toBeNull()
  })
})
