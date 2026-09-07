import { tolkDeling, kanModtage } from './shareIntake'

it('delt tekst bliver et udkast — den sendes IKKE af sig selv', () => {
  const h = tolkDeling({ text: 'noget jeg vil spørge om' })
  expect(h).toEqual({ slags: 'tekst', udkast: 'noget jeg vil spørge om' })
})

it('en delt URL genkendes som link', () => {
  const h = tolkDeling({ text: 'https://example.com/artikel' })
  expect(h.slags).toBe('link')
  if (h.slags === 'link') expect(h.url).toBe('https://example.com/artikel')
})

it('sidens titel kommer med, når browseren sender den', () => {
  const h = tolkDeling({ text: 'https://example.com', subject: 'En overskrift' })
  if (h.slags === 'link') expect(h.udkast).toBe('En overskrift\nhttps://example.com')
})

it('emnet gentages ikke, hvis teksten allerede indeholder det', () => {
  const h = tolkDeling({ text: 'En overskrift og resten', subject: 'En overskrift' })
  if (h.slags === 'tekst') expect(h.udkast).toBe('En overskrift og resten')
})

it('delte filer bærer deres URIer videre', () => {
  const h = tolkDeling({ uris: ['content://a', 'content://b'], mimeType: 'image/jpeg' })
  expect(h.slags).toBe('filer')
  if (h.slags === 'filer') expect(h.uris).toHaveLength(2)
})

it('tomme URIer filtreres fra frem for at blive til tomme vedhæftninger', () => {
  const h = tolkDeling({ uris: ['content://a', '', '   '] })
  if (h.slags === 'filer') expect(h.uris).toEqual(['content://a'])
})

it('en tom deling gør ingenting frem for at åbne en tom komposer', () => {
  expect(tolkDeling({})).toEqual({ slags: 'ingenting' })
  expect(tolkDeling({ text: '   ' })).toEqual({ slags: 'ingenting' })
})

it('siger ærligt hvad vi kan tage imod', () => {
  expect(kanModtage('text/plain')).toBe(true)
  expect(kanModtage('image/png')).toBe(true)
  expect(kanModtage('application/pdf')).toBe(true)
  expect(kanModtage('application/zip')).toBe(false)
  expect(kanModtage(undefined)).toBe(true)   // ren tekst har ofte ingen type
})
