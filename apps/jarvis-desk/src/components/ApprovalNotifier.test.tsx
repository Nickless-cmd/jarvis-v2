import { describe, it, expect, vi } from 'vitest'
import { render } from '@testing-library/react'
import { ApprovalNotifier } from './ApprovalNotifier'

describe('ApprovalNotifier', () => {
  it('fyrer notifikation ved ny approval', () => {
    const notify = vi.fn()
    render(<ApprovalNotifier approvalId="a1" tool="gmail_send" action="send mail til X" notify={notify} />)
    expect(notify).toHaveBeenCalledWith('Jarvis venter på din godkendelse', 'gmail_send: send mail til X')
  })

  it('fyrer ikke igen ved re-render med samme approvalId', () => {
    const notify = vi.fn()
    const { rerender } = render(<ApprovalNotifier approvalId="a1" tool="x" notify={notify} />)
    rerender(<ApprovalNotifier approvalId="a1" tool="x" notify={notify} />)
    expect(notify).toHaveBeenCalledTimes(1)
  })

  it('fyrer ikke uden approval', () => {
    const notify = vi.fn()
    render(<ApprovalNotifier approvalId={null} notify={notify} />)
    expect(notify).not.toHaveBeenCalled()
  })

  it('fyrer igen for en NY approvalId', () => {
    const notify = vi.fn()
    const { rerender } = render(<ApprovalNotifier approvalId="a1" tool="x" notify={notify} />)
    rerender(<ApprovalNotifier approvalId={null} notify={notify} />)
    rerender(<ApprovalNotifier approvalId="a2" tool="y" notify={notify} />)
    expect(notify).toHaveBeenCalledTimes(2)
  })
})
