/**
 * Code mode: hovedet skal folde UD igen når der kommer arbejde efter låsen.
 *
 * Samme fejl som `ChatFlowPresentation.svarLaast.test.tsx` måler i chat mode —
 * Bjørn 29/10-2026: «hoved folder, streamen forsætter inde i hoved -> tom
 * skærm -> stream slut -> pace starter uden for tur hoved».
 *
 * Opgaven advarede om netop dette: der er FIRE kaldesteder (ChatView 1104/1118,
 * CodeView 1323/1330), og retter man kun chat, divergerer de to visninger.
 * Denne fil er code-modens vagt.
 */
import { render } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { RaekkeTranskript } from './RaekkeTranskript'
import { SettingsProvider } from '../../contexts/SettingsContext'
import type { ContentBlock } from '../../lib/sseProtocol'

const kald: ContentBlock = {
  type: 'tool_use', id: 't1', name: 'read_file', input: { path: '/x' }, status: 'done',
}

function vis(props: { finalAnswerStarted?: boolean; arbejdeEfterSvar?: boolean }) {
  return render(
    <SettingsProvider>
      <RaekkeTranskript blocks={[kald]} streaming {...props} />
    </SettingsProvider>,
  )
}

describe('RaekkeTranskript — arbejde efter svar-låsen', () => {
  it('holder det nye arbejde inde i det foldede hoved', () => {
    // VENDT 21/11-2026 (Bjørn: «Hoved folder foerst naar beskeden er faerdig..
    // Det skal ske naar slutbeskeden fortsaetter? Hvad goer GPT?»).
    //
    // Den forrige regel (15/11) lod det nye arbejde rive folden OP, saa
    // rundelinjen igen blev turens ansigt. Det gav to fejl maalt 20/11: folden
    // sprang op over et svar brugeren havde laest, og naar brugeren selv havde
    // foldet sammen, blev baade arbejdet og hovedet vaek — en TOM flade.
    //
    // GPT holder hovedet foldet og lægger det nye arbejde ind i det: deres
    // `completed` er sand saa laenge der findes assistent-indhold, uanset
    // `isStreaming`. Brugeren kan folde ud og se det, men turen skifter ikke
    // ansigt under dem.
    const { container } = vis({ finalAnswerStarted: true, arbejdeEfterSvar: true })

    expect(container.querySelector('.rv-tur')).toHaveAttribute('aria-expanded', 'false')
    expect(container.querySelector('.rv-gruppe')).toHaveAttribute('hidden')
  })

  it('folder stadig sammen når svaret er begyndt UDEN arbejde bagefter', () => {
    const { container } = vis({ finalAnswerStarted: true })

    expect(container.querySelector('.rv-tur')).toHaveAttribute('aria-expanded', 'false')
  })
})
