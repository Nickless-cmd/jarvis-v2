import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'

const apiFetch = vi.fn()
const listProjectFiles = vi.fn()
vi.mock('../../lib/api', async () => {
  const ægte = await vi.importActual<Record<string, unknown>>('../../lib/api')
  return { ...ægte, apiFetch: (...a: unknown[]) => apiFetch(...a), uploadAttachment: vi.fn() }
})
vi.mock('../../lib/projectApi', () => ({
  listProjectFiles: (...a: unknown[]) => listProjectFiles(...a),
}))

import { Composer } from './Composer'
import { PermissionProvider } from '../../contexts/PermissionContext'

const cfg = { apiBaseUrl: 'http://x', authToken: 't' }
const FILER = [
  { path: '/r/core/tools/simple_tools.py', rel: 'core/tools/simple_tools.py', size_bytes: 1 },
  { path: '/r/core/services/visible_model.py', rel: 'core/services/visible_model.py', size_bytes: 1 },
]

const opsæt = (props: Record<string, unknown> = {}) => {
  const onSend = vi.fn()
  render(
    <PermissionProvider>
      <Composer
      streaming={false} onSend={onSend} onStop={vi.fn()} model="m" thinking="t"
        config={cfg} isOwner showPermissions={false} getSessionId={async () => 's1'} {...props}
      />
    </PermissionProvider>,
  )
  return { onSend, felt: screen.getByRole('textbox') as HTMLTextAreaElement }
}

const skriv = (felt: HTMLTextAreaElement, v: string) =>
  fireEvent.change(felt, { target: { value: v, selectionStart: v.length } })

describe('Composer · @fil', () => {
  beforeEach(() => {
    apiFetch.mockReset().mockResolvedValue({ workspace: '/r' })
    listProjectFiles.mockReset().mockResolvedValue(FILER)
  })

  it('åbner filliste når man skriver @ og henter indekset dovent', async () => {
    const { felt } = opsæt()
    expect(listProjectFiles).not.toHaveBeenCalled()   // ikke ved mount
    skriv(felt, '@simple')
    await waitFor(() => expect(screen.getByRole('listbox')).toBeTruthy())
    expect(screen.getByText('core/tools/simple_tools.py')).toBeTruthy()
  })

  it('Enter vælger filen i stedet for at sende beskeden', async () => {
    const { felt, onSend } = opsæt()
    skriv(felt, '@simple')
    await waitFor(() => screen.getByRole('listbox'))
    fireEvent.keyDown(felt, { key: 'Enter' })
    expect(onSend).not.toHaveBeenCalled()
    await waitFor(() => expect(felt.value).toBe('@core/tools/simple_tools.py '))
  })

  it('Enter sender igen når listen er lukket', async () => {
    const { felt, onSend } = opsæt()
    skriv(felt, '@simple')
    await waitFor(() => screen.getByRole('listbox'))
    fireEvent.keyDown(felt, { key: 'Escape' })
    fireEvent.keyDown(felt, { key: 'Enter' })
    expect(onSend).toHaveBeenCalled()
  })

  it('rører ikke indekset for en ikke-ejer — ruten er ejer-gatet', async () => {
    const { felt } = opsæt({ isOwner: false })
    skriv(felt, '@simple')
    await new Promise((r) => setTimeout(r, 20))
    expect(listProjectFiles).not.toHaveBeenCalled()
    expect(screen.queryByRole('listbox')).toBeNull()
  })
})
