import { describe, expect, it, vi } from 'vitest'
import { fireEvent, render, screen } from '@testing-library/react'
import { PrivacyDialog } from './PrivacyDialog'

describe('PrivacyDialog', () => {
  it('viser den eksisterende politik og lukker uden at navigere', () => {
    const close = vi.fn()
    render(<PrivacyDialog onClose={close} />)
    expect(screen.getByRole('dialog', { name: 'Privatliv og cookies' })).toBeInTheDocument()
    expect(screen.getByText('Denne app bruger ingen cookies.')).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Luk privatliv og cookies' }))
    expect(close).toHaveBeenCalledOnce()
  })
})
