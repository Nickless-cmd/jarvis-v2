import { SETTINGS_GRUPPER, SETTINGS_PUNKTER, matcherSoegning, settingsVaerdier } from './settingsGrupper'

// Bjørn 28/9-2026: «det skal være nemt og overskueligt og noget der fanger nye
// brugere og lad folk uden for stor teknisk viden kunne finde ud af menu».
// Rækkefølgen ER svaret på det, så den skal være låst — ikke overladt til
// tilfældig omrokering næste gang nogen rører skærmen.

const punkt = (id: string) =>
  SETTINGS_GRUPPER.flatMap((g) => g.punkter).find((p) => p.id === id)!

describe('indstillingernes grupper', () => {
  it('har fire grupper i den rækkefølge brugeren møder dem', () => {
    expect(SETTINGS_GRUPPER.map((g) => g.navn)).toEqual([
      'Jarvis',
      'Sanser & privatliv',
      'Forbindelser',
      'Data & konto'
    ])
  })

  /**
   * Avanceret er en RÆKKE, ikke en femte gruppe.
   *
   * Som gruppe stod teknikken side om side med «lys eller mørk» igen — bare
   * med en overskrift over. Som række i bunden af «Data & konto» er den ét
   * punkt blandt tolv, og det den indeholder fylder ikke for en ny bruger.
   */
  it('Avanceret er sidste RÆKKE, ikke en gruppe', () => {
    expect(SETTINGS_GRUPPER.map((g) => g.navn)).not.toContain('Avanceret')
    expect(SETTINGS_PUNKTER[SETTINGS_PUNKTER.length - 1]).toBe('avanceret')
  })

  it('lægger det basale før det tekniske', () => {
    // Det var hele problemet: Udseende lå som niende sektion, efter teknikken.
    const i = SETTINGS_PUNKTER
    expect(i.indexOf('udseende')).toBeLessThan(i.indexOf('avanceret'))
    expect(i.indexOf('hukommelse')).toBeLessThan(i.indexOf('avanceret'))
    expect(i.indexOf('udseende')).toBe(0)
  })

  it('hvert punkt vises præcis én gang', () => {
    expect(new Set(SETTINGS_PUNKTER).size).toBe(SETTINGS_PUNKTER.length)
  })

  /** Hver række skal kunne tegnes: den har et navn man læser og et ikon der
   *  gør den genkendelig på et halvt sekund. */
  it('hvert punkt har et navn og et ikon', () => {
    for (const g of SETTINGS_GRUPPER) {
      for (const p of g.punkter) {
        expect(p.navn.trim().length).toBeGreaterThan(0)
        expect(p.ikon.trim().length).toBeGreaterThan(0)
      }
    }
  })

  it('to punkter deler ikke ikon — så ville ikonet ikke skelne', () => {
    const ikoner = SETTINGS_GRUPPER.flatMap((g) => g.punkter.map((p) => p.ikon))
    expect(new Set(ikoner).size).toBe(ikoner.length)
  })
})

describe('søgningen', () => {
  it('tom søgning viser alt', () => {
    expect(matcherSoegning(punkt('udseende'), '')).toBe(true)
    expect(matcherSoegning(punkt('udseende'), '   ')).toBe(true)
  })

  it('søger på brugerens ord, ikke på kode-navne', () => {
    expect(matcherSoegning(punkt('hukommelse'), 'husker')).toBe(true)
    expect(matcherSoegning(punkt('udseende'), 'mørk')).toBe(true)
    expect(matcherSoegning(punkt('udseende'), 'MØRK')).toBe(true)
    expect(matcherSoegning(punkt('udseende'), 'diagnostik')).toBe(false)
  })

  /** Det man LÆSER på rækken skal også kunne søges — ellers ville «Kamera»
   *  ikke ramme den række der hedder «Kamera & mikrofon». */
  it('rækkens eget navn er med i søgningen', () => {
    expect(matcherSoegning(punkt('sanser'), 'kamera')).toBe(true)
    expect(matcherSoegning(punkt('data'), 'dine data')).toBe(true)
  })

  /** Teknikken er ikke VÆK — den er samlet. Søger man på den, skal den findes,
   *  også selv om den bor bag Avanceret. */
  it('det tekniske kan stadig findes ved søgning', () => {
    for (const ord of ['diagnostik', 'boble', 'tankestrøm', 'api']) {
      expect(matcherSoegning(punkt('avanceret'), ord)).toBe(true)
    }
  })

  it('«mikrofon» finder rækken selv om den bor under Sanser', () => {
    const traef = SETTINGS_GRUPPER
      .flatMap((g) => g.punkter)
      .filter((p) => matcherSoegning(p, 'mikrofon'))
    expect(traef.map((p) => p.id)).toEqual(['sanser'])
  })
})

describe('værdien på rækken', () => {
  const kilde = (o: Partial<Parameters<typeof settingsVaerdier>[0]> = {}) =>
    settingsVaerdier({
      temaTilstand: 'dark', sprog: 'da', svarstil: 'Rolig', kameraLyd: true,
      lokation: 'off', batteriSparer: false, aktiveTjenester: 3,
      pushTil: true, antalEnheder: 2, ...o,
    })

  /** Præcis de ord der står i forlægget. En «forkert indstilling kan ses med
   *  ét blik» kun hvis ordet siger hvad der er valgt. */
  it('viser forlæggets ord', () => {
    const v = kilde()
    expect(v.udseende).toBe('Mørk')
    expect(v.sprog).toBe('Dansk')
    expect(v.svarstil).toBe('Rolig')
    expect(v.lokation).toBe('Slukket')
    expect(v.tjenester).toBe('3 aktive')
    expect(v.notifikationer).toBe('Til')
    expect(v.enheder).toBe('2')
    expect(v.avanceret).toBe('Diagnostik m.m.')
  })

  it('følger tilstanden', () => {
    expect(kilde({ temaTilstand: 'light' }).udseende).toBe('Lys')
    expect(kilde({ temaTilstand: 'auto' }).udseende).toBe('Automatisk')
    expect(kilde({ sprog: 'en' }).sprog).toBe('English')
    expect(kilde({ lokation: 'precise' }).lokation).toBe('Præcis')
    expect(kilde({ batteriSparer: true }).batteri).toBe('Til')
    expect(kilde({ pushTil: false }).notifikationer).toBe('Fra')
  })

  /**
   * «Ved ikke endnu» må IKKE blive til et tal.
   *
   * Mens tjenesterne hentes ville `0 aktive` være et regulært forkert svar —
   * og det er værre end ingen værdi, fordi det ligner en oplysning. Derfor
   * bærer kilden `null` for «ikke hentet» og ikke bare 0.
   */
  it('viser ingenting frem for et forkert tal mens der hentes', () => {
    expect(kilde({ aktiveTjenester: null }).tjenester).toBe('')
    expect(kilde({ pushTil: null }).notifikationer).toBe('')
    expect(kilde({ svarstil: null }).svarstil).toBe('')
    // og nul tjenester ER en oplysning, når den er hentet
    expect(kilde({ aktiveTjenester: 0 }).tjenester).toBe('0 aktive')
  })

  it('rækker uden en værdi står bare med deres navn', () => {
    const v = kilde()
    expect(v.hukommelse).toBe('')
    expect(v.data).toBe('')
  })

  it('hvert punkt i strukturen har en værdi-nøgle', () => {
    const v = kilde()
    for (const id of SETTINGS_PUNKTER) expect(v).toHaveProperty(id)
  })

  it('sprog mangler → Automatisk, ikke tomt', () => {
    expect(kilde({ sprog: null }).sprog).toBe('Automatisk')
  })
})
