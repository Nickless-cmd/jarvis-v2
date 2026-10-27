import { describe, expect, it } from 'vitest'
import { dokFraResultat, erDokVaerktoej } from './dokFlade'

/** Tolkningen af de tre Google-læseres svar.
 *
 * Testen kører på RIGTIGE svarformer — kopieret fra hvad
 * `core/services/google_connector.py` returnerer, ikke fra hvad der ville være
 * bekvemt at parse. `sheets_read` giver `{status, range, values}`,
 * `docs_read` giver `{status, title, text}`, `slides_read` giver
 * `{status, title, slide_count, slides:[{slide,text}]}`.
 */

describe('erDokVaerktoej', () => {
  it('kender præcis de tre læsere', () => {
    expect(erDokVaerktoej('docs_read')).toBe(true)
    expect(erDokVaerktoej('sheets_read')).toBe(true)
    expect(erDokVaerktoej('slides_read')).toBe(true)
  })

  it('afviser søster-værktøjerne der ikke har en flade', () => {
    // Skrive-værktøjerne har intet svar at vise, og drive_search giver en
    // filliste — ikke et dokument. De skal ikke have en øje-knap.
    expect(erDokVaerktoej('docs_append')).toBe(false)
    expect(erDokVaerktoej('sheets_write')).toBe(false)
    expect(erDokVaerktoej('drive_search')).toBe(false)
    expect(erDokVaerktoej('drive_download')).toBe(false)
  })
})

describe('dokFraResultat — docs_read', () => {
  it('giver titel og tekst', () => {
    const flade = dokFraResultat('docs_read', JSON.stringify({
      status: 'ok', title: 'Mødenotater', text: 'Første afsnit.\n\nAndet afsnit.',
    }))
    expect(flade).toEqual({
      kind: 'docs', titel: 'Mødenotater', tekst: 'Første afsnit.\n\nAndet afsnit.',
    })
  })

  it('giver null når teksten er tom — der er intet at læse', () => {
    const flade = dokFraResultat('docs_read', JSON.stringify({
      status: 'ok', title: 'Tom', text: '',
    }))
    expect(flade).toBeNull()
  })
})

describe('dokFraResultat — sheets_read', () => {
  it('bevarer rækker og kolonner som de kom', () => {
    const flade = dokFraResultat('sheets_read', JSON.stringify({
      status: 'ok',
      range: 'Ark1!A1:B3',
      values: [['Navn', 'Alder'], ['Bo', '41'], ['Ida', '29']],
    }))
    expect(flade).toEqual({
      kind: 'sheets',
      interval: 'Ark1!A1:B3',
      raekker: [['Navn', 'Alder'], ['Bo', '41'], ['Ida', '29']],
    })
  })

  it('gør tal og huller til strenge uden at fjerne tomme celler', () => {
    // Google returnerer tal som tal og tomme celler som udeladte/null. En
    // tom kolonne er information om at arket HAR kolonnen — fjernede vi den,
    // ville forskudte rækker lyve om formen.
    const flade = dokFraResultat('sheets_read', JSON.stringify({
      status: 'ok', range: 'A1:C2', values: [[2013, null, 'x'], [1.5, '', 'y']],
    }))
    expect(flade).toMatchObject({
      raekker: [['2013', '', 'x'], ['1.5', '', 'y']],
    })
  })

  it('giver null for et tomt ark', () => {
    expect(dokFraResultat('sheets_read', JSON.stringify({
      status: 'ok', range: 'A1', values: [],
    }))).toBeNull()
  })
})

describe('dokFraResultat — slides_read', () => {
  it('giver slide-numre og tekst', () => {
    const flade = dokFraResultat('slides_read', JSON.stringify({
      status: 'ok', title: 'Kickoff', slide_count: 2,
      slides: [{ slide: 1, text: 'Velkomst' }, { slide: 2, text: 'Plan' }],
    }))
    expect(flade).toEqual({
      kind: 'slides', titel: 'Kickoff', antal: 2,
      slides: [{ nr: 1, tekst: 'Velkomst' }, { nr: 2, tekst: 'Plan' }],
    })
  })

  it('falder tilbage til rækkefølgen hvis slide-nummeret mangler', () => {
    const flade = dokFraResultat('slides_read', JSON.stringify({
      status: 'ok', title: '', slides: [{ text: 'a' }, { text: 'b' }],
    }))
    expect(flade).toMatchObject({ slides: [{ nr: 1, tekst: 'a' }, { nr: 2, tekst: 'b' }] })
  })
})

describe('dokFraResultat — det der IKKE skal give en flade', () => {
  it('giver null for et fejlsvar', () => {
    // `{status:"error", error:"docs_http_404"}` er en besked, ikke et
    // dokument. Den skal blive i tool-kortet, ikke åbne et tomt panel.
    for (const navn of ['docs_read', 'sheets_read', 'slides_read']) {
      expect(dokFraResultat(navn, JSON.stringify({ status: 'error', error: 'x_http_404' }))).toBeNull()
    }
  })

  it('giver null for tomt eller ugyldigt svar', () => {
    expect(dokFraResultat('docs_read', '')).toBeNull()
    expect(dokFraResultat('docs_read', undefined)).toBeNull()
    expect(dokFraResultat('docs_read', 'ikke json')).toBeNull()
    expect(dokFraResultat('docs_read', '[1,2,3]')).toBeNull()
  })

  it('giver null for et klippet svar — vi gætter ikke på resten', () => {
    const klippet = '{"status":"ok","values":[["Navn","Ald'
    expect(dokFraResultat('sheets_read', klippet)).toBeNull()
  })
})
