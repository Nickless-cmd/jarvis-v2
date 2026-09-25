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

// ── HVORNAAR der spoerges (25/9-2026) ────────────────────────────────────
//
// Fire gange har betingelsen vaeret forkert, og hver gang kunne fejlen kun
// ses ved at bygge programmet og vente. Maalt paa CT105 25/9: `POST
// /chat/warm` fyrede 22:49:31 da desk monterede, mens `GET .../recovery`
// ikke blev kaldt én eneste gang i de 11½ time der fulgte. De to effekter
// ligger ved siden af hinanden i samme komponent; forskellen var udelukkende
// betingelsen. Den bor nu her, hvor alle overgange kan proeves.
import { skalSpoergeOmVarsel } from './genoptagelsesVarsel'

describe('skalSpoergeOmVarsel', () => {
  const start = { forrige: '', sessionId: 's1', alleredeSpurgt: null }

  it('spoerger ved sessionsaabning uanset hvad stroemmen laver', () => {
    // DEN fejl der stod i produktion. `working` og `reconnecting` sprang fra,
    // og desk aabner netop ofte midt i et run — det er jo der der er noget at
    // fortaelle om.
    for (const status of ['idle', 'done', 'working', 'reconnecting', 'error', 'interrupted']) {
      expect(skalSpoergeOmVarsel({ ...start, status }).spoerg,
        `status=${status} blev sprunget over ved aabning`).toBe(true)
    }
  })

  it('spoerger ikke to gange for samme session', () => {
    // Varslet forbruges serverside naar det hentes. Et ekstra kald taber det.
    expect(skalSpoergeOmVarsel({
      forrige: 'idle', status: 'idle', sessionId: 's1', alleredeSpurgt: 's1',
    }).spoerg).toBe(false)
  })

  it('spoerger igen naar en tur slutter — ogsaa uden at se «working»', () => {
    // `useRammeReducer` samler opdateringer til én pr. frame, saa effekten ser
    // fx kun `idle -> done`. Betingelsen maa derfor vaere ANKOMSTEN i en
    // afsluttet tilstand, ikke afrejsen fra `working`.
    for (const status of ['done', 'interrupted', 'error']) {
      const b = skalSpoergeOmVarsel({
        forrige: 'idle', status, sessionId: 's1', alleredeSpurgt: 's1',
      })
      expect(b.nulstil, `${status} taeller ikke som en afsluttet tur`).toBe(true)
      expect(b.spoerg).toBe(true)
    }
  })

  it('en uaendret afsluttet status spoerger ikke igen', () => {
    // Ellers ville hver render i `done` hente — og forbruge — et varsel.
    expect(skalSpoergeOmVarsel({
      forrige: 'done', status: 'done', sessionId: 's1', alleredeSpurgt: 's1',
    })).toEqual({ spoerg: false, nulstil: false })
  })

  it('skifter man session, spoerges der for den nye', () => {
    expect(skalSpoergeOmVarsel({
      forrige: 'done', status: 'done', sessionId: 's2', alleredeSpurgt: 's1',
    }).spoerg).toBe(true)
  })

  it('uden session spoerges der ikke', () => {
    expect(skalSpoergeOmVarsel({
      forrige: '', status: 'idle', sessionId: null, alleredeSpurgt: null,
    }).spoerg).toBe(false)
  })
})
