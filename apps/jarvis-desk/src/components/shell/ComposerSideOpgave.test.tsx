import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'

/**
 * `/side <opgave>` i composeren (Bjørn 15/10-2026).
 *
 * Kommandoen er ikke en besked. Den vigtigste test her er den SIDSTE: en
 * almindelig besked må ikke blive slugt af kommando-grenen. En parser der
 * fanger for bredt ville gøre en helt normal sætning usendt — og det ville
 * være et tavst tab af præcis den slags huset har brændt sig på før.
 */
const opretSideTask = vi.fn()
vi.mock('../../lib/sideTasksApi', () => ({
  opretSideTask: (...a: unknown[]) => opretSideTask(...a),
}))

vi.mock('../../lib/api', async () => {
  const real = await vi.importActual<Record<string, unknown>>('../../lib/api')
  return {
    ...real,
    apiFetch: vi.fn().mockResolvedValue({}),
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

function skrivOgSend(tekst: string) {
  const felt = screen.getByRole('textbox')
  fireEvent.change(felt, { target: { value: tekst } })
  fireEvent.keyDown(felt, { key: 'Enter' })
}

describe('Composer — /side-kommandoen', () => {
  beforeEach(() => { opretSideTask.mockReset().mockResolvedValue('side-1') })

  it('åbner opret-boksen med teksten forudfyldt — og sender INTET', async () => {
    const { onSend } = setup()
    skrivOgSend('/side ret CI-badgen')
    expect(await screen.findByTestId('side-opgave-dialog')).toBeInTheDocument()
    expect((screen.getByLabelText('Beskrivelse') as HTMLTextAreaElement).value).toBe('ret CI-badgen')
    expect(onSend).not.toHaveBeenCalled()
  })

  it('tømmer feltet, så kommandoen ikke står tilbage og kan sendes ved et uheld', () => {
    const { container } = setup()
    skrivOgSend('/side noget')
    // Composeren har classen `.composer-input`; dialogens to felter har ikke,
    // så vi rammer ikke dem ved et uheld nu hvor boksen står åben.
    expect((container.querySelector('.composer-input') as HTMLTextAreaElement).value).toBe('')
  })

  it('bar `/side` uden tekst åbner boksen med et tomt beskrivelses-felt', async () => {
    const { onSend } = setup()
    skrivOgSend('/side')
    expect(await screen.findByTestId('side-opgave-dialog')).toBeInTheDocument()
    expect((screen.getByLabelText('Beskrivelse') as HTMLTextAreaElement).value).toBe('')
    expect(onSend).not.toHaveBeenCalled()
  })

  it('en almindelig besked sendes som før — grenen fanger ikke for bredt', async () => {
    const { onSend } = setup()
    skrivOgSend('sidebar er i stykker, kan du se på den?')
    await waitFor(() => expect(onSend).toHaveBeenCalledTimes(1))
    expect((onSend.mock.calls[0] as [string])[0]).toBe('sidebar er i stykker, kan du se på den?')
    expect(screen.queryByTestId('side-opgave-dialog')).not.toBeInTheDocument()
  })
})
