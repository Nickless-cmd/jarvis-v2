import { describe, it, expect } from 'vitest'
import { delIBlokke } from './markdownBlokke'

describe('delIBlokke', () => {
  it('deler ved tomme linjer mellem afsnit, overskrifter og tabeller', () => {
    const md = '# Titel\n\nFørste afsnit.\n\n| a | b |\n|---|---|\n| 1 | 2 |\n\nSidste.'
    expect(delIBlokke(md)).toEqual(['# Titel\n', 'Første afsnit.\n', '| a | b |\n|---|---|\n| 1 | 2 |\n', 'Sidste.'])
  })

  it('deler ALDRIG inde i en kodeblok — heller ikke ved tomme linjer i den', () => {
    const md = 'Før.\n\n```ts\nconst a = 1\n\nconst b = 2\n```\n\nEfter.'
    expect(delIBlokke(md)).toEqual(['Før.\n', '```ts\nconst a = 1\n\nconst b = 2\n```\n', 'Efter.'])
  })

  it('en løs liste (tomme linjer mellem punkter) forbliver ÉN blok', () => {
    const md = '- et\n\n- to\n\n- tre\n\nAfsnit bagefter.'
    expect(delIBlokke(md)).toEqual(['- et\n\n- to\n\n- tre\n', 'Afsnit bagefter.'])
  })

  it('en indrykket fortsættelse hører til blokken over', () => {
    const md = '1. punkt\n\n   mere om punktet\n\nNyt afsnit.'
    expect(delIBlokke(md)).toEqual(['1. punkt\n\n   mere om punktet\n', 'Nyt afsnit.'])
  })

  it('samlet giver blokkene den oprindelige tekst (intet tabt, intet tilføjet)', () => {
    const md = '# A\n\ntekst\n\n```\nx\n\ny\n```\n\n- a\n\n- b\n\nslut'
    expect(delIBlokke(md).join('\n')).toBe(md)
  })

  it('den sidste blok er den levende — ingen afsluttende newline', () => {
    const b = delIBlokke('Afsnit.\n\nHalvt skrevet sæt')
    expect(b[b.length - 1]).toBe('Halvt skrevet sæt')
  })
})
