import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { SetupScreen } from './SetupScreen'

describe('SetupScreen', () => {
  it('saves apiBaseUrl + token', async () => {
    const onSave = vi.fn()
    render(<SetupScreen onSave={onSave} />)
    await userEvent.type(screen.getByLabelText(/server/i), 'http://10.0.0.39')
    await userEvent.type(screen.getByLabelText(/token/i), 'jvs-x')
    await userEvent.click(screen.getByRole('button', { name: /forbind/i }))
    expect(onSave).toHaveBeenCalledWith({ apiBaseUrl: 'http://10.0.0.39', authToken: 'jvs-x' })
  })
})
