import { describe, it, expect } from 'vitest'
import { render } from '@testing-library/react'
import { MessageRow } from './MessageRow'
import { foldToolResults } from '../../lib/foldToolResults'
import crashContent from '../../lib/__fixtures__/crashContent.json'

// Repro (Bjørn 9. jul, sort skærm): den ægte persisterede content_json fra den
// run der crashede desk. 73 blokke, 36 tool-kald, FØRSTE tool_use har input som
// en rå JSON-STRENG (OpenAI function.arguments) i stedet for et objekt.
describe('MessageRow crasher IKKE på ægte crash-content_json', () => {
  it('renderer den persisterede (reload) form uden at kaste', () => {
    const blocks = foldToolResults(crashContent as Array<Record<string, unknown>>)
    expect(() => render(
      <MessageRow role="assistant" blocks={blocks as never} density="compact" streaming={false} />,
    )).not.toThrow()
  })

  it('renderer den under streaming (uden at kaste)', () => {
    const blocks = foldToolResults(crashContent as Array<Record<string, unknown>>)
    expect(() => render(
      <MessageRow role="assistant" blocks={blocks as never} density="compact" streaming />,
    )).not.toThrow()
  })
})
