/**
 * Auto-forslaget i komponisten (Bjørn 17/9-2026).
 *
 * Kravet med hans egne ord: standardteksten er «Bed om hvad som helst»; har
 * auto-forslaget et bud, ERSTATTER det den tekst; Tab gør det grå til rigtig
 * tekst i feltet, og Enter sender. Og — det der var galt med den første
 * udgave — forslaget må IKKE komme dumpende mens han skriver.
 *
 * Testene her holder præcis de fire ting fast, fordi de er hele forskellen
 * mellem et tilbud og en afbrydelse.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor, act } from '@testing-library/react'

vi.mock('../../lib/api', async () => {
  const ægte = await vi.importActual<Record<string, unknown>>('../../lib/api')
  return { ...ægte, apiFetch: vi.fn().mockResolvedValue({}), uploadAttachment: vi.fn() }
})

import { Composer } from './Composer'
import { PermissionProvider } from '../../contexts/PermissionContext'

const cfg = { apiBaseUrl: 'http://x', authToken: 't' }

const opsæt = (props: Record<string, unknown> = {}) => {
  const onSend = vi.fn()
  render(
    <PermissionProvider>
      <Composer
        streaming={false} onSend={onSend} onStop={vi.fn()} model="m"
        config={cfg} showPermissions={false} getSessionId={async () => 's1'}
        sessionId="s1" {...props}
      />
    </PermissionProvider>,
  )
  return { onSend, felt: screen.getByRole('textbox') as HTMLTextAreaElement }
}

/** Serveren svarer med ét forslag; alt andet svarer tomt. Returnerer
 *  fetch-spionen, så valgene (fase 2) kan aflæses i de kald der blev sendt. */
function serverForeslaar(forslag: string) {
  const kald = vi.fn(async (url: string, _init?: RequestInit) => ({
    ok: true,
    json: async () => (String(url).includes('/composer/suggest')
      ? { forslag, forslag_id: forslag ? 'cs-42' : '', kilde_besked_id: 'message-7' }
      : {}),
  } as unknown as Response))
  vi.stubGlobal('fetch', kald)
  return kald
}

/** De valg der faktisk blev meldt til serveren, i rækkefølge. */
function meldteValg(kald: ReturnType<typeof serverForeslaar>): string[] {
  return kald.mock.calls
    .filter((c) => String(c[0]).includes('/composer/choice'))
    .map((c) => JSON.parse(String((c[1] as RequestInit).body)).valg as string)
}

/** De meldte valg som et SÆT — rækkefølgen er ikke en kontrakt.
 *
 *  «vist» meldes fra en `useEffect` på `ghostAktiv`; «afvist»/«eget»/
 *  «accepteret» meldes synkront fra tastetrykket. Begge er fire-and-forget.
 *  Lokalt har effekten altid nået at køre først, men på CI (20/9-2026) kom
 *  `['afvist','vist']` — vinduet mellem at teksten står i DOM'en og at den
 *  passive effekt er flushet, er bredere under belastning.
 *
 *  Koden lover ikke en rækkefølge: serveren stempler hvert valg for sig. Så
 *  testen skal måle HVAD der blev meldt, ikke i hvilken orden de to ramte
 *  mock'en. Antallet holdes fast, så et dobbelt-meldt valg stadig falder. */
function meldteSaet(kald: ReturnType<typeof serverForeslaar>): string[] {
  return [...meldteValg(kald)].sort()
}

/** Kroppen af det FØRSTE valg-kald. */
function foersteValgKrop(kald: ReturnType<typeof serverForeslaar>): Record<string, unknown> {
  const c = kald.mock.calls.find((k) => String(k[0]).includes('/composer/choice'))
  return JSON.parse(String((c?.[1] as RequestInit).body))
}

