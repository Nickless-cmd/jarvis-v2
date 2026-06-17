import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { DataPrivacyPanel } from './DataPrivacyPanel'

describe('DataPrivacyPanel', () => {
  it('navngiver data, Google-scopes og GDPR-rettigheder', () => {
    render(<DataPrivacyPanel />)
    expect(screen.getByText('Data & privatliv')).toBeInTheDocument()
    expect(screen.getByText(/Chat-historik/)).toBeInTheDocument()
    expect(screen.getByText(/Gmail\/Kalender\/Drive/)).toBeInTheDocument()
    expect(screen.getByText(/aldrig dine data til\s*modeltræning/)).toBeInTheDocument()
    expect(screen.getByText(/Dine rettigheder \(GDPR\)/)).toBeInTheDocument()
  })
})
