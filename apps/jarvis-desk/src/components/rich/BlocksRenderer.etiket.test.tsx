/**
 * Den GEMTE runde-sætning (19/9-2026). Før blev den kun streamet og var væk
 * efter en genindlæsning. Nu gemmer serveren den som en `tool_use_summary`-
 * blok — Claude Desktops egen form — og den skal hele vejen fra besked til
 * linje: normalisering → opslag på kaldets id → linjens tekst.
 */
import { describe, expect, it } from 'vitest'
import { render } from '@testing-library/react'
import { BlocksRenderer, etiketterFraBlokke } from './BlocksRenderer'
import { foldToolResults } from '../../lib/foldToolResults'

const gemt = [
  { type: 'text', text: 'Jeg kigger.' },
  { type: 'tool_use', id: 'a', name: 'read_file', input: { path: '/x/token.py' } },
  { type: 'tool_result', tool_use_id: 'a', status: 'done', content: 'ok', is_error: false },
  { type: 'tool_use', id: 'b', name: 'read_file', input: { path: '/x/session.py' } },
  { type: 'tool_result', tool_use_id: 'b', status: 'done', content: 'ok', is_error: false },
  { type: 'text', text: 'Fundet.' },
  { type: 'tool_use_summary', summary: 'Fandt fejlen i tokenfornyelsen', preceding_tool_use_ids: ['a', 'b'] },
]

describe('den gemte runde-sætning', () => {
  it('overlever normaliseringen', () => {
    const blokke = foldToolResults(gemt as never)
    expect(blokke.some((b) => b.type === 'tool_use_summary')).toBe(true)
    expect(etiketterFraBlokke(blokke)).toEqual({ a: 'Fandt fejlen i tokenfornyelsen', b: 'Fandt fejlen i tokenfornyelsen' })
  })

  it('står på linjen efter en genindlæsning — uden live-strøm', () => {
    const { container } = render(
      <BlocksRenderer blocks={foldToolResults(gemt as never)} density="compact" streaming={false} />,
    )
    expect(container.querySelector('.linje-titel')!.textContent).toBe('Fandt fejlen i tokenfornyelsen')
  })

  it('deler ikke runden op — blokken tages ud før grupperingen', () => {
    const { container } = render(
      <BlocksRenderer blocks={foldToolResults(gemt as never)} density="compact" streaming={false} />,
    )
    expect(container.querySelectorAll('.toolgroup')).toHaveLength(1)
  })

  it('live vinder over gemt, hvis de er uenige', () => {
    const { container } = render(
      <BlocksRenderer blocks={foldToolResults(gemt as never)} density="compact" streaming={false}
        rundeEtiketter={{ a: 'Live sætning' }} />,
    )
    expect(container.querySelector('.linje-titel')!.textContent).toBe('Live sætning')
  })
})
