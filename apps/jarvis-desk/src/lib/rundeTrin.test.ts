import { describe, expect, it } from 'vitest'
import { arbejdsTrin, fejlede, trinMeta, uafsluttede } from './rundeTrin'
import type { ArbejdsElement } from './raekkeModel'
import type { ContentBlock } from './sseProtocol'

/**
 * Bjørn 15/11-2026: «den aktive runde viser processen, afsluttede runder viser
 * resultatet». Vagten her måler det der gør forskellen mellem en statusflade
 * og teater: trinnene er de FAKTISKE kald, og et kald der aldrig svarede må
 * ikke se ud som om det gjorde.
 */

const kald = (
  id: string,
  navn: string,
  input: Record<string, unknown> = {},
  status?: 'running' | 'done' | 'error',
): ArbejdsElement => ({
  slags: 'blok',
  blok: { type: 'tool_use', id, name: navn, input, ...(status ? { status } : {}) } as ContentBlock,
})

const tekst = (t: string): ArbejdsElement => ({ slags: 'mellemsvar', tekst: t })

const tanke = (): ArbejdsElement => ({
  slags: 'blok',
  blok: { type: 'thinking', thinking: 'Jeg skal først se filen.' } as ContentBlock,
})

describe('arbejdsTrin — rundens faktiske kald', () => {
  it('giver ét trin pr. værktøjskald, i kaldets rækkefølge', () => {
    const trin = arbejdsTrin([
      kald('a', 'bash', { command: 'git status' }, 'done'),
      kald('b', 'bash', { command: 'npx vitest run' }, 'running'),
    ], true)
    expect(trin.map((t) => t.id)).toEqual(['a', 'b'])
    expect(trin[0]!.tekst).toContain('git status')
    expect(trin[1]!.tekst).toContain('npx vitest')
  })

  it('springer alt der ikke er et kald over — tanker og synteser er ikke trin', () => {
    const trin = arbejdsTrin([tanke(), kald('a', 'bash', { command: 'ls' }, 'done'), tekst('Så kører det.')], true)
    expect(trin).toHaveLength(1)
    expect(trin[0]!.id).toBe('a')
  })

  it('oversætter kaldets status til trinnets tilstand', () => {
    const trin = arbejdsTrin([
      kald('a', 'bash', { command: 'ls' }, 'done'),
      kald('b', 'bash', { command: 'pwd' }, 'running'),
      kald('c', 'bash', { command: 'false' }, 'error'),
    ], true)
    expect(trin.map((t) => t.status)).toEqual(['done', 'active', 'failed'])
  })

  it('et kald uden status tælles som kørende mens runden er aktiv', () => {
    const trin = arbejdsTrin([kald('a', 'bash', { command: 'ls' })], true)
    expect(trin[0]!.status).toBe('active')
  })

  it('et kald der aldrig svarede bliver ÆRLIGT afbrudt når runden er slut', () => {
    const trin = arbejdsTrin([kald('a', 'bash', { command: 'sleep 900' }, 'running')], false)
    expect(trin[0]!.status).toBe('afbrudt')
    expect(trin[0]!.note).toBe('uden resultat')
    // Datid: det må ikke lyde som om det stadig arbejder.
    expect(trin[0]!.tekst).not.toMatch(/…$/)
  })

  it('giver tom liste for en runde uden kald', () => {
    expect(arbejdsTrin([], true)).toEqual([])
    expect(arbejdsTrin([tanke(), tekst('kun ord')], true)).toEqual([])
  })
})

describe('trinMeta — hvad den afsluttede runde lover om sit indhold', () => {
  const tre = arbejdsTrin([
    kald('a', 'bash', { command: 'ls' }, 'done'),
    kald('b', 'bash', { command: 'pwd' }, 'done'),
    kald('c', 'bash', { command: 'whoami' }, 'done'),
  ], false)

  it('siger INTET når alt gik som det skulle — antallet var staffage', () => {
    // Bjørn 15/11-2026: «1 arbejdstrin · Fold ud» skulle væk fra selve
    // rundelinjen. Pilen viser at rækken kan foldes; tallet sagde intet om
    // udfaldet.
    expect(trinMeta(tre)).toBe('')
  })

  it('nævner afbrudte trin — en ufuldstændig runde må ikke se færdig ud', () => {
    const blandet = arbejdsTrin([
      kald('a', 'bash', { command: 'ls' }, 'done'),
      kald('b', 'bash', { command: 'pwd' }, 'running'),
    ], false)
    expect(uafsluttede(blandet)).toBe(1)
    expect(trinMeta(blandet)).toContain('1 uden resultat')
  })

  it('nævner fejlede trin', () => {
    const medFejl = arbejdsTrin([
      kald('a', 'bash', { command: 'ls' }, 'done'),
      kald('b', 'bash', { command: 'false' }, 'error'),
    ], false)
    expect(fejlede(medFejl)).toBe(1)
    expect(trinMeta(medFejl)).toContain('1 fejlede')
  })

  it('giver tom tekst for en runde uden trin', () => {
    expect(trinMeta([])).toBe('')
  })
})
