import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, act } from '@testing-library/react'

/**
 * Vent-og-send (Bjørn 27/9-2026).
 *
 * Målt i serverloggen: beskeden «her» gik afsted 1 sekund efter upload-svaret
 * med `attachments=[]`. Uploaden lykkedes, men id'et nåede aldrig med — fordi
 * `doSend` filtrerede den endnu ikke-færdige vedhæftning STILLE ud af `ready`.
 * Serveren gemte beskeden uden billedblok, og da serverens kopi overtog den
 * optimistiske besked, forsvandt billedet.
 *
 * Disse to tests holder begge ender: den ene at beskeden VENTER, den anden at
 * den stadig sendes med det samme når der ikke er noget at vente på.
 */
const uploadAttachment = vi.fn()

vi.mock('../../lib/api', async () => {
  const real = await vi.importActual<Record<string, unknown>>('../../lib/api')
  return {
    ...real,
    apiFetch: vi.fn().mockResolvedValue({}),
    uploadAttachment: (...args: unknown[]) => uploadAttachment(...args),
    getVisibleProviders: vi.fn().mockResolvedValue([]),
  }
})

import { Composer } from './Composer'
import { PermissionProvider } from '../../contexts/PermissionContext'

const cfg = { apiBaseUrl: 'http://x', authToken: 't' }

function setup() {
  const onSend = vi.fn()
  const r = render(
    <PermissionProvider>
      <Composer
        streaming={false} onSend={onSend} onStop={vi.fn()} model="m"
        config={cfg} showPermissions={false} getSessionId={async () => 's1'}
        sessionId="s1"
      />
    </PermissionProvider>,
  )
  return { onSend, ...r }
}

async function vaelgFil(container: HTMLElement) {
  const fil = new File(['x'], 'billede.png', { type: 'image/png' })
  const input = container.querySelector('input[type="file"]') as HTMLInputElement
  await act(async () => {
    fireEvent.change(input, { target: { files: [fil] } })
  })
}

function skrivOgSend(tekst: string) {
  const felt = screen.getByRole('textbox')
  fireEvent.change(felt, { target: { value: tekst } })
  fireEvent.keyDown(felt, { key: 'Enter' })
}

/** Vedhæftningerne fra det FØRSTE send — hvad beskeden faktisk bar med. */
function sendteVedhaeftninger(onSend: ReturnType<typeof vi.fn>) {
  const kald = onSend.mock.calls[0] as
    | [string, { attachments: Array<{ id: string; isImage: boolean }> }]
    | undefined
  return kald?.[1]?.attachments
}

describe('vent-og-send — beskeden venter på uploaden', () => {
  beforeEach(() => {
    localStorage.clear()
    uploadAttachment.mockReset()
    ;(URL as unknown as { createObjectURL: unknown }).createObjectURL = vi.fn(() => 'blob:x')
  })

  it('sender IKKE uden vedhæftningen — venter til uploaden har svar', async () => {
    let svar: ((v: { id: string }) => void) | undefined
    uploadAttachment.mockImplementation(() => new Promise((res) => { svar = res }))
    const { onSend, container } = setup()

    await vaelgFil(container)
    skrivOgSend('her')

    // Uploaden er i gang. Sendte vi nu, gik beskeden afsted uden billedet —
    // præcis den fejl Bjørn så.
    expect(onSend).not.toHaveBeenCalled()

    // Nu svarer uploaden. Beskeden skal gå afsted MED id'et på.
    await act(async () => { svar?.({ id: 'att-1' }) })

    expect(onSend).toHaveBeenCalledTimes(1)
    expect(sendteVedhaeftninger(onSend)).toEqual([
      expect.objectContaining({ id: 'att-1', isImage: true }),
    ])
  })

  it('sender straks når uploaden allerede er færdig', async () => {
    uploadAttachment.mockResolvedValue({ id: 'att-2' })
    const { onSend, container } = setup()

    await vaelgFil(container)   // uploaden svarer med det samme
    skrivOgSend('her')

    expect(onSend).toHaveBeenCalledTimes(1)
    expect(sendteVedhaeftninger(onSend)).toEqual([
      expect.objectContaining({ id: 'att-2' }),
    ])
  })
})
