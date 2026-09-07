import { byggeKontekster, sorteretTilVisning } from './recentContexts'

const grund = {
  kameraTilladt: true, lokationsPraecision: 'precise' as const,
  udklipHarTekst: true, enhedsNavn: 'Pixel', sidsteFil: 'rapport.pdf',
}

it('samler alle fem kilder ét sted', () => {
  expect(byggeKontekster(grund).map((p) => p.slags))
    .toEqual(['kamera', 'lokation', 'fil', 'udklip', 'enhed'])
})

it('en slået-fra kontekst vises med GRUNDEN, ikke som en død knap', () => {
  const p = byggeKontekster({ ...grund, kameraTilladt: false })
  const kamera = p.find((x) => x.slags === 'kamera')!
  expect(kamera.tilgaengelig).toBe(false)
  expect(kamera.detalje).toMatch(/slået fra/)
})

it('viser aldrig udklipsholderens INDHOLD — kun at der er noget', () => {
  const u = byggeKontekster(grund).find((x) => x.slags === 'udklip')!
  expect(u.detalje).toBe('Der ligger tekst klar')
})

it('sidste fil er en genvej, ikke en betingelse', () => {
  const uden = byggeKontekster({ ...grund, sidsteFil: undefined }).find((x) => x.slags === 'fil')!
  expect(uden.tilgaengelig).toBe(true)
  expect(uden.detalje).toBe('Vælg fra enheden')
  const med = byggeKontekster(grund).find((x) => x.slags === 'fil')!
  expect(med.detalje).toContain('rapport.pdf')
})

it('lokation slået fra er ikke tilgængelig', () => {
  const l = byggeKontekster({ ...grund, lokationsPraecision: 'off' })
    .find((x) => x.slags === 'lokation')!
  expect(l.tilgaengelig).toBe(false)
})

it('ukendt enhed er ærlig frem for tom', () => {
  const e = byggeKontekster({ ...grund, enhedsNavn: undefined }).find((x) => x.slags === 'enhed')!
  expect(e.detalje).toBe('Ukendt enhed')
  expect(e.tilgaengelig).toBe(false)
})

it('de brugbare står først — man leder efter hvad man kan gøre NU', () => {
  const p = sorteretTilVisning(byggeKontekster({
    ...grund, kameraTilladt: false, udklipHarTekst: false,
  }))
  expect(p.slice(0, 3).every((x) => x.tilgaengelig)).toBe(true)
  expect(p.slice(3).every((x) => !x.tilgaengelig)).toBe(true)
})

it('rækkefølgen inden for hver gruppe bevares, så knapper ikke hopper', () => {
  const p = sorteretTilVisning(byggeKontekster(grund))
  expect(p.map((x) => x.slags)).toEqual(['kamera', 'lokation', 'fil', 'udklip', 'enhed'])
})
