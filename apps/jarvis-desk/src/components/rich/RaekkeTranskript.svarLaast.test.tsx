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
  it('skjuler hovedet igen når et nyt run arbejder efter det låste svar', () => {
    // VENDT 15/11-2026 (Bjørn): hovedet findes kun når folden er lukket.
    // Kommer der nyt arbejde efter svar-låsen, er turen ikke foldet længere —
    // og så er rundelinjen igen turens ansigt. Hovedet vender tilbage når det
    // nye arbejde er færdigt.
    const { container } = vis({ finalAnswerStarted: true, arbejdeEfterSvar: true })

    expect(container.querySelector('.rv-tur')).toBeNull()
    expect(container.querySelector('.rv-gruppe')).not.toHaveAttribute('hidden')
  })

  it('folder stadig sammen når svaret er begyndt UDEN arbejde bagefter', () => {
    const { container } = vis({ finalAnswerStarted: true })

    expect(container.querySelector('.rv-tur')).toHaveAttribute('aria-expanded', 'false')
  })
})
