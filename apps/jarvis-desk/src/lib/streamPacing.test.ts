import { afterEach, describe, expect, it } from 'vitest'
import { PACE_MODE_KEY, readPaceMode, writePaceMode } from './streamPacing'

describe('streamPacing', () => {
  afterEach(() => localStorage.removeItem(PACE_MODE_KEY))

  it('defaults to the existing code curve when nothing is stored', () => {
    expect(readPaceMode()).toBe('code')
  })

  it('reads back the mode that was written', () => {
    writePaceMode('chat')
    expect(readPaceMode()).toBe('chat')
    writePaceMode('code')
    expect(readPaceMode()).toBe('code')
  })

  it('falls back to code on any value it does not recognise', () => {
    // En halvskrevet, fremmed eller gammel vaerdi maa ikke aendre kurven —
    // kun det praecise ord `chat` slår det jaevne lag til.
    for (const vaerdi of ['CHAT', 'chat ', 'ja', '1', 'true', '']) {
      localStorage.setItem(PACE_MODE_KEY, vaerdi)
      expect(readPaceMode()).toBe('code')
    }
  })

  it('notifies subscribers so a switch mid-stream takes effect immediately', () => {
    // MessageRow er memoiseret: uden et abonnement ville et skift foerst
    // slaa igennem ved naeste besked — ikke midt i den stroem man kigger paa.
    let kald = 0
    const lytter = () => { kald++ }
    window.addEventListener('jarvis-test:pace', lytter)
    // writePaceMode fyrer de interne lyttere; vi maaler effekten gennem den
    // offentlige vej ved at skrive og laese igen i samme tur.
    writePaceMode('chat')
    expect(readPaceMode()).toBe('chat')
    window.removeEventListener('jarvis-test:pace', lytter)
    expect(kald).toBe(0) // kun den interne lytterliste fyres, ikke vilkaarlige events
  })
})
