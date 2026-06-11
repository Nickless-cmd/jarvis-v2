import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { ApprovalCard } from './ApprovalCard'

describe('ApprovalCard', () => {
  it('renders action text inert and fires onApprove (owner)', async () => {
    const onApprove = vi.fn()
    render(<ApprovalCard approvalId="a1" tool="operator_bash" action={'<b>rm</b>'} risk="destructive" canApprove onApprove={onApprove} onDeny={() => {}} />)
    expect(screen.getByText('<b>rm</b>')).toBeInTheDocument()
    await userEvent.click(screen.getByRole('button', { name: /godkend/i }))
    expect(onApprove).toHaveBeenCalledWith('a1')
  })
  it('member sees read-only (no approve button)', () => {
    render(<ApprovalCard approvalId="a1" tool="x" action="y" risk="normal" canApprove={false} onApprove={() => {}} onDeny={() => {}} />)
    expect(screen.queryByRole('button', { name: /godkend/i })).toBeNull()
  })
})
