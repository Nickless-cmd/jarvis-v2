import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'

const saveTheme = vi.fn()
const applyTheme = vi.fn()
vi.mock('../../lib/themeStore', () => ({
  loadTheme: () => 'dark',
  saveTheme: (...a: unknown[]) => saveTheme(...a),
  applyTheme: (...a: unknown[]) => applyTheme(...a),
}))

import { ThemeSection } from './ThemeSection'

describe('ThemeSection', () => {
  beforeEach(() => { saveTheme.mockClear(); applyTheme.mockClear() })

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
})
