import { describe, expect, it, vi } from 'vitest'
import { parsePauseAsk, emitPauseSvar, onPauseSvar } from './pauseAsk'

const svar = (o: Record<string, unknown>) => JSON.stringify(o)

describe('parsePauseAsk', () => {
  it('parser resultatet når det kommer som JSON-streng fra disk', () => {
    // Tool-resultater eksternaliseres og kommer tilbage som strenge — det var
    // netop derfor kortet aldrig blev vist.
    const r = parsePauseAsk(svar({
      status: 'asked', kind: 'pause_and_ask',
      question: 'Skal jeg splitte filen først?', options: ['Ja, split', 'Nej, bare ret'],
      context: 'db.py er 33k linjer', urgency: 'high',
    }))
    expect(r?.question).toBe('Skal jeg splitte filen først?')
    expect(r?.options).toEqual(['Ja, split', 'Nej, bare ret'])
    expect(r?.urgency).toBe('high')
  })

  it('tager også objektet direkte', () => {
    expect(parsePauseAsk({ kind: 'pause_and_ask', question: 'Hvad nu?' })?.options).toEqual([])
  })

  it('rører ikke almindeligt tool-output', () => {
    expect(parsePauseAsk('bash: 42 filer ændret')).toBeNull()
    expect(parsePauseAsk(svar({ status: 'ok', stdout: 'hej' }))).toBeNull()
    expect(parsePauseAsk(undefined)).toBeNull()
  })

  it('afviser ugyldig JSON der tilfældigvis nævner navnet', () => {
    // Ellers ville en fejlbesked om værktøjet blive til et falsk kort.
    expect(parsePauseAsk('fejl i pause_and_ask: {ikke json')).toBeNull()
  })

  it('kræver et spørgsmål — et tomt kort hjælper ingen', () => {
    expect(parsePauseAsk(svar({ kind: 'pause_and_ask', question: '   ' }))).toBeNull()
  })

  it('holder sig til serverens lofter: 6 knapper, 120 tegn', () => {
    const r = parsePauseAsk(svar({
      kind: 'pause_and_ask', question: 'q',
      options: ['a', 'b', 'c', 'd', 'e', 'f', 'g', 'x'.repeat(121), ''],
    }))
    expect(r?.options).toEqual(['a', 'b', 'c', 'd', 'e', 'f'])
  })

  it('falder tilbage til normal ved ukendt hastegrad', () => {
    expect(parsePauseAsk(svar({ kind: 'pause_and_ask', question: 'q', urgency: 'PANIK' }))?.urgency)
      .toBe('normal')
  })
})

describe('pause-svar pub/sub', () => {
  it('når frem til lytteren og kan afmeldes', () => {
    const set = vi.fn()
    const af = onPauseSvar(set)
    emitPauseSvar('Ja, split')
    expect(set).toHaveBeenCalledWith('Ja, split')
    af()
    emitPauseSvar('igen')
    expect(set).toHaveBeenCalledTimes(1)
  })

  it('en lytter der kaster vælter ikke de andre', () => {
    const god = vi.fn()
    const af1 = onPauseSvar(() => { throw new Error('nej') })
    const af2 = onPauseSvar(god)
    emitPauseSvar('x')
    expect(god).toHaveBeenCalledWith('x')
    af1(); af2()
  })
})
