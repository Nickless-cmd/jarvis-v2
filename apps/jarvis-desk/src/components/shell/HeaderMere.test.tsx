import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { HeaderMere } from './HeaderMere'

const valg = () => [
  { id: 'figur', navn: 'Jarvis-figuren på skrivebordet', ikon: null, aktiv: true, onClick: vi.fn() },
  { id: 'filer', navn: 'Filer', ikon: null, aktiv: false, onClick: vi.fn() },
  { id: 'stemme', navn: 'Samtale med Jarvis (stemme)', ikon: null, onClick: vi.fn() },
]

describe('HeaderMere — flere-menuen (19/9-2026)', () => {
  it('lukket: kun én knap med lodrette prikker', () => {
    render(<HeaderMere visning="normal" onVisning={() => {}} valg={valg()} />)
    expect(screen.getByRole('button', { name: 'Flere valg' })).toBeInTheDocument()
    expect(screen.queryByRole('menu')).toBeNull()
  })

  it('åben: Visning som radio-valg, kontakter med flueben, handlinger uden', () => {
    const onVisning = vi.fn()
    render(<HeaderMere visning="normal" onVisning={onVisning} valg={valg()} />)
    fireEvent.click(screen.getByRole('button', { name: 'Flere valg' }))
    const radio = screen.getAllByRole('menuitemradio')
    expect(radio.map((r) => r.getAttribute('aria-checked'))).toEqual(['true', 'false', 'false'])
    expect(screen.getByRole('menuitemcheckbox', { name: /Jarvis-figuren/ })).toHaveAttribute('aria-checked', 'true')
    expect(screen.getByRole('menuitemcheckbox', { name: /Filer/ })).toHaveAttribute('aria-checked', 'false')
    expect(screen.getByRole('menuitem', { name: /Samtale med Jarvis/ })).toBeInTheDocument()
    fireEvent.click(radio[1]!)
    expect(onVisning).toHaveBeenCalledWith('thinking')
  })

  it('et valg udføres og lukker menuen; Escape lukker også', () => {
    const v = valg()
    render(<HeaderMere visning="normal" onVisning={() => {}} valg={v} />)
    fireEvent.click(screen.getByRole('button', { name: 'Flere valg' }))
    fireEvent.click(screen.getByRole('menuitemcheckbox', { name: /Filer/ }))
    expect(v[1]!.onClick).toHaveBeenCalled()
    expect(screen.queryByRole('menu')).toBeNull()
    fireEvent.click(screen.getByRole('button', { name: 'Flere valg' }))
    fireEvent.keyDown(document, { key: 'Escape' })
    expect(screen.queryByRole('menu')).toBeNull()
  })
})