describe('Composer · auto-forslag', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
    serverForeslaar('')
  })

  it('standardteksten er «Bed om hvad som helst»', () => {
    const { felt } = opsæt()
    expect(felt.placeholder).toBe('Bed om hvad som helst')
  })

  it('et forslag ERSTATTER standardteksten', async () => {
    serverForeslaar('deploy det til ct105')
    const { felt } = opsæt()
    expect(await screen.findByText('deploy det til ct105')).toBeTruthy()
    // Ellers ville de to skrive oven i hinanden — forslaget står præcis hvor
    // pladsholderen står.
    expect(felt.placeholder).toBe('')
  })

  it('Tab gør det grå til rigtig tekst, og Enter sender den', async () => {
    serverForeslaar('kør testene igen')
    const { felt, onSend } = opsæt()
    await screen.findByText('kør testene igen')

    fireEvent.keyDown(felt, { key: 'Tab' })
    await waitFor(() => expect(felt.value).toBe('kør testene igen'))
    // Nu er det hans egen tekst — ikke længere et forslag der står og venter.
    expect(screen.queryByText('Tab')).toBeNull()

    fireEvent.keyDown(felt, { key: 'Enter' })
    expect(onSend).toHaveBeenCalledWith('kør testene igen', expect.anything())
  })

  it('Escape afviser forslaget, og standardteksten kommer tilbage', async () => {
    serverForeslaar('deploy det til ct105')
    const { felt } = opsæt()
    await screen.findByText('deploy det til ct105')
    fireEvent.keyDown(felt, { key: 'Escape' })
    await waitFor(() => expect(felt.placeholder).toBe('Bed om hvad som helst'))
    expect(screen.queryByText('deploy det til ct105')).toBeNull()
  })

  it('forslaget kommer IKKE dumpende mens han skriver', async () => {
    serverForeslaar('deploy det til ct105')
    const { felt } = opsæt()
    await screen.findByText('deploy det til ct105')
    await act(async () => {
      fireEvent.change(felt, { target: { value: 'kan du lige', selectionStart: 11 } })
    })
    // Feltet er ikke tomt længere → forslaget er væk af sig selv. Det er DET
    // der var galt før: den grå tekst blev stående og konkurrerede med hans
    // egne ord.
    expect(screen.queryByText('deploy det til ct105')).toBeNull()
  })

  it('Tab flytter fokus som normalt når der ikke ER et forslag', async () => {
    const { felt } = opsæt()
    const e = fireEvent.keyDown(felt, { key: 'Tab' })
    expect(e).toBe(true)   // ikke preventDefault'et
    expect(felt.value).toBe('')
  })

  it('spørger slet ikke mens et svar streamer — samme GPU som det synlige svar', async () => {
    const f = vi.fn(async (_url: string) => ({ ok: true, json: async () => ({ forslag: 'x' }) } as unknown as Response))
    vi.stubGlobal('fetch', f)
    opsæt({ streaming: true })
    await new Promise((r) => setTimeout(r, 900))
    const suggest = f.mock.calls.filter((c) => String(c[0] ?? '').includes('/composer/suggest'))
    expect(suggest).toHaveLength(0)
  })

  // ── valget (fase 2, 20/9-2026) ─────────────────────────────────────────
  //
  // Bjørn: «vi skal gemme brugerens valg, dvs. om de brugte den suggested
  // (tab) i composer eller skrev der egen besked så næste forslag bliver mere
  // mig/målrettet». Det farligste her er ikke et tabt valg — det er at hans
  // egen tekst skulle snige sig med i kaldet.

  it('et vist forslag meldes som VIST, med beskeden det kom af', async () => {
    const kald = serverForeslaar('kør testene igen')
    opsæt()
    await screen.findByText('kør testene igen')
    await waitFor(() => expect(meldteValg(kald)).toEqual(['vist']))
    expect(foersteValgKrop(kald)).toMatchObject({
      forslag_id: 'cs-42',
      session_id: 's1',
      forslag: 'kør testene igen',
      kilde_besked_id: 'message-7',
      valg: 'vist',
    })
  })

  it('Tab melder ACCEPTERET', async () => {
    const kald = serverForeslaar('kør testene igen')
    const { felt } = opsæt()
    await screen.findByText('kør testene igen')
    fireEvent.keyDown(felt, { key: 'Tab' })
    await waitFor(() => expect(meldteSaet(kald)).toEqual(['accepteret', 'vist']))
  })

  it('Escape melder AFVIST', async () => {
    const kald = serverForeslaar('deploy det til ct105')
    const { felt } = opsæt()
    await screen.findByText('deploy det til ct105')
    fireEvent.keyDown(felt, { key: 'Escape' })
    await waitFor(() => expect(meldteSaet(kald)).toEqual(['afvist', 'vist']))
  })

  it('skriver han sin EGEN besked, meldes eget — og teksten følger ikke med', async () => {
    const kald = serverForeslaar('kør testene igen')
    const { felt } = opsæt()
    await screen.findByText('kør testene igen')

    fireEvent.change(felt, { target: { value: 'nej, vent med testene' } })
    fireEvent.keyDown(felt, { key: 'Enter' })

    await waitFor(() => expect(meldteSaet(kald)).toEqual(['eget', 'vist']))
    // Hele trafikken gennemsøges: hans sætning må ikke stå i NOGEN krop.
    const alt = JSON.stringify(kald.mock.calls.filter((c) => String(c[0]).includes('/composer/')))
    expect(alt).not.toContain('nej, vent med testene')
  })

  it('tog han forslaget, kan en senere afsendelse ikke skrive det om til EGET', async () => {
    const kald = serverForeslaar('kør testene igen')
    const { felt } = opsæt()
    await screen.findByText('kør testene igen')
    fireEvent.keyDown(felt, { key: 'Tab' })
    await waitFor(() => expect(meldteValg(kald)).toContain('accepteret'))
    fireEvent.keyDown(felt, { key: 'Enter' })
    await act(async () => { await Promise.resolve() })
    expect(meldteSaet(kald)).toEqual(['accepteret', 'vist'])
  })

  it('et forslag der ALDRIG blev vist, meldes ikke', async () => {
    const kald = serverForeslaar('kør testene igen')
    const { felt } = opsæt()
    // Han skriver FØR forslaget nåede frem — så står det aldrig på skærmen.
    fireEvent.change(felt, { target: { value: 'jeg skriver selv' } })
    await act(async () => { await new Promise((r) => setTimeout(r, 900)) })
    expect(meldteValg(kald)).toEqual([])
  })
})
