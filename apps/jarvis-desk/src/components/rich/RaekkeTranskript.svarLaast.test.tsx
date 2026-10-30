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
  it('holder hovedet ÅBENT når et nyt run arbejder efter det låste svar', () => {
    const { container } = vis({ finalAnswerStarted: true, arbejdeEfterSvar: true })

    const hoved = container.querySelector('.rv-tur')
    expect(hoved).not.toBeNull()
    expect(hoved).toHaveAttribute('aria-expanded', 'true')
  })

  it('folder stadig sammen når svaret er begyndt UDEN arbejde bagefter', () => {
    const { container } = vis({ finalAnswerStarted: true })

    expect(container.querySelector('.rv-tur')).toHaveAttribute('aria-expanded', 'false')
  })
})
