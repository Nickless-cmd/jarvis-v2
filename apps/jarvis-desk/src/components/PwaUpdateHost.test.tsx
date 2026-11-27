import { describe, it, expect } from 'vitest'
import { erTurAktiv } from './PwaUpdateHost'
import type { StreamStatus } from '../lib/streamReducer'

/**
 * Opdateringsknappen må ikke kunne blive permanent skjult.
 *
 * ## Fejlen der blev målt (27/11-2026)
 *
 * `PwaRunUpdateHost` regnede «kører der en tur?» som
 *
 *     status === 'working' || Boolean(activeRunId)
 *
 * `activeRunId` er en IDENTITET, ikke en aktivitet. Den sættes ved
 * `message_start` og nulstilles FØRST ved næste tur — `message_stop` lader
 * den stå (se `streamReducer`). Efter den første afsluttede tur var `busy`
 * derfor sand for altid, knappen blev aldrig vist, og den ventende service
 * worker blev aldrig frigivet med `SKIP_WAITING`.
 *
 * Konsekvensen var ikke kosmetisk: Bjørn genindlæste PWA'en gentagne gange
 * og blev ved med at køre 0.6.442, selv om serveren sendte 0.6.443.
 *
 * ## Hvad testen værner
 *
 * At beslutningen udelukkende hviler på `status`. Modprøven nedenfor er den
 * gamle formel: den skal give `true` på netop det input hvor den nye giver
 * `false`, ellers måler testen ingenting.
 */
describe('erTurAktiv — «kører der en tur nu?»', () => {
  it('en AFSLUTTET tur er ikke aktiv, uanset at run-id stadig står', () => {
    // Kernen i fejlen: status er terminal, men `activeRunId` er stadig sat.
    // Den gamle formel svarede «travl» her, og det var derfor knappen forsvandt.
    expect(erTurAktiv('done')).toBe(false)

    // Modprøve — den gamle formel på samme input. Ville give true, altså
    // skjule knappen. Står her så testen beviser at den måler forskellen.
    const gammelFormel = (status: StreamStatus, activeRunId: string | null) =>
      status === 'working' || Boolean(activeRunId)
    expect(gammelFormel('done', 'run-1')).toBe(true)
  })

  it('kørende og genopkoblende ture er aktive', () => {
    expect(erTurAktiv('working')).toBe(true)
    // `reconnecting` betyder at turen stadig løber — et genindlæs ville afbryde den.
    expect(erTurAktiv('reconnecting')).toBe(true)
  })

  it('ingen terminal tilstand er aktiv', () => {
    const terminale: StreamStatus[] = ['idle', 'done', 'interrupted', 'hung', 'error']
    for (const status of terminale) expect(erTurAktiv(status), status).toBe(false)
  })
})
