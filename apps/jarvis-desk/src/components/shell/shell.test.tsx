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
    render(<Composer disabled={false} onSend={onSend} model="deepseek-flash" thinking="think" />)
    const ta = screen.getByRole('textbox')
    await userEvent.type(ta, 'hej{Enter}')
    expect(onSend).toHaveBeenCalledWith('hej', expect.objectContaining({ permission: 'ask', planMode: false }))
  })
  it('Composer keeps text on Shift+Enter (no send)', async () => {
    const onSend = vi.fn()
    render(<Composer disabled={false} onSend={onSend} model="m" thinking="think" />)
    const ta = screen.getByRole('textbox')
    await userEvent.type(ta, 'linje1{Shift>}{Enter}{/Shift}linje2')
    expect(onSend).not.toHaveBeenCalled()
  })
})
