import { describe, it, expect } from 'vitest'
import { diffFraResultat, diffStat } from './diffStat'

describe('diffStat', () => {
  it('edit_file → add/del from line diff', () => {
    const r = diffStat('edit_file', { old_string: 'a\nb\nc', new_string: 'a\nX\nc\nd' })
    expect(r).not.toBeNull()
    expect(r!.add).toBeGreaterThan(0)
    expect(r!.del).toBeGreaterThan(0)
  })

  it('operator_edit_file is recognised', () => {
    const r = diffStat('operator_edit_file', { old: 'x', new: 'y' })
    expect(r).not.toBeNull()
  })

  it('write_file → all lines are additions', () => {
    const r = diffStat('write_file', { content: 'l1\nl2\nl3' })
    expect(r).toEqual({ add: 3, del: 0 })
  })

  it('returns null for non-edit tools', () => {
    expect(diffStat('web_search', { query: 'x' })).toBeNull()
  })

  it('returns null when edit args are empty', () => {
    expect(diffStat('edit_file', {})).toBeNull()
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
