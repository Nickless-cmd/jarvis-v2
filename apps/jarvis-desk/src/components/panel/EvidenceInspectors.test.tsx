import { describe, expect, it, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { SourceInspector } from './SourceInspector'
import { ToolInspector } from './ToolInspector'
import type { SourceEvidence, ToolEvidence } from '../../lib/environmentEvidence'

const tool: ToolEvidence = {
  id: 't1', name: 'web_search', input: { query: 'wled firmware' }, status: 'done',
  result: 'Fandt https://kno.wled.ge/basics/getting-started/',
}
const source: SourceEvidence = {
  url: 'https://kno.wled.ge/basics/getting-started/',
  domaene: 'kno.wled.ge',
  toolUseId: 't1',
  toolName: 'web_search',
  input: tool.input,
  resultExcerpt: tool.result,
  origin: 'tool_result',
}

describe('SourceInspector', () => {
  it('åbner ikke websiden før brugeren trykker Åbn kilde', async () => {
    const open = vi.spyOn(window, 'open').mockImplementation(() => null)
    render(<SourceInspector source={source} tool={tool} />)
    expect(open).not.toHaveBeenCalled()
    expect(screen.getByText('wled firmware')).toBeInTheDocument()
    expect(screen.getByText(source.url)).toBeInTheDocument()
    await userEvent.click(screen.getByRole('button', { name: 'Åbn kilde' }))
    expect(open).toHaveBeenCalledWith(source.url, '_blank', 'noopener,noreferrer')
  })

  it('forklarer når en kilde kun kommer fra svarteksten', () => {
    render(<SourceInspector source={{ ...source, toolUseId: undefined, toolName: undefined, input: undefined, origin: 'assistant_text' }} />)
    expect(screen.getByText('Fra svartekst')).toBeInTheDocument()
  })
})

describe('ToolInspector', () => {
  it('viser struktureret input, status og råt fejlresultat', () => {
    render(<ToolInspector
      tool={{ id: 't2', name: 'web_search', input: { query: 'wled' }, status: 'error', result: 'timeout' }}
      onOpenSource={() => {}}
    />)
    expect(screen.getByText(/"query": "wled"/)).toBeInTheDocument()
    expect(screen.getByText('Fejlet')).toBeInTheDocument()
    expect(screen.getByText('timeout')).toBeInTheDocument()
  })

  it('åbner en relateret kilde i inspector-callbacket', async () => {
    const onOpenSource = vi.fn()
    render(<ToolInspector tool={tool} onOpenSource={onOpenSource} />)
    await userEvent.click(screen.getByRole('button', { name: /kno\.wled\.ge/ }))
    expect(onOpenSource).toHaveBeenCalledWith(expect.objectContaining({ domaene: 'kno.wled.ge', toolUseId: 't1' }))
  })

  it('folder store resultater ud på en eksplicit handling', async () => {
    const longResult = `start-${'x'.repeat(13_000)}-slut`
    render(<ToolInspector tool={{ ...tool, result: longResult }} onOpenSource={() => {}} />)
    expect(screen.queryByText(/-slut/)).not.toBeInTheDocument()
    await userEvent.click(screen.getByRole('button', { name: 'Vis hele resultatet' }))
    expect(screen.getByText(/-slut/)).toBeInTheDocument()
  })
})
