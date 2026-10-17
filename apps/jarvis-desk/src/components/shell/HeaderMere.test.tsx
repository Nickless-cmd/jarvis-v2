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

  it('chat-fladen skjuler Visning og Side-opgaver — code beholder dem', () => {
    // Bjørn 17/10-2026: «i 3 priks menu'en skal visning fjernes og side-opgaver
    // menu. men kun for chat mode ikk for code mode».
    const medSideopgaver = [
      ...valg(),
      { id: 'sideopgaver', navn: 'Side-opgaver', ikon: null, aktiv: false, onClick: vi.fn() },
    ]

    render(<HeaderMere flade="chat" visning="normal" onVisning={() => {}} valg={medSideopgaver} />)
    fireEvent.click(screen.getByRole('button', { name: 'Flere valg' }))
    expect(screen.queryByRole('menuitemradio')).toBeNull()
    expect(screen.queryByText('Visning')).toBeNull()
    expect(screen.queryByRole('menuitemcheckbox', { name: /Side-opgaver/ })).toBeNull()
    // De øvrige valg står uændret.
    expect(screen.getByRole('menuitemcheckbox', { name: /Filer/ })).toBeInTheDocument()
  })

  it('code-fladen beholder Visning og Side-opgaver', () => {
    const medSideopgaver = [
      ...valg(),
      { id: 'sideopgaver', navn: 'Side-opgaver', ikon: null, aktiv: false, onClick: vi.fn() },
    ]
    render(<HeaderMere flade="code" visning="normal" onVisning={() => {}} valg={medSideopgaver} />)
    fireEvent.click(screen.getByRole('button', { name: 'Flere valg' }))
    expect(screen.getAllByRole('menuitemradio')).toHaveLength(3)
    expect(screen.getByText('Visning')).toBeInTheDocument()
    expect(screen.getByRole('menuitemcheckbox', { name: /Side-opgaver/ })).toBeInTheDocument()
  })
})
