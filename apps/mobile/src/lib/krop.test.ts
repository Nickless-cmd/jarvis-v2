import { kropFor, udenHale, pakUd, udDel, exitKode, filTekst, filnavn } from './krop'

describe('kropFor', () => {
  it('bash-familien er terminal — også de session-baserede', () => {
    for (const n of ['bash', 'operator_bash', 'bash_session_run', 'operator_run_in_background', 'phone_adb_shell']) {
      expect(kropFor(n)).toBe('terminal')
    }
  })

  it('fil-læsning er fil — begge stavemåder', () => {
    expect(kropFor('read_file')).toBe('fil')
    expect(kropFor('operator_read_file')).toBe('fil')
  })

  it('skrivning og redigering er diff', () => {
    for (const n of ['edit_file', 'operator_multi_edit', 'write_file', 'operator_write_file']) {
      expect(kropFor(n)).toBe('diff')
    }
  })

  it('alt andet falder til den rå form — det er ikke en fejl', () => {
    // Små status-objekter (`central_query`, `daemon_status`) ER feltlisten.
    // En ukendt form maa ikke gættes; den skal falde tilbage.
    expect(kropFor('central_query')).toBe('fald')
    expect(kropFor('findes_ikke_som_vaerktoej')).toBe('fald')
  })
})

describe('udenHale', () => {
  it('fjerner serverens interne instruks fra resultatet', () => {
    const med = '{"exit_code": 0}\n\n(⟳ Fortsaet: skriv en kort saetning.)'
    expect(udenHale(med)).toBe('{"exit_code": 0}')
  })

  it('roerer ikke et resultat uden hale', () => {
    expect(udenHale('hej')).toBe('hej')
  })
})

describe('pakUd', () => {
  it('pakker indpakkede result-skaller ud', () => {
    // Serveren lægger nogle gange resultatet i et objekt under `result`.
    const r = pakUd('{"result": {"exit_code": 3}}')
    expect(r.vaerdi).toEqual({ exit_code: 3 })
    expect(r.ramme).toEqual({ result: { exit_code: 3 } })
  })

  it('raa tekst uden JSON giver strengen selv og ingen ramme', () => {
    const r = pakUd('bare tekst')
    expect(r.vaerdi).toBe('bare tekst')
    expect(r.ramme).toBeNull()
  })

  it('tomt resultat giver tom streng', () => {
    expect(pakUd(undefined).vaerdi).toBe('')
  })
})

describe('udDel', () => {
  it('tager stdout og stderr — ikke hele JSON-blobben', () => {
    const r = '{"stdout": "fil1\\nfil2", "stderr": "advarsel", "exit_code": 0}'
    expect(udDel(r)).toBe('fil1\nfil2\nadvarsel')
  })

  it('falder tilbage til hele teksten naar der intet stdout er', () => {
    expect(udDel('ren tekst')).toBe('ren tekst')
  })

  it('tomt resultat giver tom streng', () => {
    expect(udDel(undefined)).toBe('')
  })
})

describe('exitKode', () => {
  it('laeser exit_code fra JSON', () => {
    expect(exitKode('{"exit_code": 7}', false)).toBe(7)
  })

  it('laeser ogsaa returncode og den indpakkede form', () => {
    expect(exitKode('{"returncode": 2}', false)).toBe(2)
    expect(exitKode('{"result": {"exit_code": 5}}', false)).toBe(5)
  })

  it('laeser tekstmaerket naar resultatet ikke er JSON', () => {
    expect(exitKode('noget output\n[exit code: 4]', false)).toBe(4)
  })

  it('falder tilbage paa fejlflaget — ikke paa et gæt', () => {
    expect(exitKode('ingen kode her', true)).toBe(1)
    expect(exitKode('ingen kode her', false)).toBe(0)
    expect(exitKode(undefined, false)).toBe(0)
  })
})

describe('filTekst', () => {
  it('tager content-feltet naar filen er pakket i JSON', () => {
    expect(filTekst('{"content": "linje 1\\nlinje 2"}')).toBe('linje 1\nlinje 2')
  })

  it('tager raa tekst naar filen ikke er pakket', () => {
    expect(filTekst('linje 1\nlinje 2')).toBe('linje 1\nlinje 2')
  })

  it('tomt resultat giver tom streng', () => {
    expect(filTekst(undefined)).toBe('')
  })
})

describe('filnavn', () => {
  it('giver sidste led af stien', () => {
    expect(filnavn('/media/projects/jarvis-v2/apps/mobile/src/lib/krop.ts')).toBe('krop.ts')
  })

  it('haandterer windows-stier', () => {
    expect(filnavn('C:\\Users\\bs\\note.txt')).toBe('note.txt')
  })
})
