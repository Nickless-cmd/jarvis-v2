import { describe, it, expect } from 'vitest'
import { render } from '@testing-library/react'
import { MessageRow } from './MessageRow'
import type { ContentBlock } from '../../lib/sseProtocol'

// Regression (Bjørn 10. jul, 2. crash — render ved svar-slut): et SPARSOMT
// blocks-array (undefined-hul fra foldet tool_result-content-blok) render'et
// ved !streaming crashede i blocksToPlainText/detectArtifacts (uden om per-
// besked-hegnet, fanget af top-hegnet). Fix: MessageRow denseBlocks'er ved
// indgangen. Her bygger vi et ægte sparsomt array og render'er begge tilstande.
describe('MessageRow crasher ikke på sparsomt array', () => {
  const sparse: ContentBlock[] = []
  sparse[0] = { type: 'text', text: 'før' }
  sparse[1] = { type: 'tool_use', id: 't1', name: 'bash', input: {}, status: 'done', result: 'ok' }
  // index 2 = hul (aldrig sat)
  sparse[3] = { type: 'text', text: 'efter' }

  it('render ved svar-slut (!streaming) kaster ikke', () => {
    expect(() => render(
      <MessageRow role="assistant" blocks={sparse} density="compact" streaming={false} />,
    )).not.toThrow()
  })

  it('render under streaming kaster ikke', () => {
    expect(() => render(
      <MessageRow role="assistant" blocks={sparse} density="compact" streaming />,
    )).not.toThrow()
  })

  it('viser begge tekst-blokke (hullet droppet, ikke renderet)', () => {
    const { container } = render(
      <MessageRow role="assistant" blocks={sparse} density="compact" streaming={false} />,
    )
    expect(container.textContent).toContain('før')
    expect(container.textContent).toContain('efter')
  })
})
