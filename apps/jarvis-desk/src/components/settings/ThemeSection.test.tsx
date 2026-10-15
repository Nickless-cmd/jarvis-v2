import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'

const setPreference = vi.fn()
vi.mock('../../hooks/useChatFlow', () => ({
  useChatFlow: () => ({
    state: { preference: 'living' },
    setPreference,
  }),
}))

const saveTheme = vi.fn()
const applyTheme = vi.fn()
vi.mock('../../lib/themeStore', () => ({
  loadTheme: () => 'dark',
  saveTheme: (...a: unknown[]) => saveTheme(...a),
  applyTheme: (...a: unknown[]) => applyTheme(...a),
}))

import { ThemeSection } from './ThemeSection'

describe('ThemeSection', () => {
  beforeEach(() => { saveTheme.mockClear(); applyTheme.mockClear(); setPreference.mockClear() })

  it('valg af Lyst gemmer og anvender temaet', () => {
    render(<ThemeSection />)
    fireEvent.click(screen.getByRole('button', { name: /lyst/i }))
    expect(saveTheme).toHaveBeenCalledWith('light')
    expect(applyTheme).toHaveBeenCalledWith('light')
  })

  it('markerer det aktive tema', () => {
    const { container } = render(<ThemeSection />)
    // default = dark → Mørkt-knappen aktiv
    const active = container.querySelector('.theme-btn.active')
    expect(active?.textContent).toMatch(/mørkt/i)
  })

  it('separates Code Mode row view from Chat Mode choices', () => {
    render(<ThemeSection />)
    expect(screen.getByRole('heading', { name: 'Code Mode' })).toBeInTheDocument()
    expect(screen.getByRole('checkbox', { name: /rækkevisning/i })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Chat Mode' })).toBeInTheDocument()
    expect(screen.getByRole('radio', { name: /levende/i })).toBeChecked()
    expect(screen.getByRole('radio', { name: /rolig/i })).not.toBeChecked()
    expect(screen.getByRole('radio', { name: /adaptiv/i })).not.toBeChecked()
  })

  it('changes Chat Mode without changing the Code Mode key', () => {
    localStorage.setItem('jarvis-desk:raekkevisning', '1')
    render(<ThemeSection />)
    fireEvent.click(screen.getByRole('radio', { name: /rolig/i }))
    expect(setPreference).toHaveBeenCalledWith('calm')
    expect(localStorage.getItem('jarvis-desk:raekkevisning')).toBe('1')
  })
})
