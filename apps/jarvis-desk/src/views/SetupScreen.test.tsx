import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { SetupScreen } from './SetupScreen'

describe('SetupScreen', () => {
  it('token-login bruger hardcoded API-URL', async () => {
    const onSave = vi.fn()
    render(<SetupScreen onSave={onSave} />)
    // Server-URL-feltet er fjernet (hardcoded) — kun token indtastes.
    expect(screen.queryByLabelText(/server/i)).not.toBeInTheDocument()
    await userEvent.type(screen.getByLabelText(/token/i), 'jvs-x')
    await userEvent.click(screen.getByRole('button', { name: /^forbind$/i }))
    expect(onSave).toHaveBeenCalledWith({ apiBaseUrl: 'https://api.srvlab.dk/', authToken: 'jvs-x' })
  })

  it('viser Log ind med Google', () => {
    render(<SetupScreen onSave={vi.fn()} />)
    expect(screen.getByRole('button', { name: /log ind med google/i })).toBeInTheDocument()
  })
})
