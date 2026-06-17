import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { DependencyCard } from './DependencyCard'

describe('DependencyCard', () => {
  it('viser manglende værktøjer + installér kalder onInstall(tool)', () => {
    const onInstall = vi.fn()
    render(<DependencyCard missing={['git', 'gh']} onInstall={onInstall} onDismiss={vi.fn()} busy="" />)
    expect(screen.getByText('git')).toBeInTheDocument()
    fireEvent.click(screen.getAllByRole('button', { name: /installér/i })[0]!)
    expect(onInstall).toHaveBeenCalledWith('git')
  })

  it('tom liste → render intet', () => {
    const { container } = render(<DependencyCard missing={[]} onInstall={vi.fn()} onDismiss={vi.fn()} busy="" />)
    expect(container.firstChild).toBeNull()
  })
})
