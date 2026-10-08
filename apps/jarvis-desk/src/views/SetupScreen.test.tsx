import { describe, it, expect, vi, afterEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { SetupScreen } from './SetupScreen'
import { googleLoginStart } from '../lib/api'

vi.mock('../lib/api', () => ({
  googleLoginStart: vi.fn(),
  googleLoginResult: vi.fn().mockResolvedValue({ status: 'pending' }),
}))

describe('SetupScreen', () => {
  afterEach(() => vi.unstubAllGlobals())

  it('token-login bruger hardcoded API-URL', async () => {
    vi.stubGlobal('jarvisDesk', { openExternal: vi.fn() })
    const onSave = vi.fn()
    render(<SetupScreen onSave={onSave} />)
    // Server-URL-feltet er fjernet (hardcoded) — kun token indtastes.
    expect(screen.queryByLabelText(/server/i)).not.toBeInTheDocument()
    await userEvent.type(screen.getByLabelText(/token/i), 'jvs-x')
    await userEvent.click(screen.getByRole('button', { name: /^forbind$/i }))
    expect(onSave).toHaveBeenCalledWith({ apiBaseUrl: 'https://api.srvlab.dk/', authToken: 'jvs-x' })
  })

  it('uses the current origin for browser token login', async () => {
    const onSave = vi.fn()
    render(<SetupScreen onSave={onSave} />)
    await userEvent.type(screen.getByLabelText(/token/i), 'test-token')
    await userEvent.click(screen.getByRole('button', { name: /^forbind$/i }))
    expect(onSave).toHaveBeenCalledWith({ apiBaseUrl: new URL('/', window.location.origin).toString(), authToken: 'test-token' })
  })

  it('opens the Google authorization URL in the browser', async () => {
    const popup = { location: { href: '' }, opener: window }
    const open = vi.fn(() => popup)
    vi.stubGlobal('open', open)
    vi.mocked(googleLoginStart).mockResolvedValue({ authorize_url: 'https://accounts.example/authorize', nonce: 'nonce' })
    render(<SetupScreen onSave={vi.fn()} />)
    await userEvent.click(screen.getByRole('button', { name: /log ind med google/i }))
    expect(open).toHaveBeenCalledWith('about:blank', '_blank')
    await waitFor(() => expect(popup.location.href).toBe('https://accounts.example/authorize'))
    expect(popup.opener).toBeNull()
  })

  it('viser Log ind med Google', () => {
    render(<SetupScreen onSave={vi.fn()} />)
    expect(screen.getByRole('button', { name: /log ind med google/i })).toBeInTheDocument()
  })
})
