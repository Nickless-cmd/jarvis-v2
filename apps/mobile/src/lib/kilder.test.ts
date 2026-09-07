import { kilderFraBlokke, kilderPrDomaene, type KildeBlok } from './kilder'

describe('kilder fra blokke', () => {
  it('finder adressen i et web-hentnings-KALD', () => {
    const b: KildeBlok[] = [{ type: 'tool_use', name: 'web_fetch', input: { url: 'https://www.dr.dk/nyheder/artikel' } }]
    expect(kilderFraBlokke(b)).toEqual([{ url: 'https://www.dr.dk/nyheder/artikel', domaene: 'dr.dk' }])
  })

  it('finder adresser i et søge-RESULTAT', () => {
    // Det var halvdelen der forsvandt: en søgnings kilder står i resultatet,
    // ikke i kaldet, og den persisterede visning tegnede kun tool_use.
    const b: KildeBlok[] = [
      { type: 'tool_use', name: 'web_search', input: { query: 'proxmox lxc memory' } },
      { type: 'tool_result', content: 'Se https://pve.proxmox.com/wiki/LXC og https://forum.proxmox.com/t/123' }
    ]
    expect(kilderFraBlokke(b).map((k) => k.domaene)).toEqual(['pve.proxmox.com', 'forum.proxmox.com'])
  })

  it('tager svarteksten med — men EFTER det han faktisk hentede', () => {
    const b: KildeBlok[] = [{ type: 'tool_result', content: 'https://hentet.dk/side' }]
    const k = kilderFraBlokke(b, 'Jeg læste også https://citeret.dk/andet')
    expect(k.map((x) => x.domaene)).toEqual(['hentet.dk', 'citeret.dk'])
  })

  it('virker uden blokke — så en gammel besked ikke mister sine kilder', () => {
    expect(kilderFraBlokke(null, 'se https://dr.dk/x').map((k) => k.domaene)).toEqual(['dr.dk'])
    expect(kilderFraBlokke(undefined)).toEqual([])
  })
})

describe('støj holdes ude', () => {
  it('hans eget maskineri er ikke en kilde', () => {
    // Uden det ville hver eneste tur vise 10.0.0.39 og localhost som «kilder».
    const b: KildeBlok[] = [{ type: 'tool_result', content:
      'http://localhost:8080/x http://10.0.0.39/api https://127.0.0.1 https://192.168.1.1 https://ægte.dk/y' }]
    // Danske domæner vises læsbart: React Natives URL-polyfill punycode-koder
    // ikke værtsnavnet, og det er det rigtige for en visning et menneske læser.
    expect(kilderFraBlokke(b).map((k) => k.domaene)).toEqual(['ægte.dk'])
  })

  it('afsluttende tegnsætning hører ikke til adressen', () => {
    const b: KildeBlok[] = [{ type: 'tool_result', content: 'Kilde: (https://dr.dk/nyt), og https://tv2.dk/x.' }]
    expect(kilderFraBlokke(b).map((k) => k.url)).toEqual(['https://dr.dk/nyt', 'https://tv2.dk/x'])
  })

  it('samme adresse tælles én gang', () => {
    const b: KildeBlok[] = [
      { type: 'tool_use', input: { url: 'https://dr.dk/a' } },
      { type: 'tool_result', content: 'https://dr.dk/a igen' }
    ]
    expect(kilderFraBlokke(b)).toHaveLength(1)
  })

  it('vrøvl der ligner en URL vælter ikke', () => {
    const b: KildeBlok[] = [{ type: 'tool_result', content: 'https://  og http://]]] og https://ok.dk' }]
    expect(kilderFraBlokke(b).map((k) => k.domaene)).toEqual(['ok.dk'])
  })
})

describe('kompakt visning', () => {
  it('ét punkt pr. domæne, første URL vinder', () => {
    const b: KildeBlok[] = [{ type: 'tool_result', content:
      'https://dr.dk/a https://dr.dk/b https://tv2.dk/c' }]
    const k = kilderPrDomaene(kilderFraBlokke(b))
    expect(k.map((x) => x.domaene)).toEqual(['dr.dk', 'tv2.dk'])
    expect(k[0]!.url).toBe('https://dr.dk/a')
  })

  it('skærer ved maks, så en tur med 40 opslag ikke fylder skærmen', () => {
    const mange = Array.from({ length: 20 }, (_, i) => `https://d${i}.dk/x`).join(' ')
    expect(kilderPrDomaene(kilderFraBlokke([{ type: 'tool_result', content: mange }]))).toHaveLength(6)
  })
})

describe('fund fra ÆGTE historik (7/9-2026)', () => {
  it('shell-syntaks klistret på en adresse hører ikke med', () => {
    // Målt i hans egen historik: en bash-kommando gav domænet
    // «apkcombo.com$(grep», fordi $ og ( ikke stoppede adressen.
    const b: KildeBlok[] = [{ type: 'tool_use', input: { command: 'curl https://apkcombo.com/x$(grep -c y)' } }]
    expect(kilderFraBlokke(b).map((k) => k.domaene)).toEqual(['apkcombo.com'])
  })

  it('hele 127-blokken er loopback, ikke kun 127.0.0.1', () => {
    const b: KildeBlok[] = [{ type: 'tool_result', content: 'http://127.0.0.1:8080 http://127.1.2.3 https://ude.dk' }]
    expect(kilderFraBlokke(b).map((k) => k.domaene)).toEqual(['ude.dk'])
  })

  it('en ægte research-tur giver de sider han faktisk hentede', () => {
    // Formen fra tur #114166: fem kilder i blokkene, NUL i svarteksten.
    // Præcis dét tilfælde viste den gamle «Kilder» ingenting for.
    const b: KildeBlok[] = [
      { type: 'tool_use', name: 'web_search', input: { query: 'tuya smart life app' } },
      { type: 'tool_result', content:
        'https://www.apkmirror.com/a https://tuya.com/b https://smartapp.tuya.com/c https://play.google.com/d' }
    ]
    const k = kilderPrDomaene(kilderFraBlokke(b, 'Her er hvad jeg fandt.'))
    expect(k.map((x) => x.domaene)).toEqual(['apkmirror.com', 'tuya.com', 'smartapp.tuya.com', 'play.google.com'])
  })
})
