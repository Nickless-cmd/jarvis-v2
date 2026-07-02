import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { AboutPanel } from './AboutPanel'

describe('AboutPanel', () => {
  it('viser app-info + version', () => {
    render(<AboutPanel apiBaseUrl="https://api.srvlab.dk" role="owner" model="deepseek" />)
    expect(screen.getByText('J.A.R.V.I.S. Desktop')).toBeInTheDocument()
    expect(screen.getByText('https://api.srvlab.dk')).toBeInTheDocument()
    expect(screen.getByText('owner')).toBeInTheDocument()
    expect(screen.getByText('deepseek')).toBeInTheDocument()
    // version-celle findes (semver-ish)
    expect(screen.getByText(/^\d+\.\d+\.\d+/)).toBeInTheDocument()
  })

  it('viser dash for manglende felter', () => {
    render(<AboutPanel />)
    expect(screen.getAllByText('–').length).toBeGreaterThan(0)
  })
})
