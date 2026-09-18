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

/** Serveren svarer med ét forslag; alt andet svarer tomt. */
function serverForeslaar(forslag: string) {
  vi.stubGlobal('fetch', vi.fn(async (url: string) => ({
    ok: true,
    json: async () => (String(url).includes('/composer/suggest') ? { forslag } : {}),
  } as unknown as Response)))
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
})
