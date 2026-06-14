/**
 * Ren linje-editor til Code-mode-terminalen (§17).
 *
 * xterm leverer rå tastetryk; denne modul oversætter dem til handlinger
 * (echo, submit, backspace, interrupt) uden at røre DOM/xterm — så logikken
 * kan unit-testes. v1 redigerer kun i slutningen af linjen (ingen pile-taster).
 */
export interface LineState {
  buffer: string
}

export type LineAction =
  | { type: 'none' }
  | { type: 'echo'; text: string }
  | { type: 'backspace' }
  | { type: 'submit'; command: string }
  | { type: 'interrupt' }

export const emptyLine: LineState = { buffer: '' }

const ENTER = '\r'
const CTRL_C = String.fromCharCode(3)
const CTRL_D = String.fromCharCode(4)
const DEL = String.fromCharCode(127)
const BACKSPACE = '\b'

/** Behandl ét tastetryk (xterm onData-streng). Returnerer ny tilstand + handling. */
export function handleKey(state: LineState, key: string): { state: LineState; action: LineAction } {
  if (key === ENTER) {
    return { state: emptyLine, action: { type: 'submit', command: state.buffer } }
  }
  if (key === CTRL_C) {
    return { state: emptyLine, action: { type: 'interrupt' } }
  }
  if (key === DEL || key === BACKSPACE) {
    if (!state.buffer) return { state, action: { type: 'none' } }
    return { state: { buffer: state.buffer.slice(0, -1) }, action: { type: 'backspace' } }
  }
  if (key === CTRL_D) {
    return { state, action: { type: 'none' } } // ignorér i v1
  }
  // Ignorér resterende kontrol-tegn og escape-sekvenser (pile-taster sendes
  // som ESC[…, dvs. første tegn er ESC/kontrol). Echo kun rent indtastbart.
  if (!key || key.charCodeAt(0) < 0x20) return { state, action: { type: 'none' } }
  return { state: { buffer: state.buffer + key }, action: { type: 'echo', text: key } }
}
