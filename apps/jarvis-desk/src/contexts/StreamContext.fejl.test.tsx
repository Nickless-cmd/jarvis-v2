/**
 * Fejl-banneret skal sige HVAD der gik galt (Bjørn 4/10-2026).
 *
 * «hvis desk mister forbindelsen vises denne over composer: network error og
 * kryds til at trykke — network error kan være meget, den er nødt til at vise
 * en fejl.»
 *
 * To fund bag den sætning:
 *
 * 1. `approve`/`deny` satte KUN den rå `Error`, hvis tekst kommer fra
 *    browseren («Failed to fetch»). Banneret fik ingen alvorlighed, intet
 *    fix-hint og intet «Prøv igen».
 * 2. CodeView rendrede den rå `stream.error` i stedet for den strukturerede
 *    `streamError` — og krydset var en tom funktion med en kommentar. Samme
 *    no-op blev rettet i ChatView 23/6-2026 og aldrig her.
 */
import { describe, it, expect } from 'vitest'
import { handlingTilInfo } from './StreamContext'

describe('en handling der fejlede', () => {
  it('navngiver HANDLINGEN foerst, ikke transporten', () => {
    const i = handlingTilInfo('Kunne ikke godkende værktøjet', new Error('Failed to fetch'))
    expect(i.message).toContain('Kunne ikke godkende værktøjet')
    // «network error» alene siger intet om hvad man forsoegte.
    expect(i.message).not.toBe('Failed to fetch')
  })

  it('BEVARER den raa aarsag i fix-hintet', () => {
    // Den er det eneste der kan skelne «serveren er nede» fra «tokenet er
    // udloebet» naar noget skal fejlfindes.
    const i = handlingTilInfo('Kunne ikke afvise værktøjet', new Error('Failed to fetch'))
    expect(i.fixHint).toContain('Failed to fetch')
  })

  it('kender forskel paa en forbindelses-fejl og en server-fejl', () => {
    const net = handlingTilInfo('X', new Error('Failed to fetch'))
    expect(net.code).toBe('network')
    expect(net.message).toContain('ingen forbindelse')

    const svr = handlingTilInfo('X', new Error('500 Internal Server Error'))
    expect(svr.code).toBe('unknown')
    expect(svr.message).toContain('svarede ikke som forventet')
  })

  it('er altid gen-proevelig — ellers staar han med et kryds og intet andet', () => {
    expect(handlingTilInfo('X', new Error('hvadsomhelst')).retryable).toBe(true)
  })

  it('taaler noget der ikke er en Error', () => {
    const i = handlingTilInfo('X', undefined)
    expect(i.message).toContain('X')
    expect(i.fixHint).toBe('Prøv igen.')
  })
})

describe('bannerets kaldesteder', () => {
  // Kilde-vagt frem for en montering: at rendre CodeView kraever hele dens
  // mock-landskab for at maale fire props. Det der GIK galt to gange er
  // praecis synligt i kilden — et kryds uden `clearError` og en raa `error`
  // i stedet for den strukturerede.
  const kilde = (f: string) =>
    // Lazy require med vilje: filen koerer i jsdom, og en top-level ESM-import
    // af node:fs ville blive evalueret ved modul-load i det miljoe.
    // 4/10-2026: her stod reglen `no-var-requires` — den GAMLE regel, som ikke
    // rammer `require()` brugt som udtryk. Derfor virkede disablen ikke, og CI
    // faldt paa `no-require-imports`. Det er den regel der skal navngives.
    // eslint-disable-next-line @typescript-eslint/no-require-imports
    (require('node:fs') as typeof import('node:fs'))
      .readFileSync(`src/views/${f}`, 'utf-8')

  const banner = (f: string) => {
    const s = kilde(f)
    const i = s.indexOf('<ErrorBanner')
    expect(i).toBeGreaterThan(-1)
    return s.slice(i, s.indexOf('/>', i) + 2)
  }

  it.each(['ChatView.tsx', 'CodeView.tsx'])('%s lukker FAKTISK banneret', (f) => {
    // Bjoern 23/6-2026: «X-knappen paa fejl-banneret var en no-op.» Rettet i
    // ChatView dengang, og CodeView havde stadig
    // `onDismiss={() => { /* ryddes ved naeste send */ }}` 4/10.
    //
    // Maalt paa netop DEN prop, ikke paa hele banneret: foerste udgave ledte
    // efter `clearError()` hvor som helst, og den staar ogsaa i «Proev
    // igen»-handleren — saa en mutation der satte krydset tilbage til en
    // no-op bestod. Vagten maalte ikke det den paastod.
    const b = banner(f)
    const i = b.indexOf('onDismiss')
    expect(i).toBeGreaterThan(-1)
    // Frem til naeste prop paa samme niveau.
    const prop = b.slice(i, b.indexOf('\n', i + 1))
    expect(prop).toContain('clearError()')
  })

  it.each(['ChatView.tsx', 'CodeView.tsx'])('%s viser den STRUKTUREREDE fejl', (f) => {
    const b = banner(f)
    expect(b).toContain('streamError')
    expect(b).toContain('fixHint')
    expect(b).toContain('severity')
  })

  it.each(['ChatView.tsx', 'CodeView.tsx'])('%s tilbyder «Proev igen»', (f) => {
    expect(banner(f)).toContain('onRetry')
  })
})
