import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { AppActionCard } from './AppActionCard'

describe('AppActionCard', () => {
  it('renders code-mode prompt + reason, fires onApprove', async () => {
    const onApprove = vi.fn()
    render(<AppActionCard action="switch_to_code_mode" reason="kræver terminal og filer" onApprove={onApprove} onReject={() => {}} />)
    expect(screen.getByText(/code mode/i)).toBeInTheDocument()
    expect(screen.getByText(/kræver terminal og filer/i)).toBeInTheDocument()
    await userEvent.click(screen.getByRole('button', { name: /ja/i }))
    expect(onApprove).toHaveBeenCalledTimes(1)
  })

  it('renders full-access prompt, fires onReject', async () => {
    const onReject = vi.fn()
    render(<AppActionCard action="request_full_access" reason="" onApprove={() => {}} onReject={onReject} />)
    expect(screen.getByText(/fuld adgang/i)).toBeInTheDocument()
    await userEvent.click(screen.getByRole('button', { name: /nej/i }))
    expect(onReject).toHaveBeenCalledTimes(1)
  })
})
