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
const saveAccent = vi.fn()
const applyTheme = vi.fn()
vi.mock('../../lib/themeStore', () => ({
  ACCENTS: [
    { name: 'gron', label: 'Grøn', color: '#6EE7A8' },
    { name: 'teal', label: 'Teal', color: '#3FC7B4' },
    { name: 'lilla', label: 'Lilla', color: '#A07FEB' },
    { name: 'rav', label: 'Rav', color: '#E8A33D' },
    { name: 'bla', label: 'Blå', color: '#5B8DEF' },
    { name: 'rose', label: 'Rosa', color: '#F4849B' },
  ],
  loadAccent: () => 'gron',
  loadTheme: () => 'dark',
  saveAccent: (...a: unknown[]) => saveAccent(...a),
  saveTheme: (...a: unknown[]) => saveTheme(...a),
  applyTheme: (...a: unknown[]) => applyTheme(...a),
}))

import { ThemeSection } from './ThemeSection'

describe('ThemeSection', () => {
  beforeEach(() => {
    saveTheme.mockClear(); saveAccent.mockClear(); applyTheme.mockClear(); setPreference.mockClear()
  })

  it('valg af Lyst gemmer og anvender temaet', () => {
    render(<ThemeSection />)
    fireEvent.click(screen.getByRole('button', { name: /lyst/i }))
    expect(saveTheme).toHaveBeenCalledWith('light')
    expect(applyTheme).toHaveBeenCalledWith('light', 'gron')
  })

  it('viser APKens seks accentfamilier og anvender dem uafhængigt af lys/mørk', () => {
    render(<ThemeSection />)
    expect(screen.getByRole('group', { name: 'Accentfarve' }).querySelectorAll('.accent-btn')).toHaveLength(6)
    fireEvent.click(screen.getByRole('button', { name: 'Lilla' }))
    expect(saveAccent).toHaveBeenCalledWith('lilla')
    expect(applyTheme).toHaveBeenCalledWith('dark', 'lilla')
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
