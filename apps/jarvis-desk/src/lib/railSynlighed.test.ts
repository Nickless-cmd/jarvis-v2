import { describe, it, expect, vi, afterEach } from 'vitest'
import { tilgaengeligBredde, erDerPladsTilSkinnen, SKINNE_MIN_BREDDE } from './railSynlighed'

/**
 * Skinnen maa ikke laegge sig hen over samtalen i en smal rude (spec punkt 3.5).
 *
 * Det vigtige er HVAD der maales: transcriptets egen tilgaengelige bredde, ikke
 * vinduets. Aabner man kode-panelet krymper transcriptet uden at vinduet roerer
 * sig — en `@media`-regel ville svare rigtigt i et maksimeret vindue og
 * forkert praecis naar panelet er aabent.
 */

function element(clientWidth: number, padL = '24px', padR = '24px'): HTMLElement {
  const el = document.createElement('div')
  Object.defineProperty(el, 'clientWidth', { value: clientWidth, configurable: true })
  vi.spyOn(window, 'getComputedStyle').mockReturnValue(
    { paddingLeft: padL, paddingRight: padR } as unknown as CSSStyleDeclaration)
  return el
}

describe('skinnens synlighed', () => {
  afterEach(() => { vi.restoreAllMocks() })

  it('den vandrette padding traekkes fra — 48 px er ikke ingenting her', () => {
    // `.transcript` har `padding: 32px 24px 8px`. Maalte man paa clientWidth,
    // laa graensen 48 px forkert, og det er praecis i det interval hvor
    // skinnen begynder at genere.
    expect(tilgaengeligBredde(element(1000))).toBe(952)
    expect(tilgaengeligBredde(element(1000, '0px', '0px'))).toBe(1000)
  })

  it('asymmetrisk padding taelles hver for sig', () => {
    expect(tilgaengeligBredde(element(1000, '40px', '8px'))).toBe(952)
  })

  it('et manglende element giver 0 og ikke et crash', () => {
    expect(tilgaengeligBredde(null)).toBe(0)
  })

  it('en padding uden enhed eller med `auto` regnes som 0', () => {
    expect(tilgaengeligBredde(element(500, 'auto', ''))).toBe(500)
  })

  it('bredden kan ikke blive negativ', () => {
    expect(tilgaengeligBredde(element(10, '40px', '40px'))).toBe(0)
  })

  it('graensen er 900 og den er EKSKLUSIV', () => {
    // Hele tabellen, saa en mutation af operatoren ses.
    expect(erDerPladsTilSkinnen(SKINNE_MIN_BREDDE + 1)).toBe(true)
    expect(erDerPladsTilSkinnen(SKINNE_MIN_BREDDE)).toBe(false)
    expect(erDerPladsTilSkinnen(SKINNE_MIN_BREDDE - 1)).toBe(false)
  })

  it('0 betyder IKKE MAALT og skjuler ikke skinnen', () => {
    // Foerste frame, en skjult flade, jsdom: alle svarer 0. Skjulte vi paa
    // det, forsvandt skinnen praecis naar vi intet ved — og kom tilbage et
    // billede senere. Testen er ogsaa den kolde sti: foer layout er alt 0.
    expect(erDerPladsTilSkinnen(0)).toBe(true)
    expect(erDerPladsTilSkinnen(-5)).toBe(true)
    expect(erDerPladsTilSkinnen(tilgaengeligBredde(null))).toBe(true)
  })

  it('en rude paa 1000 px med transcriptets padding er UNDER graensen i praksis', () => {
    // 1000 - 48 = 952 > 900 -> vises. 940 - 48 = 892 -> skjules. Den
    // sammensatte regning er det testen skal fange, ikke de to dele hver for sig.
    expect(erDerPladsTilSkinnen(tilgaengeligBredde(element(1000)))).toBe(true)
    expect(erDerPladsTilSkinnen(tilgaengeligBredde(element(940)))).toBe(false)
  })
})
