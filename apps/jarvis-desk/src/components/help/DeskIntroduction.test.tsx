import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { AiTransparencyNotice } from '../AiTransparencyNotice'
import { IntroductionButton, DeskIntroduction } from './DeskIntroduction'
beforeEach(() => localStorage.clear())
describe('Desk introduction', () => {
  it('follows the first-run notice and remembers completion on remount', () => {
    const first = render(<AiTransparencyNotice />)
    expect(screen.queryByText('Velkommen til Desk')).not.toBeInTheDocument()
    fireEvent.click(screen.getByText('Forstået'))
    expect(screen.getByRole('dialog', { name: 'Velkommen til Desk' })).toBeInTheDocument()
    fireEvent.click(screen.getByText('Kom i gang'))
    first.unmount()
    render(<AiTransparencyNotice />)
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
  })
  it('can be reopened by existing users from Help', () => {
    localStorage.setItem('jarvis-desk:ai-notice-v1', '1')
    render(<><AiTransparencyNotice /><IntroductionButton /></>)
    fireEvent.click(screen.getByText('Vis introduktion til Desk'))
    expect(screen.getByText('Velkommen til Desk')).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Luk introduktion' }))
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
  })
  it('opens the chosen surface without creating or sending a message', () => {
    const onNavigate = vi.fn(), onClose = vi.fn()
    render(<DeskIntroduction onNavigate={onNavigate} onClose={onClose} />)
    fireEvent.click(screen.getByRole('button', { name: 'Åbn Code' }))
    expect(onNavigate).toHaveBeenCalledWith('code')
    expect(onClose).toHaveBeenCalledOnce()
  })
})
