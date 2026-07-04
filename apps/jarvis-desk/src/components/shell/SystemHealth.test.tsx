import { describe, it, expect } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { SystemHealth } from './SystemHealth'
import { parseCanonicalError } from '../../lib/canonicalError'

function err(sev: string, extra: Record<string, unknown> = {}) {
  const e = parseCanonicalError({ code: 'x', severity: sev, message: 'msg-' + sev, kind: 'tool.timeout', ...extra })
  return { ...e, receivedAt: Date.now() }
}

describe('SystemHealth', () => {
  it('ingen fejl → "Alt kører"', () => {
    render(<SystemHealth errors={[]} />)
    expect(screen.getByTitle('Alt kører')).toBeInTheDocument()
  })

  it('warning → "Nedsat"', () => {
    render(<SystemHealth errors={[err('warning')]} />)
    expect(screen.getByTitle('Nedsat')).toBeInTheDocument()
  })

  it('error → "Kræver opsyn"', () => {
    render(<SystemHealth errors={[err('error')]} />)
    expect(screen.getByTitle('Kræver opsyn')).toBeInTheDocument()
  })

  it('klik åbner transparens-log med correlation_id', () => {
    render(<SystemHealth errors={[err('error', { correlation_id: 'run-deadbeef' })]} />)
    fireEvent.click(screen.getByRole('button'))
    expect(screen.getByText('msg-error')).toBeInTheDocument()
    expect(screen.getByText('#run-dead')).toBeInTheDocument()
  })
})
