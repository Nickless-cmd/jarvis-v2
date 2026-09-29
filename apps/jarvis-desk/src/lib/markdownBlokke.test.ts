import { describe, it, expect } from 'vitest'
import { delIBlokke } from './markdownBlokke'

describe('delIBlokke', () => {
  it('arbejdet ved dobbelt så mange blokke vokser omtrent lineært', () => {
    // 29/9-2026: en kopi af resten af linjerne for hver tom linje gav
    // superlineær vækst. Mange små afsluttede blokke svarer til et langt stream.
    const dokument = (antal: number) => Array.from({ length: antal }, (_, i) =>
      `## Del ${i}\n${Array.from({ length: 15 }, (_, j) => `linje ${i}-${j}`).join('\n')}\n\n`,
    ).join('') + 'slut'
    const kort = dokument(300)
    const langt = dokument(600)
    const maal = (tekst: string) => {
      const tider: number[] = []
      for (let i = 0; i < 12; i++) {
        const start = performance.now()
        delIBlokke(tekst)
        tider.push(performance.now() - start)
      }
      tider.sort((a, b) => a - b)
      return tider[6]!
    }
    maal(kort)
    maal(langt)
    expect(maal(langt) / maal(kort)).toBeLessThan(2.7)
  })

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
