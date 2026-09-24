import { describe, it, expect, vi, afterEach } from 'vitest'
import { hentGenoptagelsesVarsel } from './api'

/**
 * Varslet om et run der aldrig blev færdigt.
 *
 * Endpointet fandtes fra 17/9-2026 og havde NUL kaldere: desk kendte kun
 * `run_recovery` som et live SSE-event, så et run der blev opgivet mens ingen
 * så på fortalte aldrig nogen om det. Testene her holder de to ting fast der
 * gør hentningen forskellig fra et almindeligt GET.
 */
const cfg = { apiBaseUrl: 'http://x/', authToken: null }

afterEach(() => { vi.unstubAllGlobals() })

describe('hentGenoptagelsesVarsel', () => {
  it('giver null på 204 uden at kaste', async () => {
    // `apiFetch` kalder ellers `res.json()` på en TOM krop. Det kaster, og
    // fejlen ligner en netværksfejl — som så udløser netop den gentagelse
    // varslet ikke tåler.
    vi.stubGlobal('fetch', vi.fn(async () => new Response(null, { status: 204 })))
    expect(await hentGenoptagelsesVarsel(cfg, 'chat-1')).toBeNull()
  })

  it('henter varslet på 200', async () => {
    vi.stubGlobal('fetch', vi.fn(async () => new Response(JSON.stringify({
      task_id: 't1', state: 'failed_terminal',
      notice: { state: 'failed_terminal', reason: 'genoptagelses-vinduet udloeb',
                message: 'Opgaven naaede aldrig at blive genoptaget.', continuing: false },
    }), { status: 200, headers: { 'Content-Type': 'application/json' } })))
    const v = await hentGenoptagelsesVarsel(cfg, 'chat-1')
    expect(v?.notice.continuing).toBe(false)
    expect(v?.notice.message).toContain('aldrig')
  })

  it('gentager IKKE — serveren kvitterer varslet når det hentes', async () => {
    // Det her er den vigtigste: et gentaget kald ville ikke give det samme
    // svar to gange, det ville TABE varslet. `apiFetch` gentager ellers alle
    // GET'er to gange ved en 5xx.
    const f = vi.fn(async () => new Response('nej', { status: 503 }))
    vi.stubGlobal('fetch', f)
    await expect(hentGenoptagelsesVarsel(cfg, 'chat-1')).rejects.toThrow()
    expect(f).toHaveBeenCalledTimes(1)
  })

  it('spørger ikke uden en session', async () => {
    const f = vi.fn()
    vi.stubGlobal('fetch', f)
    expect(await hentGenoptagelsesVarsel(cfg, '')).toBeNull()
    expect(f).not.toHaveBeenCalled()
  })
})
