import { gyldigBindSti, interpolérUdtryk, udfoldKontrol, slaaOp, vurderUdtryk } from './udtryk'

const ctx = { seats: 12, pris: 29, navn: 'Bord', tom: '', liste: [3, 7, 11], objekt: { a: 1, b: 2 } }

describe('aritmetik', () => {
  it('regner det formen ikke kunne: {seats*29}', () => {
    expect(vurderUdtryk('seats * 29', ctx).vaerdi).toBe(348)
  })

  it('følger prioritetsreglerne', () => {
    expect(vurderUdtryk('2 + 3 * 4', ctx).vaerdi).toBe(14)
    expect(vurderUdtryk('(2 + 3) * 4', ctx).vaerdi).toBe(20)
    expect(vurderUdtryk('10 - 2 - 3', ctx).vaerdi).toBe(5)
    expect(vurderUdtryk('20 / 4 / 5', ctx).vaerdi).toBe(1)
  })

  it('håndterer modulo og unær minus', () => {
    expect(vurderUdtryk('10 % 3', ctx).vaerdi).toBe(1)
    expect(vurderUdtryk('-5 + 2', ctx).vaerdi).toBe(-3)
  })

  it('sammenligner tal og tekst', () => {
    expect(vurderUdtryk('seats > 10', ctx).vaerdi).toBe(true)
    expect(vurderUdtryk('seats <= 10', ctx).vaerdi).toBe(false)
    expect(vurderUdtryk('seats == 12', ctx).vaerdi).toBe(true)
    expect(vurderUdtryk('seats != 12', ctx).vaerdi).toBe(false)
    expect(vurderUdtryk('navn == "Bord"', ctx).vaerdi).toBe(true)
  })

  it('accepterer dansk decimalseparator i kilden', () => {
    expect(vurderUdtryk('29,5 * 2', ctx).vaerdi).toBe(59)
  })
})

describe('den lukkede funktionsliste', () => {
  it('round med og uden præcision', () => {
    expect(vurderUdtryk('round(3.7)', ctx).vaerdi).toBe(4)
    expect(vurderUdtryk('round(3.14159, 2)', ctx).vaerdi).toBe(3.14)
  })

  it('round advarer om en ugyldig præcision men regner videre', () => {
    const r = vurderUdtryk('round(3.14159, "to")', ctx)
    expect(r.vaerdi).toBe(3)
    expect(r.advarsler.join(' ')).toContain('round() ignored invalid precision')
  })

  it('pow', () => {
    expect(vurderUdtryk('pow(2, 10)', ctx).vaerdi).toBe(1024)
  })

  it('slice på tekst og array', () => {
    expect(vurderUdtryk('slice(navn, 0, 2)', ctx).vaerdi).toBe('Bo')
    expect(vurderUdtryk('slice(liste, 1, 3)', ctx).vaerdi).toEqual([7, 11])
  })

  it('slice returnerer den OPRINDELIGE værdi når kilden ikke kan slices', () => {
    // DIL's egen formulering — den er præcis, og den forklarer sig selv.
    const r = vurderUdtryk('slice(pris, 0, 2)', ctx)
    expect(r.vaerdi).toBe(29)
    expect(r.advarsler.join(' ')).toContain('is not sliceable')
  })

  it('keys', () => {
    expect(vurderUdtryk('keys(objekt)', ctx).vaerdi).toEqual(['a', 'b'])
  })

  it('keys defaulter til tom liste på noget der ikke er et objekt', () => {
    const r = vurderUdtryk('keys(pris)', ctx)
    expect(r.vaerdi).toEqual([])
    expect(r.advarsler.join(' ')).toContain('keys() defaulted')
  })

  it('all', () => {
    expect(vurderUdtryk('all(seats > 0, pris > 0)', ctx).vaerdi).toBe(true)
    expect(vurderUdtryk('all(seats > 0, pris > 100)', ctx).vaerdi).toBe(false)
  })

  it('formatSigFigs', () => {
    expect(vurderUdtryk('formatSigFigs(1234.5678, 3)', ctx).vaerdi).toBe(1230)
    expect(vurderUdtryk('formatSigFigs(0.00123456, 2)', ctx).vaerdi).toBe(0.0012)
  })

  it('expr evaluerer en streng som et nyt udtryk', () => {
    expect(vurderUdtryk('expr("seats * 2")', ctx).vaerdi).toBe(24)
  })

  it('expr stopper ved dybdegrænsen i stedet for at rekursere til stacken dør', () => {
    const r = vurderUdtryk('expr("expr(\\"expr(\\\\\\"expr(1)\\\\\\")\\")")', ctx)
    // Poenget er ikke hvad den svarer, men at den SVARER — ikke kaster og ikke fryser.
    expect(Array.isArray(r.advarsler)).toBe(true)
  })
})

describe('degradering frem for kast', () => {
  it('en ukendt funktion giver en advarsel, ikke en undtagelse', () => {
    const r = vurderUdtryk('hack(1)', ctx)
    expect(r.vaerdi).toBeUndefined()
    expect(r.advarsler.join(' ')).toContain('ukendt funktion')
  })

  it('en syntaksfejl giver en advarsel, ikke en undtagelse', () => {
    const r = vurderUdtryk('2 +', ctx)
    expect(r.vaerdi).toBeUndefined()
    expect(r.advarsler.length).toBeGreaterThan(0)
  })

  it('division med nul giver 0 og en advarsel — ikke Infinity', () => {
    const r = vurderUdtryk('5 / 0', ctx)
    expect(r.vaerdi).toBe(0)
    expect(r.advarsler.join(' ')).toContain('med nul')
  })

  it('en tekst i en aritmetisk position degraderer til 0 med advarsel', () => {
    const r = vurderUdtryk('navn * 2', ctx)
    expect(r.vaerdi).toBe(0)
    expect(r.advarsler.join(' ')).toContain('er ikke et tal')
  })

  it('en manglende bind giver undefined — ikke en advarsel om fejl', () => {
    const r = vurderUdtryk('findes_ikke', ctx)
    expect(r.vaerdi).toBeUndefined()
    expect(r.advarsler).toEqual([])
  })
})

