import { describe, it, expect } from 'vitest'
import { delIBlokke } from './markdownBlokke'

describe('delIBlokke', () => {
  it('arbejdet ved 4× så mange blokke vokser omtrent lineært', () => {
    // 29/9-2026: en kopi af resten af linjerne for hver tom linje gav
    // superlineær vækst. Mange små afsluttede blokke svarer til et langt stream.
    const dokument = (antal: number) => Array.from({ length: antal }, (_, i) =>
      `## Del ${i}\n${Array.from({ length: 15 }, (_, j) => `linje ${i}-${j}`).join('\n')}\n\n`,
    ).join('') + 'slut'
    const kort = dokument(400)
    const langt = dokument(1600)

    // Kalibreret 8/10-2026. Tre forsøg på at måle denne egenskab er fejlet på
    // CI, alle af samme grund: de målte ÉN kørsel ad gangen, og én kørsel af
    // det lille dokument tager under én millisekund. Så bliver
    // `performance.now()`s opløsning og en enkelt GC-pause en betydelig del af
    // tallet. Målt på CI: 9.45 og 8.40 mod en grænse på 8 — på UÆNDRET kode.
    //
    // Den robuste form er tre ting på én gang:
    //  1. BATCH — hver måling er et gennemsnit over 6 kørsler, så tallet er
    //     flere millisekunder og kvantiseringen forsvinder.
    //  2. INTERLEAVED — kort og langt måles skiftevis, så begge møder samme
    //     CPU-frekvens og samme GC-tryk. Måler man dem i to blokke, kan én
    //     throttling- eller GC-fase ramme den ene gruppe alene.
    //  3. MINIMUM over 5 batches — den mindst forstyrrede måling viser den
    //     faktiske algoritmiske pris, og den er stabil på tværs af runners.
    //
    // Kalibreringen måler sin egen spredning: lineær vækst giver 4.32-4.49
    // (4% fra min til max over 12 runder), og den gamle hale-kopierende kode
    // giver 20.2. Grænsen 8 ligger altså 1,8× over det lineære og 2,5× under
    // regressionen — regressionsværnet er intakt.
    const maalBatch = (tekst: string) => {
      const N = 6
      const start = performance.now()
      for (let i = 0; i < N; i++) delIBlokke(tekst)
      return (performance.now() - start) / N
    }

    for (let i = 0; i < 2; i++) { maalBatch(kort); maalBatch(langt) }

    let bedsteKort = Infinity
    let bedsteLangt = Infinity
    for (let i = 0; i < 5; i++) {
      bedsteKort = Math.min(bedsteKort, maalBatch(kort))
      bedsteLangt = Math.min(bedsteLangt, maalBatch(langt))
    }

    expect(bedsteLangt / bedsteKort).toBeLessThan(8)
  })

  it('deler ved tomme linjer mellem afsnit, overskrifter og tabeller', () => {
    const md = '# Titel\n\nFørste afsnit.\n\n| a | b |\n|---|---|\n| 1 | 2 |\n\nSidste.'
    expect(delIBlokke(md)).toEqual(['# Titel\n', 'Første afsnit.\n', '| a | b |\n|---|---|\n| 1 | 2 |\n', 'Sidste.'])
  })

  it('deler ALDRIG inde i en kodeblok — heller ikke ved tomme linjer i den', () => {
    const md = 'Før.\n\n```ts\nconst a = 1\n\nconst b = 2\n```\n\nEfter.'
    expect(delIBlokke(md)).toEqual(['Før.\n', '```ts\nconst a = 1\n\nconst b = 2\n```\n', 'Efter.'])
  })

  it('en kortere fence inde i fire backticks kan ikke åbne for blokdeling', () => {
    const kode = '````md\n```\n\n**Vigtig overskrift**\n````'
    expect(delIBlokke(`${kode}\n\nEfter.`)).toEqual([`${kode}\n`, 'Efter.'])
  })

  it('en løs liste (tomme linjer mellem punkter) forbliver ÉN blok', () => {
    const md = '- et\n\n- to\n\n- tre\n\nAfsnit bagefter.'
    expect(delIBlokke(md)).toEqual(['- et\n\n- to\n\n- tre\n', 'Afsnit bagefter.'])
  })

  it('holder Jarvis’ 1 · punkter sammen under streaming', () => {
    const src = '**1 · Første.**\nDetalje.\n\n**2 · Andet.** Resten.\n\nEfter listen.'
    expect(delIBlokke(src)).toEqual(['**1 · Første.**\nDetalje.\n\n**2 · Andet.** Resten.\n', 'Efter listen.'])
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
