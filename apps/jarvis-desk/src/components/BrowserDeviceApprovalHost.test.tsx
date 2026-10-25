import { beforeEach, describe, expect, it, vi } from 'vitest'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { BrowserDeviceApprovalHost } from './BrowserDeviceApprovalHost'
import * as devices from '../lib/enheder'

const config = { apiBaseUrl: 'http://x', authToken: 'desk-token' }

beforeEach(() => {
  vi.restoreAllMocks()
  ;(window as unknown as { jarvisDesk?: unknown }).jarvisDesk = { config: {} }
})

describe('BrowserDeviceApprovalHost', () => {
  it('lader den betroede Desk godkende uden et TOTP-felt', async () => {
    vi.spyOn(devices, 'hentBrowserAnmodninger').mockResolvedValue({
      ok: true,
      data: { anmodninger: [{
        id: 'req-1', app_id: 'web-1', navn: 'Firefox på Linux', status: 'pending',
        oprettet: 1, udloeber: 9999999999,
      }] },
    })
    const decide = vi.spyOn(devices, 'afgoerBrowserAnmodning').mockResolvedValue({
      ok: true, data: { ok: true, state: 'approved' },
    })
    render(<BrowserDeviceApprovalHost config={config} />)

    expect(await screen.findByText('Firefox på Linux')).toBeInTheDocument()
    expect(screen.queryByLabelText(/totrinskode/i)).toBeNull()
    fireEvent.click(screen.getByRole('button', { name: 'Godkend' }))
    await waitFor(() => expect(decide).toHaveBeenCalledWith(config, 'req-1', true))
  })
})
