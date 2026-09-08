import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { ModeDropdown } from './ModeDropdown'

/**
 * Afløser pille-slideren (Bjørn 8/9-2026). Slideren viste alle tre valg hele
 * tiden og brugte hele panelets bredde på at fortælle hvor man var.
 */
describe('ModeDropdown', () => {
  it('viser den aktive mode og skjuler de andre', () => {
    render(<ModeDropdown active="code" onChange={vi.fn()} />)
    expect(screen.getByText('Code')).toBeTruthy()
    expect(screen.queryByText('Arbejde')).toBeNull()
  })

  it('åbner og vælger', () => {
    const onChange = vi.fn()
    render(<ModeDropdown active="chat" onChange={onChange} />)
    fireEvent.click(screen.getByRole('button', { expanded: false }))
    fireEvent.click(screen.getByRole('option', { name: /Arbejde/ }))
    expect(onChange).toHaveBeenCalledWith('cowork')
  })

  it('lukker igen efter valg', () => {
    render(<ModeDropdown active="chat" onChange={vi.fn()} />)
    fireEvent.click(screen.getByRole('button', { expanded: false }))
    fireEvent.click(screen.getByRole('option', { name: /Code/ }))
    expect(screen.queryByRole('listbox')).toBeNull()
  })

  it('Escape lukker — en åben menu må ikke fange tastaturet', () => {
    render(<ModeDropdown active="chat" onChange={vi.fn()} />)
    fireEvent.click(screen.getByRole('button', { expanded: false }))
    expect(screen.getByRole('listbox')).toBeTruthy()
    fireEvent.keyDown(window, { key: 'Escape' })
    expect(screen.queryByRole('listbox')).toBeNull()
  })

  it('klik udenfor lukker', () => {
    render(<ModeDropdown active="chat" onChange={vi.fn()} />)
    fireEvent.click(screen.getByRole('button', { expanded: false }))
    fireEvent.mouseDown(document.body)
    expect(screen.queryByRole('listbox')).toBeNull()
  })
})
