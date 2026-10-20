/**
 * MÅLING, ikke en vagt: remounter slutsvaret når `finalAnswerStarted` skifter?
 *
 * ## Hvorfor denne fil findes (19/10-2026)
 *
 * Bjørn spurgte hvorfor ChatGPT's chat-view kan teleportere slutsvaret ud af
 * det foldede hoved uden at det hopper, mens vores gør det. Svaret fra deres
 * bundle: fasen er en EGENSKAB paa itemet, ikke en container det bor i — saa
 * React genbruger noden og teksten bliver bare ved med at stroemme ind i den
 * samme DOM-node.
 *
 * Hos os er `opdel(blocks, streaming && !finalAnswerStarted)` en graense der
 * FLYTTES: samme tekst ligger i `arbejde` mens turen koerer, og i `svar` naar
 * flaget falder. To containere = ny foraelder = remount.
 *
 * Denne test maaler om det faktisk sker. Den er skrevet FOER nogen rettelse,
 * saa tallet er beviset og ikke en foelge af hvad jeg haabede at finde.
 */
import { render } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import type { ContentBlock } from '../../lib/sseProtocol'

// Taeller mounts af tekst-blokke. `vi.mock` er hejset over importerne, saa
// RaekkeTranskript's `BlocksRenderer` er den mockede udgave naar den kaldes.
const mounts: string[] = []

// DELVIS mock: `RaekkeTranskript` importerer ogsaa `afslutForladteKald` herfra,
// saa kun `BlocksRenderer` erstattes. En fuld mock fik komponenten til at
// kaste foer den nogensinde naaede at rendere.
vi.mock('./BlocksRenderer', async (importOriginal) => {
  const actual = await importOriginal<typeof import('./BlocksRenderer')>()
  return {
    ...actual,
    BlocksRenderer: ({ blocks }: { blocks: ContentBlock[] }) => {
      for (const b of blocks) {
        if (b.type === 'text') mounts.push(b.text)
      }
      // Teksten SKAL med i outputtet: ellers kan testen ikke se om indholdet
      // er identisk foer og efter graensen — kun at containeren er ny.
      return <div data-testid="blocks">{blocks.map((b) => (b.type === 'text' ? b.text : '')).join('')}</div>
    },
  }
})

const { RaekkeTranskript } = await import('./RaekkeTranskript')

/** En tur: et vaerktoejskald, en syntese, og slutsvaret der lander bagefter. */
function tur(slutsvar: string): ContentBlock[] {
  return [
    { type: 'tool_use', id: 't1', name: 'bash', input: {} } as ContentBlock,
    { type: 'text', text: 'Lad mig se paa det.' } as ContentBlock,
    { type: 'text', text: slutsvar } as ContentBlock,
  ]
}

describe('RaekkeTranskript — remount ved fase-skiftet', () => {
  beforeEach(() => {
    mounts.length = 0
  })

  it('MAALER: slutsvaret remounter naar finalAnswerStarted bliver true', () => {
    const blocks = tur('Det er svaret.')

    // Foer grænsen: teksten ligger i arbejdet, svar-containeren er tom.
    const foer = render(<RaekkeTranskript blocks={blocks} streaming finalAnswerStarted={false} />)
    const mountsFoer = mounts.length

    // Graensen flyttes: samme blokke, samme tekst — kun flaget er nyt.
    foer.rerender(<RaekkeTranskript blocks={blocks} streaming finalAnswerStarted />)
    const mountsEfter = mounts.length

    // Tallet er det vi kom for. Er det 0, er der intet remount og intet at
    // rette. Er det > 0, er springet strukturelt og ikke et pacing-spoergsmaal.
    // eslint-disable-next-line no-console
    console.log(`[MAALING] mounts foer=${mountsFoer} efter=${mountsEfter} nye=${mountsEfter - mountsFoer}`)

    expect(mountsEfter).toBeGreaterThanOrEqual(mountsFoer)
  })

  it('MAALER: teksten staar i arbejdsomraadet foer graensen og i svar-containeren efter', () => {
    const blocks = tur('Det er svaret.')
    const view = render(<RaekkeTranskript blocks={blocks} streaming finalAnswerStarted={false} />)
    const foerTekst = view.container.textContent ?? ''
    view.rerender(<RaekkeTranskript blocks={blocks} streaming finalAnswerStarted />)
    const efterTekst = view.container.textContent ?? ''

    // Maalt 19/10-2026: teksten er SYNLIG begge steder — foer graensen som
    // mellemsvar inde i arbejdsomraadet, efter graensen i `rv-svar`. Det er
    // netop derfor et remount ikke kan ses paa teksten: indholdet er identisk,
    // kun foraelderen er ny. Derfor er `mounts` det eneste aerlige maal.
    expect(foerTekst).toContain('Det er svaret.')
    expect(efterTekst).toContain('Det er svaret.')
  })
})
