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

  it('summer +/− i den foldede linje — serverens tal foerst', () => {
    // Bjoern saa tallene paa mobilen men ikke paa desk: her stod de kun inde i
    // hvert kort, og gruppen er foldet som standard.
    const block: ToolGroupBlock = {
      type: 'tool_group', kind: 'round', count: 2,
      tools: [
        { type: 'tool_use', id: 'e1', name: 'edit_file', input: { path: '/a' }, status: 'done',
          result: JSON.stringify({ linjer_tilfoejet: 3, linjer_fjernet: 1 }) },
        { type: 'tool_use', id: 'e2', name: 'write_file', input: { path: '/b', content: 'x' }, status: 'done',
          result: JSON.stringify({ linjer_tilfoejet: 10, linjer_fjernet: 4 }) },
      ],
    }
    render(<ToolGroupCard block={block} density="compact" />)
    const tal = screen.getByTestId('toolgroup-diffstat')
    expect(tal).toHaveTextContent('+13')
    expect(tal).toHaveTextContent('−5')
  })

  // Den gemte historik bærer INTET resultat: et `tool_use` i `content_json`
  // har kun id/input/name/type (målt paa CT105). Aabner man en gammel samtale,
  // er argumenterne derfor den eneste kilde til tallene — og lige praecis den
  // vej havde ingen daekning. Derfor stod chat-tråden uden +/− (Bjoern 18/9).
  it('regner tallene ud af argumenterne naar historikken ingen resultater har', () => {
    const block: ToolGroupBlock = {
      type: 'tool_group', kind: 'round', count: 2,
      tools: [
        { type: 'tool_use', id: 'e1', name: 'edit_file', status: 'done',
          input: { path: '/a', old_text: 'a\nb\nc', new_text: 'a\nX' } },
        { type: 'tool_use', id: 'e2', name: 'write_file', status: 'done',
          input: { path: '/b', content: 'x\ny\n' } },
      ],
    }
    render(<ToolGroupCard block={block} density="compact" />)
    const tal = screen.getByTestId('toolgroup-diffstat')
    expect(tal).toHaveTextContent('+4')   // 2 nye + 2 skrevne
    expect(tal).toHaveTextContent('−3')
  })

  it('en runde der kun laeste har ingen tal — ikke to nuller', () => {
    render(<ToolGroupCard block={group(3)} density="compact" />)
    expect(screen.queryByTestId('toolgroup-diffstat')).toBeNull()
  })
})
