/**
 * Tænknings-pillen i komponisten (Bjørn 18/9-2026: «think dropdown virker ikke»).
 *
 * Den tegnede en pil (▾) og havde INGEN onClick. Værdien var samtidig hardkodet
 * til "think" i både ChatView og CodeView, så pillen var ren dekoration. Ledningen
 * ud til serveren fandtes hele tiden — streamClient sender `thinking_mode`, og
 * API'et tager imod — kun valget manglede.
 *
 * Testene holder de tre ting fast der gør forskellen mellem en knap og en pynt:
 * den åbner, den ændrer det der SENDES, og valget overlever.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'

vi.mock('../../lib/api', async () => {
  const ægte = await vi.importActual<Record<string, unknown>>('../../lib/api')
  return { ...ægte, apiFetch: vi.fn().mockResolvedValue({}), uploadAttachment: vi.fn() }
})

import { Composer } from './Composer'
import { PermissionProvider } from '../../contexts/PermissionContext'
import { THINK_KEY } from '../../lib/composerPrefs'

const cfg = { apiBaseUrl: 'http://x', authToken: 't' }

const opsæt = () => {
  const onSend = vi.fn()
  render(
    <PermissionProvider>
      <Composer
        streaming={false} onSend={onSend} onStop={vi.fn()} model="m"
        config={cfg} showPermissions={false} getSessionId={async () => 's1'}
        sessionId="s1"
      />
    </PermissionProvider>,
  )
  return { onSend }
}

const pille = () => screen.getByTitle('Tænknings-effekt')

describe('tænknings-pillen', () => {
  beforeEach(() => localStorage.clear())

  it('åbner en menu med de tre tilstande — før havde den ingen handler', () => {
    opsæt()
    expect(screen.queryByRole('option', { name: 'Dyb' })).toBeNull()

    fireEvent.click(pille())

    expect(screen.getByRole('option', { name: 'Hurtig' })).toBeTruthy()
    expect(screen.getByRole('option', { name: 'Automatisk' })).toBeTruthy()
    expect(screen.getByRole('option', { name: 'Dyb' })).toBeTruthy()
  })

  it('ændrer det der faktisk SENDES — ikke kun etiketten', () => {
    const { onSend } = opsæt()

    fireEvent.click(pille())
    fireEvent.click(screen.getByRole('option', { name: 'Dyb' }))

    const felt = screen.getByRole('textbox')
    fireEvent.change(felt, { target: { value: 'hej' } })
    fireEvent.keyDown(felt, { key: 'Enter' })

    expect(onSend).toHaveBeenCalled()
    const opts = onSend.mock.calls[0]?.[1] as { thinkingMode?: string }
    expect(opts.thinkingMode).toBe('deep')
  })

  it('husker valget, så det ikke skal sættes hver gang', () => {
    opsæt()
    fireEvent.click(pille())
    fireEvent.click(screen.getByRole('option', { name: 'Hurtig' }))

    expect(localStorage.getItem(THINK_KEY)).toBe('fast')
    expect(pille().textContent).toContain('Hurtig')
  })

  it('starter på Automatisk — serverens adaptive valg', () => {
    opsæt()
    expect(pille().textContent).toContain('Automatisk')
  })
})
