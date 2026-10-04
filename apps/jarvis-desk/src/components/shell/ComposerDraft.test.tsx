import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'

vi.mock('../../lib/api', async () => {
  const real = await vi.importActual<Record<string, unknown>>('../../lib/api')
  return {
    ...real,
    apiFetch: vi.fn().mockResolvedValue({}),
    uploadAttachment: vi.fn(),
    getVisibleProviders: vi.fn().mockResolvedValue([]),
  }
})

import { Composer } from './Composer'
import { PermissionProvider } from '../../contexts/PermissionContext'
import { draftKeyFor } from '../../lib/composerPrefs'

const cfg = { apiBaseUrl: 'http://x', authToken: 't' }

function mount(draftKey: string) {
  const onSend = vi.fn()
  const r = render(
    <PermissionProvider>
      <Composer
        streaming={false} onSend={onSend} onStop={vi.fn()} model="m"
        config={cfg} showPermissions={false} getSessionId={async () => 's1'}
        sessionId="s1" draftKey={draftKey}
      />
    </PermissionProvider>,
  )
  return { onSend, ...r }
}

/**
 * Bjørn 4/10-2026: «hvis jeg skriver noget i composer … og lige hopper til
 * arbejde eller chat mode, så glemmer composer hvad jeg har skrevet … tekst i
 * composer skulle gerne overleve både mode skift og app genstart».
 *
 * Mode-skiftet unmounter Composeren (ChatView og CodeView har hver sin), så
 * testen gør præcis det: unmount → mount igen.
 */
describe('composer-kladden huskes', () => {
  beforeEach(() => localStorage.clear())

  it('overlever et gen-mount — det er hvad et mode-skift gør', () => {
    const { unmount } = mount('chat')
    fireEvent.change(screen.getByRole('textbox'), { target: { value: 'halvskrevet besked' } })
    unmount()
    mount('chat')
    expect(screen.getByRole('textbox')).toHaveValue('halvskrevet besked')
  })

  it('ligger i localStorage — så den overlever app-genstart', () => {
    const { unmount } = mount('chat')
    fireEvent.change(screen.getByRole('textbox'), { target: { value: 'gemt' } })
    unmount()
    expect(localStorage.getItem(draftKeyFor('chat'))).toBe('"gemt"')
  })

  it('de to flader deler IKKE kladde', () => {
    const a = mount('chat')
    fireEvent.change(screen.getByRole('textbox'), { target: { value: 'chat-tekst' } })
    a.unmount()
    mount('code')
    expect(screen.getByRole('textbox')).toHaveValue('')
  })

  it('rydder kladden når beskeden sendes', () => {
    const { onSend, unmount } = mount('chat')
    const ta = screen.getByRole('textbox')
    fireEvent.change(ta, { target: { value: 'sendes' } })
    fireEvent.keyDown(ta, { key: 'Enter' })
    expect(onSend).toHaveBeenCalled()
    unmount()
    expect(localStorage.getItem(draftKeyFor('chat'))).toBe('""')
  })
})
