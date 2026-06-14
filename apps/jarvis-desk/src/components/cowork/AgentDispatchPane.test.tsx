import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { AgentDispatchPane } from './AgentDispatchPane'
import { buildAgentDispatchView } from '../../lib/coworkApi'

describe('AgentDispatchPane', () => {
  it('viser dispatch-agenter med status', () => {
    const view = buildAgentDispatchView({
      mode: 'dispatch',
      decision: { reason: '2 signaler' },
      plan: [
        { role: 'researcher', goal: 'find filer', parallel: true },
        { role: 'executor', goal: 'implementer', parallel: true },
      ],
      spawned: [{ agent_id: 'a1' }, { error: 'budget' }],
    })
    render(<AgentDispatchPane view={view} />)
    expect(screen.getByText('researcher')).toBeInTheDocument()
    expect(screen.getByText(/2 agenter/)).toBeInTheDocument()
    expect(screen.getByText(/1 fejl/)).toBeInTheDocument()
  })

  it('inline-tilstand', () => {
    const view = buildAgentDispatchView({ mode: 'inline', decision: { reason: 'simpel' } })
    render(<AgentDispatchPane view={view} />)
    expect(screen.getByText(/inline/i)).toBeInTheDocument()
  })

  it('tom tilstand', () => {
    render(<AgentDispatchPane view={null} />)
    expect(screen.getByText(/ingen agenter/i)).toBeInTheDocument()
  })
})
