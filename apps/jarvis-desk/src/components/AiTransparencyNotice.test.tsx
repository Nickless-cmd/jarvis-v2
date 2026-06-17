import { describe, it, expect, beforeEach } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { AiTransparencyNotice } from './AiTransparencyNotice'

describe('AiTransparencyNotice', () => {
  beforeEach(() => {
    localStorage.clear()
  })

  it('viser AI-notice ved første kørsel', () => {
    render(<AiTransparencyNotice />)
    expect(screen.getByText('Du taler med en AI')).toBeInTheDocument()
  })

  it('skjuler og husker valget efter "Forstået"', () => {
    const { rerender } = render(<AiTransparencyNotice />)
    fireEvent.click(screen.getByText('Forstået'))
    expect(screen.queryByText('Du taler med en AI')).not.toBeInTheDocument()
    expect(localStorage.getItem('jarvis-desk:ai-notice-v1')).toBe('1')
    // ny montering viser den ikke igen
    rerender(<AiTransparencyNotice />)
    expect(screen.queryByText('Du taler med en AI')).not.toBeInTheDocument()
  })

  it('viser ikke notice når allerede acked', () => {
    localStorage.setItem('jarvis-desk:ai-notice-v1', '1')
    render(<AiTransparencyNotice />)
    expect(screen.queryByText('Du taler med en AI')).not.toBeInTheDocument()
  })
})
