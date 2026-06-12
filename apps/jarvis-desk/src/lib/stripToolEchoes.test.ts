import { describe, it, expect } from 'vitest'
import { stripToolEchoes } from './stripToolEchoes'

describe('stripToolEchoes', () => {
  it('fjerner [tool_result:…]-markør + read_tool_result-hint', () => {
    const src = '[tool_result:tool-result-57456a9dcd8b4d66ba68e76b0bee9bbc]\n[list_proposals]: No pending proposals.\nUse read_tool_result with result_id="tool-result-57456a9dcd8b4d66ba68e76b0bee9bbc" to inspect.'
    expect(stripToolEchoes(src)).toBe('')
  })

  it('fjerner ledende [tool_navn]: echo men beholder Jarvis\' prosa', () => {
    const src = '[list_proposals]: Pending proposals (14): noget rod\nNej — ingen plans ligger. Listen er tom.'
    const out = stripToolEchoes(src)
    expect(out).toContain('Nej — ingen plans ligger.')
    expect(out).not.toContain('[list_proposals]:')
  })

  it('rører ikke almindelig prosa', () => {
    const src = 'Her er mit svar.\n\n- punkt et\n- punkt to'
    expect(stripToolEchoes(src)).toBe(src)
  })

  it('rører ikke et [name]: midt i prosa (kun ledende echo)', () => {
    const src = 'Jeg svarer først.\n[note]: dette er ikke en tool-echo'
    const out = stripToolEchoes(src)
    expect(out).toContain('[note]: dette er ikke en tool-echo')
  })

  it('tom/uskadelig tekst er uændret', () => {
    expect(stripToolEchoes('')).toBe('')
    expect(stripToolEchoes('bare tekst')).toBe('bare tekst')
  })
})
