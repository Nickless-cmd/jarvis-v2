import { describe, it, expect } from 'vitest'
import { diffFraResultat, diffPar, diffStat } from './diffStat'

describe('diffStat', () => {
  // DET her var fejlen. Den gamle udgave af testen sendte `old_string` ind —
  // et navn værktøjet ikke bruger — og pinnede dermed sin egen fantasi.
  // Målt på CT105 over de seneste 400 svar med værktøjskald: 666 af 672
  // `edit_file`-kald bar `old_text`, 3 bar `old_string`. Derfor gav
  // rundelinjen i chat ingen tal overhovedet.
  it('læser edit_file på de navne værktøjet FAKTISK sender', () => {
    expect(diffStat('edit_file', { old_text: 'a\nb\nc', new_text: 'a\nX\nc\nd' }))
      .toEqual({ add: 4, del: 3 })
  })

  it('tager stadig imod de gamle *_string-navne', () => {
    expect(diffStat('edit_file', { old_string: 'a\nb', new_string: 'a' }))
      .toEqual({ add: 1, del: 2 })
  })

  // Tallene tælles som HELE blokke, ikke som en minimal diff — 1:1 med
  // serverens `linjetal`. Ville vi være pænere her, ville samme kald vise ét
  // tal mens det kører og et andet når serverens måling er inde.
  it('tæller hele blokke, som serveren gør', () => {
    expect(diffStat('edit_file', { old_text: 'x', new_text: 'x' }))
      .toEqual({ add: 1, del: 1 })
  })

  it('kender værktøjet på den anden side af broen', () => {
    expect(diffStat('operator_edit_file', { old_text: 'x', new_text: 'y' }))
      .toEqual({ add: 1, del: 1 })
  })

  it('multi_edit lægger sine ændringer sammen', () => {
    const r = diffStat('multi_edit', {
      edits: [
        { old_text: 'a', new_text: 'b\nc' },
        { old_text: 'd\ne', new_text: 'f' },
      ],
    })
    expect(r).toEqual({ add: 3, del: 3 })
  })

  it('write_file → alt er tilføjet', () => {
    expect(diffStat('write_file', { content: 'l1\nl2\nl3' })).toEqual({ add: 3, del: 0 })
  })

  // Claude Desktop 1:1 (19/9-2026): linjeskift + 1, så en afsluttende newline
  // tæller som en linje — «l1\nl2\n» er 3 hos dem. Før trak vi den fra, og
  // samme redigering viste ét tal hos os og et andet hos dem.
  it('tæller som Claude Desktop: linjeskift + 1', () => {
    expect(diffStat('write_file', { content: 'l1\nl2\n' })).toEqual({ add: 3, del: 0 })
  })

  // En sletning skal vise «−N +0». Talte tom streng som én linje, ville den
  // stå som «+1» for en linje der ikke findes.
  it('tom tekst er nul linjer, ikke én', () => {
    expect(diffStat('edit_file', { old_text: 'a\nb', new_text: '' }))
      .toEqual({ add: 0, del: 2 })
  })

  // Argumenterne ankommer som en streng under streaming — først som halv
  // streng, så som hel. Begge skal kunne tegnes uden at tråden vælter.
  it('tager imod argumenter som JSON-streng', () => {
    expect(diffStat('edit_file', '{"old_text":"a","new_text":"b\\nc"}'))
      .toEqual({ add: 2, del: 1 })
  })

  it('giver null på halve argumenter midt i streamen', () => {
    expect(diffStat('edit_file', '{"old_te')).toBeNull()
  })

  it('giver null for værktøjer der ikke ændrer filer', () => {
    expect(diffStat('web_search', { query: 'x' })).toBeNull()
  })

  it('giver null når edit-argumenterne er tomme', () => {
    expect(diffStat('edit_file', {})).toBeNull()
  })
})

// ─────────────────────────────────────────────────────────────────────────
// Parrene selv — den fælles kilde (Bjørn 23/9-2026)
//
// Kroppen i rækkevisningen byggede sin diff af `old_string`/`old_text` på
// TOPNIVEAU og krævede desuden `status === 'ok'` i resultatet. `multi_edit`
// bærer sine par i `edits[]`, og `operator_*` sender ingen status — så grenen
// faldt i gennem HVER gang og viste resultatets metadata (`replacements`,
// `edits`, `path`, `strategies`) i stedet for ændringen. Begge dele læser nu
// herfra, så «+N −M» i linjen og diffen i kroppen ikke kan sige hver sit.
// ─────────────────────────────────────────────────────────────────────────

