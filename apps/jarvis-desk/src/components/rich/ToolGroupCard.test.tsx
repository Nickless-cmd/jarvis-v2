import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { ToolGroupCard } from './ToolGroupCard'
import type { ToolGroupBlock } from '../../lib/groupReadSearch'

function group(count: number): ToolGroupBlock {
  return {
    type: 'tool_group',
    kind: 'read_search',
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

describe('ToolGroupCard', () => {
  it('viser tælleren og er foldet som default', () => {
    render(<ToolGroupCard block={group(4)} density="compact" />)
    expect(screen.getByText(/Læste\/søgte 4 gange/)).toBeInTheDocument()
    // Foldet: de individuelle tool-kort-labels vises ikke endnu.
    expect(screen.queryByText('Læs fil')).not.toBeInTheDocument()
    expect(screen.getByRole('button', { name: /Læste\/søgte 4 gange/ })).toHaveAttribute(
      'aria-expanded',
      'false',
    )
  })

  it('udfolder til N tool-kort ved klik', async () => {
    const user = userEvent.setup()
    render(<ToolGroupCard block={group(3)} density="compact" />)
    await user.click(screen.getByRole('button', { name: /Læste\/søgte 3 gange/ }))
    expect(screen.getByRole('button', { name: /Læste\/søgte 3 gange/ })).toHaveAttribute(
      'aria-expanded',
      'true',
    )
    // De tre individuelle read-kort er nu synlige.
    expect(screen.getAllByText('Læs fil')).toHaveLength(3)
  })
})
