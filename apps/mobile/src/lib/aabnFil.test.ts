import { blokUrl } from './aabnFil'

// En UDGIVET fil baerer sin egen url og hentes over /files/{navn}. En
// VEDHAEFTNING baerer et attachment_id og hentes over det bruger-scopede
// /attachments/. De to har hver sin rute; en blok der blandede dem ville hente
// det forkerte sted.

describe('blokUrl', () => {
  const base = 'https://api.example.dk'

  it('udgivet fil med absolut url bruges som den er', () => {
    expect(blokUrl({ url: 'https://api.example.dk/files/a.html' }, base))
      .toBe('https://api.example.dk/files/a.html')
  })

  it('udgivet fil med relativ url foldes ud mod api-basen', () => {
    expect(blokUrl({ url: '/files/a.html' }, base))
      .toBe('https://api.example.dk/files/a.html')
  })

  it('vedhaeftet BILLEDE gaar til billed-ruten', () => {
    expect(blokUrl({ attachment_id: 'abc', type: 'image' }, base))
      .toBe('https://api.example.dk/attachments/image/abc')
  })

  it('vedhaeftet FIL gaar til den generelle rute', () => {
    expect(blokUrl({ attachment_id: 'abc', type: 'file' }, base))
      .toBe('https://api.example.dk/attachments/abc')
  })

  it('url vinder over attachment_id', () => {
    // En udgivet fil kan ogsaa have et id med; adressen skal foelge kilden.
    expect(blokUrl({ url: '/files/a.html', attachment_id: 'abc' }, base))
      .toBe('https://api.example.dk/files/a.html')
  })

  it('hverken url eller id giver tom streng, ikke en halv adresse', () => {
    // Kontrolarm: en halv adresse ville faa komponenten til at tegne et kort
    // der aabner ingenting.
    expect(blokUrl({}, base)).toBe('')
  })

  it('id med specialtegn bliver encodet', () => {
    expect(blokUrl({ attachment_id: 'a b/c', type: 'file' }, base))
      .toBe('https://api.example.dk/attachments/a%20b%2Fc')
  })
})
