import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { Composer } from './Composer'
import { PermissionProvider } from '../../contexts/PermissionContext'

/** Composer bruger usePermission → render under PermissionProvider. */
const renderComposer = (ui: React.ReactElement) => render(<PermissionProvider>{ui}</PermissionProvider>)

describe('shell', () => {
  // ModeSlider er afloest af ModeDropdown (8/9-2026) — daekket i
  // ModeDropdown.test.tsx, hvor ogsaa aabne/lukke-adfaerden hoerer hjemme.
  it('Composer sends on Enter with opts, not Shift+Enter', async () => {
    const onSend = vi.fn()
    renderComposer(<Composer streaming={false} onSend={onSend} onStop={() => {}} getSessionId={async () => "s1"} model="deepseek-flash" thinking="think" />)
    const ta = screen.getByRole('textbox')
    await userEvent.type(ta, 'hej{Enter}')
    expect(onSend).toHaveBeenCalledWith('hej', expect.objectContaining({ permission: 'ask', planMode: false }))
  })
  it('Composer keeps text on Shift+Enter (no send)', async () => {
    const onSend = vi.fn()
    renderComposer(<Composer streaming={false} onSend={onSend} onStop={() => {}} getSessionId={async () => "s1"} model="m" thinking="think" />)
    const ta = screen.getByRole('textbox')
    await userEvent.type(ta, 'linje1{Shift>}{Enter}{/Shift}linje2')
    expect(onSend).not.toHaveBeenCalled()
  })
  it('Composer viser stop-knap der kalder onStop under streaming', async () => {
    const onStop = vi.fn()
    renderComposer(<Composer streaming onSend={() => {}} onStop={onStop} getSessionId={async () => 's1'} model="m" thinking="think" />)
    screen.getByLabelText('Stop').click()
    expect(onStop).toHaveBeenCalled()
  })
})
