import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { UpdateCard } from './UpdateCard'

describe('UpdateCard', () => {
  it('available: viser version + kalder onUpdate', () => {
    const onUpdate = vi.fn()
    const onInstallNow = vi.fn()
    const onDismiss = vi.fn()
    render(<UpdateCard version="0.3.0" phase="available" onUpdate={onUpdate} onInstallNow={onInstallNow} onInstall={vi.fn()} onDismiss={onDismiss} />)
    expect(screen.getByText(/0\.3\.0/)).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Hent' }))
    expect(onUpdate).toHaveBeenCalled()
    fireEvent.click(screen.getByRole('button', { name: 'Installér nu' }))
    expect(onInstallNow).toHaveBeenCalled()
    fireEvent.click(screen.getByRole('button', { name: 'Luk opdatering' }))
    expect(onDismiss).toHaveBeenCalled()
  })

  it('ready: kalder onInstall', () => {
    const onInstall = vi.fn()
    const onDismiss = vi.fn()
    render(<UpdateCard version="0.3.0" phase="ready" onUpdate={vi.fn()} onInstallNow={vi.fn()} onInstall={onInstall} onDismiss={onDismiss} />)
    fireEvent.click(screen.getByRole('button', { name: /genstart/i }))
    expect(onInstall).toHaveBeenCalled()
    fireEvent.click(screen.getByRole('button', { name: 'Luk opdatering' }))
    expect(onDismiss).toHaveBeenCalled()
  })
})
