import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { UpdateCard } from './UpdateCard'

describe('UpdateCard', () => {
  it('available: viser version + kalder onUpdate', () => {
    const onUpdate = vi.fn()
    render(<UpdateCard version="0.3.0" phase="available" onUpdate={onUpdate} onInstall={vi.fn()} onDismiss={vi.fn()} />)
    expect(screen.getByText(/0\.3\.0/)).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: /opdat/i }))
    expect(onUpdate).toHaveBeenCalled()
  })

  it('ready: kalder onInstall', () => {
    const onInstall = vi.fn()
    render(<UpdateCard version="0.3.0" phase="ready" onUpdate={vi.fn()} onInstall={onInstall} onDismiss={vi.fn()} />)
    fireEvent.click(screen.getByRole('button', { name: /genstart/i }))
    expect(onInstall).toHaveBeenCalled()
  })
})
