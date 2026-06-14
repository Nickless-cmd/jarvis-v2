import { describe, it, expect } from 'vitest'
import { handleKey, emptyLine } from './terminalLine'

const CTRL_C = String.fromCharCode(3)
const DEL = String.fromCharCode(127)
const ESC = String.fromCharCode(27)

describe('terminalLine.handleKey', () => {
  it('echo: tilføjer printbart tegn til buffer', () => {
    const r = handleKey(emptyLine, 'l')
    expect(r.state.buffer).toBe('l')
    expect(r.action).toEqual({ type: 'echo', text: 'l' })
  })

  it('bygger en kommando tegn for tegn', () => {
    let s = emptyLine
    for (const ch of 'ls -la') s = handleKey(s, ch).state
    expect(s.buffer).toBe('ls -la')
  })

  it('Enter: submitter buffer og nulstiller', () => {
    const r = handleKey({ buffer: 'pwd' }, '\r')
    expect(r.action).toEqual({ type: 'submit', command: 'pwd' })
    expect(r.state.buffer).toBe('')
  })

  it('Backspace (DEL): fjerner sidste tegn', () => {
    const r = handleKey({ buffer: 'lss' }, DEL)
    expect(r.state.buffer).toBe('ls')
    expect(r.action).toEqual({ type: 'backspace' })
  })

  it('Backspace på tom buffer: ingen handling', () => {
    const r = handleKey(emptyLine, DEL)
    expect(r.state.buffer).toBe('')
    expect(r.action).toEqual({ type: 'none' })
  })

  it('Ctrl-C: interrupt og nulstil buffer', () => {
    const r = handleKey({ buffer: 'sleep 99' }, CTRL_C)
    expect(r.action).toEqual({ type: 'interrupt' })
    expect(r.state.buffer).toBe('')
  })

  it('ignorerer escape-sekvenser (pile-taster sendes som ESC[…)', () => {
    const r = handleKey(emptyLine, ESC + '[A') // pil-op
    expect(r.state.buffer).toBe('')
    expect(r.action).toEqual({ type: 'none' })
  })
})
