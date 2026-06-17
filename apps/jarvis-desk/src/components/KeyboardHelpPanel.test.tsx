import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { KeyboardHelpPanel } from './KeyboardHelpPanel'

describe('KeyboardHelpPanel', () => {
  it('lister genvejene', () => {
    render(<KeyboardHelpPanel />)
    expect(screen.getByText('Tastaturgenveje')).toBeInTheDocument()
    expect(screen.getByText('Esc')).toBeInTheDocument()
    expect(screen.getByText('Stop igangværende svar')).toBeInTheDocument()
    expect(screen.getByText('Ctrl/Cmd + ,')).toBeInTheDocument()
  })
})
