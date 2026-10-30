import { describe, it, expect } from 'vitest'
import { delIBlokke } from './markdownBlokke'

describe('delIBlokke', () => {
  it('koster det samme at dele 1600 blokke i ét kald som i fire', () => {
    // 29/9-2026: en kopi af resten af linjerne for hver tom linje gav
    // superlineær vækst. Mange små afsluttede blokke svarer til et langt stream.
    //
    // OMSKREVET 30/10-2026 efter en ÆGTE CI-fejl: den gamle form målte
    // `tid(1600 blokke) / tid(400 blokke)` og sammenlignede med 8. Den målte
    // 8.22 på UÆNDRET kode (run 41012450840, job «desk (lint + typecheck +
    // test)»). Årsagen er ikke støj: den lange arm udfører 4× arbejdet, og på
    // en runner med CPU-kvote rammer den kvoten mens den korte ikke gør. Så
    // bliver forholdet systematisk skævt opad, og `min` over batches hjælper
    // ikke — ALLE lange batches er ramt af samme kvote.
    //
    // Den nye form er ARBEJDSMATCHET: begge arme deler præcis 1600 blokke.
    //   arm Ét   = ét dokument på 1600 blokke
    //   arm Fire = fire dokumenter på 400 blokke, kaldt efter hinanden
    // Er koden lineær, koster de to det samme, og forholdet er ~1.0 uanset hvor
    // hurtig eller hvor hårdt kvotebelagt maskinen er — maskinens hastighed står
    // i BÅDE tæller og nævner og forkorter ud. Er koden superlineær, bliver arm
    // Ét markant dyrere, fordi den ene store kørsel betaler den kvadratiske pris.
    //
    // MÅLT 30/10-2026 (denne maskine, 7 par):
    //   lineær kode             median 1.07   (par: 0.81-1.40)
    //   hale-kopierende variant median 21.0   (par: 21.0-21.6)
    // Grænsen 3.0 ligger 2.8× over det lineære og 7× under regressionen.
    //
    // Batching (N kald pr. måling, divideret ud) er bevaret: én kørsel af det
    // lille dokument tager under én millisekund, og så bliver
    // `performance.now()`s opløsning en betydelig del af tallet.
    const dokument = (antal: number) => Array.from({ length: antal }, (_, i) =>
      `## Del ${i}\n${Array.from({ length: 15 }, (_, j) => `linje ${i}-${j}`).join('\n')}\n\n`,
    ).join('') + 'slut'
    const kort = dokument(400)
    const langt = dokument(1600)

    const maal = (tekst: string, N: number) => {
      const start = performance.now()
      for (let i = 0; i < N; i++) delIBlokke(tekst)
      return (performance.now() - start) / N
    }
    // 1600 blokke i ét kald
    const armEt = () => maal(langt, 4)
    // 1600 blokke fordelt på fire kald
    const armFire = () => {
      let sum = 0
      for (let i = 0; i < 4; i++) sum += maal(kort, 1)
      return sum
    }

    for (let i = 0; i < 2; i++) { armEt(); armFire() }

    // Interleaved, så begge arme møder samme CPU-frekvens og samme GC-tryk.
    // MEDIAN og ikke min: én enkelt forstyrret måling må ikke afgøre sagen i
    // nogen af retningerne.
    const par: number[] = []
    for (let i = 0; i < 7; i++) {
      const et = armEt()
      const fire = armFire()
      par.push(et / fire)
    }
    par.sort((a, b) => a - b)
    const median = par[Math.floor(par.length / 2)]!

    expect(median).toBeLessThan(3)
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
