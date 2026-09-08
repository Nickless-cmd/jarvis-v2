import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { ToolGroupCard } from './ToolGroupCard'
import type { ToolGroupBlock } from '../../lib/toolRounds'

function group(count: number): ToolGroupBlock {
  return {
    type: 'tool_group',
    kind: 'round',
    count,
    tools: Array.from({ length: count }, (_, i) => ({
      type: 'tool_use' as const,
      id: `t${i}`,
      name: 'read_file',
      input: { path: `/f/${i}` },
      status: 'done' as const,
      result: `content ${i}`,
    })),
  }
}

/**
 * Linjen er 1:1 med mobilens InlineToolGroup (Bjørn 8/9-2026). Teksten kommer
 * fra `summarizeRound` — samme regler som telefonen: ét kald viser sin egen
 * beskrivelse, flere ens tælles op, blandede bliver til «værktøjer».
 */
describe('ToolGroupCard', () => {
  it('flere ens kald tælles op — og er foldet som default', () => {
    render(<ToolGroupCard block={group(4)} density="compact" />)
    expect(screen.getByText('Læste 4 filer')).toBeInTheDocument()
    expect(screen.queryByText('Læs fil')).not.toBeInTheDocument()
    expect(screen.getByRole('button', { name: /Læste 4 filer/ })).toHaveAttribute(
      'aria-expanded',
      'false',
    )
  })

  it('ét kald viser sin egen beskrivelse — ikke en optælling', () => {
    // «Læste 1 fil» er en optælling af én ting. Mobilen viser i stedet HVAD:
    // «Læste 0» (filnavnet). Det er hele pointen med linjen.
    render(<ToolGroupCard block={group(1)} density="compact" />)
    expect(screen.getByText('Læste 0')).toBeInTheDocument()
  })

  it('udfolder til N tool-kort ved klik', async () => {
    const user = userEvent.setup()
    render(<ToolGroupCard block={group(3)} density="compact" />)
    await user.click(screen.getByRole('button', { name: /Læste 3 filer/ }))
    expect(screen.getByRole('button', { name: /Læste 3 filer/ })).toHaveAttribute(
      'aria-expanded',
      'true',
    )
    // Desk beholder sin funktion: de tre rigtige tool-kort med krop og metadata.
    expect(screen.getAllByText('Læs fil')).toHaveLength(3)
  })
})