describe('diffPar', () => {
  it('giver parret for et enkelt edit_file-kald', () => {
    expect(diffPar('edit_file', { old_text: 'a', new_text: 'b' }))
      .toEqual([{ gammel: 'a', ny: 'b' }])
  })

  it('læser multi_edit-parrene ud af edits[]', () => {
    expect(diffPar('multi_edit', { edits: [{ old_text: 'a', new_text: 'b' }, { old_text: 'c', new_text: 'd' }] }))
      .toEqual([{ gammel: 'a', ny: 'b' }, { gammel: 'c', ny: 'd' }])
  })

  it('tager også imod items[] og de gamle *_string-navne', () => {
    expect(diffPar('multi_edit', { items: [{ old_string: 'a', new_string: 'b' }] }))
      .toEqual([{ gammel: 'a', ny: 'b' }])
  })

  it('kender værktøjet på den anden side af broen', () => {
    expect(diffPar('operator_multi_edit', { edits: [{ old_text: 'a', new_text: 'b' }] }))
      .toEqual([{ gammel: 'a', ny: 'b' }])
  })

  // En indsættelse uden gammel tekst er et gyldigt par — og en sletning uden
  // ny tekst er det også. Kun når BEGGE sider mangler, er der intet at vise.
  it('beholder en ensidig indsættelse og en ensidig sletning', () => {
    expect(diffPar('edit_file', { new_text: 'ny' })).toEqual([{ gammel: '', ny: 'ny' }])
    expect(diffPar('edit_file', { old_text: 'gammel' })).toEqual([{ gammel: 'gammel', ny: '' }])
  })

  it('giver null når parrene ikke er kommet ind endnu', () => {
    expect(diffPar('edit_file', {})).toBeNull()
    expect(diffPar('edit_file', '{"old_te')).toBeNull()
    expect(diffPar('multi_edit', { edits: [] })).toBeNull()
  })

  it('giver null for værktøjer der ikke redigerer', () => {
    expect(diffPar('web_search', { query: 'x' })).toBeNull()
    expect(diffPar('write_file', { path: 'a', content: 'x' })).toBeNull()
  })

  it('tager imod argumenter som JSON-streng', () => {
    expect(diffPar('edit_file', '{"old_text":"a","new_text":"b"}'))
      .toEqual([{ gammel: 'a', ny: 'b' }])
  })
})

// ─────────────────────────────────────────────────────────────────────────
// Serveren måler nu, klienten behøver ikke gætte (14/9-2026) — 1:1 med mobilen
//
// `diffStat` regner ud af kaldets ARGUMENTER, og for `write_file` satte den
// altid `del: 0`. Den KUNNE ikke vide om filen fandtes. Serveren kan: den har
// filen i hånden lige før den skriver, og `edit_file`/`write_file` returnerer
// nu `linjer_tilfoejet`/`linjer_fjernet` målt på det faktiske indhold.
//
// Rækkefølgen er: målt slår gættet.
// ─────────────────────────────────────────────────────────────────────────

describe('diffFraResultat', () => {
  it('bruger serverens målte tal', () => {
    expect(diffFraResultat({ linjer_tilfoejet: 12, linjer_fjernet: 4 }))
      .toEqual({ add: 12, del: 4 })
  })

  it('tager imod en JSON-streng lige så vel som et objekt', () => {
    expect(diffFraResultat('{"linjer_tilfoejet":3,"linjer_fjernet":0}'))
      .toEqual({ add: 3, del: 0 })
  })

  it('giver null når serveren ikke har målt noget', () => {
    expect(diffFraResultat({ status: 'ok', text: 'hej' })).toBeNull()
  })

  it('giver null på et ufuldstændigt resultat midt i streamen', () => {
    expect(diffFraResultat('{"linjer_til')).toBeNull()
  })

  it('giver null på tomt og på vrøvl', () => {
    expect(diffFraResultat(undefined)).toBeNull()
    expect(diffFraResultat('')).toBeNull()
    expect(diffFraResultat('ikke json')).toBeNull()
  })

  it('accepterer et rent nul-nul resultat som MÅLT', () => {
    expect(diffFraResultat({ linjer_tilfoejet: 0, linjer_fjernet: 0 }))
      .toEqual({ add: 0, del: 0 })
  })

  it('afviser tal der ikke er tal', () => {
    expect(diffFraResultat({ linjer_tilfoejet: 'tolv', linjer_fjernet: 4 })).toBeNull()
  })
})
