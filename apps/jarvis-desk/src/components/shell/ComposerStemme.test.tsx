/**
 * Højre knap i komponisten (Bjørn 18/9-2026: «send fungere som mobilen … send
 * er lige som i mobil appen wave (aktivere samtale mode), hvis tekst eller
 * filer i composer ændre den sig til det den er nu send»).
 *
 * Mobilens egen formulering står i dens Composer: «I hvile er højre knap en
 * voice-knap (lydbølge); så snart der er tekst…». Testene holder de tre
 * tilstande fast, fordi det er selve kravet — ikke en detalje.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'

vi.mock('../../lib/api', async () => {
  const ægte = await vi.importActual<Record<string, unknown>>('../../lib/api')
  return { ...ægte, apiFetch: vi.fn().mockResolvedValue({}), uploadAttachment: vi.fn() }
})

import { Composer } from './Composer'
import { PermissionProvider } from '../../contexts/PermissionContext'

const cfg = { apiBaseUrl: 'http://x', authToken: 't' }

const opsæt = (props: Record<string, unknown> = {}) => {
  const onSend = vi.fn()
  const onVoice = vi.fn()
  render(
    <PermissionProvider>
      <Composer
        streaming={false} onSend={onSend} onStop={vi.fn()} model="m"
        config={cfg} showPermissions={false} getSessionId={async () => 's1'}
        sessionId="s1" onVoice={onVoice} voiceSupported {...props}
      />
    </PermissionProvider>,
  )
  return { onSend, onVoice }
}

describe('højre knap i komponisten', () => {
  beforeEach(() => localStorage.clear())

  it('tomt felt → bølge der starter samtale-mode', () => {
    const { onVoice } = opsæt()
    const knap = screen.getByLabelText('Start samtale')
    expect(screen.queryByLabelText('Send')).toBeNull()

    fireEvent.click(knap)
    expect(onVoice).toHaveBeenCalledTimes(1)
  })

  it('tekst i feltet → knappen bliver send', () => {
    opsæt()
    fireEvent.change(screen.getByRole('textbox'), { target: { value: 'hej' } })

    expect(screen.getByLabelText('Send')).toBeTruthy()
    expect(screen.queryByLabelText('Start samtale')).toBeNull()
  })

  it('uden stemme-støtte falder den tilbage til send — aldrig en død bølge', () => {
    opsæt({ voiceSupported: false })
    expect(screen.queryByLabelText('Start samtale')).toBeNull()
    expect(screen.getByLabelText('Send')).toBeTruthy()
  })

  it('under streaming er den stop — det slår begge dele', () => {
    opsæt({ streaming: true })
    expect(screen.getByLabelText('Stop')).toBeTruthy()
    expect(screen.queryByLabelText('Start samtale')).toBeNull()
  })
})