describe('ingen vilkårlig kode', () => {
  it('afviser egenskabsadgang gennem en funktionskonstruktør', () => {
    // Rå `eval` ville have gjort dette til kode. Her er `constructor` blot et
    // navn der ikke findes i konteksten.
    expect(vurderUdtryk('constructor', ctx).vaerdi).toBeUndefined()
    expect(vurderUdtryk('this', ctx).vaerdi).toBeUndefined()
  })

  it('afviser en sti med et ulovligt segment', () => {
    // `objekt.a-b` er IKKE et ulovligt segment — det er gyldig subtraktion.
    // En sti er først ulovlig når den ikke kan slås op: her et indeks der
    // ikke er et tal, og et punktum uden et navn efter.
    const r = vurderUdtryk('liste[pris]', ctx)
    expect(r.vaerdi).toBeUndefined()
    expect(r.advarsler.length).toBeGreaterThan(0)
    expect(vurderUdtryk('objekt.', ctx).vaerdi).toBeUndefined()
  })

  it('afviser nøglen "state" som første segment', () => {
    const r = vurderUdtryk('state.x', { state: { x: 1 } })
    expect(r.vaerdi).toBeUndefined()
  })
})

describe('bind-stier', () => {
  it('accepterer de former vi bruger', () => {
    expect(gyldigBindSti('pris')).toBe(true)
    expect(gyldigBindSti('pris_a')).toBe(true)
    expect(gyldigBindSti('_pris')).toBe(true)
    expect(gyldigBindSti('objekt.a')).toBe(true)
    expect(gyldigBindSti('liste[0]')).toBe(true)
    expect(gyldigBindSti('liste[0].navn')).toBe(true)
  })

  it('afviser former der ikke kan slås op', () => {
    expect(gyldigBindSti('')).toBe(false)
    expect(gyldigBindSti('state')).toBe(false)
    expect(gyldigBindSti('1pris')).toBe(false)
    expect(gyldigBindSti('pris.')).toBe(false)
    expect(gyldigBindSti('liste[a]')).toBe(false)
    expect(gyldigBindSti('liste[-1]')).toBe(false)
    expect(gyldigBindSti('[0]')).toBe(false)
    expect(gyldigBindSti('a b')).toBe(false)
  })

  it('slår op i både objekter og arrays', () => {
    expect(slaaOp('seats', ctx)).toBe(12)
    expect(slaaOp('objekt.b', ctx)).toBe(2)
    expect(slaaOp('liste[1]', ctx)).toBe(7)
    expect(slaaOp('findes.ikke', ctx)).toBeUndefined()
  })
})

describe('interpolation i tekst', () => {
  it('regner udtryk og lader ukendte stå', () => {
    const r = interpolérUdtryk('{seats} pladser à {pris} kr = {seats * pris} kr', ctx)
    expect(r.tekst).toBe('12 pladser à 29 kr = 348 kr')
    expect(r.advarsler).toEqual([])
  })

  it('beholder det oprindelige udtryk når det ikke kan regnes', () => {
    // Det er kernen i degraderingen: en læser kan se at der står noget
    // forkert, hvor en tom plads ville se ud som om fladen ikke havde noget
    // at sige.
    const r = interpolérUdtryk('Pris: {ukendt_funktion(1)}', ctx)
    expect(r.tekst).toBe('Pris: {ukendt_funktion(1)}')
    expect(r.advarsler.length).toBeGreaterThan(0)
  })

  it('viser decimaler med dansk komma', () => {
    expect(interpolérUdtryk('{pris / 2}', ctx).tekst).toBe('14,5')
  })

  it('rører ikke tekst uden krølleparenteser', () => {
    const r = interpolérUdtryk('Ingen udtryk her', ctx)
    expect(r.tekst).toBe('Ingen udtryk her')
    expect(r.advarsler).toEqual([])
  })

  it('kaster aldrig — heller ikke på tom eller skæv tekst', () => {
    expect(() => interpolérUdtryk('{', ctx)).not.toThrow()
    expect(() => interpolérUdtryk('{}', ctx)).not.toThrow()
    expect(() => interpolérUdtryk('{ }{ }', ctx)).not.toThrow()
  })
})

describe('kontrolstrukturer (DIL lag 2)', () => {
  it('udfolder #each over en skalar liste', () => {
    expect(udfoldKontrol('{#each xs som x}[{x}]{/each}', { xs: [1, 2, 3] }).tekst).toBe('[1][2][3]')
  })

  it('udfolder #if/:else', () => {
    expect(udfoldKontrol('{#if a > 1}stor{:else}lille{/if}', { a: 0 }).tekst).toBe('lille')
  })

  it('degraderer til kildeteksten med en advarsel — kaster ikke', () => {
    const r = udfoldKontrol('{#each nope som x}{x}{/each}', {})
    expect(r.tekst).toBe('{#each nope som x}{x}{/each}')
    expect(r.advarsler.length).toBeGreaterThan(0)
  })

  it('interpolérUdtryk udfolder først og regner bagefter', () => {
    expect(interpolérUdtryk('{#each xs som x}{x};{/each}{1+1}', { xs: [1, 2] }).tekst).toBe('1;2;2')
  })
})
