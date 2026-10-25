import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { MessageRow } from './MessageRow'
import type { ContentBlock } from '../../lib/sseProtocol'

/**
 * To ting Bjørn pegede på 25/10-2026, som begge har samme rod:
 *
 * 1. «Redigerede X filer» skal KUN vises i code mode — ikke i chat mode.
 * 2. Felterne i bunden (kilder, redigerede filer) blev vist FØR pacen var
 *    færdig. De skal rulle ind med pacen, ikke springe frem.
 *
 * Roden til (2): begge felter var gated på `!streaming`. Men `streaming`
 * bliver falsk når SSE'en er done — ikke når teksten er rullet færdig på
 * skærmen. Mellem de to tidspunkter stod felterne derfor færdige under en
 * tekst der stadig skrev sig ind.
 *
 * Kontrakten findes allerede: `paceFinalAnswer` er sand mens pacingen kører,
 * og bliver falsk når `onAnswerPaced` har meldt færdig. Felterne skal vente
 * på den — ikke på `streaming`.
 */

const REDIGERING: ContentBlock[] = [
  {
    type: 'tool_use', id: 'e1', name: 'edit_file',
    input: { path: 'src/app.ts', old_text: 'før', new_text: 'efter' },
    status: 'done', result: '{"linjer_tilfoejet":9,"linjer_fjernet":4}',
  },
  { type: 'text', text: 'Filen er rettet.' },
]

const MED_KILDE: ContentBlock[] = [
  {
    type: 'tool_use', id: 'w1', name: 'web_search',
    input: { query: 'test' }, status: 'done',
    result: 'https://api.srvlab.dk/side',
  },
  { type: 'text', text: 'Her er svaret.' },
]

describe('MessageRow — bunden venter på pacen', () => {
  it('viser «Redigerede» i code mode', () => {
    const { container } = render(<MessageRow presentation="code" role="assistant" blocks={REDIGERING}
      density="compact" streaming={false} />)
    expect(container.querySelector('.edited-files')).not.toBeNull()
  })

  it('viser IKKE «Redigerede» i chat mode — feltet hører til maskinrummet', () => {
    const { container } = render(<MessageRow presentation="chat" chatMode="living" status="done"
      role="assistant" blocks={REDIGERING} density="compact" streaming={false} />)
    expect(container.querySelector('.edited-files')).toBeNull()
    expect(screen.queryByText(/Redigerede/)).not.toBeInTheDocument()
  })

  it('holder kilderne tilbage mens pacen stadig ruller', () => {
    const { container } = render(<MessageRow presentation="chat" chatMode="living" status="done"
      role="assistant" blocks={MED_KILDE} density="compact" streaming={false}
      paceFinalAnswer />)
    expect(container.querySelector('.msg-kilder')).toBeNull()
  })

  it('viser kilderne når pacen er færdig', () => {
    const { container } = render(<MessageRow presentation="chat" chatMode="living" status="done"
      role="assistant" blocks={MED_KILDE} density="compact" streaming={false}
      paceFinalAnswer={false} />)
    expect(container.querySelector('.msg-kilder')).not.toBeNull()
  })

  it('holder «Redigerede» tilbage i code mode mens pacen ruller', () => {
    const { container } = render(<MessageRow presentation="code" role="assistant" blocks={REDIGERING}
      density="compact" streaming={false} paceFinalAnswer />)
    expect(container.querySelector('.edited-files')).toBeNull()
  })
})
