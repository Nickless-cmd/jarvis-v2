import { describe, it, expect, vi } from 'vitest'
import { render, fireEvent } from '@testing-library/react'
import { GlobalShortcuts } from './GlobalShortcuts'

describe('GlobalShortcuts', () => {
  it('Esc stopper når der genereres', () => {
    const onStop = vi.fn()
    render(<GlobalShortcuts working={true} onStop={onStop} onSettings={vi.fn()} />)
    fireEvent.keyDown(window, { key: 'Escape' })
    expect(onStop).toHaveBeenCalled()
  })

  it('Esc gør intet når der IKKE genereres', () => {
    const onStop = vi.fn()
    render(<GlobalShortcuts working={false} onStop={onStop} onSettings={vi.fn()} />)
    fireEvent.keyDown(window, { key: 'Escape' })
    expect(onStop).not.toHaveBeenCalled()
  })

  it('Ctrl+, åbner settings', () => {
    const onSettings = vi.fn()
    render(<GlobalShortcuts working={false} onStop={vi.fn()} onSettings={onSettings} />)
    fireEvent.keyDown(window, { key: ',', ctrlKey: true })
    expect(onSettings).toHaveBeenCalled()
  })

  it('Cmd+, åbner settings (Mac)', () => {
    const onSettings = vi.fn()
    render(<GlobalShortcuts working={false} onStop={vi.fn()} onSettings={onSettings} />)
    fireEvent.keyDown(window, { key: ',', metaKey: true })
    expect(onSettings).toHaveBeenCalled()
  })


  it('Ctrl+K åbner søgning', () => {
    const onSearch = vi.fn()
    render(<GlobalShortcuts working={false} onStop={vi.fn()} onSettings={vi.fn()} onSearch={onSearch} />)
    fireEvent.keyDown(window, { key: 'k', ctrlKey: true })
    expect(onSearch).toHaveBeenCalled()
  })

  it('afmelder listener ved unmount', () => {
    const onSettings = vi.fn()
    const { unmount } = render(<GlobalShortcuts working={false} onStop={vi.fn()} onSettings={onSettings} />)
    unmount()
    fireEvent.keyDown(window, { key: ',', ctrlKey: true })
    expect(onSettings).not.toHaveBeenCalled()
  })
})
