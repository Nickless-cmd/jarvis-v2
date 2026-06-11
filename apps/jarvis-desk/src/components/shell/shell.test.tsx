import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { ModeSlider } from './ModeSlider'
import { Composer } from './Composer'

describe('shell', () => {
  it('ModeSlider switches active mode', async () => {
    const onChange = vi.fn()
    render(<ModeSlider active="chat" onChange={onChange} />)
    await userEvent.click(screen.getByRole('button', { name: /code/i }))
    expect(onChange).toHaveBeenCalledWith('code')
  })
  it('Composer sends on Enter with opts, not Shift+Enter', async () => {
    const onSend = vi.fn()
    render(<Composer streaming={false} onSend={onSend} onStop={() => {}} getSessionId={async () => "s1"} model="deepseek-flash" thinking="think" />)
    const ta = screen.getByRole('textbox')
    await userEvent.type(ta, 'hej{Enter}')
    expect(onSend).toHaveBeenCalledWith('hej', expect.objectContaining({ permission: 'ask', planMode: false }))
  })
  it('Composer keeps text on Shift+Enter (no send)', async () => {
    const onSend = vi.fn()
    render(<Composer streaming={false} onSend={onSend} onStop={() => {}} getSessionId={async () => "s1"} model="m" thinking="think" />)
    const ta = screen.getByRole('textbox')
    await userEvent.type(ta, 'linje1{Shift>}{Enter}{/Shift}linje2')
    expect(onSend).not.toHaveBeenCalled()
  })
  it('Composer viser stop-knap der kalder onStop under streaming', async () => {
    const onStop = vi.fn()
    render(<Composer streaming onSend={() => {}} onStop={onStop} getSessionId={async () => 's1'} model="m" thinking="think" />)
    screen.getByLabelText('Stop').click()
    expect(onStop).toHaveBeenCalled()
  })
})
